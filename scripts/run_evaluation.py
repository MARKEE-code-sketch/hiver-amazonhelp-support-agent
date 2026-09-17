"""Score saved intent predictions against the human-reviewed golden set."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.evaluator import load_golden_intents, score_intent_predictions  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path, help="JSON array or {predictions: [...]} file")
    parser.add_argument(
        "--golden", type=Path, default=ROOT / "eval" / "golden_set_human_labelled.csv"
    )
    args = parser.parse_args()
    payload = json.loads(args.predictions.read_text(encoding="utf-8"))
    predictions = payload["predictions"] if isinstance(payload, dict) else payload
    metrics = score_intent_predictions(load_golden_intents(args.golden), predictions)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
