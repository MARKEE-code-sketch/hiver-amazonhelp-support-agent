"""Load and validate the human-readable AmazonHelp intent taxonomy."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


REQUIRED_INTENT_FIELDS = {
    "name",
    "display_name",
    "definition",
    "include",
    "exclude",
    "examples",
    "discovery_terms",
}


def load_taxonomy(path: str | Path) -> dict[str, object]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Taxonomy file not found: {source}")
    with source.open("r", encoding="utf-8") as taxonomy_file:
        taxonomy = yaml.safe_load(taxonomy_file)
    if not isinstance(taxonomy, dict):
        raise ValueError("Taxonomy root must be a mapping")
    return taxonomy


def validate_taxonomy(taxonomy: dict[str, object]) -> list[str]:
    """Return human-readable schema errors; an empty list means valid."""

    errors: list[str] = []
    intents = taxonomy.get("intents")
    expected_count = taxonomy.get("intent_count")
    if not isinstance(intents, list):
        return ["intents must be a list"]
    if expected_count != len(intents):
        errors.append(
            f"intent_count is {expected_count!r}, but {len(intents)} intents exist"
        )

    names: list[str] = []
    for index, intent in enumerate(intents, start=1):
        if not isinstance(intent, dict):
            errors.append(f"intent {index} must be a mapping")
            continue
        missing = REQUIRED_INTENT_FIELDS - intent.keys()
        if missing:
            errors.append(f"intent {index} is missing: {', '.join(sorted(missing))}")
        name = intent.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"intent {index} has an invalid name")
        else:
            names.append(name)
        for field in ("include", "exclude", "examples", "discovery_terms"):
            value = intent.get(field)
            if not isinstance(value, list):
                errors.append(f"intent {name!r} field {field!r} must be a list")
        for field in ("include", "exclude", "examples"):
            value = intent.get(field)
            if isinstance(value, list) and len(value) < 2:
                errors.append(f"intent {name!r} needs at least two {field} entries")

    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    if duplicate_names:
        errors.append(f"duplicate intent names: {', '.join(duplicate_names)}")
    if names.count("other_or_ambiguous") != 1:
        errors.append("taxonomy must contain exactly one other_or_ambiguous intent")
    return errors


def analyze_keyword_coverage(
    taxonomy: dict[str, object], case_path: str | Path
) -> dict[str, object]:
    """Measure rough TRAIN coverage from discovery terms; this does not label cases."""

    errors = validate_taxonomy(taxonomy)
    if errors:
        raise ValueError("Invalid taxonomy: " + "; ".join(errors))
    source = Path(case_path)
    if not source.is_file():
        raise FileNotFoundError(f"Case file not found: {source}")

    intents = taxonomy["intents"]
    counts = {intent["name"]: 0 for intent in intents}
    case_count = 0
    matched_case_count = 0
    overlapping_case_count = 0
    with source.open("r", encoding="utf-8") as case_file:
        for line_number, line in enumerate(case_file, start=1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
                text = str(case["customer_text"]).lower()
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                raise ValueError(f"Invalid case on line {line_number}") from error
            case_count += 1
            matches = []
            for intent in intents:
                terms = [str(term).lower() for term in intent["discovery_terms"]]
                if terms and any(term in text for term in terms):
                    counts[intent["name"]] += 1
                    matches.append(intent["name"])
            if matches:
                matched_case_count += 1
            if len(matches) > 1:
                overlapping_case_count += 1

    return {
        "source_file": source.name,
        "case_count": case_count,
        "matched_by_at_least_one_discovery_term": matched_case_count,
        "overlapping_discovery_terms": overlapping_case_count,
        "note": "Keyword coverage validates theme presence only; it is not an intent classifier.",
        "intent_keyword_matches": counts,
    }
