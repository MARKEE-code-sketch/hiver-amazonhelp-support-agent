"""CLI for reproducible brand-volume profiling."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from support_agent.brand_profiler import profile_brands  # noqa: E402


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
        default=PROJECT_ROOT / "artifacts" / "brand_profile.json",
    )
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--sample-size", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    result = profile_brands(
        args.input,
        top_n=args.top_n,
        sample_size=args.sample_size,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"Rows scanned: {result['total_rows']:,}")
    print(f"Winner by outbound occurrences: {result['winner_by_occurrence']}")
    print()
    print(
        f"{'Rank':>4}  {'Brand':<24} {'Outbound':>10} "
        f"{'Verified replies':>17} {'Unique customers':>17}"
    )
    for rank, profile in enumerate(result["top_brands"], start=1):
        print(
            f"{rank:>4}  {profile['brand']:<24} "
            f"{profile['outbound_tweets']:>10,} "
            f"{profile['verified_customer_replies']:>17,} "
            f"{profile['unique_customer_messages_replied_to']:>17,}"
        )
    print(f"\nSaved evidence: {args.output}")


if __name__ == "__main__":
    main()
