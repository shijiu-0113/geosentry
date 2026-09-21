"""M1.1 hreflang 解析与交叉校验测试。"""
import unittest
from geosentry.site_audit import parse_page, flag_page, cross_page_analysis


class TestHreflangParse(unittest.TestCase):
    def test_hreflang_collected(self):
        html = (
            '<html><head>'
            '<link rel="alternate" hreflang="en" href="https://x.com/en/">'
            '<link rel="alternate" hreflang="zh" href="https://x.com/zh/">'
            '<link rel="alternate" hreflang="x-default" href="https://x.com/">'
            '</head><body><h1>Hi</h1></body></html>'
        )
        r = parse_page(html, "https://x.com/en/", "x.com")
        hls = r["hreflangs"]
        self.assertEqual(len(hls), 3)
        langs = [h["hreflang"] for h in hls]
        self.assertIn("en", langs)
        self.assertIn("zh", langs)
        self.assertIn("x-default", langs)

    def test_no_hreflang(self):
        html = '<html><head><title>t</title></head><body><h1>h</h1></body></html>'
        r = parse_page(html, "https://x.com/", "x.com")
        self.assertEqual(r["hreflangs"], [])


class TestHreflangFlags(unittest.TestCase):
    def test_missing_xdefault_flag(self):
        html = (
            '<html><head>'
            '<link rel="alternate" hreflang="en" href="https://x.com/en/">'
            '<link rel="alternate" hreflang="zh" href="https://x.com/zh/">'
            '</head><body><h1>Hi</h1></body></html>'
        )
        r = parse_page(html, "https://x.com/en/", "x.com")
        rec = {"status": 200, "parsed": r}
        flags = flag_page("https://x.com/en/", rec)
        self.assertTrue(any("x-default" in m for sev, m in flags if sev == "major"))

    def test_with_xdefault_no_flag(self):
        html = (
            '<html><head>'
            '<link rel="alternate" hreflang="en" href="https://x.com/en/">'
            '<link rel="alternate" hreflang="x-default" href="https://x.com/">'
            '</head><body><h1>Hi</h1></body></html>'
        )
        r = parse_page(html, "https://x.com/en/", "x.com")
        rec = {"status": 200, "parsed": r}
        flags = flag_page("https://x.com/en/", rec)
        self.assertFalse(any("x-default" in m for sev, m in flags))


class TestHreflangCrossRef(unittest.TestCase):
    def test_bidirectional_ok(self):
        en_html = (
            '<html><head>'
            '<link rel="alternate" hreflang="en" href="https://x.com/en/">'
            '<link rel="alternate" hreflang="zh" href="https://x.com/zh/">'
            '</head><body><h1>Hi</h1></body></html>'
        )
        zh_html = (
            '<html><head>'
            '<link rel="alternate" hreflang="en" href="https://x.com/en/">'
            '<link rel="alternate" hreflang="zh" href="https://x.com/zh/">'
            '</head><body><h1>你好</h1></body></html>'
        )
        pages = {
            "https://x.com/en/": {"status": 200, "parsed": parse_page(en_html, "https://x.com/en/", "x.com")},
            "https://x.com/zh/": {"status": 200, "parsed": parse_page(zh_html, "https://x.com/zh/", "x.com")},
        }
        cross = cross_page_analysis(pages, "x.com")
        self.assertEqual(cross["hreflang_issues"], [])

    def test_oneway_ref_flagged(self):
        en_html = (
            '<html><head>'
            '<link rel="alternate" hreflang="zh" href="https://x.com/zh/">'
            '</head><body><h1>Hi</h1></body></html>'
        )
        zh_html = '<html><head><title>z</title></head><body><h1>你好</h1></body></html>'
        pages = {
            "https://x.com/en/": {"status": 200, "parsed": parse_page(en_html, "https://x.com/en/", "x.com")},
            "https://x.com/zh/": {"status": 200, "parsed": parse_page(zh_html, "https://x.com/zh/", "x.com")},
        }
        cross = cross_page_analysis(pages, "x.com")
        self.assertTrue(len(cross["hreflang_issues"]) >= 1)


if __name__ == "__main__":
    unittest.main()
