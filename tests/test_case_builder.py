from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.case_builder import build_cases, clean_text, is_english_candidate


class CaseBuilderTests(unittest.TestCase):
    def test_builds_direct_english_case_with_context(self) -> None:
        thread = {
            "thread_id": "1",
            "messages": [
                {
                    "tweet_id": "1",
                    "author_id": "customer",
                    "role": "customer",
                    "created_at": "2017-01-01T00:00:00+00:00",
                    "text": "My package is late",
                    "in_response_to_tweet_id": None,
                },
                {
                    "tweet_id": "2",
                    "author_id": "AmazonHelp",
                    "role": "brand",
                    "created_at": "2017-01-01T00:01:00+00:00",
                    "text": "@123 Please check your tracking page https://example.com ^AB",
                    "in_response_to_tweet_id": "1",
                },
                {
                    "tweet_id": "3",
                    "author_id": "customer",
                    "role": "customer",
                    "created_at": "2017-01-01T00:02:00+00:00",
                    "text": "I checked it but my order is still missing",
                    "in_response_to_tweet_id": "2",
                },
                {
                    "tweet_id": "4",
                    "author_id": "AmazonHelp",
                    "role": "brand",
                    "created_at": "2017-01-01T00:03:00+00:00",
                    "text": "We can help with your missing order",
                    "in_response_to_tweet_id": "3",
                },
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "threads.jsonl"
            output = Path(temp_dir) / "cases.jsonl"
            source.write_text(json.dumps(thread) + "\n", encoding="utf-8")
            stats = build_cases(source, output)
            cases = [json.loads(line) for line in output.read_text().splitlines()]

        self.assertEqual(stats["english_candidate_cases"], 2)
        self.assertEqual(cases[1]["case_id"], "3")
        self.assertEqual(len(cases[1]["context"]), 2)
        self.assertIn("[USER]", cases[0]["historical_reply"])
        self.assertIn("[URL]", cases[0]["historical_reply"])
        self.assertNotIn("^AB", cases[0]["historical_reply"])

    def test_rejects_obviously_non_english_text(self) -> None:
        self.assertFalse(is_english_candidate("荷物はどこですか"))
        self.assertFalse(is_english_candidate("¿Dónde está mi pedido?"))
        self.assertTrue(is_english_candidate("Where is my missing package?"))

    def test_cleans_platform_noise(self) -> None:
        cleaned = clean_text("@AmazonHelp  Please help https://example.com  ^XY")
        self.assertEqual(cleaned, "[USER] Please help [URL]")


if __name__ == "__main__":
    unittest.main()
