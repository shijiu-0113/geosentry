"""M2.8: URL 优先级评分 — 用于 heapq 优先 BFS 队列。
按 path depth / 文件名加权 / 重复模式 / lastmod 打分。
分数越低越优先（heapq min-heap）。
"""
from __future__ import annotations

import re
from urllib.parse import urlparse


def score_url(url: str, lastmod: str = "") -> float:
    """返回优先级分数（越低越优先）。"""
    p = urlparse(url)
    path = p.path or "/"
    score = 0.0

    # 1. depth: 越浅越优先
    depth = path.count("/")
    score += depth * 10

    # 2. 文件名加权
    pl = path.lower()
    if pl in ("/", "") or pl.endswith("/index.html") or pl.endswith("/"):
        score -= 50  # 首页/目录页
    elif re.search(r"/(product|products|item|p)", pl):
        score -= 30
    elif re.search(r"/(contact|about|quote|rfq|ask|inquiry)", pl):
        score -= 20
    elif re.search(r"/(blog|news|post|article)", pl):
        score += 10

    # 3. 重复模式惩罚
    if re.search(r"/page/\d+", pl) or re.search(r"[?&]page=\d+", url):
        score += 100  # 分页
    if re.search(r"[?&]sort=", url):
        score += 50
    if re.search(r"[?&]filter=", url):
        score += 30

    # 4. 静态资源降权
    if re.search(r"\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf)(\?|$)", pl):
        score += 500

    return score
