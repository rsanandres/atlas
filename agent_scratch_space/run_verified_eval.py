#!/usr/bin/env python3
"""
Verified Data Evaluation Script
- Verifies FHIR file and embeddings exist before selecting a patient
- Pre-scans FHIR data to find actual conditions/events that exist
- Generates questions ONLY about verified data
"""

import asyncio
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import asyncpg

# Setup paths
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv
load_dotenv()

# Verify LangSmith setup
if os.getenv("LANGCHAIN_TRACING_V2") != "true":
    print("⚠️  WARNING: LANGCHAIN_TRACING_V2 not enabled. Setting it now...")
    os.environ["LANGCHAIN_TRACING_V2"] = "true"

from POC_RAGAS.runners.api_runner import run_api_query


async def get_db_connection():
    """Get database connection using .env credentials."""
    return await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "postgres")
    )


async def get_patients_with_embeddings(limit: int = 20) -> List[str]:
    """Get patient IDs that have embeddings in the database."""
    try:
        conn = await get_db_connection()
        # Query for distinct patient IDs that have embeddings
        rows = await conn.fetch("""
            SELECT langchain_metadata::json->>'patient_id' as patient_id, COUNT(*) as chunk_count 
            FROM hc_ai_schema.hc_ai_table 
            WHERE langchain_metadata::json->>'patient_id' IS NOT NULL
            GROUP BY langchain_metadata::json->>'patient_id'
            ORDER BY chunk_count DESC
            LIMIT $1
        """, limit)
        await conn.close()
        
        patient_ids = [row['patient_id'] for row in rows]
        print(f"  Found {len(patient_ids)} patients with embeddings in DB")
        return patient_ids
    except Exception as e:
        print(f"❌ ERROR querying embeddings: {e}")
        return []


def extract_verified_data(patient_id: str) -> Dict:
    """Extract actual data that exists in the patient's FHIR files."""
    fhir_dir = _REPO_ROOT / "data" / "fhir"
    verified_data = {
        "conditions": [],
        "medications": [],
        "observations": [],
        "procedures": [],
        "immunizations": [],
        "encounters": [],
        "allergies": [],
    }
    
    # Find the FHIR file for this patient
    for f in fhir_dir.glob("*.json"):
        try:
            with open(f) as fp:
                data = json.load(fp)
            
            # Check if this file contains our patient
            patient_found = False
            for entry in data.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Patient" and resource.get("id") == patient_id:
                    patient_found = True
                    break
            
            if not patient_found:
                continue
            
            # Extract all resources for this patient
            for entry in data.get("entry", []):
                resource = entry.get("resource", {})
                rtype = resource.get("resourceType")
                
                if rtype == "Condition":
                    code = resource.get("code", {})
                    coding = code.get("coding", [{}])[0]
                    display = coding.get("display") or code.get("text", "Unknown")
                    onset = resource.get("onsetDateTime", "")[:10] if resource.get("onsetDateTime") else ""
                    status = resource.get("clinicalStatus", "")
                    if display:
                        verified_data["conditions"].append({
                            "name": display,
                            "onset": onset,
                            "status": status
                        })
                
                elif rtype == "MedicationRequest":
                    med_ref = resource.get("medicationReference", {})
                    # Try to find medication name from the reference or contained resources
                    med_name = med_ref.get("display", "")
                    if not med_name:
                        # Look for medicationCodeableConcept
                        med_cc = resource.get("medicationCodeableConcept", {})
                        coding = med_cc.get("coding", [{}])[0]
                        med_name = coding.get("display") or med_cc.get("text", "")
                    authored = resource.get("authoredOn", "")[:10] if resource.get("authoredOn") else ""
                    if med_name:
                        verified_data["medications"].append({
                            "name": med_name,
                            "date": authored
                        })
                
                elif rtype == "Observation":
                    code = resource.get("code", {})
                    coding = code.get("coding", [{}])[0]
                    display = coding.get("display") or code.get("text", "")
                    value = resource.get("valueQuantity", {})
                    value_str = f"{value.get('value', '')} {value.get('unit', '')}"
                    effective = resource.get("effectiveDateTime", "")[:10] if resource.get("effectiveDateTime") else ""
                    if display:
                        verified_data["observations"].append({
                            "name": display,
                            "value": value_str.strip(),
                            "date": effective
                        })
                
                elif rtype == "Procedure":
                    code = resource.get("code", {})
                    coding = code.get("coding", [{}])[0]
                    display = coding.get("display") or code.get("text", "")
                    performed = resource.get("performedDateTime", "")[:10] if resource.get("performedDateTime") else ""
                    if display:
                        verified_data["procedures"].append({
                            "name": display,
                            "date": performed
                        })
                
                elif rtype == "Immunization":
                    vaccine = resource.get("vaccineCode", {})
                    coding = vaccine.get("coding", [{}])[0]
                    display = coding.get("display") or vaccine.get("text", "")
                    occurrence = resource.get("occurrenceDateTime", "")[:10] if resource.get("occurrenceDateTime") else ""
                    if display:
                        verified_data["immunizations"].append({
                            "name": display,
                            "date": occurrence
                        })
                
                elif rtype == "Encounter":
                    etype = resource.get("type", [{}])[0]
                    coding = etype.get("coding", [{}])[0]
                    display = coding.get("display") or etype.get("text", "")
                    period = resource.get("period", {})
                    start = period.get("start", "")[:10] if period.get("start") else ""
                    if display:
                        verified_data["encounters"].append({
                            "name": display,
                            "date": start
                        })
                
                elif rtype == "AllergyIntolerance":
                    code = resource.get("code", {})
                    coding = code.get("coding", [{}])[0]
                    display = coding.get("display") or code.get("text", "")
                    if display:
                        verified_data["allergies"].append({
                            "name": display
                        })
            
            # Found and processed the patient's file
            break
            
        except Exception as e:
            continue
    
    return verified_data


def generate_verified_question(patient_id: str, verified_data: Dict) -> Tuple[str, str, str]:
    """Generate a question about verified data that we KNOW exists."""
    
    question_templates = []
    
    # Conditions
    for cond in verified_data.get("conditions", []):
        if cond.get("name"):
            question_templates.append((
                f"What can you tell me about this patient's {cond['name']}? When was it diagnosed?",
                "condition",
                f"{cond['name']} (onset: {cond.get('onset', 'unknown')})"
            ))
            question_templates.append((
                f"Does this patient have {cond['name']}? Provide details.",
                "condition",
                f"{cond['name']}"
            ))
    
    # Medications
    for med in verified_data.get("medications", []):
        if med.get("name"):
            question_templates.append((
                f"Is this patient taking {med['name']}? When was it prescribed?",
                "medication",
                f"{med['name']} (date: {med.get('date', 'unknown')})"
            ))
    
    # Observations with values
    for obs in verified_data.get("observations", []):
        if obs.get("name") and obs.get("value"):
            question_templates.append((
                f"What was this patient's {obs['name']} on {obs['date']}?",
                "observation",
                f"{obs['name']}: {obs['value']} on {obs['date']}"
            ))
    
    # Procedures
    for proc in verified_data.get("procedures", []):
        if proc.get("name"):
            question_templates.append((
                f"Has this patient undergone a {proc['name']}? When?",
                "procedure",
                f"{proc['name']} (date: {proc.get('date', 'unknown')})"
            ))
    
    # Immunizations
    for imm in verified_data.get("immunizations", []):
        if imm.get("name"):
            question_templates.append((
                f"Has this patient received a {imm['name']} vaccine? When?",
                "immunization",
                f"{imm['name']} (date: {imm.get('date', 'unknown')})"
            ))
    
    # Encounters
    for enc in verified_data.get("encounters", []):
        if enc.get("name"):
            question_templates.append((
                f"Did this patient have a {enc['name']} encounter on {enc['date']}?",
                "encounter",
                f"{enc['name']} on {enc['date']}"
            ))
    
    if not question_templates:
        # Fallback - ask for timeline
        return (
            "Provide a timeline of this patient's medical events.",
            "timeline",
            "General timeline request"
        )
    
    return random.choice(question_templates)


def truncate_text(text: str, max_length: int = 200) -> str:
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def truncate_patient_id(patient_id: str) -> str:
    if len(patient_id) <= 12:
        return patient_id
    return patient_id[:8] + "..."


async def query_with_retry(
    patient_id: str, 
    question: str, 
    session_id: str,
    max_retries: int = 3
) -> Dict:
    """Query agent with retry logic."""
    attempt = 0
    last_error = None
    
    while attempt < max_retries:
        try:
            start_time = time.time()
            result = await run_api_query(
                query=question,
                session_id=session_id,
                patient_id=patient_id
            )
            duration = time.time() - start_time
            
            if result.get("error"):
                last_error = result["error"]
                attempt += 1
                if attempt < max_retries:
                    print(f"  ⚠️  Attempt {attempt} failed: {last_error[:80]}... Retrying...")
                    await asyncio.sleep(2)
                    continue
                else:
                    return {
                        "success": False,
                        "answer": None,
                        "contexts": [],
                        "retries": attempt,
                        "duration": duration,
                        "error": last_error
                    }
            
            answer = result.get("response", "")
            sources = result.get("sources", [])
            contexts = []
            for src in sources:
                if isinstance(src, dict):
                    contexts.append(src.get("content_preview", ""))
                elif isinstance(src, str):
                    contexts.append(src)
            
            return {
                "success": True,
                "answer": answer,
                "contexts": contexts,
                "retries": attempt,
                "duration": duration,
                "error": None
            }
            
        except Exception as e:
            last_error = str(e)
            attempt += 1
            if attempt < max_retries:
                print(f"  ⚠️  Attempt {attempt} exception: {last_error[:80]}... Retrying...")
                await asyncio.sleep(2)
            else:
                return {
                    "success": False,
                    "answer": None,
                    "contexts": [],
                    "retries": attempt,
                    "duration": 0,
                    "error": f"Exception: {last_error}"
                }
    
    return {
        "success": False,
        "answer": None,
        "contexts": [],
        "retries": max_retries,
        "duration": 0,
        "error": last_error
    }


async def main():
    print("="*60)
    print("VERIFIED DATA EVALUATION")
    print("="*60)
    
    # Step 1: Get patients with embeddings in DB
    print("\n[1/5] Finding patients with embeddings in database...")
    patients = await get_patients_with_embeddings(limit=20)
    
    if not patients:
        print("❌ FATAL: No patients with embeddings found. Exiting.")
        sys.exit(1)
    
    # Step 2: Verify FHIR data exists and extract verified data
    print("\n[2/5] Verifying FHIR data and extracting verified records...")
    verified_patients = []
    
    for patient_id in patients:
        verified_data = extract_verified_data(patient_id)
        
        # Count total items
        total_items = sum(len(v) for v in verified_data.values())
        
        if total_items > 0:
            verified_patients.append({
                "patient_id": patient_id,
                "verified_data": verified_data,
                "item_count": total_items
            })
            print(f"  ✓ {truncate_patient_id(patient_id)}: {total_items} verified items")
        else:
            print(f"  ✗ {truncate_patient_id(patient_id)}: No FHIR data found")
    
    if len(verified_patients) < 5:
        print(f"⚠️  WARNING: Only {len(verified_patients)} patients have verified data")
    
    # Take up to 20 patients
    verified_patients = verified_patients[:20]
    print(f"\n✓ Selected {len(verified_patients)} patients with verified data")
    
    # Step 3: Generate questions about VERIFIED data
    print("\n[3/5] Generating questions about verified data...")
    questions_data = []
    
    for i, patient_info in enumerate(verified_patients):
        question, q_type, expected = generate_verified_question(
            patient_info['patient_id'],
            patient_info['verified_data']
        )
        questions_data.append({
            "patient_id": patient_info['patient_id'],
            "question": question,
            "type": q_type,
            "expected": expected,
            "index": i
        })
        print(f"  [{i+1:2d}] {truncate_patient_id(patient_info['patient_id'])} - {q_type:12s} - {truncate_text(question, 55)}")
    
    # Step 4: Run evaluation
    print("\n[4/5] Running agent evaluation (with LangSmith tracing)...")
    results = []
    
    for i, item in enumerate(questions_data):
        print(f"\n  Processing [{i+1}/{len(questions_data)}]: {truncate_patient_id(item['patient_id'])}")
        print(f"  Question: {item['question'][:80]}...")
        print(f"  Expected: {item['expected']}")
        
        result = await query_with_retry(
            patient_id=item['patient_id'],
            question=item['question'],
            session_id=f"verified-eval-{i}",
            max_retries=3
        )
        
        results.append({
            "patient_id": item['patient_id'],
            "question": item['question'],
            "type": item['type'],
            "expected": item['expected'],
            "answer": result['answer'],
            "contexts_count": len(result['contexts']),
            "retries": result['retries'],
            "duration": result['duration'],
            "success": result['success'],
            "error": result['error']
        })
        
        if result['success']:
            print(f"  ✓ Success ({result['duration']:.1f}s, {len(result['contexts'])} contexts)")
        else:
            print(f"  ✗ Failed after {result['retries']} retries: {result['error'][:80]}")
    
    # Step 5: Generate markdown report
    print("\n[5/5] Generating markdown report...")
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    output_file = Path(__file__).parent / f"verified_eval_{timestamp}.md"
    
    # Calculate statistics
    total = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = total - successful
    avg_duration = sum(r['duration'] for r in results if r['success']) / successful if successful > 0 else 0
    total_retries = sum(r['retries'] for r in results)
    
    with open(output_file, 'w') as f:
        f.write(f"# Verified Data Evaluation Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write(f"**Total Questions:** {total}\n\n")
        f.write(f"**Successful:** {successful} ({successful/total*100:.1f}%)\n\n")
        f.write(f"**Failed:** {failed} ({failed/total*100:.1f}%)\n\n")
        f.write(f"**Average Duration:** {avg_duration:.2f}s\n\n")
        f.write(f"**Total Retries:** {total_retries}\n\n")
        
        f.write("> **NOTE:** All questions are about data that was **verified to exist** in the patient's FHIR records before asking.\n\n")
        
        f.write("## Summary by Question Type\n\n")
        types = {}
        for r in results:
            types[r['type']] = types.get(r['type'], 0) + 1
        for t, count in sorted(types.items()):
            f.write(f"- {t}: {count}\n")
        f.write("\n")
        
        f.write("## Detailed Results\n\n")
        f.write("| Patient ID | Type | Question | Expected Data | Answer | Duration | Status |\n")
        f.write("|------------|------|----------|---------------|--------|----------|--------|\n")
        
        for r in results:
            patient_id_short = truncate_patient_id(r['patient_id'])
            question_short = truncate_text(r['question'], 40).replace("|", "\\|")
            expected_short = truncate_text(r['expected'], 40).replace("|", "\\|")
            answer_short = truncate_text(r['answer'], 60).replace("|", "\\|") if r['answer'] else "N/A"
            status = "✓" if r['success'] else f"✗ ({r['error'][:30]}...)" if r['error'] else "✗"
            duration_str = f"{r['duration']:.1f}s" if r['success'] else "N/A"
            
            f.write(f"| {patient_id_short} | {r['type']} | {question_short} | {expected_short} | {answer_short} | {duration_str} | {status} |\n")
        
        # Full details section
        f.write("\n## Full Response Details\n\n")
        for i, r in enumerate(results):
            f.write(f"### [{i+1}] {r['type'].title()}\n\n")
            f.write(f"**Patient ID:** `{r['patient_id']}`\n\n")
            f.write(f"**Question:** {r['question']}\n\n")
            f.write(f"**Expected (verified in FHIR):** {r['expected']}\n\n")
            if r['success']:
                f.write(f"**Answer:**\n\n{r['answer']}\n\n")
                f.write(f"**Contexts Retrieved:** {r['contexts_count']}\n\n")
                f.write(f"**Duration:** {r['duration']:.2f}s\n\n")
            else:
                f.write(f"**Status:** ✗ Failed after {r['retries']} retries\n\n")
                f.write(f"**Error:** {r['error']}\n\n")
            f.write("---\n\n")
    
    print(f"\n✓ Report saved to: {output_file}")
    print(f"\n{'='*60}")
    print(f"EVALUATION COMPLETE")
    print(f"Success Rate: {successful}/{total} ({successful/total*100:.1f}%)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
