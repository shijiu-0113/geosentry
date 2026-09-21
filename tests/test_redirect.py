"""M1.2 重定向链测试。"""
import unittest
from geosentry.site_audit import flag_page


class TestRedirectFlags(unittest.TestCase):
    def _rec(self, chain, final="https://x.com/new"):
        return {
            "status": 200, "final_url": final, "redirect_chain": chain,
            "parsed": {"title": "t", "title_len": 1, "description": "d",
                       "desc_len": 1, "h1_count": 1, "word_count": 500,
                       "canonical": "https://x.com/orig", "og_missing": [],
                       "hreflangs": [], "missing_alt": 0, "heading_skip": False,
                       "jsonld": [], "viewport": "w"},
        }

    def test_301_single_ok(self):
        chain = [("https://x.com/old", 301), ("https://x.com/new", 200)]
        flags = flag_page("https://x.com/old", self._rec(chain))
        # 301 不应报 major
        self.assertFalse(any("302" in m or "307" in m for sev, m in flags if sev == "major"))

    def test_302_should_be_301_major(self):
        chain = [("https://x.com/old", 302), ("https://x.com/new", 200)]
        flags = flag_page("https://x.com/old", self._rec(chain))
        self.assertTrue(any("302" in m for sev, m in flags if sev == "major"))

    def test_long_chain_minor(self):
        chain = [("https://x.com/a", 301), ("https://x.com/b", 301),
                 ("https://x.com/c", 301), ("https://x.com/d", 200)]
        flags = flag_page("https://x.com/a", self._rec(chain))
        self.assertTrue(any("链过长" in m or "长" in m for sev, m in flags if sev == "minor"))

    def test_short_chain_no_minor(self):
        chain = [("https://x.com/old", 301), ("https://x.com/new", 200)]
        flags = flag_page("https://x.com/old", self._rec(chain))
        self.assertFalse(any("链过长" in m for sev, m in flags))


if __name__ == "__main__":
    unittest.main()
