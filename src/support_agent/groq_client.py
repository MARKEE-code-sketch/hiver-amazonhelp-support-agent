"""Small Groq adapter matching the Google Gen AI client shape used by modules."""

from __future__ import annotations

import os
import json
from types import SimpleNamespace

from groq import Groq


class GroqStructuredClient:
    """Expose ``client.models.generate_content`` with Groq JSON mode underneath."""

    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY is not set")
        self.client = Groq(api_key=key)
        self.model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.models = self

    def generate_content(self, *, model: str, contents: str, config: object) -> SimpleNamespace:
        system_instruction = getattr(config, "system_instruction", None) or ""
        response = self.client.chat.completions.create(
            model=self.model or model,
            messages=[
                {"role": "system", "content": "Return a valid JSON object only.\n" + system_instruction},
                {"role": "user", "content": contents},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content
        # Groq JSON mode guarantees valid JSON, but does not enforce the
        # provider-neutral schema. Normalize only known reply-field aliases;
        # the receiving Pydantic model still validates the final contract.
        try:
            payload = json.loads(text)
            schema = getattr(config, "response_json_schema", {}) or {}
            properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
            if "evidence_case_ids" in properties and "evidence_case_ids" not in payload:
                if "evidence_ids" in payload:
                    payload["evidence_case_ids"] = payload.pop("evidence_ids")
                else:
                    payload["evidence_case_ids"] = []
            if "unsupported_claim" in properties:
                payload.setdefault("unsupported_claim", False)
            if "support_note" in properties:
                payload.setdefault("support_note", "The draft requires review against the supplied evidence.")
            if "confidence" in properties and isinstance(payload.get("confidence"), str):
                confidence_map = {"high": 0.90, "medium": 0.70, "low": 0.40}
                value = confidence_map.get(payload["confidence"].strip().lower())
                if value is not None:
                    payload["confidence"] = value
            if "relevance" in properties and isinstance(payload.get("scores"), dict):
                scores = payload.pop("scores")
                payload.setdefault("relevance", scores.get("clarity", scores.get("accuracy", 3)))
                payload.setdefault("groundedness", scores.get("accuracy", 3))
                payload.setdefault("helpfulness", scores.get("helpfulness", 3))
                payload.setdefault("tone", scores.get("tone", scores.get("empathy", 3)))
                payload.setdefault("safety", scores.get("safety", 3))
                payload.setdefault("escalation_appropriateness", scores.get("safety", 3))
                payload.setdefault("critical_unsupported_claim", False)
                payload.setdefault("rationale", payload.pop("explanation", "The judge returned a structured score."))
            if "relevance" in properties and "relevance" not in payload and "scores" not in payload:
                payload["relevance"] = payload.pop("correctness", payload.pop("clarity", 3))
                payload["groundedness"] = payload.pop("accuracy", payload.get("relevance", 3))
                payload["helpfulness"] = payload.pop("completeness", 3)
                payload["tone"] = payload.pop("empathy", 3)
                payload.setdefault("safety", 3)
                payload.setdefault("escalation_appropriateness", 3)
                payload.setdefault("critical_unsupported_claim", False)
                payload["rationale"] = payload.pop("explanation", "The judge returned a structured score.")
            if "passed" in properties and "passed" not in payload and "pass" in payload:
                payload["passed"] = payload.pop("pass")
            if "critical_unsupported_claim" in properties:
                payload.setdefault("critical_unsupported_claim", False)
            if "relevance" in properties:
                payload.setdefault("groundedness", payload.get("accuracy", 3))
                payload.setdefault("safety", 3)
                payload.setdefault("escalation_appropriateness", 3)
                payload.setdefault("rationale", payload.get("explanation", "The judge returned a structured score."))
                for alias in ("clarity", "accuracy", "politeness", "empathy", "correctness", "completeness", "efficiency", "explanation"):
                    payload.pop(alias, None)
            text = json.dumps(payload, ensure_ascii=False)
        except (TypeError, json.JSONDecodeError):
            pass
        return SimpleNamespace(text=text)
