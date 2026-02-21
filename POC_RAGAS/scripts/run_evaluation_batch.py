"""
Batch Evaluation Runner for RAGAS (API mode only).

Runs evaluation on a single question by index. Designed to be called
repeatedly by a shell script.

Usage:
  python run_evaluation_batch.py --testset path/to/test.json --question-index 0 --output-dir ./results/batch
"""

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from POC_RAGAS.config import CONFIG
from POC_RAGAS.runners.api_runner import run_api_query

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def parse_args():
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation on a single question.")
    parser.add_argument("--testset", type=Path, required=True, help="Path to full testset JSON")
    parser.add_argument("--question-index", type=int, required=True, help="Index of question to run (0-based)")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory to save individual result")
    parser.add_argument("--cooldown", type=int, default=None, help="Seconds between requests")
    return parser.parse_args()


async def main():
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with open(args.testset) as f:
        data = json.load(f)
        if isinstance(data, dict):
            questions = data.get("data", data)
        else:
            questions = data

    if args.question_index >= len(questions):
        print(f"Error: Question index {args.question_index} out of range (max {len(questions) - 1})")
        sys.exit(1)

    item = questions[args.question_index]
    question = item.get("user_input") or item.get("question") or ""
    metadata = item.get("metadata", {})

    # Extract patient_id from metadata or question text
    patient_id = metadata.get("patient_id")
    if not patient_id:
        match = UUID_RE.search(question)
        patient_id = match.group(0) if match else None

    print(f"Processing Q[{args.question_index}]: {question[:60]}... (PID: {patient_id})")

    result_data = {
        "question_index": args.question_index,
        "question": question,
        "metadata": metadata,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }

    try:
        response = await run_api_query(
            query=question,
            session_id=f"batch-test-{args.question_index}",
            patient_id=patient_id,
            cooldown=args.cooldown,
        )
        result_data["response"] = response

        if response.get("error"):
            result_data["status"] = "failed"
            result_data["error"] = response["error"]
            if "500" in str(response["error"]):
                print(f"Detected 500 Error: {response['error']}")
                sys.exit(2)
        else:
            result_data["status"] = "success"
    except SystemExit:
        raise
    except Exception as e:
        result_data["status"] = "error"
        result_data["error"] = str(e)
        print(f"Error processing question: {e}")

    output_file = args.output_dir / f"result_{args.question_index:03d}.json"
    with open(output_file, "w") as f:
        json.dump(result_data, f, indent=2)
    print(f"Saved result for Q[{args.question_index}] to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
