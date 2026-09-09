# -*- coding: utf-8 -*-
"""Check BWL / DM / SM / Ony zone pages for creature links (proper script)."""
import re, os, json

CACHE = r"D:\workspace\emberloot\tools\cache"

def rsc_blob(h):
    return "".join(json.loads(p) for p in
                   re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', h))

for zid, name in [(2677, "BWL"), (2557, "DireMaul"), (796, "SM"), (2159, "Onyxia"), (1584, "BRD")]:
    h = open(os.path.join(CACHE, f"zone_{zid}_en.html"), encoding="utf-8").read()
    blob = rsc_blob(h)
    hrefs = sorted(set(re.findall(r"/creature/(\d+)", blob)))
    pins = re.findall(r'\{"href":"/creature/(\d+)","title":"([^"]+)"', blob)
    print(f"zone {zid} {name}: hrefs={len(hrefs)} pins={len(pins)} sample={[p[1] for p in pins[:4]]}")
