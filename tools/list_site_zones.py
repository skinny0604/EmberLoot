# -*- coding: utf-8 -*-
"""解析当前站点 /zones 页的 76 个 zone 行，输出全部 id+名称顺序。"""
import io, re, sys, html as htmllib

sys.stdout.reconfigure(encoding="utf-8")
raw = io.open(r"D:\workspace\emberloot\tools\out\zones_page_now.html", "r", encoding="utf-8").read()
rows = re.findall(r'<a[^>]*href="/zone/(\d+)"[^>]*>(.{0,500}?)</a>', raw)
seen = []
for zid, inner in rows:
    txt = htmllib.unescape(re.sub(r"<[^>]+>", " ", inner))
    txt = re.sub(r"\s+", " ", txt).strip()
    seen.append((int(zid), txt))
for zid, txt in seen:
    print(zid, "|", txt)
print("total", len(seen))
