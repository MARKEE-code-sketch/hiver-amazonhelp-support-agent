"""Freeze the approved 150-row intent evaluation snapshot once."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.golden_freezer import freeze_golden_set  # noqa: E402


if __name__ == "__main__":
    result = freeze_golden_set(
        ROOT / "eval" / "golden_set_review_assistant_proposals.csv",
        ROOT / "configs" / "intents.yaml",
        ROOT / "data" / "processed" / "amazonhelp_cases" / "test.jsonl",
        ROOT / "eval" / "golden_set.csv",
        ROOT / "artifacts" / "golden_set_manifest.json",
    )
    print(json.dumps(result, indent=2))
