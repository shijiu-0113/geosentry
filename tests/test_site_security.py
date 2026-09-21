"""第五轮新增检查项的单元测试：A 安全头 / B AI bots / C llms.txt 质量 /
D 软 404 / E 加权总分 / F sitemap 质量 / G 图片优化 / H 外部 stub。"""
import unittest
from geosentry.site_security import analyze_security_headers, score_security_headers
from geosentry.scoring import compute_overall_score
from geosentry.site_audit import analyze_sitemap_quality, analyze_images
from geosentry.geo_audit import _AI_BOTS, _validate_llmstxt


class TestSecurityHeaders(unittest.TestCase):
    def test_all_pass(self):
        headers = {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "strict-origin",
            "Permissions-Policy": "camera=()",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Resource-Policy": "same-origin",
        }
        results = analyze_security_headers(headers)
        self.assertTrue(all(r["passed"] for r in results))
        s = score_security_headers(results)
        self.assertEqual(s["earned"], s["total"])
        self.assertEqual(s["pct"], 100.0)

    def test_all_fail(self):
        results = analyze_security_headers({})
        self.assertTrue(all(not r["passed"] for r in results))
        s = score_security_headers(results)
        self.assertEqual(s["earned"], 0)
        self.assertEqual(s["pct"], 0.0)

    def test_hsts_short_maxage_fails(self):
        results = analyze_security_headers({"Strict-Transport-Security": "max-age=60"})
        hsts = [r for r in results if r["key"] == "hsts"][0]
        self.assertFalse(hsts["passed"])


class TestAIBots(unittest.TestCase):
    def test_new_bots_present(self):
        for bot in ("OAI-SearchBot", "ChatGPT-User", "Claude-User",
                    "Claude-SearchBot"):
            self.assertIn(bot, _AI_BOTS)


class TestLLMsTxtQuality(unittest.TestCase):
    def test_good_llmstxt(self):
        text = ("# Acme Corp\n"
                "> Industrial flange manufacturer\n"
                "\n"
                "- [About](https://x.com/about)\n"
                "- [Products](https://x.com/products)\n")
        errors = _validate_llmstxt(text)
        self.assertEqual(errors, [])

    def test_html_rejected(self):
        text = "<!DOCTYPE html><html><body>hi</body></html>"
        errors = _validate_llmstxt(text)
        self.assertTrue(any("HTML" in e for e in errors))

    def test_no_links_rejected(self):
        text = "# Acme\n> blah\n"
        errors = _validate_llmstxt(text)
        self.assertTrue(any("URL" in e or "链接" in e for e in errors))


class Test404Probe(unittest.TestCase):
    def test_soft_404_detected(self):
        from geosentry.site_crawler import probe_404, FetchResult
        orig = None
        import geosentry.site_crawler as sc
        def fake_get(url, **kw):
            return FetchResult(url=url, status=200, final_url=url,
                               body=b"<html><body>homepage content here " * 20 + b"</body></html>")
        orig = sc.http_get
        sc.http_get = fake_get
        try:
            r = probe_404("https://x.com", delay=0)
        finally:
            sc.http_get = orig
        self.assertTrue(r["soft_404"])
        self.assertEqual(r["status"], 200)

    def test_hard_404_ok(self):
        from geosentry.site_crawler import probe_404, FetchResult
        import geosentry.site_crawler as sc
        body = b"<html><body><a href='/'>Home</a>" + b"404 not found. " * 30 + b"</body></html>"
        sc.http_get = lambda url, **kw: FetchResult(url=url, status=404,
                                                     final_url=url, body=body)
        r = probe_404("https://x.com", delay=0)
        self.assertFalse(r["soft_404"])
        self.assertTrue(r["has_home_link"])
        self.assertGreater(r["body_len"], 200)


class TestScoring(unittest.TestCase):
    def test_grade_A(self):
        s = compute_overall_score(
            security_results=[{"passed": True, "severity": "severe"}] * 2 +
                             [{"passed": True, "severity": "medium"}] * 2)
        self.assertEqual(s["grade"], "A")
        self.assertEqual(s["pct"], 100.0)

    def test_grade_F_when_all_fail(self):
        s = compute_overall_score(
            security_results=[{"passed": False, "severity": "severe"}])
        self.assertEqual(s["grade"], "F")
        self.assertEqual(s["pct"], 0.0)

    def test_offline_skips_categories(self):
        s = compute_overall_score()
        self.assertEqual(s["earned"], 0)
        self.assertEqual(s["total"], 0)


class TestSitemapQuality(unittest.TestCase):
    def test_valid_sitemap(self):
        xml = ('<?xml version="1.0"?><urlset>'
               '<url><loc>https://x.com/</loc><lastmod>2024-01-01</lastmod></url>'
               '<url><loc>https://x.com/about</loc></url></urlset>')
        robots = "Sitemap: https://x.com/sitemap.xml\n"
        q = analyze_sitemap_quality(xml, robots, [])
        self.assertTrue(q["xml_valid"])
        self.assertTrue(q["has_url_entries"])
        self.assertTrue(q["has_lastmod"])
        self.assertTrue(q["robots_declares_sitemap"])

    def test_privacy_leaked(self):
        xml = ('<urlset><url><loc>https://x.com/privacy</loc></url>'
               '<url><loc>https://x.com/about</loc></url></urlset>')
        q = analyze_sitemap_quality(xml, "", [])
        self.assertEqual(len(q["privacy_leaked"]), 1)


class TestImageAnalysis(unittest.TestCase):
    def test_good_images(self):
        html = ('<img src="/a.webp" width="800" height="600" alt="hero" fetchpriority="high">'
                 '<img src="/b.jpg" loading="lazy" width="400" height="300" alt="b">')
        r = analyze_images(html, "https://x.com")
        self.assertEqual(r["total"], 2)
        self.assertTrue(r["has_dimensions"])
        self.assertTrue(r["uses_modern_format"])
        self.assertTrue(r["has_alt"])
        self.assertTrue(r["has_fetchpriority"])

    def test_no_images(self):
        r = analyze_images("<p>no images</p>", "https://x.com")
        self.assertEqual(r["total"], 0)


class TestExternalStubs(unittest.TestCase):
    def test_dns_skips_without_dnspython(self):
        from geosentry.site_external import run_dns_email_checks
        r = run_dns_email_checks("example.com")
        # 没装 dnspython 时应 skipped=True
        self.assertTrue(r.get("skipped") or "records" in r)



class TestOnlinePipelineWiring(unittest.TestCase):
    """CLI 级集成测试：monkeypatch 网络层，跑完整在线 audit 流程，
    断言报告 HTML 里出现'加权总分'卡片和'技术与安全响应头'小节。"""

    def test_online_report_contains_new_sections(self):
        import tempfile, argparse
        from pathlib import Path as _P
        from unittest import mock
        from geosentry import cli
        from geosentry import site_crawler as sc
        from geosentry.site_crawler import FetchResult

        def fake_get(url, **kw):
            if "nonexistent" in url:
                return FetchResult(url=url, status=404, final_url=url,
                                   body=b"<html><body><a href='/'>Home</a>404 not found. " * 10,
                                   headers={})
            return FetchResult(url=url, status=200, final_url=url,
                               body=b"<html><head><title>Test</title></head>"
                                    b"<body><h1>Hello</h1><img src='/a.webp' width='800' height='600' alt='a'></body></html>",
                               headers={
                                   "Strict-Transport-Security": "max-age=31536000",
                                   "Content-Security-Policy": "default-src 'self'",
                                   "X-Frame-Options": "DENY",
                                   "X-Content-Type-Options": "nosniff",
                               })

        with mock.patch.object(sc, "fetch_robots", return_value="Sitemap: https://x.com/sitemap.xml\n"), \
             mock.patch.object(sc, "fetch_sitemap",
                               return_value=["https://x.com/", "https://x.com/about"]), \
             mock.patch.object(sc, "bfs_discover", return_value=[]), \
             mock.patch.object(sc, "http_get", side_effect=fake_get), \
             mock.patch.object(sc, "probe_dead_links", return_value=[]), \
             mock.patch.object(sc, "probe_404",
                               return_value={"tested_url": "https://x.com/nope",
                                             "status": 404, "soft_404": False,
                                             "body_len": 500, "has_home_link": True,
                                             "custom_404_ok": True}), \
             mock.patch.object(sc, "crawl_site",
                               return_value={"site": "https://x.com",
                                             "counts": {"unique": 2, "html": 2, "pdf": 0},
                                             "html_urls": ["https://x.com/", "https://x.com/about"],
                                             "pages": {
                                                 "https://x.com/": {"status": 200, "parsed": {}},
                                                 "https://x.com/about": {"status": 200, "parsed": {}},
                                             },
                                             "pdfs": []}), \
             mock.patch("geosentry.site_external.run_pagespeed",
                        return_value={"skipped": True, "error": "test mock"}), \
             mock.patch("geosentry.site_audit.cross_page_analysis",
                        return_value={"title_duplicates": {}, "desc_duplicates": {},
                                      "similar_pairs": [], "orphans": [],
                                      "dead_links": [], "unknown_internal_hrefs": [],
                                      "trailing_slash_duos": []}), \
             mock.patch("geosentry.site_audit.build_facts",
                        return_value={"rows": [], "issues_count": {"critical": 0, "major": 0, "minor": 0},
                                      "counts": {"html": 2, "pdf": 0},
                                      "title_duplicates": {}, "desc_duplicates": {},
                                      "similar_top": [], "similar_total": 0,
                                      "orphans": [], "dead_links": [], "pdfs": [],
                                      "trailing_slash_duos": []}), \
             tempfile.TemporaryDirectory() as td:
            ns = argparse.Namespace(
                url="https://x.com", deep=True, out=td, offline=None,
                delay=0, no_verify_ssl=False, max_pages=None,
                bfs=False, bfs_fallback=True)
            cli._cmd_audit_deep(ns)
            report = (_P(td) / "audit-report.html").read_text(encoding="utf-8")

        self.assertIn("加权总分", report)
        self.assertIn("技术与安全响应头", report)
        self.assertIn("sitemap 质量", report)
        self.assertIn("图片优化", report)
        self.assertIn("软 404", report)


if __name__ == "__main__":
    unittest.main()
