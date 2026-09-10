# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
t = open(r'D:\workspace\emberloot\tools\cache\js\3m6c41j3u6e5p.js', encoding='utf-8', errors='replace').read()
# find the tooltip component: locate N?.error and the fetch that produces N
i = t.find('tooltip_loading')
seg = t[max(0, i - 3000):i + 3000]
print(seg.encode('gbk', 'replace').decode('gbk'))
