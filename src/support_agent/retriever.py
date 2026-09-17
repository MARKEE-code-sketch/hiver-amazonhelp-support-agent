"""Find similar historical AmazonHelp cases from a fixed TRAIN sample."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from support_agent.intent_discovery import sample_cases


class HistoricalRetriever:
    """In-memory cosine search; historical replies are evidence, not final answers."""

    def __init__(
        self,
        train_cases: str | Path,
        encoder: object,
        *,
        sample_size: int = 5_000,
        seed: int = 42,
        cache_path: str | Path | None = None,
        model_id: str = "",
    ) -> None:
        source = Path(train_cases)
        if source.name != "train.jsonl":
            raise ValueError("Retriever corpus must come from train.jsonl")
        self.cases = sample_cases(source, sample_size=sample_size, seed=seed)
        self.encoder = encoder
        ids = np.asarray([str(case["case_id"]) for case in self.cases])
        cache = Path(cache_path) if cache_path is not None else None
        vectors = None
        if cache is not None and cache.is_file():
            with np.load(cache, allow_pickle=False) as stored:
                if (
                    stored["model_id"].item() == model_id
                    and np.array_equal(stored["case_ids"], ids)
                ):
                    vectors = stored["vectors"]
        if vectors is None:
            vectors = np.asarray(
                encoder.encode(
                    [str(case["customer_text"]) for case in self.cases],
                    convert_to_numpy=True,
                    show_progress_bar=False,
                ),
                dtype=np.float32,
            )
            if cache is not None:
                cache.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(
                    cache, model_id=model_id, case_ids=ids, vectors=vectors
                )
        if vectors.ndim != 2 or vectors.shape[0] != len(self.cases):
            raise ValueError("Encoder must return one vector per TRAIN case")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        self.vectors = vectors / np.where(norms == 0, 1, norms)

    def search(self, message: str, *, k: int = 5) -> list[dict[str, object]]:
        """Return the top-k TRAIN cases, most similar first."""

        if k < 1:
            raise ValueError("k must be at least 1")
        if not message.strip():
            return []
        query = np.asarray(
            self.encoder.encode(
                [message], convert_to_numpy=True, show_progress_bar=False
            ),
            dtype=np.float32,
        )
        if query.shape != (1, self.vectors.shape[1]):
            raise ValueError("Encoder returned an invalid query vector")
        query_norm = float(np.linalg.norm(query[0]))
        if query_norm == 0:
            return []
        scores = self.vectors @ (query[0] / query_norm)
        indices = np.argsort(-scores, kind="stable")[:k]
        return [
            {
                "case_id": str(self.cases[index]["case_id"]),
                "thread_id": str(self.cases[index]["thread_id"]),
                "customer_text": str(self.cases[index]["customer_text"]),
                "historical_reply": str(self.cases[index]["historical_reply"]),
                "similarity": round(float(scores[index]), 4),
            }
            for index in indices
        ]
