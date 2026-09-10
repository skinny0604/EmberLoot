# -*- coding: utf-8 -*-
"""统计 creatures 阶段还差多少页。"""
import json, os, sys, io

sys.stdout.reconfigure(encoding="utf-8")
OUT = r"D:\workspace\emberloot\tools\out"
CACHE = r"D:\workspace\emberloot\tools\cache"

zones = json.load(open(os.path.join(OUT, "zones.json"), encoding="utf-8"))
creatures = json.load(open(os.path.join(OUT, "creatures.json"), encoding="utf-8"))

todo = set()
for zid, z in zones.items():
    if "limit" in z:
        for c in z.get("creatures", []):
            todo.add(c["id"])

fetched = sum(1 for k, v in creatures.items() if v.get("fetched"))
cached_en = sum(1 for cid in todo
                if os.path.exists(os.path.join(CACHE, f"creature_{cid}_en.html")))
missing = [cid for cid in todo
           if not os.path.exists(os.path.join(CACHE, f"creature_{cid}_en.html"))]
print("todo creatures:", len(todo), "fetched rec:", fetched,
      "cached en:", cached_en, "missing:", len(missing))
print("sample missing:", missing[:10])
