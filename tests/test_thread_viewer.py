from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.thread_viewer import find_thread, format_thread


class ThreadViewerTests(unittest.TestCase):
    def test_finds_and_formats_thread(self) -> None:
        thread = {
            "thread_id": "thread-2",
            "brand": "AmazonHelp",
            "started_at": "2017-01-01T00:00:00+00:00",
            "ended_at": "2017-01-01T00:01:00+00:00",
            "messages": [
                {
                    "tweet_id": "customer-2",
                    "role": "customer",
                    "created_at": "2017-01-01T00:00:00+00:00",
                    "text": "Where is my package?",
                },
                {
                    "tweet_id": "reply-2",
                    "role": "brand",
                    "created_at": "2017-01-01T00:01:00+00:00",
                    "text": "Please check the tracking page.",
                },
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "threads.jsonl"
            other = dict(thread, thread_id="thread-1")
            path.write_text(
                json.dumps(other) + "\n" + json.dumps(thread) + "\n",
                encoding="utf-8",
            )
            found_by_id = find_thread(path, thread_id="thread-2")
            found_by_number = find_thread(path, number=2)

        self.assertEqual(found_by_id, thread)
        self.assertEqual(found_by_number, thread)
        formatted = format_thread(thread)
        self.assertIn("# Thread thread-2", formatted)
        self.assertIn("## 1. CUSTOMER", formatted)
        self.assertIn("Where is my package?", formatted)
        self.assertIn("## 2. AMAZONHELP", formatted)

    def test_requires_exactly_one_selector(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "threads.jsonl"
            path.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly one"):
                find_thread(path)


if __name__ == "__main__":
    unittest.main()
