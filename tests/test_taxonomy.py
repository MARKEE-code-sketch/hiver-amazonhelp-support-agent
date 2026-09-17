from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.taxonomy import load_taxonomy, validate_taxonomy


class TaxonomyTests(unittest.TestCase):
    def test_project_taxonomy_has_thirteen_valid_unique_intents(self) -> None:
        taxonomy = load_taxonomy(PROJECT_ROOT / "configs" / "intents.yaml")
        self.assertEqual(validate_taxonomy(taxonomy), [])
        self.assertEqual(taxonomy["intent_count"], 13)
        names = [intent["name"] for intent in taxonomy["intents"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("other_or_ambiguous", names)
        self.assertIn("customer_appreciation", names)

    def test_duplicate_and_missing_fallback_are_rejected(self) -> None:
        intent = {
            "name": "duplicate",
            "display_name": "Duplicate",
            "definition": "Test",
            "include": ["one", "two"],
            "exclude": ["one", "two"],
            "examples": ["one", "two"],
            "discovery_terms": [],
        }
        taxonomy = {"intent_count": 2, "intents": [intent, intent.copy()]}
        errors = validate_taxonomy(taxonomy)
        self.assertTrue(any("duplicate intent names" in error for error in errors))
        self.assertTrue(any("other_or_ambiguous" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
