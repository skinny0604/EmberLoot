# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
t = open(r'D:\workspace\emberloot\tools\cache\js\1053b4_4orxt3.js', encoding='utf-8', errors='replace').read()
# find function r (apiFetch) and l (getUiStrings): search "function r(" or "r=" near CLIENT_BASE_URL; find 'fetch(' occurrences
for m in re.finditer(r'fetch\(', t):
    a, b = max(0, m.start() - 700), m.start() + 700
    print(t[a:b].replace('\n', ' ')[:1400].encode('gbk', 'replace').decode('gbk'))
    print('=' * 60)
