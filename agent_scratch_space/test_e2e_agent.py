"""
End-to-End Agent API Test for Few-Shot Examples.

This script sends the EXACT queries from the few-shot examples to the running
agent API and verifies the agent's responses match the expected behavior patterns.
"""

import asyncio
import json
import httpx
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

API_BASE = "http://localhost:8000"

async def query_agent(query: str, patient_id: str, session_id: str) -> dict:
    """Send a query to the agent API and return the full response."""
    async with httpx.AsyncClient(timeout=300) as client:
        payload = {
            "query": query,
            "patient_id": patient_id,
            "session_id": session_id,
        }
        response = await client.post(f"{API_BASE}/agent/query", json=payload)
        response.raise_for_status()
        return response.json()

async def test_researcher_exhaustive_list():
    """
    Few-Shot Example 1: Exhaustive List Request
    Expected: Agent uses include_full_json=True and returns a list of conditions.
    """
    print(f"\n{'='*70}")
    print("E2E TEST 1: Exhaustive List - 'List all active conditions'")
    print(f"{'='*70}")
    
    patient_id = "179713d4-6c3d-4397-81f4-687dc9d7e609"
    query = f"List all active conditions for patient {patient_id}."
    
    try:
        result = await query_agent(query, patient_id, "e2e-test-1")
        response_text = result.get("response", "")
        
        print(f"Agent Response (first 500 chars):")
        print(f"  {response_text[:500]}...")
        
        # Verification: Check if response contains condition names
        keywords = ["hypertension", "sinusitis", "copd", "condition"]
        found = [kw for kw in keywords if kw.lower() in response_text.lower()]
        
        if found:
            print(f"\n✅ SUCCESS: Found clinical terms: {found}")
        else:
            print(f"\n⚠️  WARNING: Expected clinical conditions not found in response.")
            print("   This may indicate the agent did not retrieve full patient data.")
            
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")

async def test_researcher_date_lookup():
    """
    Few-Shot Example 2: Specific Date Lookup
    Expected: Agent searches for observation on exact date and returns value.
    """
    print(f"\n{'='*70}")
    print("E2E TEST 2: Date Lookup - 'Weight on 2010-12-07'")
    print(f"{'='*70}")
    
    patient_id = "179713d4-6c3d-4397-81f4-687dc9d7e609"
    query = f"What was patient {patient_id}'s weight on 2010-12-07?"
    
    try:
        result = await query_agent(query, patient_id, "e2e-test-2")
        response_text = result.get("response", "")
        
        print(f"Agent Response (first 500 chars):")
        print(f"  {response_text[:500]}...")
        
        # Verification: Check if response contains the date or weight
        if "2010" in response_text or "75" in response_text or "kg" in response_text.lower():
            print(f"\n✅ SUCCESS: Found date/weight reference in response.")
        else:
            print(f"\n⚠️  WARNING: Date or weight value not found in response.")
            
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")

async def test_researcher_drug_interaction():
    """
    Few-Shot Example 3: Drug Interaction Check
    Expected: Agent uses cross_reference_meds and flags bleeding risk.
    """
    print(f"\n{'='*70}")
    print("E2E TEST 3: Drug Interaction - 'Warfarin + Aspirin'")
    print(f"{'='*70}")
    
    patient_id = "179713d4-6c3d-4397-81f4-687dc9d7e609"
    query = f"Patient {patient_id} is taking Warfarin. Can they also take Aspirin for a headache?"
    
    try:
        result = await query_agent(query, patient_id, "e2e-test-3")
        response_text = result.get("response", "")
        
        print(f"Agent Response (first 600 chars):")
        print(f"  {response_text[:600]}...")
        
        # Verification: Check if response mentions interaction or bleeding
        keywords = ["interaction", "bleeding", "risk", "caution", "avoid", "warfarin", "aspirin"]
        found = [kw for kw in keywords if kw.lower() in response_text.lower()]
        
        if len(found) >= 2:
            print(f"\n✅ SUCCESS: Found safety-related terms: {found}")
        else:
            print(f"\n⚠️  WARNING: Expected safety warnings not found.")
            print(f"   Found terms: {found}")
            
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")

async def test_validator_grounding():
    """
    Test Validator Behavior: Agent should provide citations.
    """
    print(f"\n{'='*70}")
    print("E2E TEST 4: Grounding Check - Does agent cite sources?")
    print(f"{'='*70}")
    
    patient_id = "179713d4-6c3d-4397-81f4-687dc9d7e609"
    query = f"What is the latest creatinine lab result for patient {patient_id}?"
    
    try:
        result = await query_agent(query, patient_id, "e2e-test-4")
        response_text = result.get("response", "")
        sources = result.get("sources", [])
        
        print(f"Agent Response (first 400 chars):")
        print(f"  {response_text[:400]}...")
        print(f"\nSources returned: {len(sources)}")
        
        # Verification: Check if response has FHIR citations or sources
        has_citation = "[FHIR:" in response_text or "Observation" in response_text or len(sources) > 0
        
        if has_citation:
            print(f"\n✅ SUCCESS: Agent provided grounded citations or sources.")
        else:
            print(f"\n⚠️  WARNING: No citations found. Validator would flag this.")
            
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")

async def main():
    print("="*70)
    print("END-TO-END AGENT API TEST FOR FEW-SHOT EXAMPLES")
    print("="*70)
    print(f"Testing against: {API_BASE}/agent/query")
    
    # Check API health first
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            health = await client.get(f"{API_BASE}/health")
            if health.status_code != 200:
                print(f"❌ API not healthy: {health.status_code}")
                return
            print(f"✅ API Health: OK\n")
        except Exception as e:
            print(f"❌ Cannot reach API: {e}")
            return
    
    await test_researcher_exhaustive_list()
    await test_researcher_date_lookup()
    await test_researcher_drug_interaction()
    await test_validator_grounding()
    
    print(f"\n{'='*70}")
    print("END-TO-END TESTS COMPLETE")
    print(f"{'='*70}")

if __name__ == "__main__":
    asyncio.run(main())
