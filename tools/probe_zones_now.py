# -*- coding: utf-8 -*-
"""抓站点 /zones 列表页，统计 instance 类型与数量。"""
import io, json, re, sys, http.client, gzip

sys.stdout.reconfigure(encoding="utf-8")

_tls = http.client.HTTPSConnection("database.emberveil.org", timeout=30)
_tls.request("GET", "/zones", headers={
    "User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip",
    "Accept": "text/html",
})
r = _tls.getresponse()
raw = r.read()
if r.getheader("Content-Encoding") == "gzip":
    raw = gzip.decompress(raw)
html = raw.decode("utf-8", "replace")
io.open(r"D:\workspace\emberloot\tools\out\zones_page_now.html", "w", encoding="utf-8").write(html)
print("status", r.status, "bytes", len(html))

# 站点是 Next.js SSR：找 zone 行链接 /zone/<id> 及 instance 标记
ids = re.findall(r'href="/zone/(\d+)"', html)
print("zone links:", len(set(ids)))
# 页面里有没有 instance/battleground 字样
for kw in ("instance", "Instance", "battleground", "Battleground", "副本", "战场"):
    print(kw, html.count(kw))
