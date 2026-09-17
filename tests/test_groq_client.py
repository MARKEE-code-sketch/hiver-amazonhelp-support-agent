from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.groq_client import GroqStructuredClient  # noqa: E402


class FakeCompletions:
    def create(self, **kwargs: object) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))]
        )


class FakeGroq:
    def __init__(self, **kwargs: object) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions())


class GroqClientTests(unittest.TestCase):
    def test_adapter_returns_text_and_uses_json_mode(self) -> None:
        with patch("support_agent.groq_client.Groq", FakeGroq), patch.dict(
            os.environ, {"GROQ_API_KEY": "test-key"}, clear=False
        ):
            client = GroqStructuredClient()
            result = client.models.generate_content(
                model="ignored", contents="test", config=SimpleNamespace(system_instruction="Rules")
            )
        self.assertEqual(result.text, '{"ok": true}')

    def test_missing_key_is_rejected(self) -> None:
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            GroqStructuredClient()


if __name__ == "__main__":
    unittest.main()
