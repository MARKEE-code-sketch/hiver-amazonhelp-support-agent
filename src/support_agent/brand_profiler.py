"""Stream the Twitter support CSV and rank brands by usable volume."""

from __future__ import annotations

import csv
import random
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


REQUIRED_COLUMNS = {
    "tweet_id",
    "author_id",
    "inbound",
    "text",
    "in_response_to_tweet_id",
}


def _mask_sample_text(text: str) -> str:
    """Mask public identifiers in sample text saved as an artifact."""

    without_urls = re.sub(r"https?://\S+", "[URL]", text)
    return re.sub(r"@\d+", "@customer", without_urls)


@dataclass(frozen=True)
class BrandProfile:
    brand: str
    outbound_tweets: int
    outbound_with_parent: int
    verified_customer_replies: int
    unique_customer_messages_replied_to: int

    @property
    def verified_reply_rate(self) -> float:
        if self.outbound_tweets == 0:
            return 0.0
        return self.verified_customer_replies / self.outbound_tweets

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["verified_reply_rate"] = round(self.verified_reply_rate, 6)
        return result


def _rows(csv_path: Path):
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
        yield from reader


def _is_inbound(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"Invalid inbound value: {value!r}")


def profile_brands(
    csv_path: str | Path,
    *,
    top_n: int = 20,
    sample_size: int = 10,
    seed: int = 42,
) -> dict[str, object]:
    """Return top-brand counts and sample customer-to-brand reply pairs.

    The first pass counts all brand-authored rows and collects inbound tweet IDs.
    The second pass verifies that each candidate brand reply points to a real
    inbound customer tweet. A final pass resolves text for a small winner sample.
    """

    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Twitter dataset not found: {path}")
    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    if sample_size < 0:
        raise ValueError("sample_size cannot be negative")

    inbound_ids: set[str] = set()
    outbound_counts: Counter[str] = Counter()
    outbound_with_parent: Counter[str] = Counter()
    total_rows = 0
    inbound_rows = 0

    for row in _rows(path):
        total_rows += 1
        tweet_id = row["tweet_id"].strip()
        if _is_inbound(row["inbound"]):
            inbound_rows += 1
            if tweet_id:
                inbound_ids.add(tweet_id)
            continue

        brand = row["author_id"].strip()
        if not brand:
            continue
        outbound_counts[brand] += 1
        if row["in_response_to_tweet_id"].strip():
            outbound_with_parent[brand] += 1

    ranked_candidates = [brand for brand, _ in outbound_counts.most_common(top_n)]
    candidate_set = set(ranked_candidates)
    winner = ranked_candidates[0]
    verified_replies: Counter[str] = Counter()
    unique_parents: dict[str, set[str]] = defaultdict(set)

    random_source = random.Random(seed)
    sampled_replies: list[dict[str, str]] = []
    seen_winner_parents: set[str] = set()
    winner_unique_seen = 0

    for row in _rows(path):
        if _is_inbound(row["inbound"]):
            continue
        brand = row["author_id"].strip()
        if brand not in candidate_set:
            continue
        parent_id = row["in_response_to_tweet_id"].strip()
        if not parent_id or parent_id not in inbound_ids:
            continue

        verified_replies[brand] += 1
        unique_parents[brand].add(parent_id)

        if brand != winner or parent_id in seen_winner_parents or sample_size == 0:
            continue
        seen_winner_parents.add(parent_id)
        winner_unique_seen += 1
        sample = {
            "customer_tweet_id": parent_id,
            "customer_text": "",
            "brand_reply_tweet_id": row["tweet_id"].strip(),
            "brand_reply_text": _mask_sample_text(row["text"].strip()),
        }
        if len(sampled_replies) < sample_size:
            sampled_replies.append(sample)
        else:
            replacement_index = random_source.randrange(winner_unique_seen)
            if replacement_index < sample_size:
                sampled_replies[replacement_index] = sample

    sampled_parent_ids = {sample["customer_tweet_id"] for sample in sampled_replies}
    customer_text_by_id: dict[str, str] = {}
    if sampled_parent_ids:
        for row in _rows(path):
            tweet_id = row["tweet_id"].strip()
            if tweet_id in sampled_parent_ids:
                customer_text_by_id[tweet_id] = row["text"].strip()
                if len(customer_text_by_id) == len(sampled_parent_ids):
                    break

    for sample in sampled_replies:
        sample["customer_text"] = _mask_sample_text(
            customer_text_by_id.get(sample["customer_tweet_id"], "")
        )

    profiles = [
        BrandProfile(
            brand=brand,
            outbound_tweets=outbound_counts[brand],
            outbound_with_parent=outbound_with_parent[brand],
            verified_customer_replies=verified_replies[brand],
            unique_customer_messages_replied_to=len(unique_parents[brand]),
        )
        for brand in ranked_candidates
    ]

    return {
        "source_file": path.name,
        "source_bytes": path.stat().st_size,
        "total_rows": total_rows,
        "inbound_customer_rows": inbound_rows,
        "outbound_brand_rows": total_rows - inbound_rows,
        "selection_metric": "outbound_tweets",
        "validation_metric": "unique_customer_messages_replied_to",
        "winner_by_occurrence": winner,
        "top_brands": [profile.to_dict() for profile in profiles],
        "winner_sample_pairs": sampled_replies,
        "seed": seed,
    }
