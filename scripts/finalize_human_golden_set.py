"""Create the human-reviewed golden-set snapshot from the reviewed proposal CSV."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "eval" / "golden_set_review_assistant_proposals.csv"
DESTINATION = ROOT / "eval" / "golden_set_human_labelled.csv"
MANIFEST = ROOT / "artifacts" / "human_golden_set_manifest.json"


def main() -> None:
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = csv.DictReader(source_file)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    if len(rows) != 150:
        raise ValueError(f"Expected 150 rows, found {len(rows)}")
    taxonomy = yaml.safe_load((ROOT / "configs" / "intents.yaml").read_text(encoding="utf-8"))
    number_to_name = {
        str(index): intent["name"]
        for index, intent in enumerate(taxonomy["intents"], start=1)
    }
    for row in rows:
        if not row.get("gold_intent") or not row.get("intent_name"):
            raise ValueError(f"Missing intent for {row.get('example_id')}")
        if row["gold_intent"] not in number_to_name:
            raise ValueError(f"Unknown intent number for {row['example_id']}")
        row["intent_name"] = number_to_name[row["gold_intent"]]
        row["review_status"] = "human_reviewed"
        row["label_source"] = "human_reviewed"

    if DESTINATION.exists() or MANIFEST.exists():
        raise FileExistsError("Human-labelled snapshot already exists")
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with DESTINATION.open("x", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    MANIFEST.write_text(
        json.dumps(
            {
                "status": "human_reviewed",
                "row_count": len(rows),
                "source": str(SOURCE.relative_to(ROOT)),
                "note": "User reviewed and corrected the proposal labels before this snapshot was created.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {DESTINATION} with {len(rows)} human-reviewed rows")


if __name__ == "__main__":
    main()
