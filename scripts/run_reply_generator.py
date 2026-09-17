"""Run one synthetic grounded-reply smoke test."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_agent.reply_generator import ReplyGenerator  # noqa: E402


if __name__ == "__main__":
    load_dotenv(ROOT / ".env")
    generator = ReplyGenerator()
    draft = generator.generate(
        "My parcel says delivered but I cannot find it.",
        "delivered_not_received",
        [
            {
                "case_id": "synthetic-1",
                "customer_text": "It says delivered, but I did not receive the parcel.",
                "historical_reply": "Please contact support so we can investigate the delivery.",
                "similarity": 0.86,
            }
        ],
    )
    print(draft.model_dump_json())
