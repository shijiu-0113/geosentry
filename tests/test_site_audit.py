# -*- coding: utf-8 -*-
"""geosentry.site_crawler / site_audit / report_html 的单元测试。"""
from __future__ import annotations

import argparse
import json
import unittest
from pathlib import Path

from geosentry.site_crawler import robots_allows, slug, fetch_sitemap, http_get, FetchResult
import geosentry.site_crawler as sc
from geosentry.site_audit import (
    PageParser, parse_page, flag_page, build_facts,
    cross_page_analysis, audit_offline, _url_from_html_or_slug,
)
from geosentry.report_html import render_report


RAW_DIR = (Path(__file__).resolve().parent.parent
           / "docs" / "site-audit-hbyagada" / "raw")
BASE_URL = "https://hbyagada.com"


SAMPLE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Flange Manufacturer | ASME B16.5 Flanges China</title>
<meta name="description" content="Hebei Yajiada manufactures pipe flanges to ASME B16.5, EN 1092-1, JIS B2220.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://example.com/products/weld-neck-flange">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","name":"WN Flange"}</script>
</head>
<body>
<header><nav><a href="/products">Products</a></nav></header>
<main>
<h1>Weld Neck Flange</h1>
<p>A weld neck flange has a long tapered hub and is suitable for high pressure,
high temperature and cyclic service. It is the most robust flange type for
critical piping applications. The welding neck flange is rated by ASME B16.5
and is available in stainless steel, carbon steel and alloy steel grades.
It provides excellent stress distribution and is ideal for refinery,
petrochemical and power generation applications. The weld neck design
ensures full penetration and radiographic quality joints. Choose weld neck
flanges when long-term reliability is required in demanding service conditions.</p>
<img src="/img/wn.png" alt="Weld neck flange">
<img src="/img/wn2.png">
</main>
<footer><a href="/contact">Contact</a></footer>
</body></html>"""


class TestRobots(unittest.TestCase):
    def test_robots_allows_by_default(self):
        self.assertTrue(robots_allows("", "/any/page"))
        self.assertTrue(robots_allows("User-agent: *\nDisallow: /admin/", "/products"))

    def test_robots_blocks(self):
        robots_txt = "User-agent: *\nDisallow: /admin/\nDisallow: /private"
        self.assertFalse(robots_allows(robots_txt, "https://x.com/admin/users"))
        self.assertFalse(robots_allows(robots_txt, "https://x.com/private"))
        self.assertTrue(robots_allows(robots_txt, "https://x.com/public"))

    def test_robots_full_disallow(self):
        self.assertFalse(robots_allows("User-agent: *\nDisallow: /", "/anything"))


class TestSlug(unittest.TestCase):
    def test_slug_home(self):
        self.assertEqual(slug("https://x.com/"), "home")

    def test_slug_simple(self):
        self.assertEqual(slug("https://x.com/about"), "about")

    def test_slug_nested(self):
        self.assertEqual(slug("https://x.com/blog/16mndr-lng-cryogenic"),
                         "blog_16mndr-lng-cryogenic")


class TestParsePage(unittest.TestCase):
    def test_basic_fields(self):
        pr = parse_page(SAMPLE_HTML, "https://example.com/products/weld-neck-flange",
                        "example.com")
        self.assertEqual(pr["title"], "Flange Manufacturer | ASME B16.5 Flanges China")
        self.assertIn("Hebei Yajiada", pr["description"])
        self.assertEqual(pr["canonical"], "https://example.com/products/weld-neck-flange")
        self.assertEqual(pr["h1_count"], 1)
        self.assertEqual(pr["h1_texts"][0], "Weld Neck Flange")
        self.assertTrue(pr["viewport"])
        self.assertEqual(pr["missing_alt"], 1)  # one img without alt
        self.assertEqual(pr["empty_alt"], 0)
        # JSON-LD valid
        self.assertEqual(pr["jsonld"][0]["valid"], True)
        self.assertIn("Product", pr["jsonld"][0]["types"])

    def test_word_count_reasonable(self):
        pr = parse_page(SAMPLE_HTML, "https://example.com/x", "example.com")
        # visible text has many words; assert > 30 (well above 300 threshold)
        self.assertGreater(pr["word_count"], 30)

    def test_links_internal_external(self):
        pr = parse_page(SAMPLE_HTML, "https://example.com/x", "example.com")
        internal = [l for l in pr["links"] if l["internal"]]
        self.assertGreaterEqual(len(internal), 2)


class TestFlagPage(unittest.TestCase):
    def test_thin_page_flags(self):
        rec = {"status": 200, "final_url": "https://x.com/short",
               "parsed": {"title": "Tiny", "title_len": 4,
                          "description": "Short desc", "desc_len": 10,
                          "robots_meta": "index, follow", "viewport": "width",
                          "canonical": "https://x.com/short",
                          "h1_count": 0, "h1_texts": [],
                          "word_count": 5, "missing_alt": 0, "empty_alt": 0,
                          "heading_skip": False, "jsonld": [],
                          "og_missing": ["og:title"], "links": []}}
        flags = flag_page("https://x.com/short", rec)
        sevs = [s for s, _ in flags]
        self.assertIn("major", sevs)  # no H1
        self.assertIn("major", sevs)  # thin content
        self.assertIn("minor", sevs)  # short title / desc

    def test_missing_canonical_critical(self):
        rec = {"status": 200, "final_url": "https://x.com/x",
               "parsed": {"title": "A proper title here", "title_len": 20,
                          "description": "A proper description long enough",
                          "desc_len": 35,
                          "robots_meta": "index, follow", "viewport": "width",
                          "canonical": None,
                          "h1_count": 1, "h1_texts": ["H"],
                          "word_count": 500, "missing_alt": 0, "empty_alt": 0,
                          "heading_skip": False, "jsonld": [],
                          "og_missing": [], "links": []}}
        flags = flag_page("https://x.com/x", rec)
        self.assertIn(("critical", "缺少 canonical"), flags)

    def test_long_title_major(self):
        rec = {"status": 200, "final_url": "https://x.com/x",
               "parsed": {"title": "x" * 80, "title_len": 80,
                          "description": "d" * 100, "desc_len": 100,
                          "robots_meta": "index", "viewport": "w",
                          "canonical": "https://x.com/x",
                          "h1_count": 1, "h1_texts": ["H"],
                          "word_count": 500, "missing_alt": 0, "empty_alt": 0,
                          "heading_skip": False, "jsonld": [],
                          "og_missing": [], "links": []}}
        flags = flag_page("https://x.com/x", rec)
        self.assertTrue(any(m.startswith("title 过长") for _, m in flags))


class TestOfflineUrlInference(unittest.TestCase):
    def test_home_filename(self):
        url = _url_from_html_or_slug("<html></html>", "home.html", BASE_URL)
        self.assertEqual(url, BASE_URL + "/")

    def test_nested_slug(self):
        url = _url_from_html_or_slug("<html></html>",
                                     "blog_isiri-9117-iran-import.html",
                                     BASE_URL)
        self.assertEqual(url, BASE_URL + "/blog/isiri-9117-iran-import")


@unittest.skipUnless(RAW_DIR.exists(), "hbyagada raw/ fixture not present")
class TestOfflineAgainstFixture(unittest.TestCase):
    """用真实 raw/ 目录验证离线分析与样板 facts.json 口径一致。"""

    @classmethod
    def setUpClass(cls):
        cls.facts = audit_offline(RAW_DIR, BASE_URL)
        sample_path = (RAW_DIR.parent / "data" / "facts.json")
        cls.sample = json.loads(sample_path.read_text(encoding="utf-8"))

    def test_page_count(self):
        # 离线少一个 410 页（未存 raw），其余 72 页应齐全
        self.assertEqual(len(self.facts["rows"]), 72)

    def test_issue_counts_offline(self):
        # 410 页贡献 3 critical + 4 major；离线无该页，故 critical=0, major=62, minor=47
        self.assertEqual(self.facts["issues_count"],
                         {"critical": 0, "major": 62, "minor": 47})

    def test_per_page_flags_match(self):
        mine = {r["path"]: sorted(tuple(f) for f in r["flags"])
                for r in self.facts["rows"]}
        theirs = {r["path"]: sorted(tuple(f) for f in r["flags"])
                  for r in self.sample["rows"]}
        shared = set(mine) & set(theirs)
        for p in shared:
            self.assertEqual(mine[p], theirs[p], f"flags differ on {p}")

    def test_orphans_match(self):
        mine = set(o["url"] for o in self.facts["orphans"])
        theirs = set(o["url"] for o in self.sample["orphans"])
        # 离线少 410 孤儿页
        self.assertEqual(mine, theirs - {"https://hbyagada.com/ask/how-do-i-import-pipe-flanges-from-china-to-iran"})

    def test_similar_total(self):
        self.assertEqual(self.facts["similar_total"],
                         self.sample["similar_total"])


class TestRecursiveSitemap(unittest.TestCase):
    """TODO 3: 递归 sitemapindex → 子 sitemap → 真实 URL 三层解析（monkeypatch 桩）。"""

    def _make_fake_get(self, fixture):
        def fake_get(url, **kw):
            body = fixture.get(url, "").encode("utf-8")
            status = 200 if url in fixture else 404
            return FetchResult(url=url, status=status, final_url=url, body=body)
        return fake_get

    def test_sitemapindex_three_levels(self):
        index_xml = (
            '<?xml version="1.0"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<sitemap><loc>https://x.com/page-sitemap.xml</loc></sitemap>'
            '<sitemap><loc>https://x.com/post-sitemap.xml</loc></sitemap>'
            '</sitemapindex>')
        page_xml = (
            '<?xml version="1.0"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://x.com/about</loc></url>'
            '<url><loc>https://x.com/contact</loc></url>'
            '</urlset>')
        post_xml = (
            '<?xml version="1.0"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://x.com/blog/hello</loc></url>'
            '</urlset>')
        fixture = {
            "https://x.com/sitemap.xml": index_xml,
            "https://x.com/page-sitemap.xml": page_xml,
            "https://x.com/post-sitemap.xml": post_xml,
        }
        orig = sc.http_get
        sc.http_get = self._make_fake_get(fixture)
        try:
            urls = fetch_sitemap("https://x.com")
        finally:
            sc.http_get = orig
        self.assertEqual(set(urls), {
            "https://x.com/about", "https://x.com/contact", "https://x.com/blog/hello"})

    def test_sitemapindex_dedup_children(self):
        # 两个子 sitemap 含同一 URL → 去重
        index_xml = (
            '<sitemapindex>'
            '<sitemap><loc>https://x.com/a.xml</loc></sitemap>'
            '<sitemap><loc>https://x.com/b.xml</loc></sitemap>'
            '</sitemapindex>')
        a_xml = '<urlset><url><loc>https://x.com/dup</loc></url></urlset>'
        b_xml = '<urlset><url><loc>https://x.com/dup</loc></url></urlset>'
        fixture = {
            "https://x.com/sitemap.xml": index_xml,
            "https://x.com/a.xml": a_xml,
            "https://x.com/b.xml": b_xml,
        }
        orig = sc.http_get
        sc.http_get = self._make_fake_get(fixture)
        try:
            urls = fetch_sitemap("https://x.com")
        finally:
            sc.http_get = orig
        self.assertEqual(urls, ["https://x.com/dup"])

    def test_flat_sitemap_no_recursion(self):
        # 单层 urlset 不应递归
        xml = ('<urlset>'
               '<url><loc>https://x.com/one</loc></url>'
               '<url><loc>https://x.com/two</loc></url>'
               '</urlset>')
        fixture = {"https://x.com/sitemap.xml": xml}
        orig = sc.http_get
        sc.http_get = self._make_fake_get(fixture)
        try:
            urls = fetch_sitemap("https://x.com")
        finally:
            sc.http_get = orig
        self.assertEqual(urls, ["https://x.com/one", "https://x.com/two"])


class TestRenderReport(unittest.TestCase):
    def test_render_smoke(self):
        facts = {
            "counts": {"html": 2, "pdf": 0},
            "issues_count": {"critical": 1, "major": 3, "minor": 2},
            "rows": [
                {"path": "/a", "url": "https://x.com/a", "status": 200,
                 "title_len": 40, "desc_len": 100, "words": 500, "h1_count": 1,
                 "flags": [("major", "title 过长 80 字符")]},
                {"path": "/b", "url": "https://x.com/b", "status": 404,
                 "title_len": 0, "desc_len": 0, "words": 0, "h1_count": 0,
                 "flags": [("critical", "HTTP 404")]},
            ],
            "title_duplicates": {}, "desc_duplicates": {},
            "similar_top": [], "similar_total": 0,
            "orphans": [], "dead_links": [], "pdfs": [],
        }
        html = render_report(facts, "https://x.com")
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("头部摘要", html)
        self.assertIn("/a", html)
        self.assertIn("/b", html)
        self.assertIn("P0", html)



class TestDeadLinkProbe(unittest.TestCase):
    """TODO 1: dead-link online probe (monkeypatch stub)."""
    def test_probe_finds_404(self):
        from geosentry.site_crawler import probe_dead_links
        fixture = {
            "https://x.com/good": FetchResult(url="https://x.com/good", status=200,
                                              final_url="https://x.com/good", body=b""),
            "https://x.com/bad": FetchResult(url="https://x.com/bad", status=404,
                                             final_url="https://x.com/bad", body=b""),
        }
        orig = sc.http_get
        sc.http_get = lambda url, **kw: fixture.get(
            url, FetchResult(url=url, status=500, final_url=url, body=b""))
        try:
            dead = probe_dead_links(["https://x.com/good", "https://x.com/bad"],
                                    delay=0, max_probes=10)
        finally:
            sc.http_get = orig
        self.assertEqual(len(dead), 1)
        self.assertEqual(dead[0]["url"], "https://x.com/bad")
        self.assertEqual(dead[0]["status"], 404)

    def test_probe_respects_max(self):
        from geosentry.site_crawler import probe_dead_links
        calls = []
        def fake_get(url, **kw):
            calls.append(url)
            return FetchResult(url=url, status=404, final_url=url, body=b"")
        orig = sc.http_get
        sc.http_get = fake_get
        try:
            probe_dead_links([f"https://x.com/{i}" for i in range(100)],
                             delay=0, max_probes=10)
        finally:
            sc.http_get = orig
        self.assertEqual(len(calls), 10)


class TestOfflinePDF(unittest.TestCase):
    """TODO 2: offline PDF header check."""
    def test_scan_valid_and_corrupt(self):
        import tempfile
        from geosentry.site_audit import scan_local_pdfs
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "good.pdf").write_bytes(b"%PDF-1.4\n...binary...")
            (d / "bad.pdf").write_bytes(b"this is not a pdf")
            pdfs = scan_local_pdfs(d, "https://x.com")
            self.assertEqual(len(pdfs), 2)
            by_name = {p["url"].split("/")[-1]: p for p in pdfs}
            self.assertEqual(by_name["good.pdf"]["status"], 200)
            self.assertIsNone(by_name["good.pdf"]["error"])
            self.assertEqual(by_name["bad.pdf"]["status"], 500)
            self.assertIn("corrupt", by_name["bad.pdf"]["error"])

    def test_missing_dir(self):
        import tempfile
        from geosentry.site_audit import scan_local_pdfs
        with tempfile.TemporaryDirectory() as td:
            pdfs = scan_local_pdfs(Path(td) / "nope", "https://x.com")
            self.assertEqual(pdfs, [])


class TestTrailingSlashDetection(unittest.TestCase):
    """TODO 4: trailing-slash dual-version detection."""
    def test_detects_dual_version(self):
        pages = {
            "https://x.com/query": {"status": 200, "parsed": {}},
            "https://x.com/query/": {"status": 200, "parsed": {}},
            "https://x.com/legal": {"status": 200, "parsed": {}},
        }
        cross = cross_page_analysis(pages, "x.com")
        duos = cross["trailing_slash_duos"]
        self.assertEqual(len(duos), 1)
        self.assertEqual(duos[0]["without_slash"], "https://x.com/query")
        self.assertEqual(duos[0]["with_slash"], "https://x.com/query/")

    def test_no_duo_if_non_200(self):
        pages = {
            "https://x.com/query": {"status": 200, "parsed": {}},
            "https://x.com/query/": {"status": 301, "parsed": {}},
        }
        cross = cross_page_analysis(pages, "x.com")
        self.assertEqual(cross["trailing_slash_duos"], [])


class TestTopIssueSort(unittest.TestCase):
    """TODO 5: same severity sorted by affected-page count."""
    def test_sorted_by_weight(self):
        from geosentry.report_html import _aggregate_top_issues
        facts = {
            "rows": [
                {"path": "/a", "url": "https://x.com/a", "status": 200,
                 "title_len": 100, "desc_len": 100, "words": 500, "h1_count": 1,
                 "flags": [("major", "title too long 100")]},
            ] * 5 + [
                {"path": "/b", "url": "https://x.com/b", "status": 200,
                 "title_len": 100, "desc_len": 100, "words": 100, "h1_count": 1,
                 "flags": [("major", "thin ~100 words")]},
            ],
            "title_duplicates": {}, "desc_duplicates": {},
            "similar_top": [], "similar_total": 0,
            "orphans": [], "dead_links": [], "pdfs": [],
            "trailing_slash_duos": [],
        }
        items = _aggregate_top_issues(facts, "https://x.com")
        majors = [it for it in items if it["sev"] == "major"]
        self.assertGreaterEqual(majors[0]["weight"], majors[-1]["weight"])


class TestBFSDiscover(unittest.TestCase):
    """TODO 6: BFS internal-link discovery (monkeypatch stub)."""
    def test_bfs_follows_internal_links(self):
        from geosentry.site_crawler import bfs_discover
        pages = {
            "https://x.com/": b'<a href="/about">About</a><a href="/contact">C</a>',
            "https://x.com/about": b'<a href="/team">Team</a>',
            "https://x.com/contact": b"<p>contact</p>",
            "https://x.com/team": b"<p>team</p>",
        }
        orig = sc.http_get
        sc.http_get = lambda url, **kw: FetchResult(
            url=url, status=200, final_url=url,
            body=pages.get(url, b""))
        try:
            urls = bfs_discover("https://x.com", delay=0, max_pages=10)
        finally:
            sc.http_get = orig
        self.assertIn("https://x.com/", urls)
        self.assertIn("https://x.com/about", urls)
        self.assertIn("https://x.com/contact", urls)
        self.assertIn("https://x.com/team", urls)



class TestCLIBFSMerge(unittest.TestCase):
    """CLI 层 --bfs / --bfs-fallback 合并行为（全桩，不联网）。"""

    def _run_deep(self, extra_flags):
        """Invoke _cmd_audit_deep with monkeypatched crawler stack."""
        import tempfile
        from unittest import mock
        from geosentry import cli
        from geosentry import site_crawler as sc_mod

        sm = ["https://x.com/", "https://x.com/about", "https://x.com/contact"]
        bfs = ["https://x.com/", "https://x.com/team", "https://x.com/career"]

        captured = {}

        fake_crawl_sig = lambda base, out_dir, **kw: captured.setdefault(
            "pre", kw.get("pre_discovered_urls")) or kw.get("pre_discovered_urls")

        with mock.patch.object(sc_mod, "fetch_robots", return_value=""), \
             mock.patch.object(sc_mod, "fetch_sitemap", return_value=list(sm)), \
             mock.patch.object(sc_mod, "bfs_discover", return_value=list(bfs)), \
             mock.patch.object(sc_mod, "crawl_site",
                               side_effect=lambda *a, **kw: (
                                   captured.setdefault(
                                       "pre", kw.get("pre_discovered_urls")),
                                   {"site": a[0], "counts": {}, "pages": {},
                                    "pdfs": [], "html_urls": []})[1]) as mock_crawl, \
             mock.patch.object(sc_mod, "probe_dead_links", return_value=[]), \
             mock.patch.object(sc_mod, "http_get",
                               return_value=sc_mod.FetchResult(url="https://x.com", status=200,
                                                               final_url="https://x.com",
                                                               headers={}, body=b"")), \
             mock.patch.object(sc_mod, "probe_404",
                               return_value={"tested_url": "https://x.com/n",
                                             "status": 404, "soft_404": False,
                                             "body_len": 100, "has_home_link": True,
                                             "custom_404_ok": True}), \
             mock.patch("geosentry.site_external.run_pagespeed",
                        return_value={"skipped": True, "error": "test mock"}), \
             mock.patch("geosentry.site_audit.cross_page_analysis",
                        return_value={"title_duplicates": {}, "desc_duplicates": {},
                                      "similar_pairs": [], "orphans": [],
                                      "dead_links": [], "unknown_internal_hrefs": [],
                                      "trailing_slash_duos": []}), \
             mock.patch("geosentry.site_audit.build_facts",
                        return_value={"rows": [], "issues_count": {"critical": 0, "major": 0, "minor": 0},
                                      "counts": {}, "title_duplicates": {},
                                      "desc_duplicates": {}, "similar_top": [],
                                      "similar_total": 0, "orphans": [],
                                      "dead_links": [], "pdfs": [],
                                      "trailing_slash_duos": []}), \
             mock.patch("geosentry.report_html.render_report",
                        return_value="<html></html>"), \
             tempfile.TemporaryDirectory() as td:
            ns = argparse.Namespace(
                url="https://x.com", deep=True, out=td, offline=None,
                delay=0, no_verify_ssl=False, max_pages=None,
                bfs=extra_flags.get("bfs", False),
                bfs_fallback=extra_flags.get("bfs_fallback", True))
            cli._cmd_audit_deep(ns)
        return captured.get("pre")

    def test_no_bfs_uses_only_sitemap(self):
        urls = self._run_deep({"bfs": False, "bfs_fallback": False})
        self.assertEqual(urls, ["https://x.com/", "https://x.com/about",
                                "https://x.com/contact"])

    def test_bfs_merges_and_dedupes(self):
        urls = self._run_deep({"bfs": True, "bfs_fallback": True})
        # sitemap 3 + bfs 3, homepage 重叠 → 去重后 5
        self.assertIn("https://x.com/about", urls)
        self.assertIn("https://x.com/team", urls)
        self.assertIn("https://x.com/career", urls)
        self.assertEqual(len(urls), 5)

    def test_bfs_fallback_off_skips_when_sitemap_present(self):
        # sitemap 非空 + fallback off + 不显式 --bfs → 不调 bfs
        urls = self._run_deep({"bfs": False, "bfs_fallback": False})
        self.assertEqual(len(urls), 3)


if __name__ == "__main__":
    unittest.main()
