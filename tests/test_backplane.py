"""geosentry 核心单元测试（unittest，零第三方依赖）。

运行：py -3.11 -m unittest discover -s tests -v
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from geosentry import GeoSentry, scan_corpus
from geosentry.bm25 import BM25, tokenize
from geosentry.chunker import chunk_file, chunk_markdown
from geosentry.retriever import cosine_sparse, Retriever
from geosentry.vectorizer import TFIDFBackend


class TestChunker(unittest.TestCase):
    def test_frontmatter_stripped_and_url_extracted(self):
        md = """---
title: https://example.com/doc
url: https://example.com/doc
---
---
title: Real Page Title | Example
url: https://example.com/doc
---
# Intro
Some intro paragraph text that is reasonably long for a heading section.

## Section One
This is the body of section one with enough content to be a chunk.
"""
        chunks = chunk_markdown(md, doc="test")
        self.assertTrue(chunks, "应至少产生一个 chunk")
        for c in chunks:
            self.assertNotIn("---", c.text)
            self.assertEqual(c.url, "https://example.com/doc")
        self.assertEqual(chunks[0].title, "Real Page Title | Example")

    def test_heading_based_splitting(self):
        md = "# T\n## A\n" + "para a text " * 30 + "\n## B\n" + "para b text " * 30
        chunks = chunk_markdown(md, doc="t")
        self.assertGreaterEqual(len(chunks), 2)
        self.assertEqual(chunks[0].heading, "A")
        self.assertEqual(chunks[1].heading, "B")

    def test_file_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.md"
            p.write_text("---\nurl: https://x.dev/y\n---\n# T\n## S\n"
                         + "body text content here " * 20, encoding="utf-8")
            chunks = chunk_file(p, source="test")
            self.assertTrue(chunks)
            self.assertEqual(chunks[0].url, "https://x.dev/y")


class TestBM25(unittest.TestCase):
    def test_tokenize_mixed(self):
        toks = tokenize("How to fix a lawn full of weeds 怎么清除杂草")
        self.assertIn("lawn", toks)
        self.assertIn("weeds", toks)
        self.assertTrue(any(len(t) == 2 and "\u4e00" <= t[0] <= "\u9fff" for t in toks))

    def test_relevance_ranking(self):
        corpus = [
            "Google search engine optimization guide for website owners",
            "Cooking recipes for tomato pasta with fresh basil",
            "Google SEO robots.txt crawling indexing best practices",
        ]
        bm = BM25().fit(corpus)
        scores = bm.get_scores("google search crawling robots")
        self.assertEqual(max(range(3), key=scores.__getitem__), 2)


class TestVectorizer(unittest.TestCase):
    def test_tfidf_cosine(self):
        texts = [
            "robots txt controls crawler access to website",
            "sitemap xml lists pages for search engines",
            "robots txt disallow blocks search engine crawlers",
        ]
        b = TFIDFBackend().fit(texts)
        vecs = b.encode(texts)
        sim = cosine_sparse(vecs[0], vecs[2])
        self.assertGreater(sim, cosine_sparse(vecs[0], vecs[1]))

    def test_serialize_roundtrip(self):
        b = TFIDFBackend().fit(["hello world", "world of search"])
        b2 = TFIDFBackend.from_dict(b.to_dict())
        v1 = b.encode(["hello search"])
        v2 = b2.encode(["hello search"])
        self.assertEqual(v1[0], v2[0])


class TestRetriever(unittest.TestCase):
    def _make_index(self):
        chunks = [
            {"id": "c0", "text": "robots.txt controls Googlebot and AI crawler access.",
             "doc": "a", "url": "https://x/a", "title": "A", "heading": "", "source": "t"},
            {"id": "c1", "text": "Sitemaps list all pages for search engines to discover.",
             "doc": "b", "url": "https://x/b", "title": "B", "heading": "", "source": "t"},
            {"id": "c2", "text": "Google ignores llms.txt files for search ranking purposes.",
             "doc": "c", "url": "https://x/c", "title": "C", "heading": "", "source": "t"},
        ]
        b = TFIDFBackend().fit([c["text"] for c in chunks])
        index_data = {"backend": "tfidf", "vectors": b.encode([c["text"] for c in chunks])}
        index_data.update(b.to_dict())
        return chunks, index_data

    def test_search_returns_citations(self):
        chunks, idx = self._make_index()
        r = Retriever(chunks, idx)
        qvec = TFIDFBackend.from_dict(idx).encode(["robots crawler access"])[0]
        results = r.search("robots crawler", query_vec=qvec, top_k=2)
        self.assertTrue(results)
        self.assertEqual(results[0]["doc"], "a")
        self.assertIn("url", results[0])
        self.assertIn("text", results[0])


class TestEndToEnd(unittest.TestCase):
    def test_index_and_search_small_corpus(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            corpus = root / "corpus" / "google-docs"
            corpus.mkdir(parents=True)
            (corpus / "doc1.md").write_text(
                "---\nurl: https://x/d1\n---\n# Doc1\n## Topic\n"
                "Google recommends helpful people-first content for ranking. " * 15,
                encoding="utf-8")
            (corpus / "doc2.md").write_text(
                "---\nurl: https://x/d2\n---\n# Doc2\n## Topic\n"
                "structured data JSON-LD enables rich results in search. " * 15,
                encoding="utf-8")
            bp = GeoSentry(data_dir=root / "data")
            meta = bp.index(corpus_dirs=[corpus])
            self.assertGreaterEqual(meta["n_chunks"], 2)
            hits = bp.search("helpful people-first content", top_k=2)
            self.assertEqual(hits[0]["doc"], "doc1")


class TestScanCorpus(unittest.TestCase):
    def test_scan_default(self):
        chunks = scan_corpus()
        self.assertGreaterEqual(len(chunks), 300, "内置语料应 >= 300 chunks")


class TestFixes(unittest.TestCase):
    """针对代码审计发现的回归 bug 补的单元测试。"""

    def test_bom_stripped_before_frontmatter(self):
        # 文件首字符带 BOM 时，frontmatter 仍应被正确剥离
        text = "\ufeff---\nurl: https://x/y\n---\n# T\n## S\n" + "body content " * 20
        chunks = chunk_markdown(text, doc="bom")
        self.assertTrue(chunks)
        self.assertEqual(chunks[0].url, "https://x/y")
        self.assertNotIn("\ufeff", chunks[0].text)

    def test_cjk_word_count(self):
        from geosentry.geo_audit import _count_words
        html = "<html><body><p>" + "搜索引擎优化是一项长期工作。" * 40 + "</p></body></html>"
        self.assertGreaterEqual(_count_words(html), 300)

    def test_cjk_word_count_zero_on_ascii_short(self):
        from geosentry.geo_audit import _count_words
        self.assertLess(_count_words("<p>hi</p>"), 300)

    def test_robots_allows_home(self):
        from geosentry.geo_audit import _robots_allows_home
        # 无规则 -> 允许
        self.assertTrue(_robots_allows_home(""))
        # 全站 Disallow
        self.assertFalse(_robots_allows_home("User-agent: *\nDisallow: /\n"))
        # 子路径 Disallow 不影响首页
        self.assertTrue(_robots_allows_home("User-agent: *\nDisallow: /private/\n"))
        # 子路径 Disallow 覆盖该路径
        self.assertFalse(_robots_allows_home("User-agent: *\nDisallow: /private/\n", "/private/x"))

    def test_corrupted_index_raises_friendly(self):
        import json as _json
        from geosentry import store
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            (dd / "chunks.json").write_text("[]", encoding="utf-8")
            (dd / "index.json").write_text("{ not json", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                store.load_index(dd)

    def test_siliconflow_vec_unpack(self):
        # 模拟 JSON 往返后向量变成 ["dense", [...]] 形式，retriever 应能解包
        chunks = [{"id": "c0", "text": "t", "doc": "a", "url": "", "title": "",
                   "heading": "", "source": "t"}]
        idx = {"backend": "siliconflow", "vectors": [["dense", [0.1, 0.2, 0.3]]]}
        r = Retriever(chunks, idx)
        scores = r.vector_search([0.1, 0.2, 0.3], top_k=1)
        self.assertEqual(scores, [0])


class TestRoundTwo(unittest.TestCase):
    """第二轮 GitHub digest 整合后的新行为测试。"""

    def test_breadcrumb_prefix_in_chunk_text(self):
        md = ("# Doc Title\n## Section A\n" + "body of section a " * 30
              + "\n## Section B\n" + "body of section b " * 30)
        chunks = chunk_markdown(md, doc="bc")
        self.assertGreaterEqual(len(chunks), 2)
        self.assertIn("Doc Title > Section A", chunks[0].text)
        self.assertIn("Doc Title > Section B", chunks[1].text)

    def test_fence_not_split_by_heading(self):
        md = ("# T\n## Code\nHere is code:\n\n```\n# not a heading\nprint('x')\n```\n\n"
              + "real content body " * 30)
        chunks = chunk_markdown(md, doc="fence")
        self.assertTrue(chunks)
        joined = " ".join(c.text for c in chunks)
        self.assertIn("```", joined)
        self.assertIn("print('x')", joined)

    def test_stopwords_filtered_from_english(self):
        toks = tokenize("the robots controls the of and a an indexing")
        self.assertIn("controls", toks)
        self.assertIn("indexing", toks)
        for stop in ("the", "of", "and", "a", "an"):
            self.assertNotIn(stop, toks)

    def test_edit_distance_fuzzy(self):
        from geosentry.bm25 import BM25
        corpus = [
            "canonical tag tells search engine preferred URL",
            "this is some other unrelated content about cooking pasta",
        ]
        bm = BM25().fit(corpus)
        scores = bm.get_scores("canonial")
        self.assertEqual(max(range(2), key=scores.__getitem__), 0)

    def test_synonym_expansion(self):
        from geosentry.bm25 import BM25
        corpus = [
            "This page describes how a crawler fetches and indexes pages.",
            "This page is about baking bread and pastry recipes.",
        ]
        bm = BM25().fit(corpus)
        scores = bm.get_scores("爬虫")
        self.assertEqual(max(range(2), key=scores.__getitem__), 0)

    def test_llmstxt_validator_ok(self):
        from geosentry.geo_audit import _validate_llmstxt
        good = """# My Site

> A short description of my site.

- [Home](https://example.com/)
- [About](https://example.com/about)
"""
        self.assertEqual(_validate_llmstxt(good), [])

    def test_llmstxt_validator_errors(self):
        from geosentry.geo_audit import _validate_llmstxt
        bad = """Not a title

some text without blockquote

- [bad link](relative/path)
- [dup](https://example.com/x)
- [dup](https://example.com/x)
"""
        errs = _validate_llmstxt(bad)
        self.assertTrue(any("首行" in e for e in errs))
        self.assertTrue(any("blockquote" in e for e in errs))
        self.assertTrue(any("重复" in e for e in errs))

    def test_ai_bot_robots_parsing(self):
        from geosentry.geo_audit import _parse_robots_bots, _bot_allowed_root
        txt = """User-agent: GPTBot
Disallow: /

User-agent: *
Disallow: /private/
"""
        rules = _parse_robots_bots(txt)
        self.assertFalse(_bot_allowed_root(rules, "GPTBot"))
        self.assertTrue(_bot_allowed_root(rules, "ClaudeBot"))

    def test_rrf_both_channels_empty_returns_empty(self):
        chunks = [{"id": "c0", "text": "x", "doc": "a", "url": "", "title": "",
                   "heading": "", "source": "t"}]
        idx = {"backend": "tfidf", "vectors": [{}]}
        r = Retriever(chunks, idx)
        results = r.search("zzqqxxwv", query_vec={}, top_k=5)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
