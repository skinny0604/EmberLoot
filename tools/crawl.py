# -*- coding: utf-8 -*-
"""
EmberLoot data crawler for database.emberveil.org.

Stages (run in order, each resumes from cache):
  zones      - fetch /zones list, then every zone page (en+zh) -> zones.json
  creatures  - for each instance zone, fetch pinned creature pages (en+zh) -> creatures.json, drops.json
  lua        - emit compact Lua tables for the addon

Usage: python crawl.py zones|creatures|lua|all
"""
import json
import os
import re
import subprocess
import sys
import time

BASE = "https://database.emberveil.org"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OneJudgeResearch/1.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", "cache")
OUT = os.path.join(ROOT, "tools", "out")
os.makedirs(CACHE, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

SLEEP = 0.4          # polite delay between requests
ZH = {"Cookie": "locale=zhCN"}          # localized payload cookie


def fetch(url, out_name, zh=False, force=False):
    """curl with on-disk cache. Returns (text, from_cache)."""
    p = os.path.join(CACHE, out_name)
    if os.path.exists(p) and os.path.getsize(p) > 0 and not force:
        return open(p, encoding="utf-8", errors="ignore").read(), True
    cmd = ["curl.exe", "-sL", "-m", "60", "-A", UA, url, "-o", p]
    if zh:
        cmd += ["-H", "Cookie: locale=zhCN"]
    subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(p) and os.path.getsize(p) > 0:
        time.sleep(SLEEP)
        return open(p, encoding="utf-8", errors="ignore").read(), False
    return "", False


def rsc_blob(html_text):
    """Concat all self.__next_f.push([1,"..."]) chunks into one string."""
    pushes = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html_text)
    return "".join(json.loads(p) for p in pushes)


def jload(path, default):
    p = os.path.join(OUT, path)
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    return default


def jsave(path, obj):
    with open(os.path.join(OUT, path), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- zones

def stage_zones():
    zone_ids = set()
    for page in range(1, 12):
        html_z, cached = fetch(f"{BASE}/zones?page={page}", f"zones_list_p{page}.html")
        found = set(int(x) for x in re.findall(r'href="/zone/(\d+)"', html_z))
        new = found - zone_ids
        zone_ids |= found
        print(f"  zones page {page}: +{len(new)} (total {len(zone_ids)})")
        if not new and page > 1:
            break
        if not cached and not new:
            break
    zone_ids = sorted(zone_ids)
    print(f"zones list: {len(zone_ids)} zone ids")
    zones = jload("zones.json", {})
    for i, zid in enumerate(zone_ids):
        h_en, _ = fetch(f"{BASE}/zone/{zid}", f"zone_{zid}_en.html")
        blob_en = rsc_blob(h_en)
        info = zones.get(zid, {"id": zid})
        # zone name: first big display heading
        m = re.search(r'"font-display text-2xl font-bold text-brand-\d+","children":"([^"]+)"', blob_en)
        if m:
            info["name_en"] = m.group(1)
        # instance marker: rendered "Player limit: N"
        m = re.search(r'"children":\["Player limit: ",(\d+)\]', blob_en) or \
            re.search(r'Player limit: (\d+)', blob_en)
        if m:
            info["limit"] = int(m.group(1))
        # reset days (raids)
        m = re.search(r'Resets every (\d+) days', blob_en)
        if m:
            info["reset_days"] = int(m.group(1))
        # creature links: map pins (with names/ranks) + all creature hrefs (union)
        pins = re.findall(r'\{"href":"/creature/(\d+)","title":"([^"]+)"', blob_en)
        all_hrefs = re.findall(r'/creature/(\d+)', blob_en)
        pin_by_id = {}
        creatures = []
        for cid, title in pins:
            mm = re.match(r"^(.*?) \(([^)]+)\)$", title)
            if mm:
                pin_by_id[int(cid)] = {"id": int(cid), "name_en": mm.group(1), "rank_en": mm.group(2)}
            else:
                pin_by_id[int(cid)] = {"id": int(cid), "name_en": title, "rank_en": None}
        for cid in all_hrefs:
            cidi = int(cid)
            if cidi not in pin_by_id:
                pin_by_id[cidi] = {"id": cidi, "name_en": None, "rank_en": None}
        creatures = [pin_by_id[k] for k in sorted(pin_by_id)]
        # localized page for zh names
        h_zh, _ = fetch(f"{BASE}/zone/{zid}", f"zone_{zid}_zh.html", zh=True)
        blob_zh = rsc_blob(h_zh)
        m = re.search(r'"font-display text-2xl font-bold text-brand-\d+","children":"([^"]+)"', blob_zh)
        if m:
            info["name_zh"] = m.group(1)
        pins_zh = dict(re.findall(r'\{"href":"/creature/(\d+)","title":"([^"]+)"', blob_zh))
        for c in creatures:
            t = pins_zh.get(str(c["id"]), "")
            mm = re.match(r"^(.*?) \(([^)]+)\)$", t)
            if mm:
                c["name_zh"], c["rank_zh"] = mm.group(1), mm.group(2)
            else:
                c["name_zh"], c["rank_zh"] = t, None
        info["creatures"] = creatures
        zones[zid] = info
        inst = " [instance]" if "limit" in info else ""
        print(f"  [{i+1}/{len(zone_ids)}] {zid} {info.get('name_en','?')} / {info.get('name_zh','?')}"
              f"{inst} creatures={len(creatures)}")
    jsave("zones.json", zones)
    n_inst = sum(1 for z in zones.values() if "limit" in z)
    print(f"done: {len(zones)} zones, {n_inst} instances")


# ---------------------------------------------------------------- creatures/drops

def parse_creature_page(h):
    blob = rsc_blob(h)
    out = {}
    # overlay name (level may be a range like "19-20")
    m = re.search(r'"name":"([^"]+)","level":"([^"]*)","levelTemplate"', blob)
    if not m:
        m = re.search(r'"overlay":\[.{0,600}?"name":"([^"]+)"', blob)
        if m:
            out["name"] = m.group(1)
    else:
        out["name"] = m.group(1)
        mm = re.match(r"(\d+)", m.group(2))
        out["level"] = int(mm.group(1)) if mm else 0
    m = re.search(r'"rank":(\d+),"rankName":"([^"]+)"', blob)
    if m:
        out["rank"], out["rank_name"] = int(m.group(1)), m.group(2)
    if "name" not in out:
        out["notfound"] = True
        return out
    # drops rows: anchored to the creature_drop panel
    idx = blob.find('"creature_drop"')
    if idx >= 0:
        r0 = blob.find('"rows":["' if False else '"rows":[', idx)
        if r0 >= 0:
            r1 = blob.find('}],"labels"', r0)
            if r1 >= 0:
                try:
                    rows = json.loads(blob[r0 + 7:r1 + 2])
                    out["drops"] = [{
                        "entry": r["entry"],
                        "name": r["item"]["name"],
                        "icon": r["item"]["icon"],
                        "quality": r["item"]["quality"]["id"],
                        "chance": r["chance"],
                        "group": r.get("group_id"),
                        "min": r.get("min_count", 1),
                        "max": r.get("max_count", 1),
                        "quest": bool(r.get("requires_quest")),
                        "condition": r.get("condition"),
                    } for r in rows]
                except Exception as e:
                    out["drops_err"] = str(e)
    return out


def stage_creatures():
    zones = jload("zones.json", {})
    inst = {zid: z for zid, z in zones.items() if "limit" in z}
    todo = {}
    for zid, z in inst.items():
        for c in z.get("creatures", []):
            todo.setdefault(c["id"], []).append(zid)
    print(f"instances: {len(inst)}, pinned creatures: {len(todo)}")

    creatures = jload("creatures.json", {})   # cid -> meta (en/zh name, level, rank)
    drops = jload("drops.json", {})           # cid -> [drop rows en]
    drops_zh = jload("drops_zh.json", {})     # cid -> [drop rows zh]
    ids = sorted(todo)
    for i, cid in enumerate(ids):
        if str(cid) in creatures and creatures[str(cid)].get("fetched"):
            continue
        h_en, _ = fetch(f"{BASE}/creature/{cid}", f"creature_{cid}_en.html")
        if not h_en:
            print(f"  [{i+1}] {cid}: FETCH FAILED")
            continue
        meta = parse_creature_page(h_en)
        blob_en = rsc_blob(h_en)
        m = re.search(r'\{"href":"/creature/%d","title":"([^"]+)"' % cid, blob_en)
        h_zh, _ = fetch(f"{BASE}/creature/{cid}", f"creature_{cid}_zh.html", zh=True)
        meta_zh = parse_creature_page(h_zh) if h_zh else {}
        rec = {"id": cid, "name_en": meta.get("name"), "name_zh": meta_zh.get("name"),
               "level": meta.get("level"), "rank": meta.get("rank"),
               "rank_en": meta.get("rank_name"), "rank_zh": meta_zh.get("rank_name"),
               "zones": todo[cid], "fetched": True}
        creatures[str(cid)] = rec
        if "drops" in meta:
            drops[str(cid)] = meta["drops"]
        if "drops" in meta_zh:
            drops_zh[str(cid)] = meta_zh["drops"]
        nd = len(meta.get("drops", []))
        print(f"  [{i+1}/{len(ids)}] {cid} {rec['name_en']} / {rec['name_zh']} "
              f"L{rec.get('level')} rank={rec.get('rank')} drops={nd}")
        if (i + 1) % 20 == 0:
            jsave("creatures.json", creatures)
            jsave("drops.json", drops)
            jsave("drops_zh.json", drops_zh)
    jsave("creatures.json", creatures)
    jsave("drops.json", drops)
    jsave("drops_zh.json", drops_zh)
    total_rows = sum(len(v) for v in drops.values())
    items = set()
    for rows in drops.values():
        for r in rows:
            items.add(r["entry"])
    print(f"done: {len(creatures)} creatures, {total_rows} drop rows, {len(items)} unique items")


# ---------------------------------------------------------------- lua emit

def lua_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def stage_lua():
    zones = jload("zones.json", {})
    creatures = jload("creatures.json", {})
    drops = jload("drops.json", {})
    drops_zh = jload("drops_zh.json", {})
    inst = {zid: z for zid, z in zones.items() if "limit" in z and z.get("creatures")}

    # items: entry -> [name_en, name_zh, quality, icon]
    items = {}
    for cid, rows in drops.items():
        zrows = drops_zh.get(cid, [])
        zh_by_entry = {r["entry"]: r for r in zrows}
        for r in rows:
            e = r["entry"]
            if e not in items:
                zr = zh_by_entry.get(e, {})
                items[e] = {"n_en": r["name"], "n_zh": zr.get("name", r["name"]),
                            "q": r["quality"], "icon": r["icon"]}
            else:
                zr = zh_by_entry.get(e)
                if zr and items[e]["n_zh"] == items[e]["n_en"]:
                    items[e]["n_zh"] = zr["name"]

    lines = []
    lines.append("-- EmberLoot data v1 (generated by tools/crawl.py - do not edit)")
    lines.append("-- zones: {id, name_en, name_zh, player_limit, creatures{cid=priority}}")
    lines.append("EL_Zones = {")
    for zid, z in sorted(inst.items()):
        cids = [c["id"] for c in z["creatures"]
                if str(c["id"]) in creatures and str(c["id"]) in drops]
        if not cids:
            continue
        lines.append(f'  [{zid}] = {{{lua_str(z.get("name_en","?"))},{lua_str(z.get("name_zh","?"))},'
                     f'{z.get("limit",0)},{{{",".join(map(str, cids))}}}}},')
    lines.append("}")
    lines.append("-- creatures: cid -> {name_en, name_zh, level, rank, zoneIds...}")
    lines.append("EL_Creatures = {")
    for cid_s, c in sorted(creatures.items(), key=lambda kv: int(kv[0])):
        if cid_s not in drops:
            continue
        zl = ",".join(str(z) for z in c.get("zones", []))
        lines.append(f'  [{cid_s}] = {{{lua_str(c.get("name_en") or "?")},{lua_str(c.get("name_zh") or "?")},'
                     f'{c.get("level") or 0},{c.get("rank") or 0},{{{zl}}}}},')
    lines.append("}")
    lines.append("-- drops: cid -> rows {entry, chance, group, min, max, quest}")
    lines.append("EL_Drops = {")
    for cid_s, rows in sorted(drops.items(), key=lambda kv: int(kv[0])):
        cells = []
        for r in rows:
            cells.append(f'{{{r["entry"]},{r["chance"]},{r["group"] or 0},{r["min"]},{r["max"]},'
                         f'{"1" if r["quest"] else "0"}}}')
        lines.append(f'  [{cid_s}] = {{{",".join(cells)}}},')
    lines.append("}")
    lines.append("-- items: entry -> {name_en, name_zh, quality, icon}")
    lines.append("EL_Items = {")
    for e, it in sorted(items.items()):
        lines.append(f'  [{e}] = {{{lua_str(it["n_en"])},{lua_str(it["n_zh"])},{it["q"]},{lua_str(it["icon"])}}},')
    lines.append("}")

    out_path = os.path.join(ROOT, "EmberLoot", "data.lua")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    kb = os.path.getsize(out_path) // 1024
    print(f"data.lua written: {kb} KB, {len(inst)} instances, {len(items)} items")


# ---------------------------------------------------------------- main

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("zones", "all"):
        stage_zones()
    if stage in ("creatures", "all"):
        stage_creatures()
    if stage in ("lua", "all"):
        stage_lua()
