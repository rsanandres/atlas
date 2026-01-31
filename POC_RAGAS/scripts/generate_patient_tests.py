#!/usr/bin/env python3
"""
Patient-Oriented Test Generator for RAGAS Evaluation.

Generates 2 sets of 10 questions per patient:
- Set A: Factual retrieval (conditions, meds, labs, procedures)
- Set B: Complex queries (calculations, timelines, interactions)

Uses OpenAI API to generate clinical questions based on patient data samples.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add repo root to path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))



# Top 10 richest patients from patient_inventory_top100.json
TOP_10_PATIENTS = [
    "3e80196f-06df-4568-a5e5-480b742b8639",  # 317 chunks, 9 resource types
    "3f89ff20-09aa-40e7-a359-389863c7e574",  # 305 chunks, 9 resource types
    "5dcb9365-483d-48d7-bc62-816221b3f8b7",  # 291 chunks, 8 resource types
    "e149aa89-cc9e-483e-b78b-00f0433072e0",  # 262 chunks, 8 resource types
    "be36dfc3-e8f9-46d4-b02b-03466388c34d",  # 258 chunks, 9 resource types
    "d0b81fcd-b4a2-43d9-99ac-8fe6dd6f4921",  # 247 chunks, 9 resource types
    "723d6d77-8a55-424b-b4fc-99e3b48e7e73",  # 246 chunks, 8 resource types
    "72790c7f-7ee6-400f-aba9-b4bea77d929a",  # 244 chunks, 10 resource types (ALL!)
    "d930e322-8c86-4c17-8ce8-217cb252e2e4",  # 240 chunks, 9 resource types
    "c19e653d-f0d3-4a08-817a-ad0da990a288",  # 240 chunks, 8 resource types
]

# Question templates for Set A (Factual Retrieval)
SET_A_TEMPLATES = [
    "What active conditions does patient {patient_id} have?",
    "List all medications prescribed to patient {patient_id}.",
    "What immunizations has patient {patient_id} received?",
    "Has patient {patient_id} undergone any procedures? List them.",
    "What is the most recent body weight recorded for patient {patient_id}?",
    "What allergies does patient {patient_id} have on record?",
    "List all encounters for patient {patient_id} in chronological order.",
    "What diagnostic reports exist for patient {patient_id}?",
    "What is patient {patient_id}'s blood pressure history?",
    "What lab results are on file for patient {patient_id}?",
]

# Question templates for Set B (Complex Queries)
SET_B_TEMPLATES = [
    "Calculate the BMI for patient {patient_id} using their most recent height and weight.",
    "What is the trend in patient {patient_id}'s glucose levels over time?",
    "Are there any drug interactions between the medications patient {patient_id} is taking?",
    "Summarize the complete medical history for patient {patient_id}.",
    "What were the vital signs recorded during patient {patient_id}'s last encounter?",
    "Compare patient {patient_id}'s cholesterol levels across multiple visits.",
    "Has patient {patient_id} had any medication dosage changes? Describe the timeline.",
    "What conditions was patient {patient_id} diagnosed with in the past 2 years?",
    "Calculate the eGFR for patient {patient_id} if creatinine data is available.",
    "What follow-up care recommendations exist for patient {patient_id}?",
]


# Note: fetch_patient_sample removed - templates are sufficient for initial generation
# Can add OpenAI-based question generation later if needed


def generate_questions_for_patient(patient_id: str, use_openai: bool = False) -> dict:
    """Generate 2 sets of 10 questions for a patient."""
    
    # Use templates - simple and reliable
    set_a = [q.format(patient_id=patient_id) for q in SET_A_TEMPLATES]
    set_b = [q.format(patient_id=patient_id) for q in SET_B_TEMPLATES]
    
    return {
        "patient_id": patient_id,
        "set_a_factual": [
            {
                "user_input": q,
                "reference_contexts": [],  # Will be filled by ground truth generation
                "reference": "",
                "metadata": {
                    "patient_id": patient_id,
                    "question_type": "factual_retrieval",
                    "set": "A",
                }
            }
            for q in set_a
        ],
        "set_b_complex": [
            {
                "user_input": q,
                "reference_contexts": [],
                "reference": "",
                "metadata": {
                    "patient_id": patient_id,
                    "question_type": "complex_query",
                    "set": "B",
                }
            }
            for q in set_b
        ]
    }


def create_full_testset(output_path: Path):
    """Generate complete patient-oriented testset."""
    all_questions = []
    patient_data = {}
    
    print(f"Generating tests for {len(TOP_10_PATIENTS)} patients...")
    
    for i, patient_id in enumerate(TOP_10_PATIENTS, 1):
        print(f"[{i}/{len(TOP_10_PATIENTS)}] Generating questions for {patient_id[:8]}...")
        
        patient_questions = generate_questions_for_patient(patient_id)
        patient_data[patient_id] = {
            "set_a_count": len(patient_questions["set_a_factual"]),
            "set_b_count": len(patient_questions["set_b_complex"]),
        }
        
        # Add to flat list
        all_questions.extend(patient_questions["set_a_factual"])
        all_questions.extend(patient_questions["set_b_complex"])
    
    # Create output structure
    testset = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "total_questions": len(all_questions),
            "patients": len(TOP_10_PATIENTS),
            "questions_per_patient": 20,
            "sets": {
                "A": "Factual retrieval (conditions, meds, labs, procedures)",
                "B": "Complex queries (calculations, timelines, interactions)"
            },
            "patient_summary": patient_data
        },
        "data": all_questions
    }
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(testset, f, indent=2)
    
    print(f"\n✅ Generated {len(all_questions)} questions for {len(TOP_10_PATIENTS)} patients")
    print(f"   Saved to: {output_path}")
    
    return testset


def main():
    output_path = _REPO_ROOT / "POC_RAGAS" / "data" / "testsets" / "patient_oriented_testset.json"
    create_full_testset(output_path)


if __name__ == "__main__":
    main()
