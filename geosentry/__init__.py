"""geosentry：本地轻量 RAG 知识背板（零部署）。

核心入口 GeoSentry：
    bp = GeoSentry()                    # 自动加载 data/ 索引
    bp.index()                          # 从 corpus/ 重建索引
    results = bp.search("robots.txt 规范", top_k=5)
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import List, Optional

from . import store
from .chunker import Chunk, assign_ids, chunk_file
from .retriever import Retriever
from .vectorizer import get_backend

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS_DIRS = [
    PROJECT_ROOT / "corpus" / "google-docs",
    PROJECT_ROOT / "corpus" / "mdn-docs",
    PROJECT_ROOT / "corpus" / "geo-knowledge",
]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
LABELS_FILE = PROJECT_ROOT / "corpus" / "doc_labels_zh.json"


def load_labels() -> dict:
    """加载文档中文检索标签（doc stem -> 中文关键词串）。"""
    if LABELS_FILE.exists():
        import json
        return json.loads(LABELS_FILE.read_text(encoding="utf-8"))
    return {}


def scan_corpus(dirs: Optional[List[Path]] = None) -> List[Chunk]:
    """扫描语料目录，切块并编号。"""
    dirs = dirs or DEFAULT_CORPUS_DIRS
    chunks: List[Chunk] = []
    for d in dirs:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            source = "google" if "google-docs" in str(d) else (
                "mdn" if "mdn-docs" in str(d) else "geo")
            chunks.extend(chunk_file(p, source=source))
    return assign_ids(chunks)


class GeoSentry:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.chunks: list = []
        self.index_data: dict = {}
        self.meta: dict = {}
        self._retriever: Optional[Retriever] = None
        if store.index_exists(self.data_dir):
            self._load()

    # ---------- 索引 ----------

    def index(self, corpus_dirs: Optional[List[Path]] = None) -> dict:
        chunks = scan_corpus(corpus_dirs)
        labels = load_labels()
        # 索引文本 = 原文 + 中文标签（中文查询可命中；展示仍用原文）
        chunk_dicts = []
        index_texts = []
        for c in chunks:
            tag = labels.get(c.doc, "")
            index_text = f"{c.text}\n{tag}" if tag else c.text
            index_texts.append(index_text)
            d = c.__dict__.copy()
            d["index_text"] = index_text
            chunk_dicts.append(d)

        backend = get_backend()
        backend.fit(index_texts)
        vectors = backend.encode(index_texts)
        backend_name = "siliconflow" if backend.__class__.__name__ == "SiliconFlowBackend" else "tfidf"

        index_data = {"backend": backend_name, "vectors": vectors}
        if backend_name == "tfidf":
            # JSON 无法保留 int key，稀疏向量序列化为 [[dim, weight], ...]
            index_data["vectors"] = [
                [[int(k), float(v)] for k, v in vec.items()] for vec in vectors
            ]
            index_data.update(backend.to_dict())

        doc_count = len({c.doc for c in chunks})
        meta = {"backend": backend_name, "created_at": time.time(),
                "n_chunks": len(chunks), "doc_count": doc_count,
                "version": store.INDEX_VERSION}
        store.save_index(self.data_dir, chunk_dicts, index_data, meta)
        if backend_name == "tfidf":
            # 内存态还原为 {int dim: float weight}（与 _load 一致）
            index_data["vectors"] = [
                {int(k): float(v) for k, v in vec} for vec in index_data["vectors"]
            ]
        self.chunks = chunk_dicts
        self.index_data = index_data
        self.meta = meta
        self._retriever = Retriever(self.chunks, index_data)
        return meta

    def _load(self):
        chunks, index_data, meta = store.load_index(self.data_dir)
        if meta.get("backend") == "tfidf":
            # 还原稀疏向量为 {int dim: float weight}
            index_data["vectors"] = [
                {int(k): float(v) for k, v in vec} for vec in index_data["vectors"]
            ]
        self.chunks = chunks
        self.index_data = index_data
        self.meta = meta
        self._retriever = Retriever(chunks, index_data)

    # ---------- 检索 ----------

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        if self._retriever is None:
            raise RuntimeError("索引不存在，请先运行 index() 或 python -m geosentry index")
        query_vec = None
        if self.meta.get("backend") == "siliconflow":
            try:
                backend = get_backend()
                encoded = backend.encode([query])
                query_vec = encoded[0][1] if isinstance(encoded[0], tuple) else encoded[0]
            except Exception:
                query_vec = None  # API 不可用时退化为 BM25
        else:
            from .vectorizer import TFIDFBackend
            try:
                backend = TFIDFBackend.from_dict({
                    "vocab": self.index_data["vocab"],
                    "idf": self.index_data["idf"],
                })
                query_vec = backend.encode([query])[0]
            except Exception:
                query_vec = None
        return self._retriever.search(query, query_vec=query_vec, top_k=top_k)

    def info(self) -> dict:
        return {
            "indexed": store.index_exists(self.data_dir),
            "backend": self.meta.get("backend"),
            "chunks": self.meta.get("n_chunks", 0),
            "docs": self.meta.get("doc_count", 0),
            "data_dir": str(self.data_dir),
        }
