#!/usr/bin/env python3
import asyncio
import json
import sys
from pathlib import Path

# Simple inline version
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

async def main():
    from POC_RAGAS.runners.api_runner import run_api_query
    
    question = "What is the patient's Body Mass Index (BMI) as of December 2010?"
    patient_id = "0000d346-2e09-428f-b37b-b9d5182e313f"
    
    print(f"Retrying BMI question...")
    
    result = await run_api_query(
        query=question,
        session_id="retry-bmi",
        patient_id=patient_id
    )
    
    if result.get("error"):
        print(f"Failed: {result['error']}")
        return
    
    answer = result.get("response", "")
    sources = result.get("sources", [])
    contexts = [s.get("content_preview", "") if isinstance(s, dict) else s for s in sources]
    
    print(f"✓ Success: {len(answer)} chars, {len(contexts)} contexts")
    
    # Update JSON
    json_path = Path(__file__).parent / "golden_testset_candidate.json"
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    data[6]["agent_answer"] = answer
    data[6]["agent_contexts"] = contexts
    
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Updated golden_testset_candidate.json")

asyncio.run(main())
