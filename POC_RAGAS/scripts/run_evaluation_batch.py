"""
Batch Evaluation Runner for RAGAS.

This script runs RAGAS evaluation on a subset of the testset or a specific question index.
Designed to be called repeatedly by a shell script that restarts the API service in between.

Usage:
  python run_evaluation_batch.py --question-index 0 --output-dir ./results/batch
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Import necessary modules from RAGAS runner
from POC_RAGAS.config import CONFIG
from POC_RAGAS.runners.api_runner import run_api_query
from POC_RAGAS.runners.agent_runner import run_agent_query
from POC_RAGAS.utils.db_loader import get_distinct_patient_ids

def parse_args():
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation on a single question.")
    parser.add_argument("--testset", type=Path, required=True, help="Path to full testset JSON")
    parser.add_argument("--question-index", type=int, required=True, help="Index of question to run (0-based)")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory to save individual result")
    parser.add_argument("--mode", choices=["api", "direct"], default="api", help="Evaluation mode")
    parser.add_argument("--patient-mode", choices=["with", "without", "both"], default="both", help="Patient filter mode")
    return parser.parse_args()

async def main():
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load testset
    with open(args.testset, 'r') as f:
        data = json.load(f)
        if isinstance(data, dict):
            questions = data.get("data", data)
        else:
            questions = data
    
    if args.question_index >= len(questions):
        print(f"Error: Question index {args.question_index} out of range (max {len(questions)-1})")
        sys.exit(1)
        
    item = questions[args.question_index]
    # Handle different field names in synthetic vs manual testsets
    question = item.get("question") or item.get("user_input") or ""
    metadata = item.get("metadata", {})
    
    ground_truths = item.get("ground_truths", [])
    if not ground_truths and item.get("reference"):
        ground_truths = [item.get("reference")]
    
    # Identify patient ID
    distinct_patients = await get_distinct_patient_ids()
    current_patient_id = next((pid for pid in distinct_patients if pid in question), None)
    if not current_patient_id:
        current_patient_id = distinct_patients[0] if distinct_patients else "unknown"
        
    print(f"Processing Q[{args.question_index}]: {question[:60]}... (PID: {current_patient_id})")
    
    result_data = {
        "question_index": args.question_index,
        "question": question,
        "ground_truths": ground_truths,
        "metadata": metadata,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "pending"
    }
    
    try:
        if args.mode == "api":
            response = await run_api_query(
                query=question,
                session_id=f"batch-test-{args.question_index}",
                patient_id=current_patient_id if args.patient_mode != "without" else None
            )
        else:
            response = await run_agent_query(
                query=question,
                session_id=f"batch-test-{args.question_index}",
                patient_id=current_patient_id if args.patient_mode != "without" else None
            )
            
        result_data["response"] = response
        
        if response.get("error"):
            error_msg = response["error"]
            result_data["status"] = "failed"
            result_data["error"] = error_msg
            
            # Special handling for 500 errors: Exit with code 2 to trigger retry
            if "500" in str(error_msg) or "Internal Server Error" in str(error_msg):
                print(f"Detected 500 Error: {error_msg}")
                sys.exit(2)  # Exit code 2 triggers retry in shell script
        else:
            result_data["status"] = "success"
            
    except SystemExit:
        raise
    except Exception as e:
        result_data["status"] = "error"
        result_data["error"] = str(e)
        print(f"Error processing question: {e}")

    # Save individual result
    output_file = args.output_dir / f"result_{args.question_index:03d}.json"
    with open(output_file, 'w') as f:
        json.dump(result_data, f, indent=2)
        
    print(f"Saved result for Q[{args.question_index}] to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
