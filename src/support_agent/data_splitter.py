"""Split complete conversation threads chronologically without leakage."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SplitRatios:
    train: float = 0.70
    dev: float = 0.15
    test: float = 0.15

    def validate(self) -> None:
        values = (self.train, self.dev, self.test)
        if any(value <= 0 for value in values):
            raise ValueError("All split ratios must be greater than zero")
        if abs(sum(values) - 1.0) > 1e-9:
            raise ValueError("Split ratios must add up to 1.0")


def _read_metadata(input_path: Path) -> list[tuple[datetime, str]]:
    metadata: list[tuple[datetime, str]] = []
    seen_ids: set[str] = set()
    with input_path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                thread_id = str(record["thread_id"])
                started_at = datetime.fromisoformat(record["started_at"])
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                raise ValueError(f"Invalid thread record on line {line_number}") from error
            if thread_id in seen_ids:
                raise ValueError(f"Duplicate thread_id: {thread_id}")
            seen_ids.add(thread_id)
            metadata.append((started_at, thread_id))
    if not metadata:
        raise ValueError("Thread file is empty")
    return metadata


def _allocation(total: int, ratios: SplitRatios) -> dict[str, int]:
    train_count = int(total * ratios.train)
    dev_count = int(total * ratios.dev)
    test_count = total - train_count - dev_count
    if min(train_count, dev_count, test_count) == 0:
        raise ValueError("Not enough threads to create three non-empty splits")
    return {"train": train_count, "dev": dev_count, "test": test_count}


def split_threads(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    ratios: SplitRatios = SplitRatios(),
) -> dict[str, object]:
    """Write deterministic TRAIN/DEV/TEST JSONL files by thread start time."""

    source = Path(input_path)
    destination = Path(output_dir)
    if not source.is_file():
        raise FileNotFoundError(f"Thread dataset not found: {source}")
    ratios.validate()

    metadata = _read_metadata(source)
    metadata.sort(key=lambda item: (item[0], item[1]))
    counts = _allocation(len(metadata), ratios)

    train_end = counts["train"]
    dev_end = train_end + counts["dev"]
    ordered_assignments = {
        "train": metadata[:train_end],
        "dev": metadata[train_end:dev_end],
        "test": metadata[dev_end:],
    }
    split_by_thread = {
        thread_id: split_name
        for split_name, items in ordered_assignments.items()
        for _, thread_id in items
    }

    destination.mkdir(parents=True, exist_ok=True)
    final_paths = {
        split_name: destination / f"{split_name}.jsonl"
        for split_name in ordered_assignments
    }
    temporary_paths = {
        split_name: path.with_suffix(".jsonl.tmp")
        for split_name, path in final_paths.items()
    }
    handles = {
        split_name: path.open("w", encoding="utf-8", newline="\n")
        for split_name, path in temporary_paths.items()
    }
    written_counts = {split_name: 0 for split_name in ordered_assignments}
    message_counts = {split_name: 0 for split_name in ordered_assignments}

    try:
        with source.open("r", encoding="utf-8") as input_file:
            for line in input_file:
                if not line.strip():
                    continue
                record = json.loads(line)
                thread_id = str(record["thread_id"])
                split_name = split_by_thread[thread_id]
                handles[split_name].write(line.rstrip("\r\n") + "\n")
                written_counts[split_name] += 1
                message_counts[split_name] += len(record.get("messages", []))
    finally:
        for handle in handles.values():
            handle.close()

    if written_counts != counts:
        for path in temporary_paths.values():
            path.unlink(missing_ok=True)
        raise RuntimeError(f"Written split counts do not match allocation: {written_counts}")

    for split_name, temporary_path in temporary_paths.items():
        temporary_path.replace(final_paths[split_name])

    split_details: dict[str, dict[str, object]] = {}
    for split_name, items in ordered_assignments.items():
        path = final_paths[split_name]
        digest = hashlib.sha256()
        with path.open("rb") as split_file:
            for chunk in iter(lambda: split_file.read(1024 * 1024), b""):
                digest.update(chunk)
        split_details[split_name] = {
            "file": path.name,
            "threads": len(items),
            "messages": message_counts[split_name],
            "earliest_started_at": items[0][0].isoformat(),
            "latest_started_at": items[-1][0].isoformat(),
            "bytes": path.stat().st_size,
            "sha256": digest.hexdigest().upper(),
        }

    return {
        "source_file": source.name,
        "method": "chronological_by_complete_thread",
        "total_threads": len(metadata),
        "ratios": {
            "train": ratios.train,
            "dev": ratios.dev,
            "test": ratios.test,
        },
        "splits": split_details,
    }
