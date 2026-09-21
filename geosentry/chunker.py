"""Markdown 语料切块器：按标题层级切块，保留出处元数据。

切块策略（面向 AI 引用友好）：
- 以 H2/H3 为语义切分点；无标题的正文按段落聚合
- 每块目标长度 ~600 字，超长块再按段落/句子拆
- Fenced code block（``` 或 ~~~）整段原子保护，不在 fence 内 flush
- 遇到新标题时，把祖先标题面包屑（" > " 拼接）拼到 chunk 正文前，
  让 BM25/TF-IDF 向量能看到上下文
- 每块附带 {doc, url, title, source} 元数据，检索结果可追溯出处
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

MAX_CHUNK_CHARS = 1200
TARGET_CHUNK_CHARS = 600
MIN_CHUNK_CHARS = 80

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_FRONTMATTER_RE = re.compile(r"^---[ \t]*\r?\n.*?\r?\n---[ \t]*\r?\n", re.S)
_FENCE_RE = re.compile(r"^[ \t]*(```|~~~)")
_TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")


@dataclass
class Chunk:
    text: str
    doc: str
    url: str = ""
    title: str = ""
    source: str = ""
    heading: str = ""
    id: str = field(default="")


def _strip_frontmatter(text: str) -> tuple[str, dict]:
    """剥离文档开头所有连续 frontmatter 块（原项目爬虫叠加了双层），
    并提取 title/url/source 元数据。"""
    meta: dict = {}
    titles: list = []
    while True:
        m = _FRONTMATTER_RE.match(text)
        if not m:
            break
        block = m.group(0)
        for line in block.splitlines():
            line = line.strip()
            if ":" in line and not line.startswith("---"):
                k, _, v = line.partition(":")
                k = k.strip().lower()
                v = v.strip().strip("'\"")
                if not v:
                    continue
                if k == "title":
                    titles.append(v)
                elif k in ("url", "source", "description", "hostname"):
                    meta.setdefault(k, v)
        text = text[m.end():].lstrip("\ufeff\n\r")
    real = [t for t in titles if not t.startswith("http")]
    meta.setdefault("title", (real or titles or [""])[-1])
    return text, meta


def _split_paragraphs(text: str) -> List[str]:
    """按空行拆段落，去掉过短片段。"""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text)]
    return [p for p in paras if len(p) >= MIN_CHUNK_CHARS // 2]


def _split_long(text: str, limit: int = MAX_CHUNK_CHARS) -> List[str]:
    """超长块按句子边界拆分。"""
    if len(text) <= limit:
        return [text]
    parts = re.split(r"(?<=[。．.!?；;])\s*", text)
    out, buf = [], ""
    for p in parts:
        if buf and len(buf) + len(p) > limit:
            out.append(buf)
            buf = p
        else:
            buf += p
    if buf:
        out.append(buf)
    return [x for x in out if len(x) >= MIN_CHUNK_CHARS // 2]


def chunk_markdown(text: str, doc: str, url: str = "", title: str = "",
                   source: str = "", meta: dict | None = None) -> List[Chunk]:
    """把一个 Markdown 文档切成 chunk 列表。meta 为 frontmatter 提取的元数据。"""
    # 防御性剥离 BOM（避免 frontmatter 正则在文件首字符为 ﻿ 时失配）
    text = text.lstrip("\ufeff")
    text, fm = _strip_frontmatter(text)
    if meta:
        fm.update(meta)
    url = url or fm.get("url", "")
    title = title or fm.get("title", "")
    source = source or fm.get("source", "")
    lines = text.splitlines()

    chunks: List[Chunk] = []
    headings: dict[int, str] = {}  # level -> 文本，用于面包屑
    cur_heading = ""
    buf: List[str] = []
    in_fence = False

    def breadcrumb() -> str:
        if not headings:
            return ""
        return " > ".join(headings[lvl] for lvl in sorted(headings))

    def flush():
        nonlocal buf
        body = "\n".join(buf).strip()
        buf = []
        if not body or len(body) < MIN_CHUNK_CHARS // 2:
            return
        bc = breadcrumb()
        pieces = _split_long(body)
        for piece in pieces:
            out_text = (bc + "\n\n" + piece) if bc else piece
            chunks.append(Chunk(
                text=out_text, doc=doc, url=url, title=title,
                source=source, heading=cur_heading,
            ))

    for line in lines:
        # fence 状态翻转：fence 内不允许因标题而 flush
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            buf.append(line)
            continue
        if in_fence:
            buf.append(line)
            continue

        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            heading_text = m.group(2).strip()
            if level == 1:
                # H1 视为文档标题，不单独开块，但纳入面包屑
                headings[1] = heading_text
                # H1 之后更深层级旧值已失效（新章节）
                continue
            if level >= 2:
                flush()
                cur_heading = heading_text
                headings[level] = heading_text
                # 清掉更深层级（H3 出现时清 H4+，以此类推）
                for deeper in [l for l in headings if l > level]:
                    del headings[deeper]
                continue
        if line.strip():
            buf.append(line)
    flush()
    return chunks


def chunk_file(path: Path, source: str = "corpus") -> List[Chunk]:
    """从语料文件切块，文件名即 doc 名；frontmatter 提供真实 URL/标题。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    return chunk_markdown(text, doc=path.stem, source=source)


def assign_ids(chunks: List[Chunk]) -> List[Chunk]:
    for i, c in enumerate(chunks):
        c.id = f"chunk-{i:05d}"
    return chunks
