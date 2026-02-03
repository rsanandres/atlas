#!/usr/bin/env python3
"""
Retry failed questions in golden_testset_candidate.json.
Finds entries where agent_answer starts with "ERROR" or "EXCEPTION" and reruns them.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add repo root to path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Load environment
from dotenv import load_dotenv
load_dotenv(_REPO_ROOT / ".env")

# Import runner
try:
    from POC_RAGAS.runners.api_runner import run_api_query
    from POC_RAGAS.utils.db_loader import get_distinct_patient_ids
except ImportError as e:
    print(f"Error importing POC_RAGAS modules: {e}")
    sys.exit(1)

async def main():
    candidate_path = Path(__file__).parent / "golden_testset_candidate.json"
    
    if not candidate_path.exists():
        print(f"File not found: {candidate_path}")
        sys.exit(1)
        
    print(f"Loading candidates from: {candidate_path}")
    with open(candidate_path, 'r') as f:
        candidates = json.load(f)
        
    distinct_patients = await get_distinct_patient_ids()
    updated_count = 0
    
    for i, item in enumerate(candidates):
        agent_answer = item.get("agent_answer", "")
        
        # Check if it failed
        if agent_answer.startswith("ERROR") or agent_answer.startswith("EXCEPTION"):
            question = item.get("question", "")
            print(f"\n[RETRYING] Q[{i}]: {question[:60]}...")
            
            # Identify patient ID
            current_patient_id = next((pid for pid in distinct_patients if pid in question), None)
            if not current_patient_id and distinct_patients:
                current_patient_id = distinct_patients[0]
                
            try:
                result = await run_api_query(
                    query=question,
                    session_id=f"golden-retry-{i}",
                    patient_id=current_patient_id
                )
                
                error = result.get("error")
                if error:
                    print(f"  > Retry Failed: {error}")
                    # Keep error message or update it
                    item["agent_answer"] = f"ERROR: {error}"
                else:
                    new_answer = result.get("response", "")
                    sources = result.get("sources", [])
                    new_contexts = []
                    for src in sources:
                        if isinstance(src, dict):
                            new_contexts.append(src.get("content_preview", ""))
                        elif isinstance(src, str):
                            new_contexts.append(src)
                            
                    print(f"  > Success! Answer len: {len(new_answer)}")
                    item["agent_answer"] = new_answer
                    item["agent_contexts"] = new_contexts
                    updated_count += 1
                    
            except Exception as e:
                print(f"  > Retry Exception: {e}")
                
    if updated_count > 0:
        with open(candidate_path, 'w') as f:
            json.dump(candidates, f, indent=2)
        print(f"\nUpdated {updated_count} failed items in {candidate_path}")
    else:
        print("\nNo failed items successfully retried (or no failures found).")

if __name__ == "__main__":
    asyncio.run(main())
