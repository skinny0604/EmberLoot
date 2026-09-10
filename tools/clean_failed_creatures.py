# -*- coding: utf-8 -*-
"""清理 creatures.json 里的失败记录：
- 无 en 缓存文件 -> 网络失败，删除记录让 stage_creatures 重试
- 有 en 缓存文件但 notfound -> 站点空页，保留记录跳过（重跑不会再抓）
"""
import json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
OUT = r"D:\workspace\emberloot\tools\out"
CACHE = r"D:\workspace\emberloot\tools\cache"

p = os.path.join(OUT, "creatures.json")
creatures = json.load(open(p, encoding="utf-8"))
n_retry, n_stub = 0, 0
for cid, rec in list(creatures.items()):
    if not rec.get("fetched") or rec.get("name_en"):
        continue
    en_cache = os.path.join(CACHE, f"creature_{cid}_en.html")
    if os.path.exists(en_cache) and os.path.getsize(en_cache) > 0:
        n_stub += 1          # 站点空页，保留
    else:
        del creatures[cid]   # 网络失败，重试
        n_retry += 1

with open(p, "w", encoding="utf-8") as f:
    json.dump(creatures, f, ensure_ascii=False, indent=1)
print(f"removed for retry: {n_retry}, kept stubs: {n_stub}, total now: {len(creatures)}")
