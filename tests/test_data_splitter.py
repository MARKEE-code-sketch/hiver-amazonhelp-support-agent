from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.data_splitter import SplitRatios, split_threads


def _record(thread_number: int) -> dict[str, object]:
    started_at = datetime(2017, 1, 1, tzinfo=timezone.utc) + timedelta(
        days=thread_number
    )
    return {
        "thread_id": str(thread_number),
        "brand": "AmazonHelp",
        "started_at": started_at.isoformat(),
        "ended_at": started_at.isoformat(),
        "messages": [{"tweet_id": f"message-{thread_number}"}],
    }


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def _read_ids(path: Path) -> list[str]:
    return [
        str(json.loads(line)["thread_id"])
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


class DataSplitterTests(unittest.TestCase):
    def test_splits_complete_threads_chronologically(self) -> None:
        records = [_record(number) for number in range(20, 0, -1)]
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "threads.jsonl"
            output_dir = Path(temp_dir) / "splits"
            _write_jsonl(source, records)

            manifest = split_threads(source, output_dir)
            train_ids = _read_ids(output_dir / "train.jsonl")
            dev_ids = _read_ids(output_dir / "dev.jsonl")
            test_ids = _read_ids(output_dir / "test.jsonl")

        self.assertEqual(manifest["total_threads"], 20)
        self.assertEqual(
            sum(split["messages"] for split in manifest["splits"].values()), 20
        )
        self.assertEqual(len(train_ids), 14)
        self.assertEqual(len(dev_ids), 3)
        self.assertEqual(len(test_ids), 3)
        self.assertEqual(set(train_ids), {str(number) for number in range(1, 15)})
        self.assertEqual(set(dev_ids), {"15", "16", "17"})
        self.assertEqual(set(test_ids), {"18", "19", "20"})
        self.assertFalse(set(train_ids) & set(dev_ids))
        self.assertFalse(set(train_ids) & set(test_ids))
        self.assertFalse(set(dev_ids) & set(test_ids))

    def test_rejects_duplicate_thread_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "threads.jsonl"
            record = _record(1)
            _write_jsonl(source, [record, record])
            with self.assertRaisesRegex(ValueError, "Duplicate thread_id"):
                split_threads(source, Path(temp_dir) / "splits")

    def test_rejects_invalid_ratios(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "threads.jsonl"
            _write_jsonl(source, [_record(number) for number in range(1, 10)])
            with self.assertRaisesRegex(ValueError, "add up to 1.0"):
                split_threads(
                    source,
                    Path(temp_dir) / "splits",
                    ratios=SplitRatios(0.8, 0.15, 0.15),
                )


if __name__ == "__main__":
    unittest.main()
