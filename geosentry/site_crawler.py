"""全站爬取层：sitemap 发现 + BFS 内链发现 + robots 门禁 + 限速，纯标准库。

与 docs/site-audit-hbyagada/crawl_audit.py 同口径，但通用化：
- 不硬编码 BASE 域名，由调用方传入 base_url
- robots 门禁：解析 User-agent 段，尊重 Disallow
- 限速（默认 1.2s/请求），gzip 解码，HTML 存 raw/
- PDF 用 GET 探测（content-type 判定）
- 纯 stdlib：urllib / gzip / html.parser / re
"""
from __future__ import annotations

import gzip
import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urldefrag, urljoin, urlparse

DEFAULT_UA = "Mozilla/5.0 (compatible; geosentry-site-audit/1.0)"
DEFAULT_DELAY = 1.2
DEFAULT_TIMEOUT = 25
MAX_BYTES = 3_000_000


@dataclass
class FetchResult:
    url: str
    status: Optional[int]
    final_url: str
    headers: dict = field(default_factory=dict)
    body: bytes = b""
    error: Optional[str] = None
    redirect_chain: list = field(default_factory=list)


class _RecordingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """记录重定向链 [[from, code, to], ...]，仍自动跟随。实例属性，线程安全。"""
    def __init__(self):
        self.chain = []
        super().__init__()

    def http_error_301(self, req, fp, code, msg, headers):
        self.chain.append([req.full_url, code, headers.get("Location", "")])
        return super().http_error_301(req, fp, code, msg, headers)

    http_error_302 = http_error_301
    http_error_303 = http_error_301
    http_error_307 = http_error_301
    http_error_308 = http_error_301


def http_get(url: str, ua: str = DEFAULT_UA, timeout: int = DEFAULT_TIMEOUT,
             delay: float = 0.0, verify_ssl: bool = True,
             extra_headers: dict = None) -> FetchResult:
    """GET 一个 URL，返回 FetchResult；gzip 自动解压。"""
    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    hdrs = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip",
    }
    if extra_headers:
        hdrs.update(extra_headers)
    req = urllib.request.Request(url, headers=hdrs)
    rh = _RecordingRedirectHandler()
    opener = urllib.request.build_opener(rh, urllib.request.HTTPSHandler(context=ctx))
    try:
        with opener.open(req, timeout=timeout) as r:
            body = r.read(MAX_BYTES)
            if r.headers.get("Content-Encoding") == "gzip":
                try:
                    body = gzip.decompress(body)
                except Exception:
                    pass
            if delay:
                time.sleep(delay)
            return FetchResult(url=r.geturl(), status=r.status, final_url=r.geturl(),
                               headers=dict(r.headers), body=body,
                               redirect_chain=rh.chain)
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read(1_000_000)
        except Exception:
            pass
        if delay:
            time.sleep(delay)
        return FetchResult(url=url, status=e.code, final_url=url,
                           headers=dict(e.headers or {}), body=body,
                           redirect_chain=rh.chain)
    except Exception as e:  # noqa: BLE001
        if delay:
            time.sleep(delay)
        return FetchResult(url=url, status=None, final_url=url, error=f"{type(e).__name__}: {e}",
                           redirect_chain=rh.chain)


def fetch_robots(base_url: str, ua: str = DEFAULT_UA, timeout: int = DEFAULT_TIMEOUT) -> str:
    """抓取 robots.txt 文本；失败返回空串（不视为禁止）。"""
    parts = urlparse(base_url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    res = http_get(robots_url, ua=ua, timeout=timeout)
    if res.status == 200 and res.body:
        return res.body.decode("utf-8", errors="replace")
    return ""


def robots_allows(robots_txt: str, url: str, ua_token: str = "*") -> bool:
    """简化 robots 门禁：解析 User-agent 段（按 * 或指定 token），
    检查 Disallow 前缀是否覆盖目标 path。无 robots.txt 视为允许。"""
    if not robots_txt:
        return True
    target_path = urlparse(url).path or "/"
    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None
    for raw in robots_txt.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"(?i)^user-agent:\s*(.+)$", line)
        if m:
            current = m.group(1).strip().lower()
            sections.setdefault(current, [])
            continue
        if current is None:
            continue
        md = re.match(r"(?i)^disallow:\s*(.*)$", line)
        if md:
            sections[current].append(md.group(1).strip())
    for sec in (ua_token.lower(), "*"):
        for path in sections.get(sec, ()):
            # 空 Disallow: 按 robots 规范表示"允许抓取所有内容"，不禁止；
            # 只有 Disallow: / 才是禁止全站。
            if path == "/":
                return False
            if path and target_path.startswith(path):
                return False
    return True


def _extract_sitemap_locs(text: str) -> List[str]:
    """从 sitemap XML 提取所有 <loc> URL。"""
    return [m.strip() for m in re.findall(r"<loc>\s*(.*?)\s*</loc>", text, re.S)]


def fetch_sitemap(base_url: str, ua: str = DEFAULT_UA, timeout: int = DEFAULT_TIMEOUT,
                  entry: Optional[str] = None) -> List[str]:
    """抓取 sitemap，递归解析 sitemapindex（如 Yoast 的 post/page-sitemap.xml），
    返回去重后的真实页面 URL 列表（保持顺序）。

    entry: 入口 sitemap URL（通常来自 robots.txt 的 Sitemap: 指令）；
           为 None 时回退到 <base>/sitemap.xml。
    """
    parts = urlparse(base_url)
    root = f"{parts.scheme}://{parts.netloc}"
    entry = entry or f"{root}/sitemap.xml"

    seen_sitemaps: set = set()
    page_urls: List[str] = []
    seen_pages: set = set()

    def _recurse(sm_url: str) -> None:
        if sm_url in seen_sitemaps:
            return
        seen_sitemaps.add(sm_url)
        res = http_get(sm_url, ua=ua, timeout=timeout)
        if res.status != 200 or not res.body:
            return
        text = res.body.decode("utf-8", errors="replace")
        locs = _extract_sitemap_locs(text)
        # <sitemapindex> 里含 <sitemap> 子节点 → 递归；
        # <urlset> 里的 <loc> 才是真实页面 URL。
        is_index = bool(re.search(r"<sitemap[\s>]", text))
        if is_index:
            for loc in locs:
                _recurse(loc)
        else:
            for loc in locs:
                if loc and loc not in seen_pages:
                    seen_pages.add(loc)
                    page_urls.append(loc)

    _recurse(entry)
    return page_urls


def slug(url: str) -> str:
    """URL path → 文件名 slug（与原 crawl_audit.py 一致）。"""
    u = urldefrag(url)[0]
    p = urlparse(u).path.strip("/")
    if not p:
        return "home"
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", p)[:80]


def probe_dead_links(candidates: List[str], robots_txt: str = "",
                     ua: str = DEFAULT_UA, delay: float = DEFAULT_DELAY,
                     timeout: int = DEFAULT_TIMEOUT, verify_ssl: bool = True,
                     max_probes: int = 50, external: bool = False,
                     base_url: str = "") -> List[dict]:
    """在线死链探测：对已知但未在 sitemap 里的内部 href 主动 GET，
    记录非 200 为死链。遵守 robots 门禁与限速，max_probes 防失控。
    返回 [{"url", "status", "final_url", "error"}]。"""
    from urllib.parse import urlparse
    host = urlparse(base_url).netloc if base_url else ""
    if external:
        delay = max(delay, 2.0)
    dead = []
    probed = 0
    for u in candidates:
        if probed >= max_probes:
            break
        if not external and host and urlparse(u).netloc and urlparse(u).netloc != host:
            continue
        if not robots_allows(robots_txt, u):
            continue
        probed += 1
        res = http_get(u, ua=ua, timeout=timeout, delay=delay,
                       verify_ssl=verify_ssl)
        if res.status != 200:
            dead.append({
                "url": u, "status": res.status, "final_url": res.final_url,
                "error": res.error,
            })
    return dead


def probe_404(base_url: str, ua: str = DEFAULT_UA,
              delay: float = DEFAULT_DELAY, timeout: int = DEFAULT_TIMEOUT,
              verify_ssl: bool = True) -> dict:
    """软 404 探测：GET 一个随机不存在路径。
    返回 dict: {soft_404, body_len, has_home_link, tested_url, status}
    - soft_404: True = 返回 200（软 404，失败）
    - body_len: 404 页正文长度（<200 视为自定义页过短）
    - has_home_link: 404 页是否含回首页链接
    """
    import secrets
    rand = secrets.token_hex(6)
    tested = base_url.rstrip("/") + f"/nonexistent-{rand}"
    res = http_get(tested, ua=ua, timeout=timeout, delay=delay,
                   verify_ssl=verify_ssl)
    text = res.body.decode("utf-8", errors="replace") if res.body else ""
    soft = (res.status == 200)
    # 去掉 HTML 标签估算正文长度
    plain = re.sub(r"<[^>]+>", " ", text)
    plain = re.sub(r"\s+", " ", plain).strip()
    body_len = len(plain)
    # 是否有回首页链接
    host = urlparse(base_url).netloc
    has_home = False
    for m in re.finditer(r"""href\s*=\s*"([^"]+)"|href\s*=\s*'([^']+)'""", text, re.I):
        href = m.group(1) or m.group(2) or ""
        if href in ("/", f"https://{host}/") or href.startswith(f"https://{host}/"):
            has_home = True
            break
    return {
        "tested_url": tested,
        "status": res.status,
        "soft_404": soft,
        "body_len": body_len,
        "has_home_link": has_home,
        "custom_404_ok": (not soft) and body_len > 200 and has_home,
    }


def _extract_internal_links(html_text: str, base_url: str, host: str) -> list:
    """极简 <a href> 提取（BFS 发现用，不做 anchor 文本配对）。"""
    out = []
    for m in re.finditer(r'<a\b[^>]*href\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+))',
                         html_text, re.I):
        href = m.group(2) or m.group(3) or m.group(4) or ""
        href = href.strip()
        if not href or href.startswith(("mailto:", "javascript:", "#", "tel:")):
            continue
        full = urljoin(base_url, href)
        full = urldefrag(full)[0]
        if urlparse(full).netloc == host:
            out.append(full)
    return out


def bfs_discover(base_url: str, robots_txt: str = "",
                 ua: str = DEFAULT_UA, delay: float = DEFAULT_DELAY,
                 timeout: int = DEFAULT_TIMEOUT, verify_ssl: bool = True,
                 max_pages: int = 100) -> List[str]:
    """从首页开始 BFS 抓取同域 <a href>，返回发现的 URL 列表（去重、保序）。
    与 sitemap 互为补充：sitemap 为空或显式 --bfs 时使用。"""
    parts = urlparse(base_url)
    host = parts.netloc
    root = f"{parts.scheme}://{parts.netloc}"
    start = root + "/"

    seen = {start}
    queue = [start]
    discovered = []
    while queue and len(discovered) < max_pages:
        u = queue.pop(0)
        if not robots_allows(robots_txt, u, ua_token=ua):
            continue
        res = http_get(u, ua=ua, timeout=timeout, delay=delay,
                       verify_ssl=verify_ssl)
        if res.status != 200 or not res.body:
            continue
        discovered.append(u)
        text = res.body.decode("utf-8", errors="replace")
        for link in _extract_internal_links(text, u, host):
            if link not in seen:
                seen.add(link)
                queue.append(link)
    return discovered


def parse_crawl_delay(robots_txt: str, ua: str = "*") -> Optional[float]:
    """M2.12: 从 robots.txt 解析 Crawl-delay: N（秒）。返回 None 则用默认。"""
    import re as _re
    # 逐 User-agent block 找匹配的
    blocks = robots_txt.split("User-agent:")
    for block in blocks:
        if not block.strip():
            continue
        lines = block.strip().splitlines()
        uas = [l.split(":", 1)[1].strip().lower() for l in lines if l.lower().startswith("user-agent:")]
        # Actually first line is the UA after split
        first_ua = lines[0].strip().lower() if lines else ""
        if ua.lower() in first_ua or first_ua == "*" or first_ua == "":
            for l in lines:
                if l.lower().startswith("crawl-delay:"):
                    try:
                        return float(l.split(":", 1)[1].strip())
                    except ValueError:
                        return None
    # fallback: global crawl-delay
    m = _re.search(r"(?i)^crawl-delay:\s*(\d+(?:\.\d+)?)", robots_txt, _re.M)
    if m:
        return float(m.group(1))
    return None


def crawl_site(base_url: str, out_dir: Path,
               ua: str = DEFAULT_UA, delay: float = DEFAULT_DELAY,
               timeout: int = DEFAULT_TIMEOUT, verify_ssl: bool = True,
               max_pages: Optional[int] = None,
               pre_discovered_urls: Optional[List[str]] = None,
               concurrency: int = 1,
               cache=None, render_mode: str = "off") -> dict:
    """主爬取流程：sitemap → 抓 HTML → 存 raw/ → 探测 PDF。
    pre_discovered_urls: 外部（cli.py 已合并 sitemap+BFS）传入的 URL 列表；
                         传入则跳过内部 sitemap 抓取。
    返回 pages.json 风格 dict（不含 cross-page 分析，那一步在 site_audit.py）。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    print("[1/3] fetch sitemap ...")
    robots_txt = fetch_robots(base_url, ua=ua, timeout=timeout)
    if pre_discovered_urls is not None:
        urls = pre_discovered_urls
        print(f"  using pre-discovered urls: {len(urls)}")
    else:
        # 优先用 robots.txt 里 Sitemap: 指令作为入口（如 Yoast 指向 sitemap_index.xml）
        sm_entry = None
        m = re.search(r"(?i)^sitemap:\s*(\S+)", robots_txt, re.M)
        if m:
            sm_entry = m.group(1).strip()
        urls = fetch_sitemap(base_url, ua=ua, timeout=timeout, entry=sm_entry)
    html_urls = [u for u in urls if not u.lower().endswith(".pdf")]
    pdf_urls = [u for u in urls if u.lower().endswith(".pdf")]
    if max_pages:
        html_urls = html_urls[:max_pages]
    print(f"  sitemap unique: {len(urls)} | html: {len(html_urls)} | pdf: {len(pdf_urls)}")

    # M2.12: robots Crawl-delay 覆盖默认 delay
    cd = parse_crawl_delay(robots_txt, ua)
    if cd is not None:
        delay = cd
        print(f"  robots Crawl-delay: {delay}s")
    print(f"[2/3] crawling HTML pages ({delay}s delay, concurrency={concurrency}) ...")
    pages: Dict[str, dict] = {}
    _lock = __import__("threading").Lock()

    def _fetch_one(u):
        if not robots_allows(robots_txt, u):
            return
        t0 = time.time()
        cached = cache.get(u) if cache else None
        use_cache = False
        if cached is not None:
            res = http_get(u, ua=ua, timeout=timeout, delay=0,
                           verify_ssl=verify_ssl,
                           extra_headers=cache.get_conditional_headers(u))
            if res.status == 304:
                res = type(res)(url=u, status=200, final_url=u, headers={},
                                body=cached, error="", redirect_chain=[])
                use_cache = True
        else:
            res = http_get(u, ua=ua, timeout=timeout, delay=delay, verify_ssl=verify_ssl)
        if render_mode != "off" and res.status == 200:
            try:
                from .site_render import render_page
                rd = render_page(u, mode=render_mode)
                if rd.get("html"):
                    res = type(res)(url=u, status=200, final_url=u,
                                    headers=res.headers, body=rd["html"].encode("utf-8"),
                                    error=res.error, redirect_chain=res.redirect_chain)
            except Exception:
                pass
        ms = int((time.time() - t0) * 1000)
        rec = {
            "url": u, "final_url": res.final_url, "status": res.status,
            "error": res.error, "load_ms": ms,
            "content_type": res.headers.get("Content-Type", ""),
            "bytes": len(res.body),
            "redirect_chain": res.redirect_chain,
        }
        if res.status == 200 and res.body:
            txt = res.body.decode("utf-8", errors="replace")
            if cache and not use_cache:
                cache.put(u, res.body,
                          etag=res.headers.get("ETag", ""),
                          last_modified=res.headers.get("Last-Modified", ""))
            (raw_dir / (slug(u) + ".html")).write_text(txt, encoding="utf-8")
        with _lock:
            pages[u] = rec

    if concurrency and concurrency > 1:
        import threading, queue
        q = queue.Queue()
        for u in html_urls:
            q.put(u)
        def _worker():
            while True:
                try:
                    u = q.get_nowait()
                except queue.Empty:
                    return
                try:
                    _fetch_one(u)
                finally:
                    q.task_done()
        threads = [threading.Thread(target=_worker, daemon=True) for _ in range(concurrency)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    else:
        for i, u in enumerate(html_urls, 1):
            _fetch_one(u)
            print(f"  [{i:3d}/{len(html_urls)}] {pages.get(u, {}).get('status', '?')} {u}")

    print("[3/3] probing PDFs ...")
    pdfs = []
    for i, u in enumerate(pdf_urls, 1):
        res = http_get(u, ua=ua, timeout=timeout, delay=delay, verify_ssl=verify_ssl)
        pdfs.append({
            "url": u, "status": res.status, "final_url": res.final_url,
            "content_type": res.headers.get("Content-Type", ""),
            "content_length": res.headers.get("Content-Length", ""),
            "error": res.error,
        })
        print(f"  [{i:2d}/{len(pdf_urls)}] {res.status} {u}")

    return {
        "site": base_url,
        "counts": {"unique": len(urls), "html": len(html_urls), "pdf": len(pdf_urls)},
        "html_urls": html_urls,
        "pages": pages,
        "pdfs": pdfs,
    }
