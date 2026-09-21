"""第九轮新模块测试（纯本地，不联网）。"""
import unittest
import tempfile
from pathlib import Path
from geosentry.url_scorer import score_url
from geosentry.content_extract import extract_main_content
from geosentry.cache import DiskCache
from geosentry.rate_limiter import TokenBucket
from geosentry.site_render import render_page


class TestURLScorer(unittest.TestCase):
    def test_homepage_priority(self):
        self.assertLess(score_url("https://x.com/"), score_url("https://x.com/blog/post/1"))
    def test_product_priority(self):
        self.assertLess(score_url("https://x.com/products/flange"),
                        score_url("https://x.com/blog/post/1"))
    def test_penalizes_pagination(self):
        self.assertGreater(score_url("https://x.com/?page=5"), score_url("https://x.com/"))
    def test_static_asset_low_priority(self):
        self.assertGreater(score_url("https://x.com/style.css"), score_url("https://x.com/"))


class TestContentExtract(unittest.TestCase):
    def test_pruning_removes_nav(self):
        html = "<nav>menu</nav><article><p>Flanges are used in piping systems.</p></article><footer>copy</footer>"
        text = extract_main_content(html, "pruning")
        self.assertIn("Flanges", text)
    def test_none_mode(self):
        html = "<div>hello <span>world</span></div>"
        text = extract_main_content(html, "none")
        self.assertIn("hello", text)


class TestDiskCache(unittest.TestCase):
    def test_put_get(self):
        with tempfile.TemporaryDirectory() as td:
            c = DiskCache(Path(td))
            c.put("https://x.com/?utm_source=ig", b"<html>x</html>", etag="abc")
            self.assertEqual(c.get("https://x.com/"), b"<html>x</html>")
            h = c.get_conditional_headers("https://x.com/")
            self.assertEqual(h["If-None-Match"], "abc")
    def test_disabled(self):
        c = DiskCache(Path("/tmp/x"), enabled=False)
        self.assertIsNone(c.get("https://x.com/"))


class TestTokenBucket(unittest.TestCase):
    def test_acquire_blocks(self):
        import time
        tb = TokenBucket(rate_per_sec=10.0)
        t0 = time.monotonic()
        for _ in range(3):
            tb.acquire()
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 0.5)  # 10 rps, 3 tokens should be fast


class TestSiteRender(unittest.TestCase):
    def test_off(self):
        r = render_page("https://x.com", "off")
        self.assertTrue(r["skipped"])
    def test_crawl4ai_not_installed(self):
        r = render_page("https://x.com", "crawl4ai")
        self.assertTrue(r["skipped"])


if __name__ == "__main__":
    unittest.main()
