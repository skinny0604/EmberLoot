# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

s = open(r'D:\workspace\emberloot\tools\cache\quests81_p1.html', encoding='utf-8').read()
chunks = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', s)
buf = ''.join(chunks)

# context around first two /quest/ links
for m in list(re.finditer(r'/quest/(\d+)', buf))[:2]:
    a,b = max(0,m.start()-500), m.start()+500
    print('='*40)
    print(buf[a:b].encode('gbk','replace').decode('gbk'))

# total / pages hints
for pat in [r'"total_label[^}]{0,120}', r'共[^,\\]{0,40}', r'第[^,\\]{0,30}页', r'last_?[Pp]age[^,]{0,30}', r'"count[^,]{0,30}', r'page=2']:
    ms = re.findall(pat, buf)
    print(pat, '->', len(ms), ms[:6])
