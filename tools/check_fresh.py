# -*- coding: utf-8 -*-
import re
h = open(r"D:\workspace\emberloot\tools\cache\zones_fresh.html", encoding="utf-8", errors="ignore").read()
ids = sorted(set(int(x) for x in re.findall(r'href="/zone/(\d+)"', h)))
print("fresh /zones: %d zone ids" % len(ids))
known = {1, 3, 4, 8, 10, 11, 12, 14, 15, 16, 17, 28, 33, 36, 38, 40, 41, 44, 45, 46, 47, 51, 85,
         130, 139, 141, 148, 215, 267, 331, 357, 361, 400, 405, 406, 440, 490, 493, 618, 796,
         1377, 1497, 1519, 1537, 1581, 1584, 1637, 1638, 1657, 2017, 2159, 2557, 2597, 2677,
         2717, 3277, 3358}
print("ids not in known 57:", [i for i in ids if i not in known])
