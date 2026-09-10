# -*- coding: utf-8 -*-
"""诊断：BWL/AQ/NAXX zone 页里 creature 引用长什么样。"""
import io, re, sys

sys.stdout.reconfigure(encoding="utf-8")
for zid in (2677, 3428, 3456):
    p = rf"D:\workspace\emberloot\tools\cache\zone_{zid}_en.html"
    h = io.open(p, encoding="utf-8", errors="ignore").read()
    refs = re.findall(r"/creature/(\d+)", h)
    pins = re.findall(r'\{"href":"/creature/(\d+)","title":"([^"]+)"', h)
    print(zid, "all refs:", len(set(refs)), "pins:", len(pins))
    # pin 附近的其他字段形状
    i = h.find('"mapPins"')
    print("  mapPins at:", i)
    for kw in ('"href":"/creature/', '"creaturePins"', '"spawns"', '"notable"'):
        print(" ", kw, h.count(kw))
    # 打一个 pin 上下文样本
    j = h.find('"href":"/creature/')
    if j >= 0:
        print("  sample:", h[j:j + 220])
