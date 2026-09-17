"""Wire the tested support-agent modules into one deterministic pipeline."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from support_agent.escalation_policy import decide
from support_agent.reply_generator import ReplyDraft, SAFE_HANDOFF


class AgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str
    intent_confidence: float = Field(ge=0, le=1)
    intent_reason: str
    reply: str
    reply_supported: bool
    unsupported_claim: bool
    evidence: list[dict[str, object]]
    decision: str
    decision_reason: str
    top_similarity: float = Field(ge=0)
    generator_error: str | None = None


class SupportAgent:
    """Sequence modules; keep classification, retrieval, generation, and policy separate."""

    def __init__(self, classifier: object, retriever: object, generator: object) -> None:
        self.classifier = classifier
        self.retriever = retriever
        self.generator = generator

    def handle_message(
        self, message: str, context: Sequence[str] | None = None
    ) -> AgentResult:
        if not message.strip():
            raise ValueError("Customer message must not be blank")
        context_items = list(context or [])
        prediction = self.classifier.predict(message, context_items)
        evidence = self.retriever.search(message, k=5)
        generator_error = None
        try:
            draft = self.generator.generate(
                message, prediction.intent, evidence, context_items
            )
        except Exception as error:  # fail closed: never send a guessed reply
            generator_error = type(error).__name__
            draft = ReplyDraft(
                reply=SAFE_HANDOFF,
                supported=False,
                evidence_case_ids=[],
                unsupported_claim=True,
                support_note="Reply generation failed; human review is required.",
            )
        decision = decide(
            intent=prediction.intent,
            intent_confidence=prediction.confidence,
            evidence=evidence,
            reply_supported=draft.supported,
            ambiguous=prediction.intent == "other_or_ambiguous",
            unsupported_claim=draft.unsupported_claim,
        )
        if generator_error:
            decision["decision_reason"] = "GENERATOR_FAILURE"
        return AgentResult(
            intent=prediction.intent,
            intent_confidence=prediction.confidence,
            intent_reason=prediction.reason,
            reply=draft.reply,
            reply_supported=draft.supported,
            unsupported_claim=draft.unsupported_claim,
            evidence=evidence,
            decision=str(decision["decision"]),
            decision_reason=str(decision["decision_reason"]),
            top_similarity=float(decision["top_similarity"]),
            generator_error=generator_error,
        )
