"""Run both offline baselines on a small DEV sample without touching TEST."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.baselines import SimilarityBaseline, fixed_baseline  # noqa: E402
from support_agent.intent_discovery import sample_cases  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-sample", type=int, default=5_000)
    parser.add_argument("--dev-sample", type=int, default=10)
    args = parser.parse_args()
    train = ROOT / "data" / "processed" / "amazonhelp_cases" / "train.jsonl"
    dev = ROOT / "data" / "processed" / "amazonhelp_cases" / "dev.jsonl"
    model = SimilarityBaseline(
        train, ROOT / "configs" / "intents.yaml", sample_size=args.train_sample
    )
    for case in sample_cases(dev, sample_size=args.dev_sample, seed=42):
        message = str(case["customer_text"])
        similarity = model.predict(message)
        print(
            json.dumps(
                {
                    "case_id": case["case_id"],
                    "customer_text": message,
                    "fixed_intent": fixed_baseline(message)["intent"],
                    "similarity_intent": similarity["intent"],
                    "intent_similarity": similarity["intent_similarity"],
                    "evidence_case_id": similarity["evidence_case_id"],
                    "evidence_similarity": similarity["evidence_similarity"],
                    "action": similarity["action"],
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
