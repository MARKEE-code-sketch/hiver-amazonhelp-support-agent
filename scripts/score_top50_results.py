"""Calculate offline metrics from the completed top-50 prediction artifact."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.evaluator import score_intent_predictions  # noqa: E402


def main() -> None:
    source = ROOT / "artifacts" / "top50_predictions.json"
    artifact = json.loads(source.read_text(encoding="utf-8"))
    if not artifact.get("complete") or artifact.get("count") != 50:
        raise ValueError("Top-50 artifact is incomplete")
    rows = artifact["results"]
    metrics: dict[str, object] = {}
    for system in ("fixed", "tfidf", "main"):
        predictions = [
            {"example_id": row["example_id"], "intent": row["systems"][system]["intent"]}
            for row in rows
        ]
        metrics[system] = score_intent_predictions(
            {row["example_id"]: row["gold_intent"] for row in rows}, predictions
        )
    main_rows = [row["systems"]["main"] for row in rows]
    report = {
        "slice": "first 50 rows of eval/golden_set_human_labelled.csv",
        "provider": "Groq",
        "model": "openai/gpt-oss-20b",
        "metrics": metrics,
        "generator_error_count": sum(bool(row.get("generator_error")) for row in main_rows),
        "generator_error_types": dict(Counter(row.get("generator_error") for row in main_rows if row.get("generator_error"))),
        "main_decisions": dict(Counter(row["decision"] for row in main_rows)),
        "main_decision_reasons": dict(Counter(row["decision_reason"] for row in main_rows)),
        "limitation": "Intent labels are human-reviewed; escalation/action labels and independent reply ratings are not available.",
    }
    destination = ROOT / "artifacts" / "top50_metrics.json"
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
