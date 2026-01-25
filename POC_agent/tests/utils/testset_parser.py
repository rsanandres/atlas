"""Parse synthetic testset and extract test data for tool validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
TESTSET_PATH = _REPO_ROOT / "POC_RAGAS" / "data" / "testsets" / "synthetic_testset.json"


def load_testset(path: Path = TESTSET_PATH) -> List[Dict[str, Any]]:
    """Load synthetic testset from JSON file."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_fhir_resources(testset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract all FHIR resources from reference_contexts."""
    resources = []
    for item in testset:
        contexts = item.get("reference_contexts", [])
        for context_str in contexts:
            try:
                resource = json.loads(context_str)
                resources.append(resource)
            except (json.JSONDecodeError, TypeError):
                continue
    return resources


def extract_loinc_codes(testset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract LOINC codes from Observation resources."""
    loinc_codes = []
    resources = extract_fhir_resources(testset)
    
    for resource in resources:
        if resource.get("resourceType") == "Observation":
            code = resource.get("code", {})
            codings = code.get("coding", [])
            for coding in codings:
                system = coding.get("system", "")
                if "loinc.org" in system.lower():
                    loinc_codes.append({
                        "code": coding.get("code", ""),
                        "display": coding.get("display", ""),
                        "system": system,
                        "resource_id": resource.get("id", ""),
                    })
    return loinc_codes


def extract_icd10_codes(testset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract ICD-10 codes from Condition resources."""
    icd10_codes = []
    resources = extract_fhir_resources(testset)
    
    for resource in resources:
        if resource.get("resourceType") == "Condition":
            code = resource.get("code", {})
            codings = code.get("coding", [])
            for coding in codings:
                system = coding.get("system", "")
                if "icd10" in system.lower() or "icd-10" in system.lower():
                    icd10_codes.append({
                        "code": coding.get("code", ""),
                        "display": coding.get("display", ""),
                        "system": system,
                        "resource_id": resource.get("id", ""),
                    })
    return icd10_codes


def extract_rxnorm_codes(testset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract RxNorm codes from Medication resources."""
    rxnorm_codes = []
    resources = extract_fhir_resources(testset)
    
    for resource in resources:
        if resource.get("resourceType") == "Medication":
            code = resource.get("code", {})
            codings = code.get("coding", [])
            for coding in codings:
                system = coding.get("system", "")
                if "rxnorm" in system.lower():
                    rxnorm_codes.append({
                        "code": coding.get("code", ""),
                        "display": coding.get("display", ""),
                        "system": system,
                        "resource_id": resource.get("id", ""),
                    })
    return rxnorm_codes


def extract_medication_names(testset: List[Dict[str, Any]]) -> List[str]:
    """Extract medication names from Medication resources."""
    medication_names = []
    resources = extract_fhir_resources(testset)
    
    for resource in resources:
        if resource.get("resourceType") == "Medication":
            code = resource.get("code", {})
            text = code.get("text", "")
            if text:
                medication_names.append(text)
            else:
                codings = code.get("coding", [])
                for coding in codings:
                    display = coding.get("display", "")
                    if display:
                        medication_names.append(display)
                        break
    return list(set(medication_names))  # Remove duplicates


def extract_height_weight_observations(testset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract height and weight observations for BMI/BSA calculations."""
    observations = []
    resources = extract_fhir_resources(testset)
    
    for resource in resources:
        if resource.get("resourceType") == "Observation":
            code = resource.get("code", {})
            codings = code.get("coding", [])
            value_quantity = resource.get("valueQuantity", {})
            
            for coding in codings:
                code_value = coding.get("code", "")
                display = coding.get("display", "").lower()
                
                # Check for height (LOINC 8302-2) or weight (LOINC 29463-7)
                if code_value in ("8302-2", "29463-7") or "height" in display or "weight" in display:
                    value = value_quantity.get("value")
                    unit = value_quantity.get("unit", "").lower()
                    
                    if value is not None:
                        observations.append({
                            "type": "height" if "height" in display or code_value == "8302-2" else "weight",
                            "value": float(value),
                            "unit": unit,
                            "code": code_value,
                            "display": coding.get("display", ""),
                            "resource_id": resource.get("id", ""),
                        })
    return observations


def extract_calculation_test_cases(testset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract height/weight pairs for BMI/BSA calculation testing."""
    observations = extract_height_weight_observations(testset)
    
    # Group by resource context to find height/weight pairs
    height_weight_pairs = []
    height_by_context = {}
    weight_by_context = {}
    
    for obs in observations:
        context_key = obs.get("resource_id", "").split("-")[0] if obs.get("resource_id") else ""
        
        if obs["type"] == "height":
            if context_key not in height_by_context:
                height_by_context[context_key] = []
            height_by_context[context_key].append(obs)
        else:  # weight
            if context_key not in weight_by_context:
                weight_by_context[context_key] = []
            weight_by_context[context_key].append(obs)
    
    # Create pairs (use first height and first weight from same context if available)
    for context_key in set(list(height_by_context.keys()) + list(weight_by_context.keys())):
        heights = height_by_context.get(context_key, [])
        weights = weight_by_context.get(context_key, [])
        
        if heights and weights:
            height = heights[0]
            weight = weights[0]
            
            # Convert to standard units
            height_cm = height["value"] if height["unit"] in ("cm", "centimeter") else height["value"] * 2.54
            weight_kg = weight["value"] if weight["unit"] in ("kg", "kilogram") else weight["value"] * 0.453592
            
            height_weight_pairs.append({
                "height_cm": round(height_cm, 2),
                "weight_kg": round(weight_kg, 2),
                "height_unit": height["unit"],
                "weight_unit": weight["unit"],
                "height_code": height["code"],
                "weight_code": weight["code"],
            })
    
    return height_weight_pairs


def extract_queries_by_tool_type(testset: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize queries by likely tool usage."""
    categorized = {
        "retrieval": [],  # search_patient_records, search_clinical_notes
        "calculator": [],  # calculate_bmi, calculate_gfr, etc.
        "code_lookup": [],  # lookup_loinc, validate_icd10_code, lookup_rxnorm
        "fda": [],  # search_fda_drugs, get_drug_recalls, etc.
        "research": [],  # search_pubmed, search_clinical_trials
        "other": [],
    }
    
    for item in testset:
        query = item.get("user_input", "").lower()
        
        if any(word in query for word in ["height", "weight", "bmi", "gfr", "creatinine", "calculate", "bsa"]):
            categorized["calculator"].append(item)
        elif any(word in query for word in ["code", "loinc", "icd", "rxnorm", "coding"]):
            categorized["code_lookup"].append(item)
        elif any(word in query for word in ["drug", "medication", "fda", "recall", "shortage", "faers"]):
            categorized["fda"].append(item)
        elif any(word in query for word in ["pubmed", "clinical trial", "research", "study", "who"]):
            categorized["research"].append(item)
        elif any(word in query for word in ["patient", "record", "encounter", "observation", "condition"]):
            categorized["retrieval"].append(item)
        else:
            categorized["other"].append(item)
    
    return categorized


def get_test_data_summary(testset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get summary of available test data in testset."""
    return {
        "total_queries": len(testset),
        "loinc_codes": len(extract_loinc_codes(testset)),
        "icd10_codes": len(extract_icd10_codes(testset)),
        "rxnorm_codes": len(extract_rxnorm_codes(testset)),
        "medication_names": len(extract_medication_names(testset)),
        "height_weight_pairs": len(extract_calculation_test_cases(testset)),
        "categorized_queries": {
            k: len(v) for k, v in extract_queries_by_tool_type(testset).items()
        },
    }
