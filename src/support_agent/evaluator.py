"""Metrics and structured judge helpers for the final evaluation."""

from __future__ import annotations

import csv
import json
import os
from collections.abc import Sequence
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field
from scipy.stats import spearmanr
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score, precision_recall_fscore_support


class ReplyJudgeScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relevance: int = Field(ge=1, le=5)
    groundedness: int = Field(ge=1, le=5)
    helpfulness: int = Field(ge=1, le=5)
    tone: int = Field(ge=1, le=5)
    safety: int = Field(ge=1, le=5)
    escalation_appropriateness: int = Field(ge=1, le=5)
    passed: bool
    critical_unsupported_claim: bool
    rationale: str = Field(min_length=1)


def load_golden_intents(path: str | Path) -> dict[str, str]:
    """Load example_id -> numeric-label-normalized intent from the golden CSV."""

    with Path(path).open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError("Golden set is empty")
    result: dict[str, str] = {}
    for row in rows:
        example_id = str(row.get("example_id", ""))
        intent = str(row.get("intent_name", ""))
        if not example_id or not intent:
            raise ValueError(f"Golden row is missing example_id or intent: {row}")
        if example_id in result:
            raise ValueError(f"Duplicate golden example_id: {example_id}")
        result[example_id] = intent
    return result


def score_intent_predictions(
    golden: dict[str, str], predictions: Sequence[dict[str, object]]
) -> dict[str, object]:
    """Score predictions only when their IDs exactly match the golden IDs."""

    predicted_by_id: dict[str, str] = {}
    for row in predictions:
        example_id = str(row.get("example_id", ""))
        intent = str(row.get("intent", ""))
        if not example_id or not intent:
            raise ValueError("Every prediction needs example_id and intent")
        if example_id in predicted_by_id:
            raise ValueError(f"Duplicate prediction example_id: {example_id}")
        predicted_by_id[example_id] = intent
    if set(predicted_by_id) != set(golden):
        missing = sorted(set(golden) - set(predicted_by_id))
        extra = sorted(set(predicted_by_id) - set(golden))
        raise ValueError(f"Prediction IDs do not match golden IDs; missing={missing}, extra={extra}")

    ids = sorted(golden)
    y_true = [golden[item] for item in ids]
    y_pred = [predicted_by_id[item] for item in ids]
    labels = sorted(set(y_true) | set(y_pred))
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    per_intent = {
        label: {
            "precision": round(float(precision[index]), 4),
            "recall": round(float(recall[index]), 4),
            "f1": round(float(f1[index]), 4),
            "support": int(support[index]),
        }
        for index, label in enumerate(labels)
    }
    return {
        "count": len(ids),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), 4),
        "weighted_f1": round(float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)), 4),
        "per_intent": per_intent,
    }


def score_reply_judgments(judgments: Sequence[dict[str, object]]) -> dict[str, object]:
    """Aggregate saved judge outputs; no model call is made here."""

    if not judgments:
        raise ValueError("At least one reply judgment is required")
    dimensions = (
        "relevance", "groundedness", "helpfulness", "tone", "safety", "escalation_appropriateness"
    )
    averages = {
        dimension: round(sum(int(row[dimension]) for row in judgments) / len(judgments), 4)
        for dimension in dimensions
    }
    failed = sum(not bool(row["passed"]) for row in judgments)
    critical = sum(bool(row["critical_unsupported_claim"]) for row in judgments)
    return {
        "count": len(judgments),
        "pass_rate": round((len(judgments) - failed) / len(judgments), 4),
        "critical_unsupported_claim_rate": round(critical / len(judgments), 4),
        "average_scores": averages,
    }


def judge_human_agreement(
    human_scores: Sequence[int], judge_scores: Sequence[int], human_pass: Sequence[bool], judge_pass: Sequence[bool]
) -> dict[str, float]:
    """Compare blinded human and judge ratings on the same outputs."""

    if not (len(human_scores) == len(judge_scores) == len(human_pass) == len(judge_pass)):
        raise ValueError("Human and judge arrays must have equal lengths")
    if not human_scores:
        raise ValueError("At least one paired rating is required")
    correlation = spearmanr(human_scores, judge_scores).statistic
    return {
        "spearman_correlation": round(float(correlation), 4),
        "cohen_kappa": round(float(cohen_kappa_score(human_pass, judge_pass)), 4),
        "pass_fail_agreement": round(
            sum(left == right for left, right in zip(human_pass, judge_pass)) / len(human_pass), 4
        ),
    }


class GeminiReplyJudge:
    """Use Gemini only for reply scoring; aggregation remains offline and deterministic."""

    def __init__(self, *, client: object | None = None, model: str = "gemini-3.5-flash-lite") -> None:
        self.model = model
        if client is None:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY is not set")
            client = genai.Client(api_key=api_key)
        self.client = client

    def judge(
        self,
        *,
        customer_message: str,
        intent: str,
        reply: str,
        evidence: Sequence[dict[str, object]],
        expected_resolution: str | None = None,
    ) -> ReplyJudgeScore:
        if not customer_message.strip() or not reply.strip():
            raise ValueError("Customer message and reply must not be blank")
        schema = ReplyJudgeScore.model_json_schema()
        response = self.client.models.generate_content(
            model=self.model,
            contents=json.dumps(
                {
                    "customer_message": customer_message,
                    "intent": intent,
                    "reply": reply,
                    "evidence": list(evidence),
                    "expected_resolution": expected_resolution,
                },
                ensure_ascii=False,
            ),
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_json_schema=schema,
                system_instruction=(
                    "Score the support reply using the six 1-to-5 dimensions in the schema. "
                    "Judge only the supplied customer message, intent, evidence, and reply. "
                    "A critical unsupported claim forces passed=false. Be conservative and explain briefly."
                ),
            ),
        )
        if not response.text:
            raise ValueError("Judge returned no score")
        score = ReplyJudgeScore.model_validate_json(response.text)
        if score.critical_unsupported_claim:
            score.passed = False
        return score
