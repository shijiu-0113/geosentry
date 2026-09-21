"""调试：输出查询在 BM25 / 向量 / RRF 各通道的得分，定位误命中原因。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geosentry import GeoSentry  # noqa: E402
from geosentry.retriever import cosine_sparse  # noqa: E402
from geosentry.vectorizer import TFIDFBackend  # noqa: E402

QUERIES = [
    "robots.txt 是干什么的，怎么用它限制爬虫访问？",
    "canonical 标签怎么用？",
    "favicon 在搜索结果里起什么作用？",
    "noindex 和 robots.txt 阻止收录有什么区别？",
]

bp = GeoSentry()
idx = bp.index_data
backend = TFIDFBackend.from_dict({"vocab": idx["vocab"], "idf": idx["idf"]})

for q in QUERIES:
    print("=" * 80)
    print("Q:", q)
    qv = backend.encode([q])[0]
    bm25_scores = bp._retriever.bm25.get_scores(q)
    vec_scores = [cosine_sparse(qv, v) for v in idx["vectors"]]
    # top3 per channel
    bm = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:3]
    vec = sorted(range(len(vec_scores)), key=lambda i: vec_scores[i], reverse=True)[:3]
    print("  BM25 top3:", [(bp.chunks[i]["doc"], round(bm25_scores[i], 3)) for i in bm])
    print("  VEC  top3:", [(bp.chunks[i]["doc"], round(vec_scores[i], 3)) for i in vec])
    # 打印 BM25 top1 的索引文本开头
    t = bp.chunks[bm[0]]
    print("  BM25 top1:", t["doc"], "| 片段:", t["text"][:100].replace("\n", " "))
    print("  VEC  top1:", bp.chunks[vec[0]]["doc"], "| 片段:", bp.chunks[vec[0]]["text"][:100].replace("\n", " "))
