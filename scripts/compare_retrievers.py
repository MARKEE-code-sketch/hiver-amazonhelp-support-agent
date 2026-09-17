"""Save DEV-only top-five candidates from embedding and TF-IDF retrieval."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.baselines import SimilarityBaseline  # noqa: E402
from support_agent.intent_discovery import sample_cases  # noqa: E402
from support_agent.retriever import HistoricalRetriever  # noqa: E402


MODEL_PATH = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--sentence-transformers--all-mpnet-base-v2"
    / "snapshots"
    / "e8c3b32edf5434bc2275fc9bab85f82640a19130"
)


def main() -> None:
    if not MODEL_PATH.is_dir():
        raise SystemExit(f"Local model not found: {MODEL_PATH}")
    from sentence_transformers import SentenceTransformer

    train = ROOT / "data" / "processed" / "amazonhelp_cases" / "train.jsonl"
    dev = ROOT / "data" / "processed" / "amazonhelp_cases" / "dev.jsonl"
    output = ROOT / "data" / "processed" / "retrieval_dev_candidates.json"
    encoder = SentenceTransformer(str(MODEL_PATH), local_files_only=True)
    started = time.perf_counter()
    semantic = HistoricalRetriever(
        train,
        encoder,
        sample_size=5_000,
        cache_path=ROOT / "data" / "processed" / "retriever_mpnet_seed42_5000.npz",
        model_id=str(MODEL_PATH.resolve()),
    )
    build_seconds = round(time.perf_counter() - started, 2)
    lexical = SimilarityBaseline(train, ROOT / "configs" / "intents.yaml")
    dev_cases = sample_cases(dev, sample_size=25, seed=91)
    results = []
    for case in dev_cases:
        message = str(case["customer_text"])
        started = time.perf_counter()
        semantic_hits = semantic.search(message, k=5)
        semantic_ms = round((time.perf_counter() - started) * 1_000, 2)
        started = time.perf_counter()
        lexical_hits = lexical.search_cases(message, k=5)
        lexical_ms = round((time.perf_counter() - started) * 1_000, 2)
        results.append(
            {
                "query_case_id": case["case_id"],
                "query": message,
                "embedding_top5": semantic_hits,
                "tfidf_top5": lexical_hits,
                "embedding_search_ms": semantic_ms,
                "tfidf_search_ms": lexical_ms,
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "dev_queries": len(results),
                "train_pool": len(semantic.cases),
                "embedding_build_seconds": build_seconds,
                "mean_embedding_search_ms": round(
                    sum(row["embedding_search_ms"] for row in results) / len(results), 2
                ),
                "mean_tfidf_search_ms": round(
                    sum(row["tfidf_search_ms"] for row in results) / len(results), 2
                ),
                "output": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
