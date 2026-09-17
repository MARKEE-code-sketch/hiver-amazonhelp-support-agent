"""Reconstruct complete conversations connected to one support brand."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


TWITTER_TIME_FORMAT = "%a %b %d %H:%M:%S %z %Y"
REQUIRED_COLUMNS = {
    "tweet_id",
    "author_id",
    "inbound",
    "created_at",
    "text",
    "response_tweet_id",
    "in_response_to_tweet_id",
}


@dataclass(slots=True, frozen=True)
class Message:
    tweet_id: str
    author_id: str
    role: str
    created_at: str
    text: str
    in_response_to_tweet_id: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _response_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_inbound(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"Invalid inbound value: {value!r}")


def _timestamp(value: str) -> datetime:
    try:
        return datetime.strptime(value, TWITTER_TIME_FORMAT)
    except ValueError as error:
        raise ValueError(f"Invalid Twitter timestamp: {value!r}") from error


def _rows(csv_path: Path):
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
        yield from reader


def _discover_connected_ids(
    csv_path: Path, brand: str, max_passes: int
) -> tuple[set[str], int, int]:
    selected_ids: set[str] = set()
    source_rows = 0
    brand_tweets = 0

    for row in _rows(csv_path):
        source_rows += 1
        if _is_inbound(row["inbound"]) or row["author_id"].strip() != brand:
            continue
        brand_tweets += 1
        selected_ids.add(row["tweet_id"].strip())
        parent_id = row["in_response_to_tweet_id"].strip()
        if parent_id:
            selected_ids.add(parent_id)
        selected_ids.update(_response_ids(row["response_tweet_id"]))

    if brand_tweets == 0:
        raise ValueError(f"No outbound tweets found for brand: {brand}")

    for pass_number in range(1, max_passes + 1):
        count_before = len(selected_ids)
        for row in _rows(csv_path):
            tweet_id = row["tweet_id"].strip()
            parent_id = row["in_response_to_tweet_id"].strip()
            children = _response_ids(row["response_tweet_id"])
            related_ids = [tweet_id, parent_id, *children]
            if any(item and item in selected_ids for item in related_ids):
                selected_ids.update(item for item in related_ids if item)
        if len(selected_ids) == count_before:
            return selected_ids, source_rows, pass_number

    raise RuntimeError(f"Thread discovery did not converge within {max_passes} passes")


def _root_for(
    tweet_id: str,
    parent_by_id: dict[str, str | None],
    root_cache: dict[str, str],
) -> tuple[str, bool]:
    path: list[str] = []
    positions: dict[str, int] = {}
    current = tweet_id
    cycle_found = False

    while current not in root_cache:
        if current in positions:
            cycle_found = True
            root = min(path[positions[current] :])
            break
        positions[current] = len(path)
        path.append(current)
        parent = parent_by_id.get(current)
        if not parent:
            root = current
            break
        if parent not in parent_by_id:
            root = parent
            break
        current = parent
    else:
        root = root_cache[current]

    for item in path:
        root_cache[item] = root
    return root, cycle_found


def build_brand_threads(
    csv_path: str | Path,
    output_path: str | Path,
    *,
    brand: str,
    max_passes: int = 20,
) -> dict[str, object]:
    """Write usable connected brand conversations as JSON Lines."""

    source = Path(csv_path)
    destination = Path(output_path)
    if not source.is_file():
        raise FileNotFoundError(f"Twitter dataset not found: {source}")

    selected_ids, source_rows, closure_passes = _discover_connected_ids(
        source, brand, max_passes
    )
    messages: dict[str, Message] = {}
    parent_by_id: dict[str, str | None] = {}

    for row in _rows(source):
        tweet_id = row["tweet_id"].strip()
        if tweet_id not in selected_ids:
            continue
        inbound = _is_inbound(row["inbound"])
        parent_id = row["in_response_to_tweet_id"].strip() or None
        messages[tweet_id] = Message(
            tweet_id=tweet_id,
            author_id=row["author_id"].strip(),
            role="customer" if inbound else "brand",
            created_at=_timestamp(row["created_at"].strip()).isoformat(),
            text=row["text"].strip(),
            in_response_to_tweet_id=parent_id,
        )
        parent_by_id[tweet_id] = parent_id

    root_cache: dict[str, str] = {}
    messages_by_root: dict[str, list[Message]] = defaultdict(list)
    cycle_roots: set[str] = set()
    for tweet_id, message in messages.items():
        root, cycle_found = _root_for(tweet_id, parent_by_id, root_cache)
        messages_by_root[root].append(message)
        if cycle_found:
            cycle_roots.add(root)

    usable_threads: list[tuple[str, list[Message]]] = []
    excluded_threads = 0
    for root, thread_messages in messages_by_root.items():
        has_customer = any(message.role == "customer" for message in thread_messages)
        has_brand = any(
            message.role == "brand" and message.author_id == brand
            for message in thread_messages
        )
        if not (has_customer and has_brand):
            excluded_threads += 1
            continue
        thread_messages.sort(key=lambda message: (message.created_at, message.tweet_id))
        usable_threads.append((root, thread_messages))

    usable_threads.sort(
        key=lambda item: (item[1][0].created_at, item[0])
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    thread_lengths: list[int] = []
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as output_file:
            for root, thread_messages in usable_threads:
                thread_lengths.append(len(thread_messages))
                record = {
                    "thread_id": root,
                    "brand": brand,
                    "started_at": thread_messages[0].created_at,
                    "ended_at": thread_messages[-1].created_at,
                    "messages": [message.to_dict() for message in thread_messages],
                }
                output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()

    return {
        "source_file": source.name,
        "output_file": destination.name,
        "brand": brand,
        "source_rows": source_rows,
        "brand_seed_tweets": sum(
            1
            for message in messages.values()
            if message.role == "brand" and message.author_id == brand
        ),
        "closure_passes": closure_passes,
        "selected_reference_ids": len(selected_ids),
        "resolved_messages": len(messages),
        "missing_referenced_ids": len(selected_ids - messages.keys()),
        "usable_threads": len(usable_threads),
        "excluded_threads_without_customer_or_brand": excluded_threads,
        "usable_messages": sum(thread_lengths),
        "single_message_threads": sum(length == 1 for length in thread_lengths),
        "multi_message_threads": sum(length > 1 for length in thread_lengths),
        "cycle_count": len(cycle_roots),
    }
