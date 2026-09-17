"""Command-line entry point for one AmazonHelp support-agent request."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from support_agent.intent_classifier import IntentClassifier
from support_agent.orchestrator import SupportAgent
from support_agent.reply_generator import ReplyGenerator
from support_agent.retriever import HistoricalRetriever


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--sentence-transformers--all-mpnet-base-v2"
    / "snapshots"
    / "e8c3b32edf5434bc2275fc9bab85f82640a19130"
)


def build_default_agent(*, model_path: Path = DEFAULT_MODEL_PATH, train_sample: int = 5_000) -> SupportAgent:
    if not model_path.is_dir():
        raise FileNotFoundError(f"Local embedding model not found: {model_path}")
    from sentence_transformers import SentenceTransformer

    encoder = SentenceTransformer(str(model_path), local_files_only=True)
    retriever = HistoricalRetriever(
        ROOT / "data" / "processed" / "amazonhelp_cases" / "train.jsonl",
        encoder,
        sample_size=train_sample,
        cache_path=ROOT / "data" / "processed" / f"retriever_mpnet_seed42_{train_sample}.npz",
        model_id=str(model_path.resolve()),
    )
    return SupportAgent(
        IntentClassifier(ROOT / "configs" / "intents.yaml"),
        retriever,
        ReplyGenerator(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", required=True)
    parser.add_argument("--context", action="append", default=[])
    parser.add_argument("--train-sample", type=int, default=5_000)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    result = build_default_agent(model_path=args.model_path, train_sample=args.train_sample).handle_message(
        args.message, args.context
    )
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
