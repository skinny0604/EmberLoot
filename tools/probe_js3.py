# -*- coding: utf-8 -*-
import re, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
d = r'D:\workspace\emberloot\tools\cache\js'
for name in os.listdir(d):
    t = open(os.path.join(d, name), encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'tooltip', t):
        a, b = max(0, m.start() - 150), m.start() + 150
        seg = t[a:b]
        if 'fetch' in seg or 'api' in seg or 'url' in seg or '/' in seg:
            print(name, '>>', seg.replace('\n', ' ')[:300].encode('gbk', 'replace').decode('gbk'))
            print('-' * 50)
