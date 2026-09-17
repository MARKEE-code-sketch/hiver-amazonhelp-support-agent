"""Small, offline comparison systems for the support agent."""

from __future__ import annotations

from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from support_agent.intent_discovery import sample_cases
from support_agent.taxonomy import load_taxonomy, validate_taxonomy


SAFE_REPLY = (
    "Thanks for reaching out. Please contact Amazon support through your account "
    "so they can review the details safely."
)


def fixed_baseline(message: str) -> dict[str, object]:
    """A deliberately weak, fixed-intent comparison with safe escalation."""

    if not message.strip():
        raise ValueError("Customer message cannot be empty")
    return {
        "intent": "delivery_or_courier_issue",
        "reply": SAFE_REPLY,
        "action": "ESCALATE",
        "evidence_case_id": None,
    }


class SimilarityBaseline:
    """Match taxonomy descriptions and find one similar TRAIN support case."""

    def __init__(
        self,
        train_cases: str | Path,
        taxonomy_path: str | Path,
        *,
        sample_size: int = 5_000,
        seed: int = 42,
    ) -> None:
        source = Path(train_cases)
        if source.name != "train.jsonl":
            raise ValueError("The similarity baseline must fit TRAIN cases only")
        taxonomy = load_taxonomy(taxonomy_path)
        errors = validate_taxonomy(taxonomy)
        if errors:
            raise ValueError("Invalid taxonomy: " + "; ".join(errors))

        self.cases = sample_cases(source, sample_size=sample_size, seed=seed)
        self.intent_names = [intent["name"] for intent in taxonomy["intents"]]
        intent_documents = [
            " ".join(
                [
                    intent["display_name"],
                    intent["definition"],
                    *intent["include"],
                    *intent["examples"],
                    *intent["discovery_terms"],
                ]
            )
            for intent in taxonomy["intents"]
        ]
        case_documents = [str(case["customer_text"]) for case in self.cases]
        self.vectorizer = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), max_features=20_000
        )
        matrix = self.vectorizer.fit_transform(intent_documents + case_documents)
        self.intent_matrix = matrix[: len(intent_documents)]
        self.case_matrix = matrix[len(intent_documents) :]

    def predict(self, message: str) -> dict[str, object]:
        """Return an intent and evidence; never auto-send an old support reply."""

        if not message.strip():
            raise ValueError("Customer message cannot be empty")
        query = self.vectorizer.transform([message])
        intent_scores = cosine_similarity(query, self.intent_matrix).ravel()
        case_scores = cosine_similarity(query, self.case_matrix).ravel()
        if not intent_scores.any():
            return {
                "intent": "other_or_ambiguous",
                "intent_similarity": 0.0,
                "reply": SAFE_REPLY,
                "action": "ESCALATE",
                "evidence_case_id": None,
                "evidence_similarity": 0.0,
                "historical_reply_for_review": None,
            }
        intent_index = int(intent_scores.argmax())
        case_index = int(case_scores.argmax())
        case = self.cases[case_index] if case_scores[case_index] > 0 else None
        return {
            "intent": self.intent_names[intent_index],
            "intent_similarity": round(float(intent_scores[intent_index]), 4),
            "reply": SAFE_REPLY,
            "action": "ESCALATE",
            "evidence_case_id": str(case["case_id"]) if case else None,
            "evidence_similarity": round(float(case_scores[case_index]), 4),
            "historical_reply_for_review": (
                str(case["historical_reply"]) if case else None
            ),
        }

    def search_cases(self, message: str, *, k: int = 5) -> list[dict[str, object]]:
        """Expose the TF-IDF case ranking for a fair retrieval comparison."""

        if k < 1:
            raise ValueError("k must be at least 1")
        if not message.strip():
            return []
        query = self.vectorizer.transform([message])
        scores = cosine_similarity(query, self.case_matrix).ravel()
        indices = (-scores).argsort(kind="stable")[:k]
        return [
            {
                "case_id": str(self.cases[index]["case_id"]),
                "customer_text": str(self.cases[index]["customer_text"]),
                "similarity": round(float(scores[index]), 4),
            }
            for index in indices
            if scores[index] > 0
        ]
