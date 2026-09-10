# -*- coding: utf-8 -*-
"""Crawl item details from database.emberveil.org /api/proxy/items/<id>.
- zhCN for all ids; enUS additionally when spells/description/set present.
- Raw JSON cached at tools/cache/items/<id>_<loc>.json (resume-safe).
- Compact detail written to tools/out/item_details.json at the end.
"""
import json, os, re, subprocess, sys, time, io, http.client, ssl, threading

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = 'https://database.emberveil.org/api/proxy/items/'
HOST = 'database.emberveil.org'
CACHE = r'D:\workspace\emberloot\tools\cache\items'
OUT = r'D:\workspace\emberloot\tools\out'
os.makedirs(CACHE, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

_tls = threading.local()

def _get_conn():
    if getattr(_tls, 'conn', None) is None:
        ctx = ssl.create_default_context()
        _tls.conn = http.client.HTTPSConnection(HOST, timeout=25, context=ctx)
    return _tls.conn

def _drop_conn():
    try:
        if getattr(_tls, 'conn', None):
            _tls.conn.close()
    except Exception:
        pass
    _tls.conn = None

def http_get(path):
    """GET with keep-alive; returns (status, body_bytes)."""
    for attempt in range(3):
        try:
            c = _get_conn()
            c.request('GET', path, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Cookie': 'locale=zhCN',
                'Accept': 'application/json, */*',
                'Connection': 'keep-alive',
            })
            r = c.getresponse()
            body = r.read()
            return r.status, body
        except Exception:
            _drop_conn()
            time.sleep(0.5 + attempt)
    return 0, b''

def fetch(url_path, path):
    for attempt in range(4):
        code, body = http_get(url_path)
        if code == 200 and body and len(body) > 10:
            with open(path, 'wb') as f:
                f.write(body)
            return True
        if code == 404:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('{"data": null}')
            return True
        time.sleep(1.0 + attempt * 2.0)
    return False

DMG_SCHOOL_ZH2EN = {
    '物理': 'Physical', '神圣': 'Holy', '火焰': 'Fire', '自然': 'Nature',
    '冰霜': 'Frost', '暗影': 'Shadow', '奥术': 'Arcane',
}
BOND_ZH2ID = {
    '拾取后绑定': 1, '拾取时绑定': 1, '装备后绑定': 2, '装备时绑定': 3,
    '使用后绑定': 3, '与账号绑定': 4,
}

def load(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f).get('data')
    except Exception:
        return None

def compact(d):
    if not d:
        return None
    det = {}
    if d.get('item_level'): det['il'] = d['item_level']
    if d.get('required_level'): det['rl'] = d['required_level']
    if d.get('class') and d['class'].get('id') is not None:
        det['c'] = d['class']['id']
        det['sc'] = d.get('subclass')
    if d.get('inventory_type'):
        det['inv'] = d['inventory_type']['id']
    b = d.get('bonding')
    if b:
        det['b'] = BOND_ZH2ID.get(b, b)  # id or raw zh fallback
    st = [[x['stat'], x['value']] for x in (d.get('stats') or [])]
    if st: det['st'] = st
    rs = [[x['school'], x['value']] for x in (d.get('resistances') or [])]
    if rs: det['rs'] = rs
    dg = [[x['min'], x['max'], DMG_SCHOOL_ZH2EN.get(x['school'], x['school'])]
          for x in (d.get('damage') or [])]
    if dg: det['dg'] = dg
    if d.get('armor'): det['ar'] = d['armor']
    if d.get('block'): det['bl'] = d['block']
    if d.get('delay'): det['dl'] = d['delay']
    if d.get('max_count') and d['max_count'] > 1: det['mc'] = d['max_count']
    if d.get('buy_price'): det['bp'] = d['buy_price']
    if d.get('sell_price'): det['sp'] = d['sell_price']
    if d.get('max_durability'): det['du'] = d['max_durability']
    if d.get('has_random_enchantment'): det['re'] = 1
    sp = [[x.get('trigger') or '', x.get('name') or '', x.get('description') or '',
           x.get('cooldown') or ''] for x in (d.get('spells') or [])]
    if sp: det['spx'] = sp  # zh, replaced by bilingual after en fetch
    if d.get('description'):
        det['dx_zh'] = d['description']
    if d.get('set') and isinstance(d['set'], dict) and d['set'].get('name'):
        det['set_zh'] = d['set'].get('name')
        det['set_id'] = d['set'].get('id')
    return det

def need_en(det):
    return bool(det and (det.get('spx') or det.get('dx_zh') or det.get('set_zh')))

def en_annotate(det, e):
    """Merge enUS names/descriptions into detail (from raw zh-compat structure)."""
    if not e:
        return
    if e.get('description'):
        det['dx_en'] = e['description']
    if e.get('set') and isinstance(e['set'], dict) and e['set'].get('name'):
        det['set_en'] = e['set']['name']
    sp = e.get('spells') or []
    if sp and det.get('spx') and len(sp) == len(det['spx']):
        for z, x in zip(det['spx'], sp):
            # z = [trig_zh, name_zh, desc_zh, cooldown]
            z.insert(1, x.get('name') or '')   # -> [trig, name_en, name_zh, ...]
            z.insert(3, x.get('description') or '')
            # final: [trig, name_en, name_zh, desc_en, desc_zh, cooldown]

def main():
    from concurrent.futures import ThreadPoolExecutor
    ids = json.load(open(os.path.join(OUT, 'item_ids.json')))
    total = len(ids)
    print('items:', total, flush=True)

    # ---- phase 1: parallel download missing zh
    missing = [i for i in ids if not os.path.exists(os.path.join(CACHE, '%d_zh.json' % i))]
    print('zh missing:', len(missing), flush=True)
    fails = []
    def dl(pair):
        iid, loc, path = pair
        return (iid, loc, fetch('/api/proxy/items/%d?locale=%s' % (iid, loc), path))
    with ThreadPoolExecutor(max_workers=8) as ex:
        for n, (iid, loc, ok) in enumerate(ex.map(dl, [(i, 'zhCN', os.path.join(CACHE, '%d_zh.json' % i)) for i in missing]), 1):
            if not ok:
                fails.append(iid)
                print('FAIL zh', iid, flush=True)
            if n % 200 == 0:
                print('zh dl %d/%d' % (n, len(missing)), flush=True)
    print('zh done, fails:', len(fails), flush=True)

    # ---- phase 2: parse zh, decide en set
    details, stats = {}, {'zh': 0, 'en': 0, 'miss': 0, 'null': 0, 'fail': 0}
    need_en_ids = []
    for iid in ids:
        pz = os.path.join(CACHE, '%d_zh.json' % iid)
        if not os.path.exists(pz):
            stats['fail'] += 1
            continue
        dz = load(pz)
        if dz is None:
            try:
                null_hit = open(pz, encoding='utf-8').read().strip() == '{"data": null}'
            except Exception:
                null_hit = False
            if null_hit:
                stats['null'] += 1
            else:
                stats['miss'] += 1
                print('MISS', iid, flush=True)
            continue
        det = compact(dz)
        stats['zh'] += 1
        details[iid] = det
        if need_en(det):
            need_en_ids.append(iid)
    print('en needed:', len(need_en_ids), flush=True)

    # ---- phase 3: parallel download missing en
    miss_en = [i for i in need_en_ids if not os.path.exists(os.path.join(CACHE, '%d_en.json' % i))]
    print('en missing:', len(miss_en), flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        for n, (iid, loc, ok) in enumerate(ex.map(dl, [(i, 'enUS', os.path.join(CACHE, '%d_en.json' % i)) for i in miss_en]), 1):
            if not ok:
                print('FAIL en', iid, flush=True)
            if n % 200 == 0:
                print('en dl %d/%d' % (n, len(miss_en)), flush=True)

    # ---- phase 4: annotate
    for iid in need_en_ids:
        det = details.get(iid)
        if not det:
            continue
        en_annotate(det, load(os.path.join(CACHE, '%d_en.json' % iid)))
        stats['en'] += 1
    with open(os.path.join(OUT, 'item_details.json'), 'w', encoding='utf-8') as f:
        json.dump(details, f, ensure_ascii=False, separators=(',', ':'))
    print('DONE', stats, 'written item_details.json', flush=True)

if __name__ == '__main__':
    main()
