"""Convert reconstructed threads into English customer-to-Amazon support cases."""

from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path


URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"@\w+")
SIGNATURE_PATTERN = re.compile(r"\s+\^[A-Za-z]{1,4}\s*$")
TOKEN_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
ENGLISH_MARKERS = {
    "a", "about", "after", "again", "all", "am", "an", "and", "are", "as",
    "at", "back", "be", "been", "before", "but", "by", "can", "cancel",
    "card", "could", "customer", "day", "delivery", "did", "do", "does",
    "done", "for", "from", "get", "got", "had", "has", "have", "help",
    "how", "i", "if", "in", "is", "it", "item", "late", "me", "missing",
    "my", "no", "not", "of", "on", "order", "package", "payment", "please",
    "prime", "problem", "received", "refund", "return", "still", "thanks",
    "that", "the", "this", "to", "tracking", "was", "we", "what", "when",
    "where", "why", "will", "with", "working", "would", "you", "your",
}


def clean_text(text: str) -> str:
    """Remove platform noise while preserving issue-bearing words."""

    cleaned = html.unescape(text)
    cleaned = URL_PATTERN.sub("[URL]", cleaned)
    cleaned = MENTION_PATTERN.sub("[USER]", cleaned)
    cleaned = SIGNATURE_PATTERN.sub("", cleaned)
    return " ".join(cleaned.split())


def is_english_candidate(text: str) -> bool:
    """Conservatively identify likely English text without a model dependency."""

    letters = [character for character in text if character.isalpha()]
    if not letters:
        return False
    ascii_ratio = sum(character.isascii() for character in letters) / len(letters)
    if ascii_ratio < 0.95:
        return False
    tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]
    if not tokens:
        return False
    marker_count = sum(token in ENGLISH_MARKERS for token in tokens)
    if len(tokens) <= 3:
        return marker_count >= 1
    return marker_count >= 2 or marker_count / len(tokens) >= 0.15


def build_cases(
    input_path: str | Path,
    output_path: str | Path,
    *,
    brand: str = "AmazonHelp",
    context_messages: int = 4,
) -> dict[str, object]:
    """Write direct customer-message/Amazon-reply cases as JSON Lines."""

    source = Path(input_path)
    destination = Path(output_path)
    if not source.is_file():
        raise FileNotFoundError(f"Thread split not found: {source}")
    if context_messages < 0:
        raise ValueError("context_messages cannot be negative")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    thread_count = 0
    direct_pairs = 0
    english_cases = 0
    rejected_language_scope = 0
    threads_with_cases: set[str] = set()

    try:
        with source.open("r", encoding="utf-8") as input_file, temporary.open(
            "w", encoding="utf-8", newline="\n"
        ) as output_file:
            for line_number, line in enumerate(input_file, start=1):
                if not line.strip():
                    continue
                try:
                    thread = json.loads(line)
                    messages = thread["messages"]
                except (json.JSONDecodeError, KeyError, TypeError) as error:
                    raise ValueError(
                        f"Invalid thread record on line {line_number}"
                    ) from error
                thread_count += 1
                position_by_id = {
                    str(message["tweet_id"]): index
                    for index, message in enumerate(messages)
                }
                replies_by_customer: dict[str, list[dict[str, object]]] = defaultdict(list)
                for message in messages:
                    parent_id = message.get("in_response_to_tweet_id")
                    if (
                        message.get("role") == "brand"
                        and message.get("author_id") == brand
                        and parent_id in position_by_id
                        and messages[position_by_id[parent_id]].get("role") == "customer"
                    ):
                        replies_by_customer[str(parent_id)].append(message)

                for customer_id, replies in replies_by_customer.items():
                    direct_pairs += 1
                    customer_index = position_by_id[customer_id]
                    customer = messages[customer_index]
                    replies.sort(key=lambda message: (message["created_at"], message["tweet_id"]))
                    raw_customer_text = str(customer["text"])
                    raw_reply = "\n".join(str(reply["text"]) for reply in replies)
                    if not (
                        is_english_candidate(raw_customer_text)
                        and is_english_candidate(raw_reply)
                    ):
                        rejected_language_scope += 1
                        continue

                    context_start = max(0, customer_index - context_messages)
                    context = [
                        {
                            "role": previous["role"],
                            "text": clean_text(str(previous["text"])),
                        }
                        for previous in messages[context_start:customer_index]
                    ]
                    record = {
                        "case_id": customer_id,
                        "thread_id": str(thread["thread_id"]),
                        "created_at": customer["created_at"],
                        "customer_text_raw": raw_customer_text,
                        "customer_text": clean_text(raw_customer_text),
                        "context": context,
                        "historical_reply": clean_text(raw_reply),
                        "reply_tweet_ids": [str(reply["tweet_id"]) for reply in replies],
                        "language_scope": "english_candidate",
                    }
                    output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                    english_cases += 1
                    threads_with_cases.add(str(thread["thread_id"]))
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)

    return {
        "source_file": source.name,
        "output_file": destination.name,
        "brand": brand,
        "threads_read": thread_count,
        "direct_customer_reply_pairs": direct_pairs,
        "english_candidate_cases": english_cases,
        "rejected_by_english_scope": rejected_language_scope,
        "threads_with_cases": len(threads_with_cases),
        "english_filter": "conservative_heuristic_requires_human_validation",
    }
