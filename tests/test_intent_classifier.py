from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.intent_classifier import IntentClassifier  # noqa: E402


class FakeClient:
    def __init__(self, text: str | None) -> None:
        self.text = text
        self.calls: list[dict[str, object]] = []
        self.models = self

    def generate_content(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(text=self.text)


class IntentClassifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.taxonomy = ROOT / "configs" / "intents.yaml"

    def test_prediction_uses_approved_labels_and_context(self) -> None:
        client = FakeClient(json.dumps({
            "intent": "delivered_not_received",
            "confidence": 0.81,
            "reason": "Tracking says delivered, but the parcel is missing.",
        }))
        classifier = IntentClassifier(self.taxonomy, client=client)
        result = classifier.predict(
            "It says delivered but I cannot find it", ["Tracking updated today"]
        )
        self.assertEqual(result.intent, "delivered_not_received")
        self.assertEqual(result.confidence, 0.81)
        self.assertIn("Tracking updated today", client.calls[0]["contents"])
        config = client.calls[0]["config"]
        self.assertEqual(config.temperature, 0)
        self.assertEqual(
            set(config.response_json_schema["properties"]["intent"]["enum"]),
            set(classifier.intent_names),
        )

    def test_every_taxonomy_label_is_allowed(self) -> None:
        client = FakeClient(None)
        classifier = IntentClassifier(self.taxonomy, client=client)
        self.assertEqual(len(classifier.intent_names), 13)
        for name in classifier.intent_names:
            client.text = json.dumps({"intent": name, "confidence": 0.5, "reason": "Test"})
            with self.subTest(name=name):
                self.assertEqual(classifier.predict("Example message").intent, name)

    def test_blank_message_does_not_call_api(self) -> None:
        client = FakeClient(None)
        classifier = IntentClassifier(self.taxonomy, client=client)
        with self.assertRaises(ValueError):
            classifier.predict("  ")
        self.assertEqual(client.calls, [])

    def test_invalid_model_outputs_are_rejected(self) -> None:
        client = FakeClient(None)
        classifier = IntentClassifier(self.taxonomy, client=client)
        invalid_outputs = [
            None,
            "not json",
            json.dumps({"intent": "made_up", "confidence": 0.8, "reason": "Test"}),
            json.dumps({"intent": "prime_membership", "confidence": 1.5, "reason": "Test"}),
            json.dumps({"intent": "prime_membership", "confidence": 0.8, "reason": ""}),
        ]
        for output in invalid_outputs:
            client.text = output
            with self.subTest(output=output), self.assertRaises(ValueError):
                classifier.predict("Please cancel Prime")


if __name__ == "__main__":
    unittest.main()
