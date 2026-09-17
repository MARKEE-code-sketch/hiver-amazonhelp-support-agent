"""Small, deterministic human-in-the-loop policy for support replies."""

from __future__ import annotations

from collections.abc import Iterable, Sequence


INTENT_CONFIDENCE_THRESHOLD = 0.80
RETRIEVAL_SIMILARITY_THRESHOLD = 0.70

# These categories are deliberately conservative for the first version.
HIGH_RISK_INTENTS = frozenset(
    {
        "account_access_or_security",
        "payment_charge_or_gift_card",
        "return_refund_or_replacement",
    }
)
HIGH_RISK_TAGS = frozenset(
    {"unauthorized_access", "payment_dispute", "legal_or_safety", "personal_data"}
)

ESCALATION_INSTRUCTIONS = """Escalate to a human when the issue is ambiguous, the customer needs account or personal-data action, or the issue involves payment, refund, unauthorized access, legal/safety concerns, or unsupported policy claims. Do not promise refunds, account changes, compensation, or timelines. Auto-handle only a clear, low-risk request with strong historical evidence and a supported reply."""


def decide(
    *,
    intent: str,
    intent_confidence: float,
    evidence: Sequence[dict[str, object]] | None,
    reply_supported: bool,
    ambiguous: bool = False,
    unsupported_claim: bool = False,
    context_sufficient: bool = True,
    risk_tags: Iterable[str] = (),
) -> dict[str, str | float]:
    """Return an auditable AUTO_HANDLE or ESCALATE decision.

    Rules are ordered so a high-risk reason wins when several checks fail.
    Thresholds are intentionally conservative and are not calibrated yet.
    """

    if not 0 <= intent_confidence <= 1:
        raise ValueError("intent_confidence must be between 0 and 1")
    tags = {str(tag) for tag in risk_tags}
    top_similarity = max(
        (float(item.get("similarity", 0.0)) for item in (evidence or [])),
        default=0.0,
    )

    reason_code = None
    if intent in HIGH_RISK_INTENTS or tags & HIGH_RISK_TAGS:
        reason_code = "HIGH_RISK_TOPIC"
    elif ambiguous or intent == "other_or_ambiguous":
        reason_code = "AMBIGUOUS_INTENT"
    elif intent_confidence < INTENT_CONFIDENCE_THRESHOLD:
        reason_code = "LOW_INTENT_CONFIDENCE"
    elif not context_sufficient:
        reason_code = "INSUFFICIENT_CONTEXT"
    elif not evidence or top_similarity < RETRIEVAL_SIMILARITY_THRESHOLD:
        reason_code = "LOW_RETRIEVAL_CONFIDENCE"
    elif unsupported_claim or not reply_supported:
        reason_code = "UNSUPPORTED_REPLY"

    if reason_code:
        return {
            "decision": "ESCALATE",
            "decision_reason": reason_code,
            "top_similarity": round(top_similarity, 4),
        }
    return {
        "decision": "AUTO_HANDLE",
        "decision_reason": "CLEAR_LOW_RISK_SUPPORTED_CASE",
        "top_similarity": round(top_similarity, 4),
    }
