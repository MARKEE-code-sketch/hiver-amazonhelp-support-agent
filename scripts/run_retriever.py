"""Search a seeded TRAIN case sample with the locally cached embedding model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.retriever import HistoricalRetriever  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", help="Customer message to search")
    parser.add_argument("--sample-size", type=int, default=5_000)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--model-path",
        type=Path,
        default=Path.home()
        / ".cache"
        / "huggingface"
        / "hub"
        / "models--sentence-transformers--all-mpnet-base-v2"
        / "snapshots"
        / "e8c3b32edf5434bc2275fc9bab85f82640a19130",
    )
    args = parser.parse_args()
    if not args.model_path.is_dir():
        raise SystemExit(f"Local embedding model not found: {args.model_path}")

    from sentence_transformers import SentenceTransformer

    encoder = SentenceTransformer(str(args.model_path), local_files_only=True)
    retriever = HistoricalRetriever(
        ROOT / "data" / "processed" / "amazonhelp_cases" / "train.jsonl",
        encoder,
        sample_size=args.sample_size,
        cache_path=ROOT
        / "data"
        / "processed"
        / f"retriever_mpnet_seed42_{args.sample_size}.npz",
        model_id=str(args.model_path.resolve()),
    )
    print(json.dumps(retriever.search(args.message, k=args.k), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
