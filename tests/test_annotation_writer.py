from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.annotation_writer import apply_annotation_proposals


class AnnotationWriterTests(unittest.TestCase):
    def test_builds_complete_proposal_copy_without_overwriting_pilot(self) -> None:
        source = PROJECT_ROOT / "eval" / "golden_set_review.csv"
        with source.open("r", encoding="utf-8-sig", newline="") as source_file:
            original_rows = list(csv.DictReader(source_file))

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "labelled.csv"
            result = apply_annotation_proposals(
                source,
                PROJECT_ROOT / "eval" / "assistant_label_proposals.json",
                PROJECT_ROOT
                / "data"
                / "processed"
                / "amazonhelp_cases"
                / "test.jsonl",
                output,
            )
            with output.open("r", encoding="utf-8-sig", newline="") as output_file:
                rows = list(csv.DictReader(output_file))

        by_id = {row["example_id"]: row for row in rows}
        self.assertEqual(result["row_count"], 150)
        self.assertEqual(result["user_pilot_rows"], 20)
        self.assertEqual(result["assistant_proposed_rows"], 130)
        self.assertEqual(by_id["GH-001"]["gold_intent"], original_rows[0]["gold_intent"])
        self.assertEqual(by_id["GH-007"]["gold_intent"], "13")
        self.assertEqual(by_id["GH-014"]["gold_intent"], "13")
        self.assertEqual(by_id["GH-021"]["review_status"], "assistant_proposed")
        self.assertEqual(by_id["GH-043"]["case_id"], "2831688")
        self.assertEqual(by_id["GH-052"]["case_id"], "2830660")
        self.assertEqual(by_id["GH-088"]["case_id"], "2831668")
        self.assertTrue(all(row["gold_intent"] for row in rows))
        self.assertTrue(all(row["intent_name"] for row in rows))
        self.assertEqual(len({row["thread_id"] for row in rows}), 150)


if __name__ == "__main__":
    unittest.main()
