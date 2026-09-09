# -*- coding: utf-8 -*-
"""Strict reconciliation of zones.json on disk vs crawler runtime."""
import json, os, sys
sys.path.insert(0, r"D:\workspace\emberloot\tools")
import crawl

p = os.path.join(crawl.OUT, "zones.json")
print("crawl.OUT =", crawl.OUT)
print("exists:", os.path.exists(p), "size:", os.path.getsize(p) if os.path.exists(p) else "-")
z = json.load(open(p, encoding="utf-8"))
inst = {k: v for k, v in z.items() if isinstance(v, dict) and "limit" in v}
print("on disk: zones=%d instances=%d" % (len(z), len(inst)))
newz = [k for k in z if int(k) not in (1, 3, 4, 8, 10, 11, 12, 14, 15, 16, 17, 28, 33, 36, 38, 40, 41, 44, 45, 46, 47, 51, 85, 130, 139, 141, 148, 215, 267, 331, 357, 361, 400, 405, 406, 440, 490, 493, 618, 796, 1377, 1497, 1519, 1537, 1581, 1584, 1637, 1638, 1657, 2017, 2159, 2557, 2597, 2677, 2717, 3277, 3358)]
print("sample of 'new' zone ids:", newz[:15])
