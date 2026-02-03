#!/usr/bin/env python3
"""
Extract ground truths from the database for all questions in golden_dataset_experiment.
Synthesizes answers in the same style as the agent (per prompts.yaml).
"""

import asyncio
import json
import os
import re
import sys
from glob import glob
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add repo root to path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Load environment
from dotenv import load_dotenv
load_dotenv(_REPO_ROOT / ".env")

# Import database functions
from api.database.postgres import hybrid_search, get_patient_timeline


def classify_question(question: str) -> str:
    """Classify the question type to determine which FHIR resources to query."""
    q_lower = question.lower()
    
    if any(kw in q_lower for kw in ["procedure", "surgery", "operation"]):
        return "Procedure"
    elif any(kw in q_lower for kw in ["condition", "diagnosis", "diagnosed"]):
        return "Condition"
    elif any(kw in q_lower for kw in ["medication", "drug", "prescribed", "medicine"]):
        return "MedicationRequest"
    elif any(kw in q_lower for kw in ["immunization", "vaccine", "vaccination"]):
        return "Immunization"
    elif any(kw in q_lower for kw in ["observation", "lab", "test", "result", "weight", "bmi", "blood pressure"]):
        return "Observation"
    elif any(kw in q_lower for kw in ["allergy", "allergies"]):
        return "AllergyIntolerance"
    elif any(kw in q_lower for kw in ["encounter", "visit"]):
        return "Encounter"
    elif any(kw in q_lower for kw in ["care plan", "follow-up", "recommendation"]):
        return "CarePlan"
    else:
        return "general"


def extract_patient_id(result_data: Dict) -> Optional[str]:
    """Extract patient_id from result metadata."""
    metadata = result_data.get("metadata", {})
    return metadata.get("patient_id")


async def query_fhir_data(patient_id: str, resource_type: str, query: str) -> List[Dict]:
    """Query the database for FHIR resources matching the patient and type."""
    try:
        # Use hybrid search for better coverage
        results = await hybrid_search(
            query=query,
            k=20,
            filter_metadata={"patient_id": patient_id}
        )
        
        # Filter by resource type if specified
        filtered = []
        for doc in results:
            content = doc.page_content
            metadata = doc.metadata
            
            # Check if this is the right resource type
            if resource_type == "general":
                filtered.append({"content": content, "metadata": metadata})
            elif metadata.get("resourceType") == resource_type or resource_type.lower() in content.lower():
                filtered.append({"content": content, "metadata": metadata})
        
        return filtered
    except Exception as e:
        print(f"  > Error querying database: {e}")
        return []


def synthesize_golden_answer(question: str, fhir_data: List[Dict], resource_type: str) -> str:
    """
    Synthesize a professional, clinical answer based on FHIR data.
    Style: Professional, clinical, evidence-based (per prompts.yaml).
    """
    if not fhir_data:
        return "No relevant records found in the patient's data."
    
    # Parse and format the FHIR data
    findings = []
    for item in fhir_data[:10]:  # Limit to top 10 results
        content = item.get("content", "")
        metadata = item.get("metadata", {})
        
        try:
            # Try to parse as JSON for structured data
            if content.startswith("{"):
                data = json.loads(content)
                
                if resource_type == "Condition":
                    display = data.get("code", {}).get("text") or data.get("code", {}).get("coding", [{}])[0].get("display", "")
                    status = data.get("clinicalStatus", "")
                    onset = data.get("onsetDateTime", data.get("assertedDate", ""))[:10] if data.get("onsetDateTime") or data.get("assertedDate") else ""
                    if display:
                        findings.append(f"- {display} (Status: {status}, Onset: {onset})")
                        
                elif resource_type == "Procedure":
                    display = data.get("code", {}).get("text") or data.get("code", {}).get("coding", [{}])[0].get("display", "")
                    performed = data.get("performedDateTime", data.get("performedPeriod", {}).get("start", ""))[:10] if data.get("performedDateTime") or data.get("performedPeriod") else ""
                    if display:
                        findings.append(f"- {display} (Date: {performed})")
                        
                elif resource_type == "MedicationRequest":
                    display = data.get("medicationCodeableConcept", {}).get("text") or ""
                    status = data.get("status", "")
                    authored = data.get("authoredOn", "")[:10] if data.get("authoredOn") else ""
                    if display:
                        findings.append(f"- {display} (Status: {status}, Prescribed: {authored})")
                        
                elif resource_type == "Immunization":
                    display = data.get("vaccineCode", {}).get("text") or data.get("vaccineCode", {}).get("coding", [{}])[0].get("display", "")
                    date = data.get("date", data.get("occurrenceDateTime", ""))[:10] if data.get("date") or data.get("occurrenceDateTime") else ""
                    if display:
                        findings.append(f"- {display} (Date: {date})")
                        
                elif resource_type == "Observation":
                    display = data.get("code", {}).get("text") or data.get("code", {}).get("coding", [{}])[0].get("display", "")
                    value = data.get("valueQuantity", {})
                    val_str = f"{value.get('value', '')} {value.get('unit', '')}" if value else data.get("valueString", "")
                    date = data.get("effectiveDateTime", "")[:10] if data.get("effectiveDateTime") else ""
                    if display:
                        findings.append(f"- {display}: {val_str} (Date: {date})")
                        
                elif resource_type == "CarePlan":
                    status = data.get("status", "")
                    activities = data.get("activity", [])
                    activity_list = [a.get("detail", {}).get("code", {}).get("text", "") for a in activities if a.get("detail")]
                    if activity_list:
                        findings.append(f"- Care Plan ({status}): {', '.join(activity_list[:5])}")
                else:
                    # General case
                    findings.append(f"- {content[:200]}...")
            else:
                findings.append(f"- {content[:200]}...")
        except json.JSONDecodeError:
            findings.append(f"- {content[:200]}...")
    
    if not findings:
        return "No specific records matching the query were found."
    
    # Format as a professional clinical answer
    unique_findings = list(dict.fromkeys(findings))  # Remove duplicates
    return "Based on the patient's records:\n\n" + "\n".join(unique_findings[:10])


async def main():
    experiment_dir = _REPO_ROOT / "agent_scratch_space" / "golden_dataset_experiment"
    output_path = _REPO_ROOT / "agent_scratch_space" / "verified_golden_truths.json"
    
    print(f"Loading results from: {experiment_dir}")
    
    # Find all result files
    result_files = sorted(glob(str(experiment_dir / "result_*.json")))
    print(f"Found {len(result_files)} result files.")
    
    verified_data = []
    
    for fpath in result_files:
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
            
            question = data.get("question", "")
            patient_id = extract_patient_id(data)
            question_index = data.get("question_index", 0)
            
            print(f"\nProcessing Q[{question_index}]: {question[:60]}...")
            
            if not patient_id:
                print(f"  > Warning: No patient_id found, skipping.")
                continue
            
            # Classify the question
            resource_type = classify_question(question)
            print(f"  > Resource type: {resource_type}")
            
            # Query the database
            fhir_data = await query_fhir_data(patient_id, resource_type, question)
            print(f"  > Retrieved {len(fhir_data)} FHIR records.")
            
            # Synthesize golden answer
            golden_answer = synthesize_golden_answer(question, fhir_data, resource_type)
            
            # Extract agent's previous answer
            response_data = data.get("response", {})
            agent_answer = response_data.get("response", "") if isinstance(response_data, dict) else str(response_data)
            
            # Build verified entry
            entry = {
                "question_index": question_index,
                "question": question,
                "patient_id": patient_id,
                "resource_type": resource_type,
                "agent_answer": agent_answer,
                "golden_answer": golden_answer,
                "retrieved_fhir_count": len(fhir_data),
                "metadata": data.get("metadata", {})
            }
            verified_data.append(entry)
            
            print(f"  > Golden answer: {golden_answer[:100]}...")
            
        except Exception as e:
            print(f"Error processing {fpath}: {e}")
    
    # Save output
    with open(output_path, 'w') as f:
        json.dump(verified_data, f, indent=2)
    
    print(f"\nSaved {len(verified_data)} verified entries to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
