"""QA 评测：Recall@5 门禁（>=0.90）+ 关键词命中率。

用法：py -3.11 eval/run_eval.py [--top-k 5]
依赖：先运行 python -m geosentry index 建立索引。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from geosentry import GeoSentry  # noqa: E402

PASS_THRESHOLD = 0.90


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--qa", default=str(ROOT / "eval" / "qa_seed.jsonl"))
    args = p.parse_args()

    bp = GeoSentry()
    if not bp.info()["indexed"]:
        print("请先运行: python -m geosentry index")
        return 1

    qa = [json.loads(line) for line in Path(args.qa).read_text(encoding="utf-8").splitlines() if line.strip()]
    hits = 0
    kw_hits = 0
    kw_total = 0
    misses = []
    for item in qa:
        results = bp.search(item["q"], top_k=args.top_k)
        docs = [r["doc"] for r in results]
        ok = item["doc"] in docs
        hits += int(ok)
        if not ok:
            misses.append((item["q"], item["doc"], docs[:3]))
        # 关键词验证（在 top-k 全部片段里找）
        blob = " ".join(r["text"] for r in results).lower()
        kws = [k.lower() for k in item.get("kw", [])]
        kw_total += len(kws)
        kw_hits += sum(1 for k in kws if k in blob)

    recall = hits / len(qa)
    kw_rate = kw_hits / kw_total if kw_total else 0.0
    print(f"QA 评测（{len(qa)} 题, top-{args.top_k}）")
    print(f"  Recall@{args.top_k}: {recall:.2%}  (命中 {hits}/{len(qa)})")
    print(f"  关键词命中率:      {kw_rate:.2%}  ({kw_hits}/{kw_total})")
    print(f"  门禁 Recall@{args.top_k} >= {PASS_THRESHOLD}: {'✅ PASS' if recall >= PASS_THRESHOLD else '❌ FAIL'}")
    if misses:
        print("\n未命中题目：")
        for q, expect, got in misses:
            print(f"  - {q}\n    期望: {expect} | 实际: {got}")
    return 0 if recall >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
