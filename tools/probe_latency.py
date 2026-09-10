# -*- coding: utf-8 -*-
"""探测单个 creature 页的响应时间与状态码。"""
import http.client, gzip, ssl, sys, time, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ctx = ssl.create_default_context()
for path in ("/creature/6145", "/creature/10257"):
    t0 = time.time()
    try:
        c = http.client.HTTPSConnection("database.emberveil.org", timeout=30, context=ctx)
        c.request("GET", path, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OneJudgeResearch/1.0",
            "Accept": "text/html,*/*", "Accept-Encoding": "gzip", "Connection": "keep-alive",
        })
        r = c.getresponse()
        body = r.read()
        if r.getheader("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        print(path, r.status, len(body), f"{time.time() - t0:.2f}s")
        c.close()
    except Exception as e:
        print(path, "ERR", repr(e), f"{time.time() - t0:.2f}s")
