"""纯 Python BM25（Okapi BM25）实现，零依赖。

分词策略：
- 英文按单词（小写、去标点，长度>1）；CJK 按 unigram + bigram 混合
- 微型内嵌停用词表（the/of/的/了...），bigram 不过滤停用词
- 查询期：未命中的英文词（长度>=4）做 Levenshtein<=1 容错；
  领域同义词表（crawler/爬虫、redirect/跳转...）以 0.5 权重扩展

数据量小，全程 dict 实现足够快。
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple

K1 = 1.5
B = 0.75
EPS = 0.25

_WORD_RE = re.compile(r"[a-z0-9]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# 微型停用词表：英文高频虚词 + 中文常用虚词。bigram 不过滤。
_STOP = frozenset({
    "the", "of", "and", "a", "an", "is", "are", "to", "in", "on", "for",
    "with", "as", "by", "at", "from", "or", "be", "this", "that", "it",
    "的", "了", "和", "在", "是", "我", "你", "他", "她", "它", "们",
    "也", "都", "就", "还", "又", "但", "而", "及", "与", "或", "个",
})

# SEO/GEO 领域同义词：查询期把值里的词以 0.5 权重并入查询。
_SYNONYMS: Dict[str, List[str]] = {
    "ai search": ["generative engine optimization", "generative ai search"],
    "ai搜索": ["generative engine", "generative ai"],
    "爬虫": ["crawler", "spider", "googlebot"],
    "跳转": ["redirect", "301"],
    "收录": ["index", "indexing"],
    "排名": ["ranking", "rank"],
    "搜索": ["search"],
    "优化": ["optimization", "seo"],
    "网站": ["website", "site"],
    "页面": ["page"],
    "标签": ["tag", "meta"],
    "结构": ["structured data", "schema"],
    "内容": ["content"],
}


def tokenize(text: str) -> List[str]:
    """中英混合分词：英文单词（去停用词） + CJK bigram。
    不引入 CJK unigram：单字会翻倍文档长度、扭曲 BM25 的 dl/avgdl 归一化，
    实测会让短英文文档（do-i-need-seo）在混合查询中误占 top 位。"""
    text = text.lower()
    tokens: List[str] = []
    for w in _WORD_RE.findall(text):
        if len(w) > 1 and w not in _STOP:
            tokens.append(w)
    cjk = _CJK_RE.findall(text)
    # bigram：相邻二字组（不做停用词过滤，bigram 本身有区分度）
    for i in range(len(cjk) - 1):
        tokens.append(cjk[i] + cjk[i + 1])
    return tokens


def _levenshtein_le1(a: str, b: str) -> bool:
    """快速判断两个字符串编辑距离是否 <=1（只允许 1 次增/删/改）。
    比完整 DP 快，足够 typo 容错。"""
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diff = sum(1 for x, y in zip(a, b) if x != y)
        return diff <= 1
    # 一长一短：短串插入一个字符能变成长串
    if la > lb:
        a, b = b, a
    # a 是短的，b 是长的
    i = j = diff = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
        else:
            diff += 1
            if diff > 1:
                return False
            j += 1
    return True


def _expand_synonyms(tokens: List[str]) -> List[Tuple[str, float]]:
    """把查询 token 列表展开成 (term, weight) 列表。
    原词 weight=1.0；命中同义词表时，同义词按 0.5 追加。"""
    out: List[Tuple[str, float]] = []
    lowered = [t.lower() for t in tokens]
    for t in tokens:
        out.append((t, 1.0))
    joined = " ".join(lowered)
    for key, syns in _SYNONYMS.items():
        if key in joined:
            for s in syns:
                for st in tokenize(s):
                    out.append((st, 0.5))
    return out


class BM25:
    def __init__(self, k1: float = K1, b: float = B):
        self.k1 = k1
        self.b = b
        self.corpus_size = 0
        self.avgdl = 0.0
        self.doc_freqs: List[Counter] = []
        self.idf: Dict[str, float] = {}
        self.doc_len = 0.0
        self._all_tokens: List[List[str]] = []
        self._by_len: Dict[int, List[str]] = defaultdict(list)

    def fit(self, corpus: Iterable[str]) -> "BM25":
        self._all_tokens = [tokenize(doc) for doc in corpus]
        self.corpus_size = len(self._all_tokens)
        self.doc_len = sum(len(t) for t in self._all_tokens)
        self.avgdl = self.doc_len / self.corpus_size if self.corpus_size else 0.0

        df: Dict[str, int] = {}
        self.doc_freqs = []
        for toks in self._all_tokens:
            c = Counter(toks)
            self.doc_freqs.append(c)
            for term in c:
                df[term] = df.get(term, 0) + 1

        n = self.corpus_size
        self.idf = {
            term: math.log(1 + (n - freq + 0.5) / (freq + 0.5)) + 1
            for term, freq in df.items()
        }
        # 编辑距离容错用：按词长分桶，查询时只扫 len±1 桶
        self._by_len = defaultdict(list)
        for term in self.idf:
            if term.isascii() and term.isalpha() and len(term) >= 4:
                self._by_len[len(term)].append(term)
        return self

    def _fuzzy_candidates(self, word: str) -> List[str]:
        """对未命中的英文词，在同长±1 的词典里找 Levenshtein<=1 的候选。"""
        if not (word.isascii() and word.isalpha() and len(word) >= 4):
            return []
        hits = []
        for L in (len(word) - 1, len(word), len(word) + 1):
            for cand in self._by_len.get(L, ()):
                if cand == word:
                    continue
                if _levenshtein_le1(word, cand):
                    hits.append(cand)
        return hits

    def get_scores(self, query: str) -> List[float]:
        raw_tokens = tokenize(query)
        if not raw_tokens:
            return [0.0] * self.corpus_size

        # 同义词扩展 + 编辑距离容错
        weighted = _expand_synonyms(raw_tokens)
        resolved: List[Tuple[str, float]] = []
        for term, w in weighted:
            if term in self.idf:
                resolved.append((term, w))
            elif term.isascii() and term.isalpha() and len(term) >= 4:
                for cand in self._fuzzy_candidates(term):
                    resolved.append((cand, w))

        if not resolved:
            return [0.0] * self.corpus_size

        scores = [0.0] * self.corpus_size
        # 按 term 聚合权重（同一 term 多来源相加）
        term_weight: Dict[str, float] = defaultdict(float)
        for term, w in resolved:
            term_weight[term] += w

        for i, doc_freq in enumerate(self.doc_freqs):
            dl = len(self._all_tokens[i])
            for term, weight in term_weight.items():
                if term not in self.idf or term not in doc_freq:
                    continue
                tf = doc_freq[term]
                denom = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl) if self.avgdl else tf + self.k1 * (1 - self.b)
                scores[i] += self.idf[term] * tf * (self.k1 + 1) / denom * weight
        return scores
