# -*- coding: utf-8 -*-
"""Verify Deadmines cached page parse counts."""
import re, os, json

CACHE = r"D:\workspace\emberloot\tools\cache"
p = os.path.join(CACHE, "zone_1581_en.html")
h = open(p, encoding="utf-8").read()
print("html bytes:", len(h))
pushes = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', h)
blob = "".join(json.loads(x) for x in pushes)
print("blob chars:", len(blob))
print("href matches:", len(re.findall(r"/creature/(\d+)", blob)))
print("unique:", len(set(re.findall(r"/creature/(\d+)", blob))))
pins = re.findall(r'\{"href":"/creature/(\d+)","title":"([^"]+)"', blob)
print("pins:", len(pins), pins[:3])
