"""M2.2-M3.4 新功能测试（纯本地，不联网）。"""
import unittest
from geosentry.site_audit import normalize_url, flag_page
from geosentry.site_external import (run_bing_webmaster, check_dkim,
                                     gsc_verification_guide, run_lighthouse_cli)


class TestURLNormalize(unittest.TestCase):
    def test_strips_utm(self):
        self.assertEqual(normalize_url("https://x.com/?utm_source=ig&page=2"),
                         "https://x.com/?page=2")
    def test_strips_gclid(self):
        self.assertEqual(normalize_url("https://x.com/?gclid=abc&x=1"),
                         "https://x.com/?x=1")
    def test_no_query(self):
        self.assertEqual(normalize_url("https://x.com/about"), "https://x.com/about")


class TestJSONLDRequired(unittest.TestCase):
    def test_product_missing_price_critical(self):
        rec = {"parsed": {"jsonld": [{"valid": True, "data": {"@type": "Product", "name": "wheel"}}]}}
        flags = flag_page("https://x.com/p", rec)
        self.assertTrue(any("Product" in f[1] and "offers" in f[1] for f in flags))
    def test_org_ok(self):
        rec = {"parsed": {"jsonld": [{"valid": True, "data": {"@type": "Organization", "name": "Co", "url": "https://x.com"}}]}}
        flags = flag_page("https://x.com/", rec)
        self.assertFalse(any("Organization" in f[1] for f in flags))


class TestExternalStubs(unittest.TestCase):
    def test_bing_no_key(self):
        r = run_bing_webmaster("https://x.com", "")
        self.assertTrue(r["skipped"])
    def test_dkim_no_dnspython(self):
        r = check_dkim("example.com")
        # may be skipped (no dnspython) or found (if installed)
        self.assertIn("skipped", r)
    def test_gsc_guide(self):
        r = gsc_verification_guide("example.com")
        self.assertFalse(r["skipped"])
        self.assertIn("dns_txt", r["guide"])
    def test_lighthouse_not_installed(self):
        r = run_lighthouse_cli("https://x.com")
        self.assertTrue(r["skipped"])


if __name__ == "__main__":
    unittest.main()
