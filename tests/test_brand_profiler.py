from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.brand_profiler import profile_brands


FIELDS = [
    "tweet_id",
    "author_id",
    "inbound",
    "created_at",
    "text",
    "response_tweet_id",
    "in_response_to_tweet_id",
]


class BrandProfilerTests(unittest.TestCase):
    def test_ranks_outbound_brands_and_verifies_customer_links(self) -> None:
        rows = [
            ["1", "customer-1", "True", "", "Need help", "2", ""],
            [
                "2",
                "BrandA",
                "False",
                "",
                "@123 We can help at https://example.com/help",
                "",
                "1",
            ],
            ["3", "customer-2", "True", "", "Another issue", "4", ""],
            ["4", "BrandA", "False", "", "Try this", "", "3"],
            ["5", "BrandA", "False", "", "Announcement", "", ""],
            ["6", "BrandB", "False", "", "Reply", "", "999"],
            ["7", "BrandB", "False", "", "Post", "", ""],
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "fixture.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(FIELDS)
                writer.writerows(rows)

            result = profile_brands(csv_path, top_n=2, sample_size=1, seed=7)

        self.assertEqual(result["total_rows"], 7)
        self.assertEqual(result["winner_by_occurrence"], "BrandA")
        self.assertEqual(result["top_brands"][0]["outbound_tweets"], 3)
        self.assertEqual(result["top_brands"][0]["verified_customer_replies"], 2)
        self.assertEqual(
            result["top_brands"][0]["unique_customer_messages_replied_to"], 2
        )
        self.assertEqual(result["top_brands"][1]["verified_customer_replies"], 0)
        self.assertTrue(result["winner_sample_pairs"][0]["customer_text"])
        sample_reply = result["winner_sample_pairs"][0]["brand_reply_text"]
        self.assertNotIn("@123", sample_reply)
        self.assertNotIn("https://example.com/help", sample_reply)
        self.assertEqual(result["source_file"], "fixture.csv")

    def test_rejects_missing_required_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "bad.csv"
            csv_path.write_text("tweet_id,author_id\n1,BrandA\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing required columns"):
                profile_brands(csv_path)


if __name__ == "__main__":
    unittest.main()
