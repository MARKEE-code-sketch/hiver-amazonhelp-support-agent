from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.golden_freezer import freeze_golden_set


class GoldenFreezerTests(unittest.TestCase):
    def test_freeze_validates_and_preserves_source(self) -> None:
        source = ROOT / "eval" / "golden_set_review_assistant_proposals.csv"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "golden_set.csv"
            manifest_file = Path(directory) / "manifest.json"
            manifest = freeze_golden_set(
                source,
                ROOT / "configs" / "intents.yaml",
                ROOT / "data" / "processed" / "amazonhelp_cases" / "test.jsonl",
                target,
                manifest_file,
            )
            with target.open(encoding="utf-8-sig", newline="") as output_file:
                rows = list(csv.DictReader(output_file))
            self.assertEqual(manifest["row_count"], 150)
            self.assertEqual(manifest["unique_test_threads"], 150)
            self.assertEqual(manifest["review_status_counts"]["user_approved_batch"], 130)
            self.assertEqual(manifest["review_status_counts"]["user_pilot_approved"], 20)
            self.assertEqual(manifest["pilot_disagreements_preserved"], 9)
            self.assertEqual(rows[0]["gold_intent"], "12")
            self.assertEqual(rows[0]["review_status"], "user_pilot_approved")
            self.assertEqual(rows[20]["review_status"], "user_approved_batch")
            with self.assertRaises(FileExistsError):
                freeze_golden_set(
                    source,
                    ROOT / "configs" / "intents.yaml",
                    ROOT / "data" / "processed" / "amazonhelp_cases" / "test.jsonl",
                    target,
                    manifest_file,
                )


if __name__ == "__main__":
    unittest.main()
