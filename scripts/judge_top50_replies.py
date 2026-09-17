"""Judge the 50 saved main-system replies with Groq and prepare human review."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.evaluator import GeminiReplyJudge, score_reply_judgments  # noqa: E402
from support_agent.groq_client import GroqStructuredClient  # noqa: E402


def main() -> None:
    load_dotenv(ROOT / ".env")
    source = ROOT / "artifacts" / "top50_predictions.json"
    artifact = json.loads(source.read_text(encoding="utf-8"))
    if not artifact.get("complete") or artifact.get("count") != 50:
        raise ValueError("Top-50 prediction artifact is incomplete")
    rows = artifact["results"]
    generator_error_ids = {
        row["example_id"] for row in rows if row["systems"]["main"].get("generator_error")
    }
    output = ROOT / "artifacts" / "top50_reply_judgments.json"
    judgments: list[dict[str, object]] = []
    if output.is_file():
        checkpoint = json.loads(output.read_text(encoding="utf-8"))
        judgments = list(checkpoint.get("judgments", []))
        print(f"Resuming reply judging from checkpoint: {len(judgments)}/50")

    judge = GeminiReplyJudge(client=GroqStructuredClient())
    for index, row in enumerate(rows[len(judgments):], start=len(judgments) + 1):
        main = row["systems"]["main"]
        if main.get("generator_error"):
            score = {
                "relevance": 1,
                "groundedness": 1,
                "helpfulness": 1,
                "tone": 3,
                "safety": 5,
                "escalation_appropriateness": 5,
                "passed": False,
                "critical_unsupported_claim": False,
                "rationale": "The reply generator failed; the safe handoff was evaluated as a failed customer reply.",
            }
        else:
            try:
                score = judge.judge(
                    customer_message=row["customer_message"],
                    intent=main["intent"],
                    reply=main["reply"],
                    evidence=main["evidence"],
                ).model_dump()
            except Exception as error:
                score = {
                    "relevance": 1,
                    "groundedness": 1,
                    "helpfulness": 1,
                    "tone": 1,
                    "safety": 1,
                    "escalation_appropriateness": 1,
                    "passed": False,
                    "critical_unsupported_claim": False,
                    "rationale": "Judge provider/format failure; manual review required.",
                    "judge_error": type(error).__name__,
                }
        judgments.append({"example_id": row["example_id"], **score})
        output.write_text(
            json.dumps({"complete": index == len(rows), "count": index, "judgments": judgments}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Judged {index}/50")

    valid_judgments = [
        row for row in judgments if not row.get("judge_error") and row["example_id"] not in generator_error_ids
    ]
    metrics = {
        "all_50": score_reply_judgments(judgments),
        "valid_judgment_subset": score_reply_judgments(valid_judgments),
        "valid_judgment_count": len(valid_judgments),
        "judge_error_counts": {
            error: sum(row.get("judge_error") == error for row in judgments)
            for error in sorted({row.get("judge_error") for row in judgments if row.get("judge_error")})
        },
        "provider": "Groq",
        "model": "openai/gpt-oss-20b",
        "limitation": "No independent human reply ratings yet; judge agreement is pending. Rate-limited and malformed judge rows are excluded from the valid subset.",
    }
    (ROOT / "artifacts" / "top50_reply_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    review_path = ROOT / "eval" / "top50_reply_human_review.csv"
    with review_path.open("w", encoding="utf-8-sig", newline="") as review_file:
        writer = csv.DictWriter(
            review_file,
            fieldnames=["example_id", "customer_message", "reply", "judge_pass", "human_score_1_to_5", "human_pass", "human_notes"],
        )
        writer.writeheader()
        for row, judgment in zip(rows, judgments):
            writer.writerow(
                {
                    "example_id": row["example_id"],
                    "customer_message": row["customer_message"],
                    "reply": row["systems"]["main"]["reply"],
                    "judge_pass": judgment["passed"],
                    "human_score_1_to_5": "",
                    "human_pass": "",
                    "human_notes": "",
                }
            )
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
