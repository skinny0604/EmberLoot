# -*- coding: utf-8 -*-
"""
EmberLoot data crawler for database.emberveil.org.

Stages (run in order, each resumes from cache):
  zones      - fetch /zones list, then every zone page (en+zh) -> zones.json
  creatures  - for each instance zone, fetch pinned creature pages (en+zh) -> creatures.json, drops.json
  lua        - emit compact Lua tables for the addon

Usage: python crawl.py zones|creatures|lua|all
"""
import http.client
import json
import gzip
import os
import re
import ssl
import subprocess
import sys
import threading
import time

BASE = "https://database.emberveil.org"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OneJudgeResearch/1.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", "cache")
OUT = os.path.join(ROOT, "tools", "out")
os.makedirs(CACHE, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

SLEEP = 0.4          # polite delay between requests (curl fallback path)
ZH = {"Cookie": "locale=zhCN"}          # localized payload cookie

_tls = threading.local()   # keep-alive 连接按线程隔离（共享连接不安全）


def _ka_get(url_path, zh=False, fresh=False):
    """GET；返回 (status, body_bytes)。fresh=True 时每次新建连接（本网络最稳）。
    fresh=False 时按线程复用连接，40 次后主动重建。"""
    for attempt in range(3):
        try:
            if fresh:
                ctx = ssl.create_default_context()
                conn = http.client.HTTPSConnection("database.emberveil.org",
                                                   timeout=20, context=ctx)
                _tls.uses = 0
            else:
                if getattr(_tls, "conn", None) is None:
                    ctx = ssl.create_default_context()
                    _tls.conn = http.client.HTTPSConnection("database.emberveil.org",
                                                            timeout=15, context=ctx)
                    _tls.uses = 0
                conn = _tls.conn
            headers = {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Accept-Encoding": "gzip",
                "Connection": "close" if fresh else "keep-alive",
            }
            if zh:
                headers["Cookie"] = "locale=zhCN"
            conn.request("GET", url_path, headers=headers)
            r = conn.getresponse()
            body = r.read()
            if r.getheader("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            if fresh:
                try:
                    conn.close()
                except Exception:
                    pass
            else:
                _tls.uses += 1
                if _tls.uses >= 40:
                    try:
                        _tls.conn.close()
                    except Exception:
                        pass
                    _tls.conn = None
            return r.status, body
        except Exception:
            try:
                if not fresh and getattr(_tls, "conn", None):
                    _tls.conn.close()
            except Exception:
                pass
            _tls.conn = None
            time.sleep(0.5 + attempt)
    return 0, b""


def fetch(url, out_name, zh=False, force=False):
    """fresh-connection http.client GET with on-disk cache. Returns (text, from_cache).

    网络实测（2026-09-10）：
    - curl.exe（Schannel 指纹）被 SNI 阻断，exit 35，几乎全灭 -> 不能用 curl
    - keep-alive 长连接会被中途静默掐断，线程挂在 read 超时 -> 不能复用连接
    - python http.client 每次新建连接（完整 TLS 握手）稳定，约 2-3s/请求
    """
    p = os.path.join(CACHE, out_name)
    if os.path.exists(p) and os.path.getsize(p) > 0 and not force:
        return open(p, encoding="utf-8", errors="ignore").read(), True
    path_q = url[len(BASE):] if url.startswith(BASE) else url
    for attempt in range(3):
        code, body = _ka_get(path_q, zh=zh, fresh=True)
        if code == 200 and body:
            with open(p, "wb") as f:
                f.write(body)
            return open(p, encoding="utf-8", errors="ignore").read(), False
        time.sleep(0.5 + attempt)
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
    p = os.path.join(OUT, path)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    tmp_check = len(json.load(open(tmp, encoding="utf-8")))
    os.replace(tmp, p)   # atomic: kill-safe
    verify = json.load(open(p, encoding="utf-8"))
    print(f"  [jsave] {os.path.abspath(p)} obj={len(obj)} tmp={tmp_check} size={os.path.getsize(p)} "
          f"reload={len(verify)}")


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
        key = str(zid)   # json 键一律字符串，避免 int/str 双键重复
        h_en, _ = fetch(f"{BASE}/zone/{zid}", f"zone_{zid}_en.html")
        blob_en = rsc_blob(h_en)
        info = zones.get(key, {"id": zid})
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
        zones[key] = info
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


def stage_creatures(workers=8):
    import concurrent.futures as cf
    import threading
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
    lock = threading.Lock()
    done = {"n": 0}
    # priority: elites/bosses first (rank>=1), rank-less trash last
    def prio(cid):
        zids = todo[cid]
        best = 0
        for zid in zids:
            for c in inst[zid].get("creatures", []):
                if c["id"] == cid and (c.get("rank_en") or c.get("rank_zh")):
                    best = max(best, 1)
        return -best
    ids = [cid for cid in sorted(todo)
           if not (str(cid) in creatures and creatures[str(cid)].get("fetched"))]
    ids.sort(key=prio)
    print(f"to fetch: {len(ids)} (skipping {len(todo) - len(ids)} cached)")

    def work(cid):
        h_en, _ = fetch(f"{BASE}/creature/{cid}", f"creature_{cid}_en.html")
        if not h_en:
            return cid, None, None
        meta = parse_creature_page(h_en)
        h_zh, _ = fetch(f"{BASE}/creature/{cid}", f"creature_{cid}_zh.html", zh=True)
        meta_zh = parse_creature_page(h_zh) if h_zh else {}
        return cid, meta, meta_zh

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for cid, meta, meta_zh in ex.map(work, ids):
            rec = {"id": cid, "name_en": (meta or {}).get("name"),
                   "name_zh": (meta_zh or {}).get("name"),
                   "level": (meta or {}).get("level"), "rank": (meta or {}).get("rank"),
                   "rank_en": (meta or {}).get("rank_name"),
                   "rank_zh": (meta_zh or {}).get("rank_name"),
                   "zones": todo[cid], "fetched": True}
            with lock:
                creatures[str(cid)] = rec
                if meta and "drops" in meta:
                    drops[str(cid)] = meta["drops"]
                if meta_zh and "drops" in meta_zh:
                    drops_zh[str(cid)] = meta_zh["drops"]
                done["n"] += 1
                n = done["n"]
                if n % 20 == 0:
                    jsave("creatures.json", creatures)
                    jsave("drops.json", drops)
                    jsave("drops_zh.json", drops_zh)
                print(f"  [{n}/{len(ids)}] {cid} {rec['name_en']} / {rec['name_zh']} "
                      f"L{rec.get('level')} rank={rec.get('rank')} "
                      f"drops={len(meta.get('drops', [])) if meta else 'FAIL'}")
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

    TRASH_BASE = 9000000   # 合成"区域小怪池"条目的 cid 前缀（9000000+zid）

    # ---- 按区瘦身：rank>=2 或 小表(<=50行) 保留个体；rank<=1 且大表合并成区域小怪池
    slim_creatures = {}   # cid -> record（含合成条目）
    slim_drops = {}       # cid -> rows（en）
    slim_drops_zh = {}
    zone_members = {}     # zid -> [cid,...]（EL_Zones 的生物表）
    for zid, z in sorted(inst.items()):
        members = []
        pool = {}          # entry -> merged row (best chance)
        pool_zh = {}
        for c in z.get("creatures", []):
            cid = str(c["id"])
            if cid not in drops or not drops[cid]:
                continue
            rec = creatures.get(cid, {})
            rank = rec.get("rank") or 0
            nrows = len(drops[cid])
            keep = rank >= 2 or nrows <= 50
            if keep:
                members.append(int(cid))
                if cid not in slim_creatures:
                    slim_creatures[cid] = rec
                    slim_drops[cid] = drops[cid]
                    slim_drops_zh[cid] = drops_zh.get(cid, [])
            else:
                zh_rows = {r["entry"]: r for r in drops_zh.get(cid, [])}
                for r in drops[cid]:
                    e = r["entry"]
                    cur = pool.get(e)
                    if cur is None or r["chance"] > cur["chance"]:
                        pool[e] = r
                        pool_zh[e] = zh_rows.get(e, r)
        synth = TRASH_BASE + int(zid)
        if pool:
            pooled = []
            for e, r in pool.items():
                pooled.append(r)
            pooled.sort(key=lambda r: r["entry"])
            slim_creatures[str(synth)] = {
                "id": synth, "name_en": "Zone Trash Pool", "name_zh": "区域小怪掉落池",
                "level": 0, "rank": 0, "zones": [int(zid)], "synthetic": True,
            }
            slim_drops[str(synth)] = pooled
            slim_drops_zh[str(synth)] = [pool_zh.get(r["entry"], r) for r in pooled]
            members.append(synth)
        zone_members[zid] = members

    # items: entry -> [name_en, name_zh, quality, icon]
    items = {}
    for cid, rows in slim_drops.items():
        zrows = slim_drops_zh.get(cid, [])
        zh_by_entry = {r["entry"]: r for r in zrows}
        for r in rows:
            e = r["entry"]
            if e not in items:
                zr = zh_by_entry.get(e, {})
                items[e] = {"n_en": r["name"], "n_zh": zr.get("name", r["name"]),
                            "q": r["quality"], "icon": r["icon"]}
            else:
                zr = zh_by_entry.get(e)
                if zr and items[e]["n_zh"] == items[e]["n_en"] and zr.get("name"):
                    items[e]["n_zh"] = zr["name"]

    lines = []
    lines.append("-- EmberLoot data v1 (generated by tools/crawl.py - do not edit)")
    lines.append("-- zones: {id, name_en, name_zh, player_limit, creatures{cid...}}")
    lines.append("EL_Zones = {")
    for zid, z in sorted(inst.items()):
        cids = zone_members.get(zid, [])
        if not cids:
            continue
        lines.append(f'  [{zid}] = {{{lua_str(z.get("name_en","?"))},{lua_str(z.get("name_zh","?"))},'
                     f'{z.get("limit",0)},{{{",".join(map(str, cids))}}}}},')
    lines.append("}")
    lines.append("-- creatures: cid -> {name_en, name_zh, level, rank, zoneIds...}")
    lines.append("EL_Creatures = {")
    for cid_s, c in sorted(slim_creatures.items(), key=lambda kv: int(kv[0])):
        if cid_s not in slim_drops:
            continue
        zl = ",".join(str(z) for z in c.get("zones", []))
        lines.append(f'  [{cid_s}] = {{{lua_str(c.get("name_en") or "?")},{lua_str(c.get("name_zh") or "?")},'
                     f'{c.get("level") or 0},{c.get("rank") or 0},{{{zl}}}}},')
    lines.append("}")
    lines.append("-- drops: cid -> rows {entry, chance, group, min, max, quest}")
    lines.append("EL_Drops = {")
    n_rows = 0
    for cid_s, rows in sorted(slim_drops.items(), key=lambda kv: int(kv[0])):
        cells = []
        for r in rows:
            cells.append(f'{{{r["entry"]},{r["chance"]},{r["group"] or 0},{r["min"]},{r["max"]},'
                         f'{"1" if r["quest"] else "0"}}}')
        n_rows += len(rows)
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
    n_trash = sum(1 for c in slim_creatures.values() if c.get("synthetic"))
    print(f"data.lua written: {kb} KB, {len(inst)} instances, {len(items)} items, "
          f"{len(slim_drops)} creatures ({n_trash} synthetic trash pools), {n_rows} drop rows")


# ---------------------------------------------------------------- main

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("zones", "all"):
        stage_zones()
    if stage in ("creatures", "all"):
        stage_creatures()
    if stage in ("lua", "all"):
        stage_lua()
