from __future__ import annotations

import json
import sys
import unittest
from types import SimpleNamespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.reply_generator import ReplyGenerator  # noqa: E402


class FakeClient:
    def __init__(self, payload: dict[str, object] | None) -> None:
        self.payload = payload
        self.calls: list[dict[str, object]] = []
        self.models = self

    def generate_content(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(text=None if self.payload is None else json.dumps(self.payload))


EVIDENCE = [
    {
        "case_id": "case-1",
        "customer_text": "Tracking says delivered but nothing arrived.",
        "historical_reply": "Please contact support so we can investigate the delivery.",
        "similarity": 0.86,
    }
]


class ReplyGeneratorTests(unittest.TestCase):
    def test_no_evidence_returns_safe_handoff_without_api_call(self) -> None:
        client = FakeClient(None)
        draft = ReplyGenerator(client=client).generate("Where is my parcel?", "delivery_or_courier_issue", [])
        self.assertFalse(draft.supported)
        self.assertEqual(draft.evidence_case_ids, [])
        self.assertEqual(client.calls, [])

    def test_structured_draft_cites_only_supplied_evidence(self) -> None:
        client = FakeClient({
            "reply": "I’m sorry your parcel is missing. Support can investigate the delivery.",
            "supported": True,
            "evidence_case_ids": ["case-1"],
            "unsupported_claim": False,
            "support_note": "The reply follows the supplied delivery example.",
        })
        draft = ReplyGenerator(client=client).generate(
            "It says delivered but I did not receive it.", "delivered_not_received", EVIDENCE
        )
        self.assertTrue(draft.supported)
        self.assertEqual(draft.evidence_case_ids, ["case-1"])
        self.assertEqual(client.calls[0]["config"].temperature, 0)

    def test_unknown_evidence_id_fails_closed(self) -> None:
        client = FakeClient({
            "reply": "Please contact support.",
            "supported": True,
            "evidence_case_ids": ["not-real"],
            "unsupported_claim": False,
            "support_note": "Evidence.",
        })
        with self.assertRaises(ValueError):
            ReplyGenerator(client=client).generate("Where is my parcel?", "delivery_or_courier_issue", EVIDENCE)

    def test_local_claim_check_marks_unsafe_reply(self) -> None:
        client = FakeClient({
            "reply": "We will issue your refund today.",
            "supported": True,
            "evidence_case_ids": ["case-1"],
            "unsupported_claim": False,
            "support_note": "Evidence.",
        })
        draft = ReplyGenerator(client=client).generate("I need a refund.", "return_refund_or_replacement", EVIDENCE)
        self.assertFalse(draft.supported)
        self.assertTrue(draft.unsupported_claim)

    def test_placeholder_reply_is_replaced_with_actionable_safe_reply(self) -> None:
        client = FakeClient({
            "reply": "Please follow these steps: [URL]",
            "supported": True,
            "evidence_case_ids": ["case-1"],
            "unsupported_claim": False,
            "support_note": "Evidence.",
        })
        draft = ReplyGenerator(client=client).generate(
            "It says delivered but I did not receive it.", "delivered_not_received", EVIDENCE
        )
        self.assertTrue(draft.supported)
        self.assertEqual(draft.evidence_case_ids, ["case-1"])
        self.assertNotIn("[URL]", draft.reply)
        self.assertIn("safe places", draft.reply)

    def test_blank_message_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ReplyGenerator(client=FakeClient(None)).generate(" ", "delivery_or_courier_issue", EVIDENCE)


if __name__ == "__main__":
    unittest.main()
