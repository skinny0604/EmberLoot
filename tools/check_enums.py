# -*- coding: utf-8 -*-
"""List distinct enum-ish values in item_details.json so addon dictionaries can be checked."""
import json, sys, io
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

d = json.load(open(r'D:\workspace\emberloot\tools\out\item_details.json', encoding='utf-8'))
print('items with details:', len(d))

stats, ress, dmgs, trigs, bonds, cs, invs, keys = (Counter() for _ in range(8))
for iid, det in d.items():
    for k in det:
        keys[k] += 1
    for x in det.get('st') or []:
        stats[x[0]] += 1
    for x in det.get('rs') or []:
        ress[x[0]] += 1
    for x in det.get('dg') or []:
        dmgs[x[2]] += 1
    for x in det.get('spx') or []:
        trigs[x[0]] += 1
    b = det.get('b')
    if b is not None:
        bonds[repr(b)] += 1
    if 'c' in det:
        cs[(det['c'], det.get('sc'), det.get('inv'))] += 1
    invs[det.get('inv')] += 1

print('--- detail keys:', dict(keys))
print('--- stat keys:', dict(stats))
print('--- res keys:', dict(ress))
print('--- dmg schools:', dict(dmgs))
print('--- triggers:', dict(trigs))
print('--- bonding:', dict(bonds))
print('--- inv types:', dict(invs))
print('--- (class, subclass) pairs:')
combo = Counter((c, s) for (c, s, _) in cs)
for (c, s), n in sorted(combo.items()):
    print('   c=%s sc=%s n=%d' % (c, s, n))
