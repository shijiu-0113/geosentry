"""GEO 实测：用 LLM 回答采购型 query，统计品牌 mention rate / citation rate。

OpenAI 兼容 chat/completions 接口；API key/base_url/model 从环境变量或 CLI 读。
纯 stdlib（urllib），无硬编码 key。
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Optional


def call_llm(prompt: str, api_key: str, base_url: str, model: str,
             timeout: int = 30) -> str:
    """调 OpenAI 兼容 /chat/completions，返回回答文本。"""
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful industrial purchasing assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read().decode("utf-8"))
    return resp["choices"][0]["message"]["content"]


def analyze_answer(answer: str, brand_terms: List[str], target_url: str) -> dict:
    """检查回答文本里是否提及品牌 / 引用目标 URL。
    返回 {mentioned, cited, matched_brand, matched_url}。
    """
    text_lower = answer.lower()
    mentioned = False
    matched_brand = ""
    for term in brand_terms:
        if term.lower() in text_lower:
            mentioned = True
            matched_brand = term
            break
    cited = False
    # 提取域名
    from urllib.parse import urlparse
    target_host = urlparse(target_url).netloc
    if target_host in answer:
        cited = True
    return {"mentioned": mentioned, "cited": cited,
            "matched_brand": matched_brand, "matched_url": target_host if cited else ""}


def run_geo_live(url: str, queries: List[str], brand_terms: List[str],
                 api_key: str, base_url: str, model: str,
                 history_dir: Optional[Path] = None) -> dict:
    """跑一组 query，统计 mention rate / citation rate。"""
    results = []
    n_mention = 0
    n_cite = 0
    for q in queries:
        prompt = f"A Chinese industrial buyer asks: {q}. Recommend specific manufacturers."
        try:
            answer = call_llm(prompt, api_key, base_url, model)
        except Exception as e:
            results.append({"query": q, "error": str(e)[:120],
                            "mentioned": False, "cited": False})
            continue
        a = analyze_answer(answer, brand_terms, url)
        results.append({"query": q, "answer_excerpt": answer[:300], **a})
        if a["mentioned"]:
            n_mention += 1
        if a["cited"]:
            n_cite += 1
    n = len(queries)
    summary = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "url": url, "model": model,
        "total_queries": n,
        "mention_rate": round(n_mention / n, 3) if n else 0,
        "citation_rate": round(n_cite / n, 3) if n else 0,
        "mention_count": n_mention,
        "citation_count": n_cite,
        "results": results,
    }
    if history_dir:
        history_dir.mkdir(parents=True, exist_ok=True)
        fname = history_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        fname.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    return summary


def load_queries(path: str) -> List[str]:
    """从文件读 query 列表（一行一个）。"""
    return [l.strip() for l in Path(path).read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]
