"""Compare three intent classifiers on a fixed, assistant-labelled DEV pilot."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from sklearn.metrics import accuracy_score, f1_score


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.baselines import SimilarityBaseline, fixed_baseline  # noqa: E402
from support_agent.intent_classifier import IntentClassifier  # noqa: E402
from support_agent.intent_discovery import sample_cases  # noqa: E402


def redact(text: str) -> str:
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", text)
    return re.sub(r"\d+", "[NUMBER]", text)


def main() -> None:
    manifest = json.loads((ROOT / "eval" / "intent_dev_pilot_labels.json").read_text(encoding="utf-8"))
    cases = sample_cases(
        ROOT / manifest["source"],
        sample_size=manifest["sample_size"],
        seed=manifest["sample_seed"],
    )
    labels = manifest["labels"]
    excluded = manifest["excluded"]
    if {str(case["case_id"]) for case in cases} != set(labels) | set(excluded):
        raise ValueError("Pilot IDs no longer match the fixed DEV sample")

    load_dotenv(ROOT / ".env")
    taxonomy_path = ROOT / "configs" / "intents.yaml"
    classifier = IntentClassifier(taxonomy_path)
    baseline = SimilarityBaseline(
        ROOT / "data" / "processed" / "amazonhelp_cases" / "train.jsonl",
        taxonomy_path,
    )
    rows: list[dict[str, object]] = []
    output = ROOT / "artifacts" / "intent_dev_pilot_results.json"
    output.parent.mkdir(exist_ok=True)
    try:
        for case in cases:
            case_id = str(case["case_id"])
            if case_id in excluded:
                continue
            message = redact(str(case["customer_text"]))
            context = [
                redact(str(item["text"]))
                for item in case.get("context", [])
                if item.get("role") == "customer"
            ]
            prediction = classifier.predict(message, context)
            rows.append({
                "case_id": case_id,
                "message": message,
                "customer_context": context,
                "gold_intent": labels[case_id],
                "classifier_intent": prediction.intent,
                "classifier_confidence": prediction.confidence,
                "classifier_reason": prediction.reason,
                "fixed_intent": fixed_baseline(message)["intent"],
                "tfidf_intent": baseline.predict(message)["intent"],
            })
            print(f"Scored {len(rows)}/{len(labels)} DEV cases")
    finally:
        output.write_text(
            json.dumps({"complete": len(rows) == len(labels), "rows": rows}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    gold = [row["gold_intent"] for row in rows]
    observed_intents = sorted(set(gold))
    metrics = {}
    for name, key in (
        ("fixed", "fixed_intent"),
        ("tfidf", "tfidf_intent"),
        ("classifier", "classifier_intent"),
    ):
        predicted = [row[key] for row in rows]
        metrics[name] = {
            "correct": sum(expected == actual for expected, actual in zip(gold, predicted)),
            "accuracy": round(float(accuracy_score(gold, predicted)), 4),
            "macro_f1_observed_intents": round(float(f1_score(
                gold, predicted, labels=observed_intents, average="macro", zero_division=0
            )), 4),
        }
    result = {
        "complete": True,
        "split": "DEV",
        "label_source": manifest["label_source"],
        "sample_seed": manifest["sample_seed"],
        "sample_size": manifest["sample_size"],
        "excluded": excluded,
        "scored_count": len(rows),
        "observed_gold_intents": dict(Counter(gold)),
        "metrics": metrics,
        "rows": rows,
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"scored_count": len(rows), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
