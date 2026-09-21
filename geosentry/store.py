"""本地持久化：chunks 元数据 + 索引向量，零依赖 JSON 存储。

目录结构（data/）：
- chunks.json   [{id, text, doc, url, title, source, heading}]
- index.json    {backend: "tfidf"|"siliconflow", vocab, idf, vectors, meta}
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

from .chunker import Chunk

INDEX_VERSION = 1


@dataclass
class IndexMeta:
    backend: str
    created_at: float
    n_chunks: int
    doc_count: int
    version: int = INDEX_VERSION


def save_index(data_dir: Path, chunks, index_data: dict, meta: dict) -> Path:
    """chunks 为 Chunk dataclass 列表或 dict 列表。"""
    data_dir.mkdir(parents=True, exist_ok=True)
    chunk_file = data_dir / "chunks.json"
    if chunks and hasattr(chunks[0], "__dict__") and not isinstance(chunks[0], dict):
        records = [asdict(c) for c in chunks]
    else:
        records = list(chunks)
    chunk_file.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    payload = {"meta": meta, "index": index_data}
    (data_dir / "index.json").write_text(json.dumps(payload, ensure_ascii=False),
                                         encoding="utf-8")
    return chunk_file


def load_index(data_dir: Path) -> tuple:
    """返回 (chunks, index_data, meta)；不存在或损坏时抛 RuntimeError 带可读信息。"""
    try:
        chunks = json.loads((data_dir / "chunks.json").read_text(encoding="utf-8"))
        payload = json.loads((data_dir / "index.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (json.JSONDecodeError, OSError) as e:
        raise RuntimeError(
            f"索引文件损坏或不可读（{e}）。请删除 {data_dir} 后重新运行 index。"
        ) from e
    if not isinstance(payload, dict) or "index" not in payload or "meta" not in payload:
        raise RuntimeError("index.json 结构异常，缺少 index/meta 字段，请重建索引。")
    return chunks, payload["index"], payload["meta"]


def index_exists(data_dir: Path) -> bool:
    return (data_dir / "chunks.json").exists() and (data_dir / "index.json").exists()
