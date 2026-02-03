#!/usr/bin/env python3
"""
Retrieve FHIR data for all questions in golden_dataset_experiment.
This script ONLY retrieves and organizes data - synthesis is done manually.
"""

import asyncio
import json
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
from api.database.postgres import hybrid_search


async def retrieve_fhir_for_question(patient_id: str, question: str) -> List[Dict]:
    """Retrieve FHIR data for a specific question."""
    try:
        # Use hybrid search
        results = await hybrid_search(
            query=question,
            k=20,
            filter_metadata={"patient_id": patient_id}
        )
        
        fhir_data = []
        for doc in results:
            try:
                # Try to parse as JSON
                if doc.page_content.startswith("{"):
                    data = json.loads(doc.page_content)
                    fhir_data.append({
                        "data": data,
                        "metadata": doc.metadata
                    })
                else:
                    fhir_data.append({
                        "data": doc.page_content[:500],
                        "metadata": doc.metadata
                    })
            except json.JSONDecodeError:
                fhir_data.append({
                    "data": doc.page_content[:500],
                    "metadata": doc.metadata
                })
        
        return fhir_data
    except Exception as e:
        print(f"  > Error: {e}")
        return []


async def main():
    experiment_dir = _REPO_ROOT / "agent_scratch_space" / "golden_dataset_experiment"
    output_path = _REPO_ROOT / "agent_scratch_space" / "fhir_data_for_synthesis.json"
    
    result_files = sorted(glob(str(experiment_dir / "result_*.json")))
    print(f"Found {len(result_files)} result files.")
    
    all_data = []
    
    for fpath in result_files:
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
            
            question = data.get("question", "")
            metadata = data.get("metadata", {})
            patient_id = metadata.get("patient_id")
            question_index = data.get("question_index", 0)
            
            print(f"\nQ[{question_index}]: {question[:60]}...")
            
            if not patient_id:
                print(f"  > No patient_id, skipping.")
                continue
            
            # Retrieve FHIR data
            fhir_data = await retrieve_fhir_for_question(patient_id, question)
            print(f"  > Retrieved {len(fhir_data)} records.")
            
            # Store for manual synthesis
            entry = {
                "question_index": question_index,
                "question": question,
                "patient_id": patient_id,
                "fhir_records": fhir_data,
                "agent_answer": data.get("response", {}).get("response", "") if isinstance(data.get("response"), dict) else str(data.get("response", "")),
                "golden_answer": ""  # To be filled manually
            }
            all_data.append(entry)
            
        except Exception as e:
            print(f"Error processing {fpath}: {e}")
    
    # Save
    with open(output_path, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f"\nSaved {len(all_data)} entries to {output_path}")
    print("Ready for manual synthesis.")


if __name__ == "__main__":
    asyncio.run(main())
