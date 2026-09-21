"""混合检索：向量余弦（稀疏/TF-IDF 或 API 稠密）+ BM25，加权 RRF 融合。

RRF（Reciprocal Rank Fusion）: score(d) = Σ w_i / (k + rank_i(d) + 1)，
k 默认 60（实测扫参后定稿），两路权重默认 (1.0, 1.0)。
两路均无命中时返回空列表，不硬拿一路凑数。
返回带出处（doc/url/title/heading/text）的结果列表。
"""
from __future__ import annotations

from typing import Dict, List, Sequence

from .bm25 import BM25

# 由 eval/sweep.py 对 52 题 qa_seed.jsonl 扫参后选定的默认值。
# 矩阵（Recall@5）：k=20 全权重组合均 100%；k=60/100 在 (1,1.5) 下掉到 98.08%。
RRF_K = 20
RRF_WEIGHTS = (1.0, 1.0)  # (vector_weight, bm25_weight)
DEFAULT_TOP_K = 5


def cosine_sparse(a: Dict[int, float], b: Dict[int, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b.get(k, 0.0) for k in a)
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def cosine_dense(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


class Retriever:
    def __init__(self, chunks: list, index_data: dict,
                 rrf_k: int = RRF_K, rrf_weights: Sequence[float] = RRF_WEIGHTS):
        self.chunks = chunks
        self.backend = index_data.get("backend", "tfidf")
        self.vectors = index_data["vectors"]
        self.rrf_k = rrf_k
        self.rrf_weights = tuple(rrf_weights)
        # BM25 用索引文本（原文+中文标签）；展示用 chunks 的 text
        self.texts = [c.get("index_text", c["text"]) for c in chunks]
        self.bm25 = BM25().fit(self.texts)

    def _unpack_vec(self, v):
        """SiliconFlow 通道的向量在 JSON 序列化后为 ["dense", [...]]，这里解包成纯 list。"""
        if isinstance(v, (list, tuple)) and len(v) == 2 and v[0] == "dense":
            return v[1]
        return v

    def vector_search(self, query_vec, top_k: int) -> List[int]:
        if query_vec is None:
            return []
        if self.backend == "siliconflow":
            scores = [cosine_dense(query_vec, self._unpack_vec(v)) for v in self.vectors]
        else:
            scores = [cosine_sparse(query_vec, v) for v in self.vectors]
        # 过滤全 0 分（查询词在语料中完全未出现）
        max_score = max(scores) if scores else 0.0
        if max_score <= 0.0:
            return []
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return ranked[:top_k * 4]

    def bm25_search(self, query: str, top_k: int) -> List[int]:
        scores = self.bm25.get_scores(query)
        max_score = max(scores) if scores else 0.0
        if max_score <= 0.0:
            return []
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return ranked[:top_k * 4]

    def _rrf(self, lists_of_ranks: List[List[int]], weights: Sequence[float],
             k: int, top_k: int) -> List[int]:
        scores: Dict[int, float] = {}
        for i, ranks in enumerate(lists_of_ranks):
            w = weights[i] if i < len(weights) else 1.0
            for rank, doc_id in enumerate(ranks):
                scores[doc_id] = scores.get(doc_id, 0.0) + w / (k + rank + 1)
        ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return [doc_id for doc_id, _ in ordered[:top_k]]

    def search(self, query: str, query_vec=None, top_k: int = DEFAULT_TOP_K) -> List[dict]:
        vector_ranks = self.vector_search(query_vec, top_k)
        bm25_ranks = self.bm25_search(query, top_k)
        if not vector_ranks and not bm25_ranks:
            return []
        merged = self._rrf([vector_ranks, bm25_ranks], self.rrf_weights, self.rrf_k, top_k)
        results = []
        for idx in merged:
            c = self.chunks[idx]
            results.append({
                "doc": c["doc"], "url": c.get("url", ""), "title": c.get("title", ""),
                "heading": c.get("heading", ""), "source": c.get("source", ""),
                "text": c["text"],
            })
        return results
