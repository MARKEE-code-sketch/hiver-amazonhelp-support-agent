"""Print or save one reconstructed conversation in readable form."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from support_agent.thread_viewer import find_thread, format_thread  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("all", "train", "dev", "test"), default="test")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--thread-id")
    selection.add_argument("--number", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.split == "all":
        input_path = PROJECT_ROOT / "data" / "processed" / "amazonhelp_threads.jsonl"
    else:
        input_path = (
            PROJECT_ROOT
            / "data"
            / "processed"
            / "amazonhelp_splits"
            / f"{args.split}.jsonl"
        )

    thread = find_thread(input_path, thread_id=args.thread_id, number=args.number)
    formatted = format_thread(thread)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(formatted, encoding="utf-8")
        print(f"Saved readable thread: {args.output}")
    else:
        print(formatted, end="")


if __name__ == "__main__":
    main()
