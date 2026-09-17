"""Find and format one JSONL conversation for human review."""

from __future__ import annotations

import json
from pathlib import Path


def find_thread(
    input_path: str | Path,
    *,
    thread_id: str | None = None,
    number: int | None = None,
) -> dict[str, object]:
    """Return a thread by ID or one-based line number."""

    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Thread file not found: {path}")
    if (thread_id is None) == (number is None):
        raise ValueError("Provide exactly one of thread_id or number")
    if number is not None and number < 1:
        raise ValueError("number must be at least 1")

    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if number == line_number:
                return json.loads(line)
            if thread_id is not None:
                record = json.loads(line)
                if str(record["thread_id"]) == str(thread_id):
                    return record

    requested = f"thread_id={thread_id}" if thread_id is not None else f"number={number}"
    raise LookupError(f"Thread not found: {requested}")


def format_thread(thread: dict[str, object]) -> str:
    """Format a thread as readable Markdown-style text."""

    lines = [
        f"# Thread {thread['thread_id']}",
        "",
        f"Brand: {thread['brand']}",
        f"Started: {thread['started_at']}",
        f"Ended: {thread['ended_at']}",
        f"Messages: {len(thread['messages'])}",
        "",
    ]
    for index, message in enumerate(thread["messages"], start=1):
        role = "CUSTOMER" if message["role"] == "customer" else "AMAZONHELP"
        lines.extend(
            [
                f"## {index}. {role}",
                f"Time: {message['created_at']}",
                f"Tweet ID: {message['tweet_id']}",
                "",
                str(message["text"]),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
