"""Command-line entry point for one AmazonHelp support-agent request."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from support_agent.intent_classifier import IntentClassifier
from support_agent.orchestrator import SupportAgent
from support_agent.reply_generator import ReplyGenerator
from support_agent.retriever import HistoricalRetriever
from support_agent.groq_client import GroqStructuredClient


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


def build_default_agent(
    *,
    model_path: Path = DEFAULT_MODEL_PATH,
    train_sample: int = 5_000,
    provider: str | None = None,
) -> SupportAgent:
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
    selected_provider = (provider or os.getenv("SUPPORT_AGENT_PROVIDER", "groq")).lower()
    if selected_provider == "groq":
        model = os.getenv("SUPPORT_AGENT_MODEL") or os.getenv("GROQ_MODEL") or "groq/compound-mini"
        client = GroqStructuredClient(model=model)
        classifier = IntentClassifier(ROOT / "configs" / "intents.yaml", client=client, model=model)
        generator = ReplyGenerator(client=client, model=model)
    elif selected_provider == "google":
        classifier = IntentClassifier(ROOT / "configs" / "intents.yaml")
        generator = ReplyGenerator()
    else:
        raise ValueError("provider must be 'groq' or 'google'")
    return SupportAgent(classifier, retriever, generator)


def main() -> None:
    # Windows PowerShell may use a cp1252 stdout that cannot print model text
    # containing Unicode punctuation. Keep the JSON response machine-readable.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", help="One message to process; omit it to start chat mode")
    parser.add_argument("--interactive", action="store_true", help="Start a reusable chat session")
    parser.add_argument("--context", action="append", default=[])
    parser.add_argument("--train-sample", type=int, default=5_000)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument(
        "--provider",
        choices=("groq", "google"),
        default=None,
        help="LLM provider; defaults to SUPPORT_AGENT_PROVIDER or groq",
    )
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    interactive = args.interactive or not args.message
    if interactive:
        print("Hey! How may I help you?")
        print("Loading the support agent once. You can ask multiple questions; type 'exit' to quit.")
    agent = build_default_agent(
        model_path=args.model_path,
        train_sample=args.train_sample,
        provider=args.provider,
    )
    if not interactive:
        result = agent.handle_message(args.message, args.context)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return

    while True:
        try:
            message = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            return
        if not message:
            continue
        if message.lower() in {"exit", "quit", ":q"}:
            print("Goodbye!")
            return
        try:
            result = agent.handle_message(message, [])
            print(f"Agent: {result.reply}")
            if result.decision == "ESCALATE":
                print(f"Human review: {result.decision_reason}")
        except Exception as error:
            print(f"Agent: I’m sorry, I could not process that request. Human review is required. ({type(error).__name__})")
