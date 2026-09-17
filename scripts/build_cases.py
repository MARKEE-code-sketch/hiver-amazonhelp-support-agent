"""Create English support cases from each AmazonHelp thread split."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.case_builder import build_cases  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--split-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "amazonhelp_splits",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "amazonhelp_cases",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "case_build_manifest.json",
    )
    args = parser.parse_args()

    results = {}
    for split_name in ("train", "dev", "test"):
        results[split_name] = build_cases(
            args.split_dir / f"{split_name}.jsonl",
            args.output_dir / f"{split_name}.jsonl",
        )
    manifest = {"language_scope": "english", "splits": results}
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
