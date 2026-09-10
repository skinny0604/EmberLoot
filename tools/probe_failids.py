# -*- coding: utf-8 -*-
"""逐个探测失败 id 的真实状态码。"""
import http.client, gzip, ssl, sys, io, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ids = [6145, 2110, 9257, 10470, 11517]
ctx = ssl.create_default_context()
for cid in ids:
    for attempt in range(2):
        try:
            c = http.client.HTTPSConnection("database.emberveil.org", timeout=20, context=ctx)
            c.request("GET", f"/creature/{cid}", headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OneJudgeResearch/1.0",
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Accept-Encoding": "gzip", "Connection": "close",
            })
            r = c.getresponse()
            body = r.read()
            if r.getheader("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            print(cid, r.status, len(body), flush=True)
            c.close()
            break
        except Exception as e:
            print(cid, "ERR", repr(e)[:80], flush=True)
            time.sleep(1)
