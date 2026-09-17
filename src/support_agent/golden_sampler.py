"""Create a readable, deterministic intent-review sample from TEST cases."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path


GENERIC_WITHOUT_CONTEXT = {
    "done",
    "no",
    "nope",
    "ok",
    "okay",
    "thanks",
    "thank you",
    "yes",
    "yep",
}


def _plain_text(text: str) -> str:
    text = text.replace("[USER]", "").replace("[URL]", "link")
    return " ".join(text.lower().split()).strip(" .!?,")


def is_reviewable(case: dict[str, object]) -> bool:
    """Reject only context-free acknowledgements that cannot reveal an intent."""

    customer_text = str(case.get("customer_text", "")).strip()
    context = case.get("context", [])
    if not customer_text:
        return False
    return bool(context) or _plain_text(customer_text) not in GENERIC_WITHOUT_CONTEXT


def _format_context(context: object) -> str:
    if not isinstance(context, list):
        return ""
    lines = []
    for message in context:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "unknown")).upper()
        text = str(message.get("text", "")).strip()
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines)


def sample_review_cases(
    input_path: str | Path, *, sample_size: int = 150, seed: int = 42
) -> list[dict[str, object]]:
    """Reservoir-sample reviewable cases, keeping at most one per thread."""

    source = Path(input_path)
    if not source.is_file():
        raise FileNotFoundError(f"Case file not found: {source}")
    if sample_size < 1:
        raise ValueError("sample_size must be at least 1")

    random_source = random.Random(seed)
    sample: list[dict[str, object]] = []
    seen_threads: set[str] = set()
    eligible_count = 0

    with source.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
                thread_id = str(case["thread_id"])
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                raise ValueError(f"Invalid case on line {line_number}") from error
            if thread_id in seen_threads or not is_reviewable(case):
                continue
            seen_threads.add(thread_id)
            eligible_count += 1
            if len(sample) < sample_size:
                sample.append(case)
                continue
            replacement_index = random_source.randrange(eligible_count)
            if replacement_index < sample_size:
                sample[replacement_index] = case

    if len(sample) < sample_size:
        raise ValueError(
            f"Requested {sample_size} cases but only found {len(sample)} eligible threads"
        )
    sample.sort(key=lambda case: (str(case["created_at"]), str(case["case_id"])))
    return sample


def write_review_csv(
    cases: list[dict[str, object]], output_path: str | Path, *, seed: int = 42
) -> dict[str, object]:
    """Write an Excel-friendly CSV with blank human annotation fields."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    fieldnames = [
        "example_id",
        "source_split",
        "case_id",
        "thread_id",
        "created_at",
        "customer_message",
        "prior_context",
        "historical_amazon_reply",
        "gold_intent",
        "ambiguous",
        "annotator_notes",
        "review_status",
    ]
    try:
        with temporary.open("w", encoding="utf-8-sig", newline="") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            writer.writeheader()
            for index, case in enumerate(cases, start=1):
                writer.writerow(
                    {
                        "example_id": f"GH-{index:03d}",
                        "source_split": "test",
                        "case_id": case["case_id"],
                        "thread_id": case["thread_id"],
                        "created_at": case["created_at"],
                        "customer_message": case["customer_text"],
                        "prior_context": _format_context(case.get("context", [])),
                        "historical_amazon_reply": case["historical_reply"],
                        "gold_intent": "",
                        "ambiguous": "",
                        "annotator_notes": "",
                        "review_status": "",
                    }
                )
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)

    return {
        "output_file": str(destination),
        "sample_size": len(cases),
        "seed": seed,
        "unique_thread_count": len({str(case["thread_id"]) for case in cases}),
        "source_split": "test",
        "label_status": "pending_human_review",
    }


def build_review_sample(
    input_path: str | Path,
    output_path: str | Path,
    *,
    sample_size: int = 150,
    seed: int = 42,
) -> dict[str, object]:
    cases = sample_review_cases(input_path, sample_size=sample_size, seed=seed)
    return write_review_csv(cases, output_path, seed=seed)
