# -*- coding: utf-8 -*-
import re, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
d = r'D:\workspace\emberloot\tools\cache\js'
for name in os.listdir(d):
    t = open(os.path.join(d, name), encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'apiFetch', t):
        a, b = max(0, m.start() - 80), m.start() + 900
        seg = t[a:b].replace('\n', ' ')
        print(name, '@', m.start())
        print(seg[:980].encode('gbk', 'replace').decode('gbk'))
        print('=' * 60)
