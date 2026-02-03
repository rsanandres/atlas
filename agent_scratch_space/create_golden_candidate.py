
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add repo root to path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Load environment
from dotenv import load_dotenv, find_dotenv
env_path = _REPO_ROOT / ".env"
load_dotenv(env_path)

# Import runner
try:
    from POC_RAGAS.runners.api_runner import run_api_query
    from POC_RAGAS.utils.db_loader import get_distinct_patient_ids
except ImportError as e:
    print(f"Error importing POC_RAGAS modules: {e}")
    sys.exit(1)

async def main():
    testset_path = _REPO_ROOT / "POC_RAGAS/data/testsets/clinical_testset.json"
    output_path = Path(__file__).parent / "golden_testset_candidate.json"
    
    print(f"Loading testset from: {testset_path}")
    
    try:
        with open(testset_path, 'r') as f:
            data = json.load(f)
            questions = data if isinstance(data, list) else data.get("data", [])
    except FileNotFoundError:
        print(f"Testset not found at {testset_path}")
        sys.exit(1)
        
    print(f"Found {len(questions)} questions.")
    
    distinct_patients = await get_distinct_patient_ids()
    candidate_data = []

    # Load existing verified truths to preserve golden answers
    verified_path = Path(__file__).parent / "verified_golden_truths.json"
    verified_map = {}
    if verified_path.exists():
        print(f"Loading existing verified truths from {verified_path}")
        with open(verified_path, 'r') as f:
            verified_list = json.load(f)
            for item in verified_list:
                q_text = item.get("question", "").strip()
                if q_text:
                    verified_map[q_text] = item.get("golden_answer", "")

    
    for i, item in enumerate(questions):
        question = item.get("user_input") or item.get("question")
        print(f"\nProcessing Q[{i+1}/{len(questions)}]: {question[:60]}...")
        
        # Identify patient ID (simple logic)
        current_patient_id = next((pid for pid in distinct_patients if pid in question), None)
        if not current_patient_id and distinct_patients:
            current_patient_id = distinct_patients[0]
            
        # Run agent
        print(f"  > Running agent for PID: {current_patient_id}...")
        try:
            result = await run_api_query(
                query=question,
                session_id=f"golden-candidate-{i}",
                patient_id=current_patient_id
            )
            
            error = result.get("error")
            if error:
                print(f"  > Error: {error}")
                agent_answer = f"ERROR: {error}"
                agent_contexts = []
            else:
                agent_answer = result.get("response", "")
                sources = result.get("sources", [])
                agent_contexts = []
                for src in sources:
                    if isinstance(src, dict):
                        agent_contexts.append(src.get("content_preview", ""))
                    elif isinstance(src, str):
                        agent_contexts.append(src)
                
                print(f"  > Success. Answer len: {len(agent_answer)}, Contexts: {len(agent_contexts)}")
                
        except Exception as e:
            print(f"  > Exception: {e}")
            agent_answer = f"EXCEPTION: {str(e)}"
            agent_contexts = []
            
        # Construct candidate entry
        entry = {
            "question": question,
            "agent_answer": agent_answer,
            "agent_contexts": agent_contexts,
            "agent_contexts": agent_contexts,
            "golden_answer": verified_map.get(question.strip(), ""), # Preserve verified answer

            "golden_contexts": [], # User to fill (optional)
            "original_reference": item.get("reference", ""), # Helpful context for user
            "metadata": item.get("metadata", {})
        }
        candidate_data.append(entry)
        
    # Save output
    with open(output_path, 'w') as f:
        json.dump(candidate_data, f, indent=2)
        
    print(f"\nSaved {len(candidate_data)} candidates to {output_path}")
    print("ACTION REQUIRED: Review this file, fill in 'golden_answer', and save as 'golden_testset_verified.json'")

if __name__ == "__main__":
    asyncio.run(main())
