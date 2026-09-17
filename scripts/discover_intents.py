"""Generate human-readable intent discovery evidence from TRAIN only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.intent_discovery import discover_intents  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "amazonhelp_cases" / "train.jsonl",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "intent_discovery",
    )
    parser.add_argument("--sample-size", type=int, default=5_000)
    parser.add_argument("--clusters", type=int, default=20)
    parser.add_argument("--examples-per-cluster", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    result = discover_intents(
        args.input,
        args.output_dir / "clusters.json",
        args.output_dir / "clusters.md",
        sample_size=args.sample_size,
        cluster_count=args.clusters,
        examples_per_cluster=args.examples_per_cluster,
        seed=args.seed,
    )
    print(
        json.dumps(
            {
                "sample_size": result["sample_size"],
                "cluster_count": result["cluster_count"],
                "silhouette_score": result["silhouette_score"],
                "output_dir": str(args.output_dir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
