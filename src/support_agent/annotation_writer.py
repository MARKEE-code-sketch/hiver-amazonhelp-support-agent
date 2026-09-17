"""Apply human pilot labels and assistant proposals without overwriting the source CSV."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


def _load_json(path: str | Path) -> dict[str, object]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"JSON file not found: {source}")
    with source.open("r", encoding="utf-8") as json_file:
        value = json.load(json_file)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {source}")
    return value


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


def _load_replacement_cases(
    test_case_path: str | Path, required_case_ids: set[str]
) -> dict[str, dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    with Path(test_case_path).open("r", encoding="utf-8") as case_file:
        for line_number, line in enumerate(case_file, start=1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
                case_id = str(case["case_id"])
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                raise ValueError(f"Invalid TEST case on line {line_number}") from error
            if case_id in required_case_ids:
                found[case_id] = case
    missing = required_case_ids - found.keys()
    if missing:
        raise ValueError(f"Replacement TEST cases not found: {', '.join(sorted(missing))}")
    return found


def _replace_case(row: dict[str, str], case: dict[str, object]) -> None:
    row.update(
        {
            "case_id": str(case["case_id"]),
            "thread_id": str(case["thread_id"]),
            "created_at": str(case["created_at"]),
            "customer_message": str(case["customer_text"]),
            "prior_context": _format_context(case.get("context", [])),
            "historical_amazon_reply": str(case["historical_reply"]),
        }
    )


def apply_annotation_proposals(
    input_csv: str | Path,
    proposals_json: str | Path,
    test_case_path: str | Path,
    output_csv: str | Path,
) -> dict[str, object]:
    """Create a labelled review copy while preserving the user's pilot source."""

    proposals = _load_json(proposals_json)
    numeric_labels = {
        str(number): str(name)
        for number, name in dict(proposals["numeric_labels"]).items()
    }
    labels = dict(proposals["labels"])
    pilot_updates = {
        str(example_id): str(number)
        for example_id, number in dict(proposals["pilot_updates"]).items()
    }
    pilot_review_notes = {
        str(example_id): str(note)
        for example_id, note in dict(proposals["pilot_review_notes"]).items()
    }
    replacements = {
        str(example_id): str(case_id)
        for example_id, case_id in dict(proposals["replacements"]).items()
    }
    replacement_cases = _load_replacement_cases(
        test_case_path, set(replacements.values())
    )

    source = Path(input_csv)
    with source.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        rows = list(reader)
        input_fields = list(reader.fieldnames or [])
    if not rows:
        raise ValueError("Input review CSV is empty")

    output_fields = input_fields + [
        field
        for field in ("intent_name", "label_source", "assistant_review_note")
        if field not in input_fields
    ]
    seen_examples: set[str] = set()
    for row in rows:
        example_id = row.get("example_id", "")
        if not example_id or example_id in seen_examples:
            raise ValueError(f"Missing or duplicate example_id: {example_id!r}")
        seen_examples.add(example_id)

        if example_id in replacements:
            _replace_case(row, replacement_cases[replacements[example_id]])

        if example_id in labels:
            proposal = labels[example_id]
            if not isinstance(proposal, dict):
                raise ValueError(f"Invalid proposal for {example_id}")
            intent_number = str(proposal["intent"])
            row["gold_intent"] = intent_number
            row["ambiguous"] = str(proposal["ambiguous"])
            row["annotator_notes"] = str(proposal.get("note", ""))
            row["review_status"] = "assistant_proposed"
            row["label_source"] = "assistant_proposed"
        else:
            if not row.get("gold_intent"):
                raise ValueError(f"Pilot label is missing for {example_id}")
            if example_id in pilot_updates:
                row["gold_intent"] = pilot_updates[example_id]
            intent_number = row["gold_intent"]
            row["label_source"] = "user_pilot"

        if intent_number not in numeric_labels:
            raise ValueError(f"Unknown numeric intent {intent_number!r} for {example_id}")
        row["intent_name"] = numeric_labels[intent_number]
        row["assistant_review_note"] = pilot_review_notes.get(example_id, "")

    missing_proposals = set(labels) - seen_examples
    if missing_proposals:
        raise ValueError(
            "Proposal IDs missing from CSV: " + ", ".join(sorted(missing_proposals))
        )

    destination = Path(output_csv)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8-sig", newline="") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=output_fields)
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)

    digest = hashlib.sha256(destination.read_bytes()).hexdigest().upper()
    distribution = Counter(row["gold_intent"] for row in rows)
    return {
        "output_file": str(destination),
        "row_count": len(rows),
        "user_pilot_rows": sum(row["label_source"] == "user_pilot" for row in rows),
        "assistant_proposed_rows": sum(
            row["label_source"] == "assistant_proposed" for row in rows
        ),
        "replaced_non_english_rows": len(replacements),
        "ambiguous_rows": sum(row["ambiguous"].lower() == "yes" for row in rows),
        "intent_distribution": dict(sorted(distribution.items(), key=lambda item: int(item[0]))),
        "sha256": digest,
        "status": "assistant_proposals_require_user_approval",
    }
