"""Create a 150-row review copy containing the assistant's label proposals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.annotation_writer import apply_annotation_proposals  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "eval" / "golden_set_review.csv",
    )
    parser.add_argument(
        "--proposals",
        type=Path,
        default=PROJECT_ROOT / "eval" / "assistant_label_proposals.json",
    )
    parser.add_argument(
        "--test-cases",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "processed"
        / "amazonhelp_cases"
        / "test.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT
        / "eval"
        / "golden_set_review_assistant_proposals.csv",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "assistant_annotation_manifest.json",
    )
    args = parser.parse_args()

    result = apply_annotation_proposals(
        args.input,
        args.proposals,
        args.test_cases,
        args.output,
    )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
