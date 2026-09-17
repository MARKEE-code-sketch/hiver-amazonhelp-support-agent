"""Classify one customer message with the approved AmazonHelp intents."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.intent_classifier import IntentClassifier  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", required=True)
    parser.add_argument("--context", action="append", default=[])
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    classifier = IntentClassifier(ROOT / "configs" / "intents.yaml")
    prediction = classifier.predict(args.message, args.context)
    print(prediction.model_dump_json())


if __name__ == "__main__":
    main()
