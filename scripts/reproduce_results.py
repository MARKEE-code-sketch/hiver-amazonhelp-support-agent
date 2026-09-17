"""Reproduce the published top-50 tables from saved artifacts without API calls."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.evaluator import score_intent_predictions, score_reply_judgments  # noqa: E402


def main() -> None:
    prediction_path = ROOT / "artifacts" / "top50_predictions.json"
    prediction_artifact = json.loads(prediction_path.read_text(encoding="utf-8"))
    if not prediction_artifact.get("complete") or prediction_artifact.get("count") != 50:
        raise ValueError("top50_predictions.json is incomplete")
    rows = prediction_artifact["results"]
    gold = {row["example_id"]: row["gold_intent"] for row in rows}

    intent_metrics: dict[str, object] = {}
    for system in ("fixed", "tfidf", "main"):
        predictions = [
            {"example_id": row["example_id"], "intent": row["systems"][system]["intent"]}
            for row in rows
        ]
        intent_metrics[system] = score_intent_predictions(gold, predictions)

    reply_path = ROOT / "artifacts" / "top50_reply_judgments.json"
    reply_artifact = json.loads(reply_path.read_text(encoding="utf-8"))
    judgments = reply_artifact["judgments"]
    generator_error_ids = {
        row["example_id"] for row in rows if row["systems"]["main"].get("generator_error")
    }
    valid_judgments = [
        row for row in judgments
        if not row.get("judge_error") and row["example_id"] not in generator_error_ids
    ]

    review_path = ROOT / "eval" / "top50_reply_human_review.csv"
    with review_path.open("r", encoding="utf-8-sig", newline="") as source:
        review_rows = list(csv.DictReader(source))
    if len(review_rows) != 50 or any(not row["human_pass"] for row in review_rows):
        raise ValueError("Human reply review must contain 50 completed rows")

    output = {
        "mode": "offline_artifact_reproduction",
        "slice": "first 50 rows of eval/golden_set_human_labelled.csv",
        "intent_metrics": intent_metrics,
        "reply_judge_valid_subset": score_reply_judgments(valid_judgments),
        "reply_judge_valid_count": len(valid_judgments),
        "generator_error_count": len(generator_error_ids),
        "reply_judge_errors": dict(Counter(row.get("judge_error") for row in judgments if row.get("judge_error"))),
        "human_review": dict(Counter(row["human_pass"] for row in review_rows)),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
