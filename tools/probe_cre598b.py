# -*- coding: utf-8 -*-
"""Deep-inspect creature 598: h1, panel sequence, rows ownership."""
import re, os, json

CACHE = r"D:\workspace\emberloot\tools\cache"
h = open(os.path.join(CACHE, "creature_598_en.html"), encoding="utf-8").read()
blob = "".join(json.loads(x) for x in
               re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', h))

# h1 heading
for m in list(re.finditer(r'"font-display text-2xl font-bold text-brand-\d+","children":"([^"]+)"', blob))[:2]:
    print("h1:", m.group(1))
for m in list(re.finditer(r'"font-display text-xl font-bold[^"]*","children":"([^"]+)"', blob))[:2]:
    print("h1x:", m.group(1))

# ordered h2 panel titles
titles = re.findall(r'\{"className":"mb-2 font-semibold text-neutral-300","children":"([^"]+)"\}', blob)
print("panels:", titles)

# how many row objects between rows@44343 and the terminator
start = blob.find('"rows":[')
end = blob.find('}],"labels"', start)
seg = blob[start + 7:end + 2]
rows = json.loads(seg)
print("first rows panel: %d rows, first=%s last=%s" % (
    len(rows), rows[0]["item"]["name"], rows[-1]["item"]["name"]))

# creature overlay name (different regex, safer)
m = re.search(r'"overlay":\[.{0,400}?"name":"([^"]+)"', blob)
print("overlay name:", m.group(1) if m else None)
