from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_intent_dev_pilot import redact  # noqa: E402
from support_agent.intent_discovery import sample_cases  # noqa: E402
from support_agent.taxonomy import load_taxonomy  # noqa: E402


class IntentDevPilotTests(unittest.TestCase):
    def test_redaction_removes_email_and_numbers(self) -> None:
        self.assertEqual(
            redact("Order 123-456 for name@example.com"),
            "Order [NUMBER]-[NUMBER] for [EMAIL]",
        )

    def test_labels_match_fixed_dev_sample_and_taxonomy(self) -> None:
        manifest = json.loads(
            (ROOT / "eval" / "intent_dev_pilot_labels.json").read_text(encoding="utf-8")
        )
        cases = sample_cases(
            ROOT / manifest["source"],
            sample_size=manifest["sample_size"],
            seed=manifest["sample_seed"],
        )
        self.assertEqual(
            {str(case["case_id"]) for case in cases},
            set(manifest["labels"]) | set(manifest["excluded"]),
        )
        names = {
            intent["name"]
            for intent in load_taxonomy(ROOT / "configs" / "intents.yaml")["intents"]
        }
        self.assertTrue(set(manifest["labels"].values()) <= names)


if __name__ == "__main__":
    unittest.main()
