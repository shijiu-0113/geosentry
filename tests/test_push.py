"""M1.5 IndexNow push 测试（mock urllib，不联网）。"""
import unittest
import json
from unittest import mock
from geosentry.site_push import push_indexnow, load_urls_from_facts


class TestIndexNowPush(unittest.TestCase):
    def test_post_body_format(self):
        captured = {}
        class FakeResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        def fake_urlopen(req, timeout=15):
            captured["url"] = req.full_url
            captured["body"] = req.data
            captured["method"] = req.method
            return FakeResp()

        with mock.patch("geosentry.site_push.urllib.request.urlopen",
                        side_effect=fake_urlopen):
            r = push_indexnow("example.com", "abc123",
                              ["https://example.com/", "https://example.com/about"])
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"], 200)
        body = json.loads(captured["body"])
        self.assertEqual(body["host"], "example.com")
        self.assertEqual(body["key"], "abc123")
        self.assertEqual(len(body["urlList"]), 2)
        self.assertIn("keyLocation", body)

    def test_403_not_ok(self):
        import urllib.error
        err = urllib.error.HTTPError("https://api.indexnow.org", 403, "Forbidden", {}, None)
        with mock.patch("geosentry.site_push.urllib.request.urlopen",
                        side_effect=err):
            r = push_indexnow("example.com", "k", ["https://example.com/"])
        self.assertFalse(r["ok"])
        self.assertEqual(r["status"], 403)

    def test_load_urls_from_facts(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "facts.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump({"rows": [{"url": "https://x.com/"},
                                    {"url": "https://x.com/about"}]}, f)
            urls = load_urls_from_facts(__import__("pathlib").Path(fpath))
            self.assertEqual(len(urls), 2)


if __name__ == "__main__":
    unittest.main()
