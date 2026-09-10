# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
s = open(r'D:\workspace\emberloot\tools\cache\item_167.html', encoding='utf-8').read()
print('len', len(s), 'tail:', repr(s[-120:]))
for key in ['Destiny', 'destiny', 'inv_sword_19', 'Loading', 'loading']:
    print(repr(key), [m.start() for m in re.finditer(re.escape(key), s)][:6])
# chunk js list
chunks = sorted(set(re.findall(r'/_next/static/chunks/[A-Za-z0-9_.%-]+\.js', s)))
print(len(chunks))
for c in chunks:
    print(c)
