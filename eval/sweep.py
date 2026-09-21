"""扫参：对 RRF 的 k 与两路权重组合跑 qa_seed.jsonl，打印 Recall@5 矩阵。

用法：py -3.11 eval\\sweep.py
不修改任何文件，只把实测最优组合打印出来；人工把最优值写回 geosentry/retriever.py。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from geosentry import GeoSentry  # noqa: E402
from geosentry.retriever import Retriever  # noqa: E402
from geosentry.vectorizer import TFIDFBackend  # noqa: E402


def recall_for(bp: GeoSentry, qa: list, k: int, weights: tuple, top_k: int = 5) -> float:
    tfidf = TFIDFBackend.from_dict({"vocab": bp.index_data["vocab"],
                                    "idf": bp.index_data["idf"]})
    r = Retriever(bp.chunks, bp.index_data, rrf_k=k, rrf_weights=weights)
    hits = 0
    for item in qa:
        qv = tfidf.encode([item["q"]])[0]
        results = r.search(item["q"], query_vec=qv, top_k=top_k)
        docs = [x["doc"] for x in results]
        if item["doc"] in docs:
            hits += 1
    return hits / len(qa)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--qa", default=str(ROOT / "eval" / "qa_seed.jsonl"))
    p.add_argument("--top-k", type=int, default=5)
    args = p.parse_args()

    bp = GeoSentry()
    if not bp.info()["indexed"]:
        print("请先运行: python -m geosentry index")
        return 1

    qa = [json.loads(line) for line in Path(args.qa).read_text(encoding="utf-8").splitlines()
          if line.strip()]

    ks = [20, 60, 100]
    weight_sets = [(1.0, 1.0), (1.5, 1.0), (1.0, 1.5)]
    labels = ["(1.0,1.0)", "(1.5,1.0)", "(1.0,1.5)"]

    print(f"Recall@{args.top_k} 矩阵（{len(qa)} 题）")
    print(f"{'k':>5} | " + " | ".join(f"{lab:>12}" for lab in labels))
    print("-" * 50)

    best = None
    for k in ks:
        row = []
        for w in weight_sets:
            r = recall_for(bp, qa, k, w, args.top_k)
            row.append(r)
            if best is None or r > best[0]:
                best = (r, k, w)
        print(f"{k:>5} | " + " | ".join(f"{v:>12.2%}" for v in row))

    print()
    print(f"最优组合: k={best[1]}, weights={best[2]} -> Recall@{args.top_k}={best[0]:.2%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
