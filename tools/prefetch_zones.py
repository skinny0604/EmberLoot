# -*- coding: utf-8 -*-
"""Prefetch zone pages for crawl.py with keep-alive concurrency.

Writes tools/cache/zone_<zid>_en.html / _zh.html in the exact names crawl.py
expects, so `python crawl.py zones` afterwards runs fully from cache.

Usage: python prefetch_zones.py
"""
import io
import http.client
import json
import os
import re
import ssl
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOST = "database.emberveil.org"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", "cache")

_tls = threading.local()


def _get_conn():
    if getattr(_tls, "conn", None) is None:
        ctx = ssl.create_default_context()
        _tls.conn = http.client.HTTPSConnection(HOST, timeout=25, context=ctx)
    return _tls.conn


def _drop_conn():
    try:
        if getattr(_tls, "conn", None):
            _tls.conn.close()
    except Exception:
        pass
    _tls.conn = None


def http_get(path, zh=False):
    for attempt in range(3):
        try:
            c = _get_conn()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OneJudgeResearch/1.0",
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Accept-Encoding": "gzip",
                "Connection": "keep-alive",
            }
            if zh:
                headers["Cookie"] = "locale=zhCN"
            c.request("GET", path, headers=headers)
            r = c.getresponse()
            body = r.read()
            if r.getheader("Content-Encoding") == "gzip":
                body = __import__("gzip").decompress(body)
            return r.status, body
        except Exception:
            _drop_conn()
            time.sleep(0.5 + attempt)
    return 0, b""


def cache_path(name):
    return os.path.join(CACHE, name)


def have(name):
    p = cache_path(name)
    return os.path.exists(p) and os.path.getsize(p) > 0


def fetch_to(path_name, url_path, zh=False, force=False):
    """Download unless cached; write decoded text. Returns True on success."""
    if have(path_name) and not force:
        return True
    for attempt in range(4):
        code, body = http_get(url_path, zh=zh)
        if code == 200 and body:
            with open(cache_path(path_name), "wb") as f:
                f.write(body)
            return True
        time.sleep(1.0 + attempt * 2.0)
    return False


def main():
    # ---- 1. zone ids from /zones list pages (list itself also cached)
    ids = set()
    for page in range(1, 12):
        name = f"zones_list_p{page}.html"
        # 列表页强制刷新：站点会扩容（0.1.0 时 57 区 -> 现 76 区），旧缓存会漏新 zone
        ok = fetch_to(name, f"/zones?page={page}", force=True)
        if not ok:
            print(f"zones list page {page}: FETCH FAIL", flush=True)
            break
        html = open(cache_path(name), encoding="utf-8", errors="ignore").read()
        found = set(int(x) for x in re.findall(r'href="/zone/(\d+)"', html))
        new = found - ids
        ids |= found
        print(f"zones page {page}: +{len(new)} (total {len(ids)})", flush=True)
        if not new and page > 1:
            break
    ids = sorted(ids)
    print("zone ids:", len(ids), flush=True)

    # ---- 2. parallel prefetch zone pages en+zh (missing only)
    jobs = []
    for zid in ids:
        if not have(f"zone_{zid}_en.html"):
            jobs.append((f"zone_{zid}_en.html", f"/zone/{zid}", False))
        if not have(f"zone_{zid}_zh.html"):
            jobs.append((f"zone_{zid}_zh.html", f"/zone/{zid}", True))
    print("to prefetch:", len(jobs), flush=True)
    fails = []

    def work(j):
        name, url, zh = j
        return name, fetch_to(name, url, zh=zh)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        for n, (name, ok) in enumerate(ex.map(work, jobs), 1):
            if not ok:
                fails.append(name)
                print("FAIL", name, flush=True)
            if n % 40 == 0:
                print(f"prefetch {n}/{len(jobs)} ({n / max(time.time() - t0, 1):.1f}/s)",
                      flush=True)
    print(f"done in {time.time() - t0:.0f}s, fails: {len(fails)}", flush=True)

    # ---- 3. sanity: how many are instances
    n_inst = 0
    for zid in ids:
        en = cache_path(f"zone_{zid}_en.html")
        if not os.path.exists(en):
            continue
        h = open(en, encoding="utf-8", errors="ignore").read()
        if re.search(r"Player limit: \d+", h):
            n_inst += 1
    print(f"siteside instances: {n_inst}", flush=True)


if __name__ == "__main__":
    main()
