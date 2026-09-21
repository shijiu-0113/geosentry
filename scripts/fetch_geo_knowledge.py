"""抓取 D 级 GEO 生态知识（本地可达源）：llmstxt.org 规范 + GEO 论文摘要。
落盘到 corpus/geo-knowledge/，来源标注非官方/学术。"""
import urllib.request
import socket
import re
from pathlib import Path

socket.setdefaulttimeout(20)
UA = {"User-Agent": "geosentry/0.1 (research; contact: dev@example.com)"}
OUT = Path(__file__).resolve().parent.parent / "corpus" / "geo-knowledge"
OUT.mkdir(parents=True, exist_ok=True)


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req) as r:
        return r.read().decode("utf-8", errors="replace")


def clean_html(html):
    # 去掉 script/style
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", html)
    # 标题
    text = re.sub(r"(?i)<h([1-6])[^>]*>", lambda m: "\n\n" + "#" * int(m.group(1)) + " ", html)
    text = re.sub(r"(?i)</h[1-6]>", "\n\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "\n- ", text)
    text = re.sub(r"(?i)<p[^>]*>", "\n\n", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)<a [^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", r"[\2](\1)", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def save(name, url, body, note):
    p = OUT / name
    p.write_text(f"# {name}\n\n> 来源：{url}\n> 类型：{note}\n\n{body}\n", encoding="utf-8")
    print(f"saved {p} ({len(body)} chars)")


# 1. llmstxt.org 规范
try:
    html = fetch("https://llmstxt.org/")
    save("llmstxt-spec.md", "https://llmstxt.org/", clean_html(html), "GEO 生态规范（非官方）")
except Exception as e:
    print("llmstxt.org ERR:", e)

# 2. GEO 论文摘要（arXiv）
try:
    html = fetch("https://arxiv.org/abs/2311.09735")
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    abstract = re.search(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>', html, re.S)
    authors = re.search(r'<div class="authors">(.*?)</div>', html, re.S)
    txt = ""
    if title:
        txt += "标题: " + clean_html(title.group(1)) + "\n\n"
    if authors:
        txt += "作者: " + clean_html(authors.group(1)) + "\n\n"
    if abstract:
        txt += "摘要: " + clean_html(abstract.group(1)) + "\n"
    save("geo-arxiv-2311-09735.md", "https://arxiv.org/abs/2311.09735", txt, "学术论文（GEO 起源，KDD 2024）")
except Exception as e:
    print("arxiv ERR:", e)
