# -*- coding: utf-8 -*-
"""对比有数据的 MC 页与空数据的 NAXX/BWL 页结构。"""
import io, re, sys

sys.stdout.reconfigure(encoding="utf-8")
for zid, tag in ((2717, "MC(有数据)"), (3456, "NAXX(空)")):
    p = rf"D:\workspace\emberloot\tools\cache\zone_{zid}_en.html"
    h = io.open(p, encoding="utf-8", errors="ignore").read()
    print(tag, zid, "bytes:", len(h))
    print("  loading shell:", h.count("loading"), " NEXT_HTTP_ERROR:", h.count("NEXT_HTTP_ERROR_FALLBACK"))
    # 找 notable creatures / boss 相关 i18n key 的实际渲染
    for kw in ("Notable creatures", "no_spawns_in_zone", '"bosses"', "Loot", "loot"):
        print("  ", kw, h.count(kw))
