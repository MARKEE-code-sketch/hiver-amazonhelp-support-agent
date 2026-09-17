from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.baselines import SimilarityBaseline, fixed_baseline


class BaselineTests(unittest.TestCase):
    def test_fixed_baseline_is_safe_and_repeatable(self) -> None:
        first = fixed_baseline("Where is my parcel?")
        self.assertEqual(first, fixed_baseline("Where is my parcel?"))
        self.assertEqual(first["action"], "ESCALATE")
        self.assertEqual(first["intent"], "delivery_or_courier_issue")
        with self.assertRaises(ValueError):
            fixed_baseline("  ")

    def test_similarity_uses_train_cases_only_and_returns_evidence(self) -> None:
        cases = [
            {
                "case_id": "1",
                "customer_text": "Where is my parcel delivery?",
                "historical_reply": "Check tracking.",
            },
            {
                "case_id": "2",
                "customer_text": "My card was charged twice",
                "historical_reply": "Please contact support.",
            },
            {
                "case_id": "3",
                "customer_text": "The package was delivered late",
                "historical_reply": "Sorry for the delay.",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            train = Path(directory) / "train.jsonl"
            train.write_text(
                "".join(json.dumps(case) + "\n" for case in cases),
                encoding="utf-8",
            )
            model = SimilarityBaseline(
                train, ROOT / "configs" / "intents.yaml", sample_size=3
            )
            prediction = model.predict("Where is my parcel delivery?")
            self.assertEqual(prediction["evidence_case_id"], "1")
            self.assertIn(prediction["intent"], model.intent_names)
            self.assertEqual(prediction["action"], "ESCALATE")
            self.assertEqual(prediction, model.predict("Where is my parcel delivery?"))
            matches = model.search_cases("Where is my parcel delivery?", k=2)
            self.assertEqual(matches[0]["case_id"], "1")
            self.assertLessEqual(len(matches), 2)
            unknown = model.predict("zzzxxyyq")
            self.assertEqual(unknown["intent"], "other_or_ambiguous")
            self.assertIsNone(unknown["evidence_case_id"])
            with self.assertRaises(ValueError):
                SimilarityBaseline(
                    Path(directory) / "test.jsonl",
                    ROOT / "configs" / "intents.yaml",
                    sample_size=3,
                )


if __name__ == "__main__":
    unittest.main()
