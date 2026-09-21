"""探测目标站点：robots.txt / sitemap 规模 / 首页可达性（只读，不存储）。"""
from __future__ import annotations

import re
import socket
import ssl
import urllib.request
from urllib.parse import urlparse

socket.setdefaulttimeout(20)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = "seo-audit-probe/1.0"


def get(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode("utf-8", errors="replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, "", dict(e.headers)
    except Exception as e:
        return None, str(e), {}


def main():
    base = "https://hbyagada.com"
    print("=" * 60)
    print("目标:", base)
    print("=" * 60)

    st, body, hdr = get(base + "/")
    print(f"\n首页 {base}/")
    print(f"  HTTP {st} | {len(body)} bytes | server: {hdr.get('Server', '?')}")
    print(f"  redirect: {hdr.get('Location', '-')}")

    st, body, hdr = get(base + "/robots.txt")
    print(f"\nrobots.txt -> HTTP {st}")
    if st == 200:
        lines = [l for l in body.splitlines() if l.strip() and not l.strip().startswith("#")]
        print("  " + "\n  ".join(lines[:25]))

    st, body, hdr = get(base + "/sitemap.xml")
    print(f"\nsitemap.xml -> HTTP {st}")
    if st == 200:
        locs = re.findall(r"<loc>(.*?)</loc>", body, re.S)
        print(f"  <loc> 总数: {len(locs)}")
        for u in locs[:15]:
            print("   -", u.strip())
        if len(locs) > 15:
            print(f"   ... 共 {len(locs)} 条")
        # 如果 sitemap 是索引，则列出子 sitemap
        subs = re.findall(r"<sitemap>\s*<loc>(.*?)</loc>", body, re.S)
        if subs:
            print(f"  子 sitemap: {len(subs)} 个")
            for s in subs:
                print("   *", s.strip())


if __name__ == "__main__":
    main()
