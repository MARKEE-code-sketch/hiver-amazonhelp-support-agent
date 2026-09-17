from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.escalation_policy import (  # noqa: E402
    ESCALATION_INSTRUCTIONS,
    decide,
)


class EscalationPolicyTests(unittest.TestCase):
    def test_safety_fixture_set(self) -> None:
        fixtures = json.loads(
            (ROOT / "eval" / "escalation_safety_cases.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(fixtures), 12)
        for fixture in fixtures:
            evidence = (
                []
                if fixture["similarity"] is None
                else [{"similarity": fixture["similarity"]}]
            )
            result = decide(
                intent=fixture["intent"],
                intent_confidence=fixture["confidence"],
                evidence=evidence,
                reply_supported=fixture["reply_supported"],
                ambiguous=fixture.get("ambiguous", False),
                context_sufficient=fixture.get("context_sufficient", True),
            )
            with self.subTest(name=fixture["name"]):
                self.assertEqual(result["decision"], fixture["expected"])
                self.assertEqual(result["decision_reason"], fixture["reason"])

    def test_risk_tag_escalates_even_for_low_risk_intent(self) -> None:
        result = decide(
            intent="delivery_or_courier_issue",
            intent_confidence=0.99,
            evidence=[{"similarity": 0.99}],
            reply_supported=True,
            risk_tags=["legal_or_safety"],
        )
        self.assertEqual(result["decision_reason"], "HIGH_RISK_TOPIC")

    def test_threshold_boundaries_are_explicit(self) -> None:
        common = {
            "intent": "delivery_or_courier_issue",
            "evidence": [{"similarity": 0.70}],
            "reply_supported": True,
        }
        self.assertEqual(
            decide(**common, intent_confidence=0.80)["decision"], "AUTO_HANDLE"
        )
        self.assertEqual(
            decide(**common, intent_confidence=0.79)["decision"], "ESCALATE"
        )

    def test_invalid_confidence_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            decide(
                intent="delivery_or_courier_issue",
                intent_confidence=1.1,
                evidence=[],
                reply_supported=True,
            )

    def test_prompt_instructions_cover_hard_rules(self) -> None:
        for phrase in ("ambiguous", "payment", "refund", "unauthorized", "Do not promise"):
            self.assertIn(phrase, ESCALATION_INSTRUCTIONS)


if __name__ == "__main__":
    unittest.main()
