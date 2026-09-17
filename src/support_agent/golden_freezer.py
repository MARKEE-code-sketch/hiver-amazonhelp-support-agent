"""Validate and freeze the user-approved AmazonHelp intent review CSV."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from support_agent.taxonomy import load_taxonomy, validate_taxonomy


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def freeze_golden_set(
    proposal_csv: str | Path,
    taxonomy_path: str | Path,
    test_cases: str | Path,
    output_csv: str | Path,
    manifest_path: str | Path,
) -> dict[str, object]:
    """Fail closed on invalid data, then write an immutable-by-default snapshot."""

    source = Path(proposal_csv)
    taxonomy_file = Path(taxonomy_path)
    test_file = Path(test_cases)
    destination = Path(output_csv)
    manifest_file = Path(manifest_path)
    if destination.exists() or manifest_file.exists():
        raise FileExistsError("Frozen golden set or manifest already exists; do not overwrite it")

    taxonomy = load_taxonomy(taxonomy_file)
    errors = validate_taxonomy(taxonomy)
    if errors:
        raise ValueError("Invalid taxonomy: " + "; ".join(errors))
    number_to_name = {
        str(index): intent["name"]
        for index, intent in enumerate(taxonomy["intents"], start=1)
    }
    with source.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames or len(rows) != 150:
        raise ValueError("Approved proposal must have exactly 150 rows and a header")

    expected_ids = {f"GH-{index:03d}" for index in range(1, 151)}
    seen_ids: set[str] = set()
    thread_ids: set[str] = set()
    case_ids: set[str] = set()
    status_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    for row in rows:
        example_id = row["example_id"]
        seen_ids.add(example_id)
        thread_ids.add(row["thread_id"])
        case_ids.add(row["case_id"])
        label = row["gold_intent"]
        if label not in number_to_name:
            raise ValueError(f"Unknown intent number for {example_id}: {label}")
        # The numeric label is the user's authoritative edit. Keep the readable
        # name synchronized so a spreadsheet change cannot leave contradictory
        # columns in the frozen snapshot.
        row["intent_name"] = number_to_name[label]
        if row["ambiguous"] not in {"yes", "no"}:
            raise ValueError(f"Invalid ambiguity value for {example_id}")
        if row["source_split"] != "test":
            raise ValueError(f"Non-TEST row: {example_id}")
        if row["label_source"] == "user_pilot" and row["review_status"] == "yes":
            row["review_status"] = "user_pilot_approved"
        elif row["label_source"] == "assistant_proposed" and row["review_status"] == "assistant_proposed":
            row["review_status"] = "user_approved_batch"
        else:
            raise ValueError(f"Unexpected provenance/status for {example_id}")
        status_counts[row["review_status"]] += 1
        label_counts[label] += 1

    if seen_ids != expected_ids or len(thread_ids) != 150 or len(case_ids) != 150:
        raise ValueError("Duplicate/missing example, case, or thread IDs")
    if status_counts != {"user_pilot_approved": 20, "user_approved_batch": 130}:
        raise ValueError("Expected 20 human pilot rows and 130 batch-approved proposals")

    matched_cases: dict[str, dict[str, object]] = {}
    with test_file.open("r", encoding="utf-8") as case_file:
        for line in case_file:
            if not line.strip():
                continue
            case = json.loads(line)
            if str(case["case_id"]) in case_ids:
                matched_cases[str(case["case_id"])] = case
    if matched_cases.keys() != case_ids:
        raise ValueError("At least one frozen case is absent from TEST")
    for row in rows:
        case = matched_cases[row["case_id"]]
        if (
            row["thread_id"] != str(case["thread_id"])
            or row["created_at"] != str(case["created_at"])
            or row["customer_message"] != str(case["customer_text"])
        ):
            raise ValueError(f"TEST case contents do not match {row['example_id']}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "status": "frozen_user_approved_batch_not_individually_hand_labelled",
        "row_count": len(rows),
        "unique_test_threads": len(thread_ids),
        "taxonomy_intents": len(number_to_name),
        "review_status_counts": dict(status_counts),
        "intent_counts": dict(sorted(label_counts.items(), key=lambda pair: int(pair[0]))),
        "pilot_disagreements_preserved": sum(
            bool(row["assistant_review_note"]) and row["label_source"] == "user_pilot"
            for row in rows
        ),
        "source_proposal_sha256": _sha256(source),
        "taxonomy_sha256": _sha256(taxonomy_file),
        "golden_set_sha256": _sha256(destination),
    }
    with manifest_file.open("x", encoding="utf-8") as output_file:
        json.dump(manifest, output_file, indent=2)
        output_file.write("\n")
    return manifest
