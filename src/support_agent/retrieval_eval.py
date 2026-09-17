"""Simple retrieval metrics over explicitly judged candidate pools."""

from __future__ import annotations


def retrieval_metrics(
    ranked_case_ids: dict[str, list[str]],
    relevant_case_ids: dict[str, set[str]],
) -> dict[str, float | int | None]:
    """Calculate macro Precision@1/@5 and pooled Recall@5."""

    if not ranked_case_ids or ranked_case_ids.keys() != relevant_case_ids.keys():
        raise ValueError("Queries and relevance judgments must match and be nonempty")
    precision_at_1 = 0.0
    precision_at_5 = 0.0
    pooled_recall_at_5 = 0.0
    recall_query_count = 0
    for query_id, ranked in ranked_case_ids.items():
        relevant = relevant_case_ids[query_id]
        if len(ranked) != len(set(ranked)):
            raise ValueError(f"Duplicate candidates for {query_id}")
        top_five = ranked[:5]
        precision_at_1 += float(bool(ranked and ranked[0] in relevant))
        precision_at_5 += sum(case_id in relevant for case_id in top_five) / 5
        if relevant:
            pooled_recall_at_5 += len(set(top_five) & relevant) / len(relevant)
            recall_query_count += 1
    count = len(ranked_case_ids)
    return {
        "precision_at_1": round(precision_at_1 / count, 4),
        "precision_at_5": round(precision_at_5 / count, 4),
        "pooled_recall_at_5": (
            round(pooled_recall_at_5 / recall_query_count, 4)
            if recall_query_count
            else None
        ),
        "recall_query_count": recall_query_count,
        "query_count": count,
    }
