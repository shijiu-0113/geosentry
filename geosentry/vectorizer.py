"""向量化后端：三档可插拔（自动降级）。

1. SiliconFlowBackend —— Qwen3-Embedding-8B API（语义最强，需 SILICONFLOW_API_KEY）
2. TFIDFBackend —— 本地 TF-IDF（纯标准库，默认，离线可用）

统一接口：fit(texts) -> 训练；encode(texts) -> 稀疏向量（dict: term_index -> weight）
稀疏向量用 dict 表示，余弦检索在 retriever 中实现，不依赖 numpy。
"""
from __future__ import annotations

import json
import math
import os
import re
import urllib.request
from collections import Counter
from typing import Dict, List

from .bm25 import tokenize

API_URL = "https://api.siliconflow.cn/v1/embeddings"
API_MODEL = "Qwen/Qwen3-Embedding-8B"


class TFIDFBackend:
    """纯标准库 TF-IDF：词表 + IDF + 向量。"""

    def __init__(self):
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.fitted = False

    def fit(self, texts: List[str]) -> "TFIDFBackend":
        df: Counter = Counter()
        token_sets = []
        for t in texts:
            toks = set(tokenize(t))
            token_sets.append(toks)
            for term in toks:
                df[term] += 1
        n = len(texts)
        self.vocab = {term: i for i, term in enumerate(sorted(df))}
        self.idf = {term: math.log(1 + n / (1 + freq)) for term, freq in df.items()}
        self.fitted = True
        return self

    def encode(self, texts: List[str]) -> List[Dict[int, float]]:
        if not self.fitted:
            raise RuntimeError("TFIDFBackend.fit() 尚未调用")
        out = []
        for t in texts:
            tf = Counter(tokenize(t))
            vec: Dict[int, float] = {}
            for term, cnt in tf.items():
                idx = self.vocab.get(term)
                if idx is None:
                    continue
                vec[idx] = (1 + math.log(cnt)) * self.idf[term]
            out.append(vec)
        return out

    def to_dict(self) -> dict:
        return {"vocab": self.vocab, "idf": self.idf}

    @classmethod
    def from_dict(cls, data: dict) -> "TFIDFBackend":
        b = cls()
        b.vocab = data["vocab"]
        b.idf = {str(k): float(v) for k, v in data["idf"].items()}
        b.fitted = True
        return b


class SiliconFlowBackend:
    """SiliconFlow OpenAI 兼容 Embedding API（可选，需 key）。"""

    def __init__(self, api_key: str, model: str = API_MODEL):
        self.api_key = api_key
        self.model = model

    def fit(self, texts: List[str]) -> "SiliconFlowBackend":
        return self  # API 无需训练

    def encode(self, texts: List[str]) -> List[Dict[int, float]]:
        # 转成密集向量列表，由 retriever 直接用于余弦
        dense = self._encode_dense(texts)
        # 统一返回结构：稀疏 dict 格式由 retriever 区分处理
        # 此处返回特殊标记：用 ("dense", vector) 包装避免与稀疏混淆
        return [("dense", v) for v in dense]

    def _encode_dense(self, texts: List[str]) -> List[List[float]]:
        vectors = []
        batch = []
        for t in texts:
            batch.append(t)
            if len(batch) >= 16:
                vectors.extend(self._call(batch))
                batch = []
        if batch:
            vectors.extend(self._call(batch))
        return vectors

    def _call(self, texts: List[str]) -> List[List[float]]:
        body = json.dumps({"model": self.model, "input": texts,
                           "encoding_format": "float"}).encode()
        req = urllib.request.Request(API_URL, data=body, method="POST",
                                     headers={"Authorization": f"Bearer {self.api_key}",
                                              "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
        return [item["embedding"] for item in data["data"]]


def get_backend(api_key: str | None = None) -> object:
    """按可用性选择后端：API key 存在 -> SiliconFlow；否则 -> TF-IDF。"""
    key = api_key or os.environ.get("SILICONFLOW_API_KEY")
    if key:
        try:
            return SiliconFlowBackend(key)
        except Exception:
            pass
    return TFIDFBackend()
