
import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Import tools (mocking context where needed)
from api.agent.tools import (
    search_patient_records,
    cross_reference_meds,
    validate_dosage,
    lookup_rxnorm
)

async def test_researcher_example_1_list():
    print(f"\n{'='*60}")
    print("TEST 1: Exhaustive List (Conditions for 179713d4...)")
    print(f"{'='*60}")
    
    patient_id = "179713d4-6c3d-4397-81f4-687dc9d7e609"
    try:
        # Expected call: search_patient_records(query="Condition", patient_id=..., include_full_json=True)
        results = await search_patient_records.ainvoke({
            "query": "Condition", 
            "patient_id": patient_id, 
            "include_full_json": True
        })
        print(f"Tool execution successful.")
        results_str = str(results)
        print(f"Result Preview: {results_str[:500]}...")
        
        # Verify if full JSON is present
        if "active conditions" in results_str.lower() or "hypertension" in results_str.lower():
             print("SUCCESS: Found expected conditions.")
        else:
             print("WARNING: Might be missing specific conditions.")
             
    except Exception as e:
        print(f"FAILED with error: {e}")

async def test_researcher_example_2_date():
    print(f"\n{'='*60}")
    print("TEST 2: Specific Date Lookup (Weight on 2010-12-07)")
    print(f"{'='*60}")
    
    patient_id = "179713d4-6c3d-4397-81f4-687dc9d7e609"
    try:
        # Expected behavior: search for specific date in query
        results = await search_patient_records.ainvoke({
            "query": "Observation 75 kg 2010-12-07",
            "patient_id": patient_id,
            "include_full_json": True
        })
        print(f"Tool execution successful.")
        results_str = str(results)
        print(f"Result Preview: {results_str[:500]}...")
        
        if "2010-12-07" in results_str:
            print("SUCCESS: Date found in results.")
        else:
            print("WARNING: Specific date not found in output text.")
            
    except Exception as e:
        print(f"FAILED with error: {e}")

async def test_researcher_example_3_interaction():
    print(f"\n{'='*60}")
    print("TEST 3: Drug Interaction (Warfarin + Aspirin)")
    print(f"{'='*60}")
    
    try:
        # Step 1: Mock input list of meds
        meds = ["Warfarin", "Aspirin"]
        print(f"Checking list: {meds}")
        
        # Step 2: Check interactions using cross_reference_meds
        results = cross_reference_meds.invoke({"medication_list": meds})
        print(f"Tool execution successful.")
        print(f"Results: {results}")
        
        if results.get("warnings"):
             print("SUCCESS: Interaction flagged.")
        else:
             print("WARNING: Interaction NOT flagged.")
             print("Note: cross_reference_meds should catch Warfarin+Aspirin.")
             
    except Exception as e:
        print(f"FAILED with error: {e}")

async def test_validator_hallucination_check():
    print(f"\n{'='*60}")
    print("TEST 4: Validator Hallucination Check (Condition/999)")
    print(f"{'='*60}")
    
    patient_id = "179713d4-6c3d-4397-81f4-687dc9d7e609"
    try:
        # Expected behavior: Search for specific ID returns nothing
        results = await search_patient_records.ainvoke({
            "query": "Condition/999", 
            "patient_id": patient_id,
            "include_full_json": False
        })
        results_str = str(results)
        print(f"Result for hallucinated ID: {results_str[:200]}")
        
        # Check if it returned nothing relevant or error
        # Implementation returns "results": [] if nothing found, likely.
        
        if "results" in results and not results["chunks"]:
             print("SUCCESS: Correctly returned empty chunks for fake ID.")
        elif "no information found" in results_str.lower():
            print("SUCCESS: Correctly returned no data for fake ID.")
        else:
            # It might perform vector search and return *something* irrelevant.
            print("WARNING: Returned some data. Check if it's just low relevance chunks.")
            
    except Exception as e:
        print(f"FAILED with error: {e}")

async def main():
    await test_researcher_example_1_list()
    await test_researcher_example_2_date()
    await test_researcher_example_3_interaction()
    await test_validator_hallucination_check()

if __name__ == "__main__":
    asyncio.run(main())
