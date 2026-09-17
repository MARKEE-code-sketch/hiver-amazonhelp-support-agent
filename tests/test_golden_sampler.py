from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.golden_sampler import build_review_sample, sample_review_cases


class GoldenSamplerTests(unittest.TestCase):
    def _write_cases(self, path: Path) -> None:
        cases = []
        for index in range(12):
            cases.append(
                {
                    "case_id": str(index),
                    "thread_id": str(index),
                    "created_at": f"2017-12-01T00:{index:02d}:00+00:00",
                    "customer_text": f"Where is order {index}?",
                    "context": [],
                    "historical_reply": "Please check the tracking page.",
                }
            )
        cases.append(
            {
                "case_id": "duplicate-thread",
                "thread_id": "1",
                "created_at": "2017-12-01T01:00:00+00:00",
                "customer_text": "I still need help with my order",
                "context": [],
                "historical_reply": "We can help.",
            }
        )
        cases.append(
            {
                "case_id": "unusable",
                "thread_id": "unusable",
                "created_at": "2017-12-01T01:01:00+00:00",
                "customer_text": "Done",
                "context": [],
                "historical_reply": "Thank you.",
            }
        )
        path.write_text(
            "".join(json.dumps(case) + "\n" for case in cases), encoding="utf-8"
        )

    def test_sampling_is_deterministic_unique_and_reviewable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "test.jsonl"
            self._write_cases(source)
            first = sample_review_cases(source, sample_size=5, seed=42)
            second = sample_review_cases(source, sample_size=5, seed=42)

        self.assertEqual(first, second)
        self.assertEqual(len({case["thread_id"] for case in first}), 5)
        self.assertNotIn("unusable", {case["case_id"] for case in first})

    def test_writes_blank_human_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "test.jsonl"
            destination = Path(temp_dir) / "review.csv"
            self._write_cases(source)
            result = build_review_sample(source, destination, sample_size=5, seed=7)
            with destination.open("r", encoding="utf-8-sig", newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(result["sample_size"], 5)
        self.assertEqual(result["unique_thread_count"], 5)
        self.assertEqual({row["source_split"] for row in rows}, {"test"})
        self.assertTrue(all(row["gold_intent"] == "" for row in rows))
        self.assertTrue(all(row["review_status"] == "" for row in rows))


if __name__ == "__main__":
    unittest.main()
