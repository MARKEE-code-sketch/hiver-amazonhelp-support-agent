"""Discover recurring support themes from TRAIN cases using TF-IDF clustering."""

from __future__ import annotations

import json
import random
from pathlib import Path

from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score


def sample_cases(
    input_path: str | Path, *, sample_size: int, seed: int
) -> list[dict[str, object]]:
    """Reservoir-sample cases without loading the full JSONL file."""

    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Case file not found: {path}")
    if sample_size < 1:
        raise ValueError("sample_size must be at least 1")

    random_source = random.Random(seed)
    sample: list[dict[str, object]] = []
    seen = 0
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
                text = str(case["customer_text"]).strip()
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                raise ValueError(f"Invalid case on line {line_number}") from error
            if not text:
                continue
            seen += 1
            if len(sample) < sample_size:
                sample.append(case)
            else:
                replacement_index = random_source.randrange(seen)
                if replacement_index < sample_size:
                    sample[replacement_index] = case
    if len(sample) < sample_size:
        raise ValueError(f"Requested {sample_size} cases but only found {len(sample)}")
    return sample


def fit_clusters(
    cases: list[dict[str, object]], *, cluster_count: int, seed: int
) -> tuple[TfidfVectorizer, MiniBatchKMeans, object]:
    """Fit a reproducible TF-IDF discovery model."""

    if cluster_count < 2 or cluster_count >= len(cases):
        raise ValueError("cluster_count must be between 2 and sample_size - 1")
    texts = [str(case["customer_text"]) for case in cases]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1 if len(cases) < 50 else 3,
        max_df=0.90,
        max_features=20_000,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(texts)
    model = MiniBatchKMeans(
        n_clusters=cluster_count,
        random_state=seed,
        n_init=10,
        batch_size=min(512, len(cases)),
    )
    model.fit(matrix)
    return vectorizer, model, matrix


def discover_intents(
    input_path: str | Path,
    output_json: str | Path,
    output_markdown: str | Path,
    *,
    sample_size: int = 5_000,
    cluster_count: int = 20,
    examples_per_cluster: int = 8,
    seed: int = 42,
) -> dict[str, object]:
    """Write cluster evidence for human intent-taxonomy design."""

    cases = sample_cases(input_path, sample_size=sample_size, seed=seed)
    vectorizer, model, matrix = fit_clusters(
        cases, cluster_count=cluster_count, seed=seed
    )
    feature_names = vectorizer.get_feature_names_out()
    distances = model.transform(matrix)
    labels = model.labels_
    clusters = []

    for cluster_id in range(cluster_count):
        member_indices = [
            index for index, label in enumerate(labels) if label == cluster_id
        ]
        member_indices.sort(key=lambda index: distances[index, cluster_id])
        top_feature_indices = model.cluster_centers_[cluster_id].argsort()[-12:][::-1]
        clusters.append(
            {
                "cluster_id": cluster_id,
                "size": len(member_indices),
                "top_terms": [feature_names[index] for index in top_feature_indices],
                "examples": [
                    {
                        "case_id": str(cases[index]["case_id"]),
                        "customer_text": str(cases[index]["customer_text"]),
                        "historical_reply": str(cases[index]["historical_reply"]),
                    }
                    for index in member_indices[:examples_per_cluster]
                ],
            }
        )

    silhouette_sample = min(1_000, len(cases))
    score = silhouette_score(
        matrix,
        labels,
        metric="cosine",
        sample_size=silhouette_sample,
        random_state=seed,
    )
    result = {
        "source_file": Path(input_path).name,
        "method": "tfidf_minibatch_kmeans_for_discovery_only",
        "sample_size": len(cases),
        "cluster_count": cluster_count,
        "seed": seed,
        "silhouette_score": round(float(score), 6),
        "clusters": clusters,
    }

    json_path = Path(output_json)
    markdown_path = Path(output_markdown)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# AmazonHelp Intent Discovery",
        "",
        f"TRAIN sample: {len(cases):,} cases",
        f"Discovery clusters: {cluster_count}",
        f"Silhouette score: {score:.4f}",
        "",
        "> Clusters are discovery evidence, not final intent labels.",
        "",
    ]
    for cluster in clusters:
        lines.extend(
            [
                f"## Cluster {cluster['cluster_id']} ({cluster['size']} cases)",
                "",
                f"Top terms: {', '.join(cluster['top_terms'])}",
                "",
            ]
        )
        for example in cluster["examples"]:
            lines.extend(
                [
                    f"- Customer: {example['customer_text']}",
                    f"  - Historical reply: {example['historical_reply']}",
                ]
            )
        lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return result
