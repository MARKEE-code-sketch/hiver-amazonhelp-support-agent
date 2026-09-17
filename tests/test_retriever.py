from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.retriever import HistoricalRetriever


class FakeEncoder:
    def __init__(self):
        self.calls = 0

    def encode(self, texts, **_kwargs):
        self.calls += 1
        vectors = []
        for text in texts:
            words = text.lower()
            vectors.append(
                [
                    float("delivery" in words or "parcel" in words),
                    float("refund" in words),
                    float("account" in words),
                ]
            )
        return np.asarray(vectors, dtype=np.float32)


class RetrieverTests(unittest.TestCase):
    def test_top_k_order_and_empty_query(self) -> None:
        cases = [
            {"case_id": "1", "thread_id": "1", "customer_text": "Parcel delivery", "historical_reply": "A"},
            {"case_id": "2", "thread_id": "2", "customer_text": "Refund", "historical_reply": "B"},
            {"case_id": "3", "thread_id": "3", "customer_text": "Account", "historical_reply": "C"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            train = Path(directory) / "train.jsonl"
            train.write_text(
                "".join(json.dumps(case) + "\n" for case in cases), encoding="utf-8"
            )
            retriever = HistoricalRetriever(train, FakeEncoder(), sample_size=3)
            hits = retriever.search("Where is my parcel delivery?", k=2)
            self.assertEqual(hits[0]["case_id"], "1")
            self.assertEqual(len(hits), 2)
            self.assertGreaterEqual(hits[0]["similarity"], hits[1]["similarity"])
            self.assertEqual(retriever.search("  "), [])
            self.assertEqual(retriever.search("unmatched"), [])
            self.assertEqual(retriever.search("Refund", k=8)[0]["case_id"], "2")
            with self.assertRaises(ValueError):
                retriever.search("refund", k=0)
            with self.assertRaises(ValueError):
                HistoricalRetriever(
                    Path(directory) / "test.jsonl", FakeEncoder(), sample_size=3
                )

            cache = Path(directory) / "vectors.npz"
            first_encoder = FakeEncoder()
            HistoricalRetriever(
                train, first_encoder, sample_size=3, cache_path=cache, model_id="fake"
            )
            self.assertEqual(first_encoder.calls, 1)
            second_encoder = FakeEncoder()
            HistoricalRetriever(
                train, second_encoder, sample_size=3, cache_path=cache, model_id="fake"
            )
            self.assertEqual(second_encoder.calls, 0)


if __name__ == "__main__":
    unittest.main()
