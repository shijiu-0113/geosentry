"""M2.9: 主内容提取 / 噪声剪枝（纯 stdlib）。
HTML→正文块评分：tag 权重 + 链接密度 + 文本长度。
剪 nav/footer/侧栏；输出喂 RAG chunker 和正文词数。
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import List, Tuple


_NOISE_TAGS = {"nav", "footer", "aside", "header", "script", "style", "noscript",
               "form", "svg"}
_GOOD_TAGS = {"p", "article", "section", "main", "div", "li", "td", "th"}


class _BlockParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks: List[Tuple[str, str, int]] = []  # (tag, text, link_chars)
        self._stack: List[str] = []
        self._cur_text = ""
        self._cur_links = 0
        self._in_noise = 0
        self._tag_stack: List[str] = []

    def handle_starttag(self, tag, attrs):
        self._tag_stack.append(tag)
        if tag in _NOISE_TAGS:
            self._in_noise += 1
        if tag in ("p", "div", "li", "section", "article"):
            if self._cur_text.strip():
                self.blocks.append((self._tag_stack[-2] if len(self._tag_stack) > 1 else "div",
                                    self._cur_text, self._cur_links))
            self._cur_text = ""
            self._cur_links = 0
        if tag == "a":
            self._cur_links += len(attrs)  # rough

    def handle_endtag(self, tag):
        if tag in _NOISE_TAGS and self._in_noise > 0:
            self._in_noise -= 1
        if tag in ("p", "div", "li", "section", "article"):
            if self._cur_text.strip():
                self.blocks.append((tag, self._cur_text, self._cur_links))
            self._cur_text = ""
            self._cur_links = 0
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data):
        if self._in_noise == 0:
            self._cur_text += data


def extract_main_content(html: str, mode: str = "pruning") -> str:
    """从 HTML 提取主文本。
    mode: pruning = tag-weight + link-density 剪枝；none = 直接去 tag。
    """
    if mode == "none":
        return re.sub(r"<[^>]+>", " ", html).strip()

    p = _BlockParser()
    try:
        p.feed(html)
    except Exception:
        return re.sub(r"<[^>]+>", " ", html).strip()

    # 评分每个 block
    blocks = [(t, x, l) for t, x, l in p.blocks if len(x.split()) >= 5]
    if mode == "bm25":
        # 块内 TF * 全局 IDF 近似：跨块稀有词所在块排名更高
        from collections import Counter
        df = Counter()
        for tag, text, links in blocks:
            for w in set(re.findall(r"[a-zA-Z][a-z0-9-]{2,}", text.lower())):
                df[w] += 1
        n = max(len(blocks), 1)
        scored = []
        for tag, text, links in blocks:
            tf = Counter(re.findall(r"[a-zA-Z][a-z0-9-]{2,}", text.lower()))
            idf_sum = sum(tf[w] * (1.0 + n / (1 + df[w])) for w in tf)
            if idf_sum > 3:
                scored.append(text)
        return "\n".join(scored) if scored else re.sub(r"<[^>]+>", " ", html).strip()

    scored = []
    for tag, text, links in blocks:
        link_density = (links * 4) / max(len(text), 1)
        weight = 3.0 if tag in ("article", "main") else (
            2.0 if tag == "p" else (1.0 if tag in ("section", "li") else 0.5))
        score = weight * (len(text.split()) ** 0.5) * (1 - link_density)
        if score > 2:
            scored.append(text)

    return "\n".join(scored) if scored else re.sub(r"<[^>]+>", " ", html).strip()
