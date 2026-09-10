# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
for name, pats in [('1053b4_4orxt3.js', [r'"/api/[^"]+"']),
                   ('0wgud9te3jn00.js', [r'.{140}entry".{200}']),
                   ('3m6c41j3u6e5p.js', [r'.{120}entry".{160}'])]:
    t = open(r'D:\workspace\emberloot\tools\cache\js' + '\\' + name, encoding='utf-8', errors='replace').read()
    for pat in pats:
        for m in re.finditer(pat, t):
            print(name, '>>', m.group(0)[:320].encode('gbk', 'replace').decode('gbk'))
            print('-' * 40)
