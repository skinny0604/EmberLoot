# -*- coding: utf-8 -*-
import re, sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
s = open(r'D:\workspace\emberloot\EmberLoot\data.lua', encoding='utf-8').read()
ids = re.findall(r'^\s*\[(\d+)\] = \{"[^"]+","[^"]+",\d,"[^"]*"\},?$', s, re.M)
print('item rows:', len(ids))
uniq = set(ids)
print('unique ids:', len(uniq))
# save id list
with open(r'D:\workspace\emberloot\tools\out\item_ids.json', 'w', encoding='utf-8') as f:
    json.dump(sorted(int(i) for i in uniq), f)
print('saved item_ids.json')

d = json.load(open(r'D:\workspace\emberloot\tools\cache\proxy_5191.json', encoding='utf-8'))
dd = d['data']
print('sample 5191 keys w/ values:')
for k in ('name', 'item_level', 'required_level', 'stats', 'armor', 'damage', 'delay', 'spells', 'description', 'bonding', 'inventory_type', 'class', 'subclass_name'):
    print(' ', k, '=', str(dd.get(k))[:160])
