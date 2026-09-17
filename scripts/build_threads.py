"""Build complete conversations connected to the selected support brand."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.thread_builder import build_brand_threads  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "twitter_dataset" / "twcs" / "twcs.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "amazonhelp_threads.jsonl",
    )
    parser.add_argument(
        "--stats-output",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "thread_build_stats.json",
    )
    parser.add_argument("--brand", default="AmazonHelp")
    parser.add_argument("--max-passes", type=int, default=20)
    args = parser.parse_args()

    stats = build_brand_threads(
        args.input,
        args.output,
        brand=args.brand,
        max_passes=args.max_passes,
    )
    args.stats_output.parent.mkdir(parents=True, exist_ok=True)
    args.stats_output.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
