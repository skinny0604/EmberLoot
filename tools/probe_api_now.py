# -*- coding: utf-8 -*-
"""测试 /api/proxy/items JSON 端点当前可用性。"""
import http.client, ssl, json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ctx = ssl.create_default_context()
for attempt in range(3):
    try:
        c = http.client.HTTPSConnection("database.emberveil.org", timeout=20, context=ctx)
        c.request("GET", "/api/proxy/items/19019?locale=zhCN", headers={
            "User-Agent": "Mozilla/5.0", "Accept": "application/json", "Connection": "close",
        })
        r = c.getresponse()
        body = r.read()
        print("status", r.status, "bytes", len(body))
        if r.status == 200:
            d = json.loads(body).get("data")
            print("name:", (d or {}).get("name"))
        c.close()
        break
    except Exception as e:
        print("ERR", repr(e)[:90], flush=True)
