#!/usr/bin/env python3
"""
Comprehensive Patient Evaluation Script
Queries 20 patients, generates diverse questions, runs agent evaluation with retry logic.
"""

import asyncio
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

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

# Question templates
COMPREHENSIVE_QUESTIONS = [
    "Provide a complete summary of this patient's medical history.",
    "What is the overall health status and medical background of this patient?",
    "Summarize all clinical information available for this patient.",
    "Give a comprehensive overview of this patient's healthcare records.",
]

SPECIFIC_QUESTIONS = [
    "What active medications is this patient currently taking?",
    "What are this patient's current active conditions?",
    "What lab results are most recent for this patient?",
    "What immunizations has this patient received?",
    "What procedures has this patient undergone?",
    "What are this patient's most recent vital signs?",
    "Does this patient have any chronic conditions? If so, what are they?",
    "What is this patient's blood pressure history?",
    "What is this patient's BMI or weight history?",
    "Are there any medication allergies documented for this patient?",
    "What diagnostic imaging has been performed on this patient?",
    "What care plans or treatment recommendations exist for this patient?",
]


async def get_patients_from_db(limit: int = 20) -> List[str]:
    """Get patient IDs from FHIR JSON files."""
    try:
        fhir_dir = _REPO_ROOT / "data" / "fhir"
        patient_ids = []
        
        for f in sorted(fhir_dir.glob("*.json")):
            if len(patient_ids) >= limit:
                break
            try:
                with open(f) as fp:
                    data = json.load(fp)
                for entry in data.get("entry", []):
                    resource = entry.get("resource", {})
                    if resource.get("resourceType") == "Patient":
                        patient_id = resource.get("id")
                        if patient_id:
                            patient_ids.append(patient_id)
                            break
            except Exception as e:
                print(f"  Error reading {f.name}: {e}")
                continue
        
        if len(patient_ids) < limit:
            print(f"⚠️  WARNING: Only {len(patient_ids)} patients found (requested {limit})")
            
        return patient_ids
    except Exception as e:
        print(f"❌ ERROR fetching patients: {e}")
        return []


def generate_question(patient_id: str, index: int) -> Tuple[str, str]:
    """Generate a question for the patient (30% comprehensive, 70% specific)."""
    # 30% comprehensive questions
    if random.random() < 0.3:
        question_type = "comprehensive"
        question = random.choice(COMPREHENSIVE_QUESTIONS)
    else:
        question_type = "specific"
        question = random.choice(SPECIFIC_QUESTIONS)
    
    return question, question_type


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
            
            # Check for error in response
            if result.get("error"):
                last_error = result["error"]
                attempt += 1
                if attempt < max_retries:
                    print(f"  ⚠️  Attempt {attempt} failed: {last_error[:100]}... Retrying...")
                    await asyncio.sleep(2)  # Brief pause before retry
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
            
            # Success
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
                print(f"  ⚠️  Attempt {attempt} exception: {last_error[:100]}... Retrying...")
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


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text for display in table."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def truncate_patient_id(patient_id: str) -> str:
    """Truncate patient ID for readability."""
    if len(patient_id) <= 12:
        return patient_id
    return patient_id[:8] + "..."


async def main():
    print("="*60)
    print("COMPREHENSIVE PATIENT EVALUATION")
    print("="*60)
    
    # Step 1: Get patients
    print("\n[1/4] Fetching patients from database...")
    patients = await get_patients_from_db(limit=20)
    
    if not patients:
        print("❌ FATAL: No patients found. Exiting.")
        sys.exit(1)
    
    print(f"✓ Found {len(patients)} patients")
    
    # Step 2: Generate questions
    print("\n[2/4] Generating questions...")
    questions_data = []
    for i, patient_id in enumerate(patients):
        question, q_type = generate_question(patient_id, i)
        questions_data.append({
            "patient_id": patient_id,
            "question": question,
            "type": q_type,
            "index": i
        })
        print(f"  [{i+1:2d}] {truncate_patient_id(patient_id)} - {q_type:13s} - {truncate_text(question, 60)}")
    
    # Step 3: Run evaluation
    print("\n[3/4] Running agent evaluation (with LangSmith tracing)...")
    results = []
    
    for i, item in enumerate(questions_data):
        print(f"\n  Processing [{i+1}/{len(questions_data)}]: {truncate_patient_id(item['patient_id'])}")
        print(f"  Question: {item['question'][:80]}...")
        
        result = await query_with_retry(
            patient_id=item['patient_id'],
            question=item['question'],
            session_id=f"comprehensive-eval-{i}",
            max_retries=3
        )
        
        results.append({
            "patient_id": item['patient_id'],
            "question": item['question'],
            "type": item['type'],
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
    
    # Step 4: Generate markdown report
    print("\n[4/4] Generating markdown report...")
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    output_file = Path(__file__).parent / f"comprehensive_eval_{timestamp}.md"
    
    # Calculate statistics
    total = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = total - successful
    avg_duration = sum(r['duration'] for r in results if r['success']) / successful if successful > 0 else 0
    total_retries = sum(r['retries'] for r in results)
    
    with open(output_file, 'w') as f:
        f.write(f"# Comprehensive Patient Evaluation Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write(f"**Total Questions:** {total}\n\n")
        f.write(f"**Successful:** {successful} ({successful/total*100:.1f}%)\n\n")
        f.write(f"**Failed:** {failed} ({failed/total*100:.1f}%)\n\n")
        f.write(f"**Average Duration:** {avg_duration:.2f}s\n\n")
        f.write(f"**Total Retries:** {total_retries}\n\n")
        
        f.write("## Summary Statistics\n\n")
        f.write(f"- Questions by type:\n")
        comprehensive_count = sum(1 for r in results if r['type'] == 'comprehensive')
        specific_count = sum(1 for r in results if r['type'] == 'specific')
        f.write(f"  - Comprehensive: {comprehensive_count}\n")
        f.write(f"  - Specific: {specific_count}\n\n")
        
        f.write("## Detailed Results\n\n")
        f.write("| Patient ID | Question | Answer | Retries | Duration | Status | Error |\n")
        f.write("|------------|----------|--------|---------|----------|--------|-------|\n")
        
        for r in results:
            patient_id_short = truncate_patient_id(r['patient_id'])
            question_short = truncate_text(r['question'], 50)
            answer_short = truncate_text(r['answer'], 100) if r['answer'] else "N/A"
            status = "✓ Success" if r['success'] else "✗ Failed"
            duration_str = f"{r['duration']:.1f}s" if r['success'] else "N/A"
            error_short = truncate_text(r['error'], 80) if r['error'] else ""
            
            # Escape pipes in text for markdown
            answer_short = answer_short.replace("|", "\\|")
            error_short = error_short.replace("|", "\\|")
            
            f.write(f"| {patient_id_short} | {question_short} | {answer_short} | {r['retries']} | {duration_str} | {status} | {error_short} |\n")
        
        # Add full details section
        f.write("\n## Full Response Details\n\n")
        for i, r in enumerate(results):
            f.write(f"### [{i+1}] {r['type'].title()} Question\n\n")
            f.write(f"**Patient ID:** `{r['patient_id']}`\n\n")
            f.write(f"**Question:** {r['question']}\n\n")
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
