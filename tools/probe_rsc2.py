# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
s = open(r'D:\workspace\emberloot\tools\cache\item_167_rsc2.txt', encoding='utf-8').read()
print('len', len(s))
for key in ['"stats"', 'stats', 'quality', 'itemLevel', 'tooltip_html', 'Destiny', 'Destino']:
    i = s.find(key)
    print(repr(key), i)
i = s.find('stats')
print(s[max(0, i-1200):i+2500])
