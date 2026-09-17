from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.evaluator import (  # noqa: E402
    GeminiReplyJudge,
    judge_human_agreement,
    load_golden_intents,
    score_intent_predictions,
    score_reply_judgments,
)


class FakeClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.models = self

    def generate_content(self, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(text=json.dumps(self.payload))


class EvaluatorTests(unittest.TestCase):
    def test_load_human_golden_set(self) -> None:
        golden = load_golden_intents(ROOT / "eval" / "golden_set_human_labelled.csv")
        self.assertEqual(len(golden), 150)
        self.assertIn("GH-001", golden)

    def test_intent_metrics_and_id_alignment(self) -> None:
        golden = {"GH-001": "delivery", "GH-002": "payment", "GH-003": "delivery"}
        metrics = score_intent_predictions(
            golden,
            [
                {"example_id": "GH-001", "intent": "delivery"},
                {"example_id": "GH-002", "intent": "delivery"},
                {"example_id": "GH-003", "intent": "delivery"},
            ],
        )
        self.assertEqual(metrics["count"], 3)
        self.assertEqual(metrics["accuracy"], 0.6667)
        with self.assertRaises(ValueError):
            score_intent_predictions(golden, [{"example_id": "GH-001", "intent": "delivery"}])

    def test_reply_aggregation_and_agreement(self) -> None:
        judgments = [
            {"relevance": 5, "groundedness": 4, "helpfulness": 4, "tone": 5, "safety": 5, "escalation_appropriateness": 4, "passed": True, "critical_unsupported_claim": False},
            {"relevance": 2, "groundedness": 1, "helpfulness": 2, "tone": 3, "safety": 1, "escalation_appropriateness": 2, "passed": False, "critical_unsupported_claim": True},
        ]
        result = score_reply_judgments(judgments)
        self.assertEqual(result["pass_rate"], 0.5)
        self.assertEqual(result["critical_unsupported_claim_rate"], 0.5)
        agreement = judge_human_agreement([5, 2], [4, 1], [True, False], [True, False])
        self.assertEqual(agreement["pass_fail_agreement"], 1.0)

    def test_gemini_judge_structured_output(self) -> None:
        client = FakeClient({
            "relevance": 5, "groundedness": 4, "helpfulness": 4, "tone": 5,
            "safety": 5, "escalation_appropriateness": 4, "passed": True,
            "critical_unsupported_claim": False, "rationale": "Supported and useful.",
        })
        score = GeminiReplyJudge(client=client).judge(
            customer_message="Where is my parcel?", intent="delivery_or_courier_issue",
            reply="Please contact support so we can investigate.", evidence=[{"case_id": "1"}],
        )
        self.assertEqual(score.groundedness, 4)


if __name__ == "__main__":
    unittest.main()
