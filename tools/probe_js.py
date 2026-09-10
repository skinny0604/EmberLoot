# -*- coding: utf-8 -*-
# Download JS chunks referenced by item page and grep for data fetch endpoints
import re, sys, io, os, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.makedirs(r'D:\workspace\emberloot\tools\cache\js', exist_ok=True)
s = open(r'D:\workspace\emberloot\tools\cache\item_19019.html', encoding='utf-8').read()
chunks = sorted(set(re.findall(r'/_next/static/chunks/[A-Za-z0-9_.%-]+\.js', s)))
for c in chunks:
    name = c.rsplit('/', 1)[1]
    p = r'D:\workspace\emberloot\tools\cache\js' + '\\' + name
    if not os.path.exists(p):
        subprocess.run(['curl.exe', '-s', '-o', p, 'https://database.emberveil.org' + c], check=True)
    sz = os.path.getsize(p)
    t = open(p, encoding='utf-8', errors='replace').read()
    hits = []
    for pat in [r'"/api/[^"]+"', r'"/db/[^"]+"', r'entry"', r'"\.rsc"', r'_rsc', r'NEXT_']:
        ms = re.findall(pat, t)
        if ms:
            hits.append((pat, len(ms)))
    print(name, sz, hits)
