from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.intent_discovery import discover_intents


class IntentDiscoveryTests(unittest.TestCase):
    def test_creates_reproducible_cluster_evidence(self) -> None:
        topics = {
            "delivery": [
                "My package delivery is late",
                "Where is my missing order package",
                "The delivery tracking is not updated",
                "My order has not arrived yet",
            ],
            "refund": [
                "My refund has not arrived",
                "Please help with my refund payment",
                "I returned the item but need a refund",
                "When will my refund be received",
            ],
            "account": [
                "I cannot access my account",
                "My account login is not working",
                "Please help me sign into my account",
                "Why is my account locked",
            ],
        }
        records = []
        for topic, texts in topics.items():
            for index, text in enumerate(texts):
                records.append(
                    {
                        "case_id": f"{topic}-{index}",
                        "customer_text": text,
                        "historical_reply": f"Historical {topic} reply",
                    }
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "train.jsonl"
            output_json = Path(temp_dir) / "clusters.json"
            output_markdown = Path(temp_dir) / "clusters.md"
            source.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )
            result = discover_intents(
                source,
                output_json,
                output_markdown,
                sample_size=12,
                cluster_count=3,
                examples_per_cluster=2,
                seed=42,
            )
            markdown = output_markdown.read_text(encoding="utf-8")

        self.assertEqual(result["sample_size"], 12)
        self.assertEqual(result["cluster_count"], 3)
        self.assertEqual(sum(cluster["size"] for cluster in result["clusters"]), 12)
        self.assertTrue(all(cluster["examples"] for cluster in result["clusters"]))
        self.assertIn("Clusters are discovery evidence", markdown)


if __name__ == "__main__":
    unittest.main()
