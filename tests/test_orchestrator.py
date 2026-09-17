from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.intent_classifier import IntentPrediction  # noqa: E402
from support_agent.orchestrator import SupportAgent  # noqa: E402
from support_agent.reply_generator import ReplyDraft  # noqa: E402


class FakeClassifier:
    def __init__(self, prediction: IntentPrediction) -> None:
        self.prediction = prediction

    def predict(self, message: str, context: list[str]) -> IntentPrediction:
        return self.prediction


class FakeRetriever:
    def __init__(self, evidence: list[dict[str, object]]) -> None:
        self.evidence = evidence

    def search(self, message: str, *, k: int) -> list[dict[str, object]]:
        self.last_k = k
        return self.evidence


class FakeGenerator:
    def __init__(self, draft: ReplyDraft) -> None:
        self.draft = draft

    def generate(self, message: str, intent: str, evidence: list[dict[str, object]], context: list[str]) -> ReplyDraft:
        self.last_intent = intent
        return self.draft


class FailingGenerator(FakeGenerator):
    def generate(self, message: str, intent: str, evidence: list[dict[str, object]], context: list[str]) -> ReplyDraft:
        raise RuntimeError("synthetic provider failure")


def prediction(intent: str, confidence: float = 0.95) -> IntentPrediction:
    return IntentPrediction(intent=intent, confidence=confidence, reason="Test reason")


def draft(supported: bool = True, unsupported_claim: bool = False) -> ReplyDraft:
    return ReplyDraft(
        reply="Please check the delivery details.",
        supported=supported,
        evidence_case_ids=["case-1"] if supported else [],
        unsupported_claim=unsupported_claim,
        support_note="Test evidence.",
    )


class OrchestratorTests(unittest.TestCase):
    def test_clear_low_risk_case_auto_handles(self) -> None:
        agent = SupportAgent(
            FakeClassifier(prediction("delivery_or_courier_issue")),
            FakeRetriever([{"case_id": "case-1", "similarity": 0.86}]),
            FakeGenerator(draft()),
        )
        result = agent.handle_message("Where is my parcel?")
        self.assertEqual(result.decision, "AUTO_HANDLE")
        self.assertEqual(result.intent, "delivery_or_courier_issue")
        self.assertEqual(agent.retriever.last_k, 5)

    def test_refund_case_escalates(self) -> None:
        agent = SupportAgent(
            FakeClassifier(prediction("return_refund_or_replacement")),
            FakeRetriever([{"case_id": "case-1", "similarity": 0.95}]),
            FakeGenerator(draft()),
        )
        result = agent.handle_message("I need a refund.")
        self.assertEqual(result.decision, "ESCALATE")
        self.assertEqual(result.decision_reason, "HIGH_RISK_TOPIC")

    def test_unsupported_reply_escalates(self) -> None:
        agent = SupportAgent(
            FakeClassifier(prediction("delivery_or_courier_issue")),
            FakeRetriever([{"case_id": "case-1", "similarity": 0.90}]),
            FakeGenerator(draft(supported=False, unsupported_claim=True)),
        )
        result = agent.handle_message("Where is my parcel?")
        self.assertEqual(result.decision, "ESCALATE")
        self.assertEqual(result.decision_reason, "UNSUPPORTED_REPLY")

    def test_blank_message_is_rejected(self) -> None:
        agent = SupportAgent(FakeClassifier(prediction("delivery_or_courier_issue")), FakeRetriever([]), FakeGenerator(draft()))
        with self.assertRaises(ValueError):
            agent.handle_message(" ")

    def test_generator_failure_returns_safe_handoff_and_escalates(self) -> None:
        agent = SupportAgent(
            FakeClassifier(prediction("delivery_or_courier_issue")),
            FakeRetriever([{"case_id": "case-1", "similarity": 0.90}]),
            FailingGenerator(draft()),
        )
        result = agent.handle_message("Where is my parcel?")
        self.assertEqual(result.decision, "ESCALATE")
        self.assertEqual(result.decision_reason, "GENERATOR_FAILURE")
        self.assertEqual(result.generator_error, "RuntimeError")


if __name__ == "__main__":
    unittest.main()
