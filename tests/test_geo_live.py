"""M2.1 GEO LIVE 测试（mock LLM，不联网）。"""
import unittest
from unittest import mock
from geosentry.geo_live import analyze_answer, run_geo_live


class TestAnalyzeAnswer(unittest.TestCase):
    def test_mention_no_citation(self):
        answer = "We recommend hbyagada as a good flange manufacturer."
        r = analyze_answer(answer, ["hbyagada", "yajiada"], "https://hbyagada.com")
        self.assertTrue(r["mentioned"])
        self.assertFalse(r["cited"])

    def test_citation(self):
        answer = "Check https://hbyagada.com for details."
        r = analyze_answer(answer, ["hbyagada"], "https://hbyagada.com")
        self.assertTrue(r["mentioned"])
        self.assertTrue(r["cited"])

    def test_neither(self):
        answer = "There are many flange suppliers in China."
        r = analyze_answer(answer, ["hbyagada"], "https://hbyagada.com")
        self.assertFalse(r["mentioned"])
        self.assertFalse(r["cited"])


class TestRunGeoLive(unittest.TestCase):
    def test_summary_rates(self):
        answers = [
            "hbyagada is a good maker.",
            "Try hbyagada.com for details.",
            "Many suppliers available.",
        ]
        with mock.patch("geosentry.geo_live.call_llm", side_effect=answers):
            r = run_geo_live("https://hbyagada.com",
                             ["q1", "q2", "q3"],
                             ["hbyagada"], "k", "http://x/v1", "m")
        self.assertEqual(r["total_queries"], 3)
        self.assertEqual(r["mention_count"], 2)
        self.assertEqual(r["citation_count"], 1)
        self.assertAlmostEqual(r["mention_rate"], 0.667, places=2)


if __name__ == "__main__":
    unittest.main()
