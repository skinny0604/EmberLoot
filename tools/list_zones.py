# -*- coding: utf-8 -*-
"""列出 zones.json 里的实例与 creature 数，并对照站点 /zones 列表。"""
import io, json, re, sys

sys.stdout.reconfigure(encoding="utf-8")

with io.open(r"D:\workspace\emberloot\tools\out\zones.json", "r", encoding="utf-8") as f:
    z = json.loads(f.read(), strict=False)

inst = {k: v for k, v in z.items() if "limit" in v}
print("total zones:", len(z), " instances:", len(inst))
for k, v in sorted(inst.items(), key=lambda kv: int(kv[0])):
    print(k, v.get("name_en"), "|", v.get("name_zh"), "| limit", v.get("limit"),
          "| creatures", len(v.get("creatures") or []))
