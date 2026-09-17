from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.retrieval_eval import retrieval_metrics


class RetrievalEvalTests(unittest.TestCase):
    def test_precision_and_pooled_recall(self) -> None:
        ranked = {
            "q1": ["a", "b", "c", "d", "e"],
            "q2": ["x", "y", "z", "w", "v"],
        }
        relevant = {"q1": {"a", "c"}, "q2": {"y", "v"}}
        result = retrieval_metrics(ranked, relevant)
        self.assertEqual(result["precision_at_1"], 0.5)
        self.assertEqual(result["precision_at_5"], 0.4)
        self.assertEqual(result["pooled_recall_at_5"], 1.0)
        self.assertEqual(result["recall_query_count"], 2)

    def test_no_relevant_candidates_have_undefined_recall(self) -> None:
        result = retrieval_metrics({"q1": ["a"]}, {"q1": set()})
        self.assertEqual(result["precision_at_1"], 0.0)
        self.assertIsNone(result["pooled_recall_at_5"])
        self.assertEqual(result["recall_query_count"], 0)

    def test_rejects_missing_judgments(self) -> None:
        with self.assertRaises(ValueError):
            retrieval_metrics({"q1": ["a"]}, {})


if __name__ == "__main__":
    unittest.main()
