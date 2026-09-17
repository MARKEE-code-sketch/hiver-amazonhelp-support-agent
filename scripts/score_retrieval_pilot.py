"""Score the explicitly judged DEV retrieval pilot, not the frozen TEST set."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.retrieval_eval import retrieval_metrics  # noqa: E402


def main() -> None:
    candidates = json.loads(
        (ROOT / "data" / "processed" / "retrieval_dev_candidates.json").read_text(
            encoding="utf-8"
        )
    )
    judgments = json.loads(
        (ROOT / "eval" / "retrieval_pilot_judgments.json").read_text(
            encoding="utf-8"
        )
    )
    by_id = {str(row["query_case_id"]): row for row in candidates}
    relevant = {
        query_id: set(case_ids)
        for query_id, case_ids in judgments["relevant_case_ids"].items()
    }
    embedding = {}
    tfidf = {}
    for query_id, relevant_ids in relevant.items():
        if query_id not in by_id:
            raise ValueError(f"Judged query absent from DEV candidates: {query_id}")
        row = by_id[query_id]
        embedding[query_id] = [hit["case_id"] for hit in row["embedding_top5"]]
        tfidf[query_id] = [hit["case_id"] for hit in row["tfidf_top5"]]
        pooled = set(embedding[query_id] + tfidf[query_id])
        if not relevant_ids <= pooled:
            raise ValueError(f"Judgment includes an unpooled case for {query_id}")
    result = {
        "status": judgments["status"],
        "judged_dev_queries": len(relevant),
        "embedding": retrieval_metrics(embedding, relevant),
        "tfidf": retrieval_metrics(tfidf, relevant),
        "mean_embedding_search_ms": round(
            sum(by_id[query_id]["embedding_search_ms"] for query_id in relevant)
            / len(relevant),
            2,
        ),
        "mean_tfidf_search_ms": round(
            sum(by_id[query_id]["tfidf_search_ms"] for query_id in relevant)
            / len(relevant),
            2,
        ),
    }
    destination = ROOT / "artifacts" / "retrieval_pilot_metrics.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
