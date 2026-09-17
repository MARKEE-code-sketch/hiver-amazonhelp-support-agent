"""Run the three intent systems on the fixed first 50 human-reviewed cases."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.baselines import SimilarityBaseline, fixed_baseline  # noqa: E402
from support_agent.groq_client import GroqStructuredClient  # noqa: E402
from support_agent.intent_classifier import IntentClassifier  # noqa: E402
from support_agent.orchestrator import SupportAgent  # noqa: E402
from support_agent.reply_generator import ReplyGenerator  # noqa: E402
from support_agent.retriever import HistoricalRetriever  # noqa: E402


DEFAULT_MODEL_PATH = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--sentence-transformers--all-mpnet-base-v2"
    / "snapshots"
    / "e8c3b32edf5434bc2275fc9bab85f82640a19130"
)


def read_cases(path: Path, limit: int) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))[:limit]
    if len(rows) != limit:
        raise ValueError(f"Expected at least {limit} golden rows, found {len(rows)}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--train-sample", type=int, default=5_000)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "top50_predictions.json")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")

    from sentence_transformers import SentenceTransformer

    if not args.model_path.is_dir():
        raise SystemExit(f"Local embedding model not found: {args.model_path}")
    encoder = SentenceTransformer(str(args.model_path), local_files_only=True)
    train_path = ROOT / "data" / "processed" / "amazonhelp_cases" / "train.jsonl"
    retriever = HistoricalRetriever(
        train_path,
        encoder,
        sample_size=args.train_sample,
        cache_path=ROOT / "data" / "processed" / f"retriever_mpnet_seed42_{args.train_sample}.npz",
        model_id=str(args.model_path.resolve()),
    )
    groq_client = GroqStructuredClient()
    agent = SupportAgent(
        IntentClassifier(ROOT / "configs" / "intents.yaml", client=groq_client),
        retriever,
        ReplyGenerator(client=groq_client),
    )
    tfidf = SimilarityBaseline(train_path, ROOT / "configs" / "intents.yaml", sample_size=args.train_sample)
    cases = read_cases(ROOT / "eval" / "golden_set_human_labelled.csv", args.limit)
    results: list[dict[str, object]] = []
    if args.output.is_file():
        checkpoint = json.loads(args.output.read_text(encoding="utf-8"))
        if checkpoint.get("complete"):
            print(f"Evaluation already complete: {args.output}")
            return
        results = list(checkpoint.get("results", []))
        print(f"Resuming from checkpoint: {len(results)}/{len(cases)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for index, case in enumerate(cases[len(results):], start=len(results) + 1):
        message = str(case["customer_message"])
        context = [str(case["prior_context"])] if case.get("prior_context") else []
        tfidf_result = tfidf.predict(message)
        try:
            main_output = agent.handle_message(message, context).model_dump(mode="json")
        except Exception as error:
            # Keep the row visible and count it as an incorrect main prediction;
            # never convert a provider failure into a guessed intent.
            main_output = {
                "intent": "__ERROR__",
                "intent_confidence": 0.0,
                "intent_reason": "Provider failure during evaluation.",
                "reply": "I’m sorry, but a human support specialist must review this request.",
                "reply_supported": False,
                "unsupported_claim": True,
                "evidence": [],
                "decision": "ESCALATE",
                "decision_reason": "PROVIDER_FAILURE",
                "top_similarity": 0.0,
                "generator_error": type(error).__name__,
            }
        results.append(
            {
                "example_id": case["example_id"],
                "gold_intent": case["intent_name"],
                "customer_message": message,
                "systems": {
                    "fixed": fixed_baseline(message),
                    "tfidf": tfidf_result,
                    "main": main_output,
                },
            }
        )
        args.output.write_text(
            json.dumps({"complete": index == len(cases), "count": index, "results": results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Scored {index}/{len(cases)}")


if __name__ == "__main__":
    main()
