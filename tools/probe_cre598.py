# -*- coding: utf-8 -*-
"""Inspect creature 598 cached page: what is it, where do 288 rows come from."""
import re, os, json

CACHE = r"D:\workspace\emberloot\tools\cache"
p = os.path.join(CACHE, "creature_598_en.html")
h = open(p, encoding="utf-8").read()
blob = "".join(json.loads(x) for x in
               re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', h))
print("page bytes:", len(h), "blob:", len(blob))
print("404?", "Page not found" in h)

# all name/level pairs
for m in list(re.finditer(r'"name":"([^"]+)","level":"(\d+)","levelTemplate"', blob))[:3]:
    print("name/lvl:", m.group(1), m.group(2))

# what does "rows":[ look like — list every rows occurrence with its first 80 chars
for m in list(re.finditer(r'"rows":\[' , blob))[:6]:
    print("--- rows@%d: %s" % (m.start(), blob[m.start():m.start() + 160].replace("\n", " ")))

# the overlay name pattern (creature header)
m = re.search(r'"overlay":\[[^\]]*?\]\,(\{"name":"[^"]+"', blob) or re.search(r'overlay":\["\$","\$L1d",null,\{"name":"([^"]+)"', blob)
i = blob.find('"overlay"')
print("--- overlay ctx ---")
print(blob[i:i + 420] if i >= 0 else "no overlay")
