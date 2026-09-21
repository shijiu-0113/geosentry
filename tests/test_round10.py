"""收尾三项接线测试（mock HTTP，不联网）。"""
import unittest
from unittest import mock
from geosentry.site_crawler import parse_crawl_delay
from geosentry.content_extract import extract_main_content


class TestCrawlDelay(unittest.TestCase):
    def test_parse_crawl_delay(self):
        robots = "User-agent: *\nCrawl-delay: 5\nDisallow: /admin"
        self.assertEqual(parse_crawl_delay(robots), 5.0)
    def test_no_crawl_delay(self):
        self.assertIsNone(parse_crawl_delay("User-agent: *\nDisallow: /admin"))
    def test_agent_specific(self):
        robots = "User-agent: Googlebot\nCrawl-delay: 1\n\nUser-agent: *\nCrawl-delay: 10"
        self.assertEqual(parse_crawl_delay(robots, "Googlebot"), 1.0)


class TestBM25Content(unittest.TestCase):
    def test_bm25_mode(self):
        html = "<nav>menu</nav><p>Flanges are used in piping systems for connections.</p>" \
               "<p>Another paragraph about industrial equipment and valves.</p>"
        text = extract_main_content(html, "bm25")
        self.assertTrue(len(text) > 10)


class TestConcurrencyParam(unittest.TestCase):
    def test_crawl_site_accepts_concurrency(self):
        from geosentry.site_crawler import crawl_site
        import inspect
        sig = inspect.signature(crawl_site)
        self.assertIn("concurrency", sig.parameters)


if __name__ == "__main__":
    unittest.main()
