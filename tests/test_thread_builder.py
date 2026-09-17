from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.thread_builder import build_brand_threads


FIELDS = [
    "tweet_id",
    "author_id",
    "inbound",
    "created_at",
    "text",
    "response_tweet_id",
    "in_response_to_tweet_id",
]


def _row(
    tweet_id: str,
    author_id: str,
    inbound: bool,
    minute: int,
    text: str,
    responses: str = "",
    parent: str = "",
) -> list[str]:
    timestamp = f"Tue Oct 31 20:{minute:02d}:00 +0000 2017"
    return [tweet_id, author_id, str(inbound), timestamp, text, responses, parent]


class ThreadBuilderTests(unittest.TestCase):
    def test_builds_complete_ordered_brand_threads(self) -> None:
        rows = [
            _row("1", "customer-a", True, 1, "First issue", "2"),
            _row("2", "AmazonHelp", False, 2, "First reply", "3", "1"),
            _row("3", "customer-a", True, 3, "More context", "4", "2"),
            _row("4", "AmazonHelp", False, 4, "Resolution", "", "3"),
            _row("10", "customer-b", True, 10, "Second issue", "11"),
            _row("11", "AmazonHelp", False, 11, "Second reply", "", "10"),
            _row("20", "AmazonHelp", False, 20, "Announcement"),
            _row("30", "customer-c", True, 30, "Other issue", "31"),
            _row("31", "OtherBrand", False, 31, "Other reply", "", "30"),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "tweets.csv"
            output = Path(temp_dir) / "threads.jsonl"
            with source.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(FIELDS)
                writer.writerows(rows)

            stats = build_brand_threads(source, output, brand="AmazonHelp")
            threads = [json.loads(line) for line in output.read_text().splitlines()]

        self.assertEqual(stats["usable_threads"], 2)
        self.assertEqual(stats["usable_messages"], 6)
        self.assertEqual(stats["cycle_count"], 0)
        self.assertEqual([thread["thread_id"] for thread in threads], ["1", "10"])
        self.assertEqual(
            [message["tweet_id"] for message in threads[0]["messages"]],
            ["1", "2", "3", "4"],
        )
        self.assertNotIn("31", {message["tweet_id"] for thread in threads for message in thread["messages"]})

    def test_rejects_unknown_brand(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "tweets.csv"
            output = Path(temp_dir) / "threads.jsonl"
            with source.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(FIELDS)
                writer.writerow(_row("1", "customer", True, 1, "Help"))

            with self.assertRaisesRegex(ValueError, "No outbound tweets"):
                build_brand_threads(source, output, brand="AmazonHelp")


if __name__ == "__main__":
    unittest.main()
