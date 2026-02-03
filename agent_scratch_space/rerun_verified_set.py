#!/usr/bin/env python3
"""
Rerun the agent on the verified 19 questions to generate a valid comparison.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add repo root_REPO_ROOT
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Load environment
from dotenv import load_dotenv
load_dotenv(_REPO_ROOT / ".env")

# Import runner
try:
    from POC_RAGAS.runners.api_runner import run_api_query
except ImportError as e:
    print(f"Error importing POC_RAGAS modules: {e}")
    sys.exit(1)

async def main():
    # Input: The verified golden truths file (contains questions + golden answers)
    input_path = Path(__file__).parent / "verified_golden_truths.json"
    output_path = Path(__file__).parent / "golden_testset_candidate_19.json"
    
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)
        
    print(f"Loading verified questions from: {input_path}")
    with open(input_path, 'r') as f:
        data = json.load(f)
        
    print(f"Found {len(data)} questions.")
    
    results = []
    
    for i, item in enumerate(data):
        question = item.get("question")
        patient_id = item.get("patient_id")
        golden_answer = item.get("golden_answer")
        
        print(f"\nProcessing Q[{i+1}/{len(data)}]: {question[:60]}...")
        print(f"  > Patient ID: {patient_id}")
        
        try:
            result = await run_api_query(
                query=question,
                session_id=f"golden-run-19-{i}",
                patient_id=patient_id
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
            
        # Construct output entry
        entry = {
            "question_index": i,
            "question": question,
            "patient_id": patient_id,
            "agent_answer": agent_answer,
            "agent_contexts": agent_contexts,
            "golden_answer": golden_answer, # Preserve golden answer
            "metadata": item.get("metadata", {})
        }
        results.append(entry)
        
    # Save output
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
        
    print(f"\nSaved {len(results)} results to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
