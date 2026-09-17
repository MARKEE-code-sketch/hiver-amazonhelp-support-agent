"""Validate the 12-intent taxonomy and measure rough TRAIN theme coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.taxonomy import (  # noqa: E402
    analyze_keyword_coverage,
    load_taxonomy,
    validate_taxonomy,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--taxonomy",
        type=Path,
        default=PROJECT_ROOT / "configs" / "intents.yaml",
    )
    parser.add_argument(
        "--train-cases",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "processed"
        / "amazonhelp_cases"
        / "train.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "taxonomy_validation.json",
    )
    args = parser.parse_args()

    taxonomy = load_taxonomy(args.taxonomy)
    errors = validate_taxonomy(taxonomy)
    if errors:
        raise SystemExit("\n".join(errors))
    result = analyze_keyword_coverage(taxonomy, args.train_cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
