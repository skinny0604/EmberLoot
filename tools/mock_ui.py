# -*- coding: utf-8 -*-
"""Render an EmberLoot window mock (PIL) from crawled data -> docs/preview.png."""
import json
import os
import subprocess
import sys
import urllib.parse

OUT = r"D:\workspace\emberloot\tools\out"
CACHE = r"D:\workspace\emberloot\tools\cache"
DOCS = r"D:\workspace\emberloot\docs"
ICON_DIR = os.path.join(CACHE, "icons")
os.makedirs(ICON_DIR, exist_ok=True)
os.makedirs(DOCS, exist_ok=True)

zones = json.load(open(os.path.join(OUT, "zones.json"), encoding="utf-8"))
creatures = json.load(open(os.path.join(OUT, "creatures.json"), encoding="utf-8"))
drops = json.load(open(os.path.join(OUT, "drops.json"), encoding="utf-8"))
drops_zh = json.load(open(os.path.join(OUT, "drops_zh.json"), encoding="utf-8"))

from PIL import Image, ImageDraw, ImageFont

def font(size):
    for p in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyh.ttf",
              r"C:\Windows\Fonts\simhei.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

QUALITY_HEX = {0: "#9d9d9d", 1: "#ffffff", 2: "#1eff00", 3: "#0070dd",
               4: "#a335ee", 5: "#ff8000", 6: "#e5cc80"}

# ---- aggregate Deadmines loot
ZID = "1581"
z = zones[ZID]
bosses = [c for c in z["creatures"] if str(c["id"]) in drops and drops[str(c["id"])]]
best = {}
for c in bosses:
    cid = str(c["id"])
    zh_rows = {r["entry"]: r for r in drops_zh.get(cid, [])}
    for r in drops[cid]:
        e = r["entry"]
        cur = best.get(e)
        if cur is None or r["chance"] > cur["chance"]:
            zh = zh_rows.get(e, {})
            best[e] = {"entry": e, "chance": r["chance"], "q": r["quality"],
                       "icon": r["icon"], "n_zh": zh.get("name", r["name"]),
                       "n_en": r["name"], "src_zh": c.get("name_zh") or c.get("name_en"), "src_cid": cid}
rows = sorted(best.values(), key=lambda d: (-d["q"], -d["chance"]))

# ---- download icons for the rows we render
def icon_path(icon):
    p = os.path.join(ICON_DIR, icon + ".png")
    if not os.path.exists(p):
        subprocess.run(["curl.exe", "-sL", "-m", "30",
                        f"https://database.emberveil.org/icons/small/{urllib.parse.quote(icon)}.png",
                        "-o", p], capture_output=True, text=True)
    return p if os.path.exists(p) else None

# ---- draw
W, H = 720, 540
ROW = 18
img = Image.new("RGB", (W, H), (18, 16, 14))
d = ImageDraw.Draw(img)
# outer border (gold-ish)
d.rectangle([0, 0, W - 1, H - 1], outline=(120, 96, 40), width=2)
d.rectangle([3, 3, W - 4, H - 4], outline=(70, 58, 28), width=1)
d.text((W // 2, 14), "EmberLoot 0.1.0", font=font(15), fill=(230, 200, 120), anchor="mm")

f_row = font(12)
f_small = font(11)

# left pane: boss list
lx, ly = 26, 84
d.line([(252, 84), (252, H - 40)], fill=(90, 74, 36), width=1)
d.text((lx, 62), "« 返回", font=f_small, fill=(200, 200, 200))
d.text((lx, 78), "死亡矿井 — 首领", font=font(13), fill=(255, 230, 150))
y = 100
sel = None
for c in bosses[:23]:
    cid = str(c["id"])
    nm = c.get("name_zh") or c.get("name_en") or "?"
    mark = "* " if (c.get("rank") or 0) >= 2 else ""
    color = (120, 255, 120) if cid == "639" else (255, 255, 215)
    d.text((lx + 4, y), f"{mark}{nm} L{c.get('level') or '?'}", font=f_row, fill=color)
    if cid == "639":
        sel = y
        d.rectangle([lx - 2, y - 1, lx + 218, y + ROW - 3], fill=(60, 60, 30))
        d.text((lx + 4, y), f"{mark}{nm} L{c.get('level') or '?'}", font=f_row, fill=(120, 255, 120))
    y += ROW
    if y > H - 50:
        break

# right pane: item rows for VanCleef
rx = 276
vc = drops["639"]
vc_zh = {r["entry"]: r for r in drops_zh.get("639", [])}
vrows = sorted(vc, key=lambda r: (-r["quality"], -r["chance"]))
y = 100
for r in vrows[:23]:
    zh = vc_zh.get(r["entry"], {})
    nm = zh.get("name", r["name"])
    chance = r["chance"]
    hexc = QUALITY_HEX.get(r["quality"], "#ffffff")
    p = icon_path(r["icon"])
    if p:
        try:
            ic = Image.open(p).convert("RGB").resize((14, 14))
            img.paste(ic, (rx + 2, y + 1))
        except Exception:
            pass
    d.rectangle([rx + 16, y, rx + 16 + 13 * len(nm) + 6, y + ROW - 3], fill=(18, 16, 14))
    d.text((rx + 18, y), nm, font=f_row, fill=hexc)
    d.text((W - 26, y), f"{chance:.0f}%", font=f_row, fill=(190, 190, 190), anchor="ra")
    y += ROW
    if y > H - 50:
        break

# status bar
d.text((22, H - 26), "艾德温·范克里夫 — 10 条掉落", font=f_small, fill=(200, 200, 200))
d.text((W - 100, 62), "品质:全部", font=f_small, fill=(210, 210, 210))
d.text((W - 175, 62), "收藏", font=f_small, fill=(210, 210, 210))
d.text((W - 215, 62), "中", font=f_small, fill=(210, 210, 210))

out_png = os.path.join(DOCS, "preview.png")
img.save(out_png)
print("saved", out_png, img.size, "| bosses:", len(bosses), "| vancleef rows:", len(vrows))
