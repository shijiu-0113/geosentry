"""增量爬取语料（面向有网络的场景；当前环境 Google 直连受限时可用工具通道补抓）。

流程：源 URL 清单 → robots.txt 门禁 → 限速 1 req/s → HTML→Markdown → 落盘 corpus/
B 级源清单内置（2026 Google Search Central 高价值文档）。
用法：python scripts/crawl_docs.py --source google [--limit N]
"""
from __future__ import annotations

import argparse
import re
import socket
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

socket.setdefaulttimeout(20)
UA = "geosentry-crawler/0.1 (research; contact: dev@example.com)"
DELAY = 1.0  # 1 req/s

ROOT = Path(__file__).resolve().parent.parent
CORPUS_GOOGLE = ROOT / "corpus" / "google-docs"

# B 级源清单（2026 新增与高价值文档）
GOOGLE_SOURCES = [
    ("preferred-sources", "https://developers.google.com/search/docs/appearance/preferred-sources"),
    ("spam-policies", "https://developers.google.com/search/docs/essentials/spam-policies"),
    ("site-reputation-policy", "https://developers.google.com/search/docs/essentials/site-reputation-policy"),
    ("gen-ai-performance-reports", "https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports"),
    ("ai-optimization-guide", "https://developers.google.com/search/docs/fundamentals/ai-optimization-guide"),
    ("overview-google-crawlers", "https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers"),
    ("creating-helpful-content", "https://developers.google.com/search/docs/fundamentals/creating-helpful-content"),
    ("structured-data-intro", "https://developers.google.com/search/docs/appearance/structured-data/intro"),
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def http_get(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [skip] {url}: {type(e).__name__}")
        return None


def robots_allows(url: str) -> bool:
    """简化 robots 门禁：解析 User-agent: * 段的 Disallow 规则，判断目标路径是否被禁。
    无 robots.txt 视为允许；只识别本爬虫 UA（按 * 段）。"""
    from urllib.parse import urlparse
    parts = urlparse(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    txt = http_get(robots_url)
    if txt is None:
        return True  # 无 robots.txt 视为允许
    path = parts.path or "/"
    in_wild = False
    disallows = []
    for raw in txt.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"(?i)^user-agent:\s*(.+)$", line)
        if m:
            in_wild = m.group(1).strip() == "*"
            continue
        if in_wild:
            md = re.match(r"(?i)^disallow:\s*(.*)$", line)
            if md:
                disallows.append(md.group(1).strip())
    for d in disallows:
        if d in ("", "/"):
            print(f"  [blocked] robots.txt 全站 Disallow: {url}")
            return False
        if d and path.startswith(d):
            print(f"  [blocked] robots.txt Disallow {d} 覆盖 {url}")
            return False
    return True


def html_to_markdown(html: str, url: str) -> str:
    # 优先 trafilatura（可选依赖）
    try:
        import trafilatura
        md = trafilatura.extract(html, url=url, include_comments=False,
                                 include_tables=True, output_format="markdown")
        if md and len(md.strip()) > 50:
            return md
    except Exception:
        pass
    # 降级：内置简单转换
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", html)
    html = re.sub(r"(?i)<h([1-6])[^>]*>", lambda m: "\n\n" + "#" * int(m.group(1)) + " ", html)
    html = re.sub(r"(?i)</h[1-6]>", "\n\n", html)
    html = re.sub(r"(?i)<li[^>]*>", "\n- ", html)
    html = re.sub(r"(?i)<p[^>]*>", "\n\n", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)<a [^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", r"[\2](\1)", html)
    html = re.sub(r"<[^>]+>", "", html)
    return re.sub(r"\n{3,}", "\n\n", html).strip()


def crawl_sources(sources, out_dir: Path, limit: int | None = None) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    fetched = 0
    for name, url in sources:
        if limit and fetched >= limit:
            break
        target = out_dir / f"{name}.md"
        if target.exists():
            print(f"[skip] 已存在 {target.name}")
            continue
        if not robots_allows(url):
            continue
        print(f"[crawl] {name} <- {url}")
        html = http_get(url)
        if html is None:
            continue
        md = html_to_markdown(html, url)
        if len(md) < 100:
            print(f"  [warn] 内容过短，跳过 {name}")
            continue
        header = f"# {name}\n\n> 来源：{url}\n\n"
        target.write_text(header + md + "\n", encoding="utf-8")
        print(f"  -> saved {target.name} ({len(md)} chars)")
        fetched += 1
        time.sleep(DELAY)
    return fetched


def main():
    p = argparse.ArgumentParser(description="增量爬取 SEO 语料")
    p.add_argument("--source", default="google", choices=["google", "all"])
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()

    print(f"UA: {UA}")
    print(f"目标目录: {CORPUS_GOOGLE}")
    n = crawl_sources(GOOGLE_SOURCES, CORPUS_GOOGLE, args.limit)
    print(f"\n完成：本次抓取 {n} 篇。运行 `python -m geosentry index` 重建索引。")


if __name__ == "__main__":
    main()
