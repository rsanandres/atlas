"""Parse and validate prompts.yaml structure and tool documentation."""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

from POC_agent.agent.prompt_loader import load_prompts
# Import tools with error handling for missing dependencies
try:
    from POC_agent.agent.tools import (
        calculate,
        calculate_bmi,
        calculate_bsa,
        calculate_creatinine_clearance,
        calculate_gfr,
        cross_reference_meds,
        get_current_date,
        get_drug_interactions,
        get_drug_recalls,
        get_drug_shortages,
        get_faers_events,
        get_patient_timeline,
        get_session_context,
        get_who_stats,
        lookup_loinc,
        lookup_rxnorm,
        search_clinical_notes,
        search_clinical_trials,
        search_fda_drugs,
        search_icd10,
        search_patient_records,
        search_pubmed,
        validate_icd10_code,
        validate_dosage,
    )
except ImportError as e:
    # If tools can't be imported (e.g., missing boto3), create placeholder None values
    # This allows tests to run even if some dependencies are missing
    import warnings
    warnings.warn(f"Could not import all tools: {e}. Some validations may be skipped.")
    
    # Create None placeholders for all tools
    calculate = None
    calculate_bmi = None
    calculate_bsa = None
    calculate_creatinine_clearance = None
    calculate_gfr = None
    cross_reference_meds = None
    get_current_date = None
    get_drug_interactions = None
    get_drug_recalls = None
    get_drug_shortages = None
    get_faers_events = None
    get_patient_timeline = None
    get_session_context = None
    get_who_stats = None
    lookup_loinc = None
    lookup_rxnorm = None
    search_clinical_notes = None
    search_clinical_trials = None
    search_fda_drugs = None
    search_icd10 = None
    search_patient_records = None
    search_pubmed = None
    validate_icd10_code = None
    validate_dosage = None

# Map of tool names to actual tool objects
TOOL_MAP = {
    "calculate": calculate,
    "calculate_bmi": calculate_bmi,
    "calculate_bsa": calculate_bsa,
    "calculate_creatinine_clearance": calculate_creatinine_clearance,
    "calculate_gfr": calculate_gfr,
    "cross_reference_meds": cross_reference_meds,
    "get_current_date": get_current_date,
    "get_drug_interactions": get_drug_interactions,
    "get_drug_recalls": get_drug_recalls,
    "get_drug_shortages": get_drug_shortages,
    "get_faers_events": get_faers_events,
    "get_patient_timeline": get_patient_timeline,
    "get_session_context": get_session_context,
    "get_who_stats": get_who_stats,
    "lookup_loinc": lookup_loinc,
    "lookup_rxnorm": lookup_rxnorm,
    "search_clinical_notes": search_clinical_notes,
    "search_clinical_trials": search_clinical_trials,
    "search_fda_drugs": search_fda_drugs,
    "search_icd10": search_icd10,
    "search_patient_records": search_patient_records,
    "search_pubmed": search_pubmed,
    "validate_icd10_code": validate_icd10_code,
    "validate_dosage": validate_dosage,
}


def get_tool_signature(tool_obj: Any) -> Dict[str, Any]:
    """Extract function signature from tool object."""
    if tool_obj is None:
        return {}
    
    func = None
    
    # Handle LangChain tools - they have a func attribute
    if hasattr(tool_obj, "func"):
        func = tool_obj.func
        # Check if func is actually None (can happen if tool wasn't properly initialized)
        if func is None:
            # Try args_schema as fallback
            if hasattr(tool_obj, "args_schema") and tool_obj.args_schema:
                params = {}
                for field_name, field_info in tool_obj.args_schema.model_fields.items():
                    params[field_name] = {
                        "required": field_info.is_required() if hasattr(field_info, "is_required") else True,
                        "default": field_info.default if hasattr(field_info, "default") else None,
                        "annotation": str(field_info.annotation) if hasattr(field_info, "annotation") else None,
                    }
                return params
            return {}
    elif hasattr(tool_obj, "args_schema"):
        # Pydantic model for args (LangChain StructuredTool)
        if tool_obj.args_schema:
            params = {}
            for field_name, field_info in tool_obj.args_schema.model_fields.items():
                params[field_name] = {
                    "required": field_info.is_required() if hasattr(field_info, "is_required") else True,
                    "default": field_info.default if hasattr(field_info, "default") else None,
                    "annotation": str(field_info.annotation) if hasattr(field_info, "annotation") else None,
                }
            return params
    elif callable(tool_obj):
        func = tool_obj
    else:
        return {}
    
    # Check if func is None before trying to inspect
    if func is None or not callable(func):
        return {}
    
    # Try to get signature
    try:
        sig = inspect.signature(func)
        params = {}
        for param_name, param in sig.parameters.items():
            params[param_name] = {
                "required": param.default == inspect.Parameter.empty,
                "default": param.default if param.default != inspect.Parameter.empty else None,
                "annotation": str(param.annotation) if param.annotation != inspect.Parameter.empty else None,
            }
        return params
    except (TypeError, ValueError) as e:
        # Tool is not callable or signature can't be extracted
        return {}


def extract_tool_names_from_prompt(prompt_text: str) -> Set[str]:
    """Extract tool names mentioned in prompt text."""
    tool_names = set()
    
    # Pattern 1: tool_name(parameters) format
    pattern1 = r'(\w+)\([^)]*\)'
    matches = re.finditer(pattern1, prompt_text)
    for match in matches:
        tool_name = match.group(1)
        if tool_name in TOOL_MAP:
            tool_names.add(tool_name)
    
    # Pattern 2: - tool_name format (bullet points)
    pattern2 = r'-\s+(\w+)\s*\('
    matches = re.finditer(pattern2, prompt_text)
    for match in matches:
        tool_name = match.group(1)
        if tool_name in TOOL_MAP:
            tool_names.add(tool_name)
    
    return tool_names


def validate_tool_names_in_prompts() -> Dict[str, Any]:
    """Validate that all tools mentioned in prompts exist in code."""
    prompts = load_prompts()
    issues = []
    
    researcher_prompt = prompts.get("researcher", {}).get("system_prompt", "")
    validator_prompt = prompts.get("validator", {}).get("system_prompt", "")
    
    researcher_tools = extract_tool_names_from_prompt(researcher_prompt)
    validator_tools = extract_tool_names_from_prompt(validator_prompt)
    
    all_prompt_tools = researcher_tools | validator_tools
    all_code_tools = set(TOOL_MAP.keys())
    
    # Check for tools in prompts but not in code (or None due to import issues)
    missing_in_code = all_prompt_tools - all_code_tools
    # Also check for tools that are None (due to import failures)
    none_tools = {tool for tool in all_prompt_tools if tool in TOOL_MAP and TOOL_MAP[tool] is None}
    if missing_in_code:
        issues.append({
            "type": "missing_in_code",
            "tools": list(missing_in_code),
            "severity": "high",
        })
    if none_tools:
        issues.append({
            "type": "tools_not_imported",
            "tools": list(none_tools),
            "severity": "medium",
            "note": "Tools could not be imported (likely missing dependencies like boto3)",
        })
    
    # Check for tools in code but not mentioned in prompts
    missing_in_prompts = all_code_tools - all_prompt_tools
    if missing_in_prompts:
        issues.append({
            "type": "missing_in_prompts",
            "tools": list(missing_in_prompts),
            "severity": "medium",
        })
    
    return {
        "researcher_tools": list(researcher_tools),
        "validator_tools": list(validator_tools),
        "all_code_tools": list(all_code_tools),
        "issues": issues,
        "valid": len(issues) == 0,
    }


def validate_tool_parameters() -> Dict[str, Any]:
    """Validate that tool parameters in prompts match function signatures."""
    prompts = load_prompts()
    issues = []
    
    researcher_prompt = prompts.get("researcher", {}).get("system_prompt", "")
    validator_prompt = prompts.get("validator", {}).get("system_prompt", "")
    
    all_prompts = researcher_prompt + "\n" + validator_prompt
    
    # Extract tool calls with parameters from prompts
    # Pattern: tool_name(param1, param2, ...)
    pattern = r'(\w+)\(([^)]+)\)'
    matches = re.finditer(pattern, all_prompts)
    
    for match in matches:
        tool_name = match.group(1)
        params_str = match.group(2)
        
        if tool_name not in TOOL_MAP:
            continue
        
        tool_obj = TOOL_MAP[tool_name]
        if tool_obj is None:
            # Tools that are None are likely due to import failures (missing dependencies)
            # This is a dependency issue, not a prompt configuration issue
            issues.append({
                "type": "tool_not_available",
                "tool": tool_name,
                "severity": "low",
                "note": "Tool could not be imported (likely missing dependencies like boto3)",
            })
            continue
        
        # Parse parameters from prompt
        prompt_params = [p.strip() for p in params_str.split(",") if p.strip()]
        
        # Get actual function signature
        try:
            actual_params = get_tool_signature(tool_obj)
        except Exception:
            # Skip tools where we can't extract signature
            continue
        
        # If we can't extract signature, skip parameter validation for this tool
        if not actual_params:
            continue
        
        # Check if all prompt parameters exist in actual signature
        for param in prompt_params:
            # Remove default values if present
            param_name = param.split("=")[0].strip()
            if param_name and param_name not in actual_params:
                issues.append({
                    "type": "parameter_mismatch",
                    "tool": tool_name,
                    "prompt_param": param_name,
                    "severity": "medium",
                })
    
    return {
        "issues": issues,
        "valid": len(issues) == 0,
    }


def validate_tool_assignments() -> Dict[str, Any]:
    """Validate that tools are assigned to correct agents."""
    issues = []
    
    # Get tools assigned to each agent from prompts (agents may not expose tools directly)
    prompts = load_prompts()
    researcher_prompt = prompts.get("researcher", {}).get("system_prompt", "")
    validator_prompt = prompts.get("validator", {}).get("system_prompt", "")
    
    researcher_tools = extract_tool_names_from_prompt(researcher_prompt)
    validator_tools = extract_tool_names_from_prompt(validator_prompt)
    
    # Check for tools mentioned in both (should be minimal)
    overlap = researcher_tools & validator_tools
    if overlap:
        issues.append({
            "type": "tool_overlap",
            "tools": list(overlap),
            "severity": "low",
            "note": "Some tools may be used by both agents",
        })
    
    return {
        "researcher_tools": list(researcher_tools),
        "validator_tools": list(validator_tools),
        "overlap": list(overlap),
        "issues": issues,
        "valid": len([i for i in issues if i["severity"] in ["high", "medium"]]) == 0,
    }


def validate_decision_trees() -> Dict[str, Any]:
    """Validate that decision trees in prompts reference valid tools."""
    prompts = load_prompts()
    issues = []
    
    researcher_prompt = prompts.get("researcher", {}).get("system_prompt", "")
    
    # Extract tool names from decision tree section
    decision_tree_section = ""
    if "DECISION TREE" in researcher_prompt:
        start = researcher_prompt.find("DECISION TREE")
        end = researcher_prompt.find("═" * 60, start + 1)
        if end > start:
            decision_tree_section = researcher_prompt[start:end]
    
    decision_tree_tools = extract_tool_names_from_prompt(decision_tree_section)
    all_code_tools = set(TOOL_MAP.keys())
    
    invalid_tools = decision_tree_tools - all_code_tools
    if invalid_tools:
        issues.append({
            "type": "invalid_tool_in_decision_tree",
            "tools": list(invalid_tools),
            "severity": "high",
        })
    
    return {
        "decision_tree_tools": list(decision_tree_tools),
        "issues": issues,
        "valid": len(issues) == 0,
    }


def get_prompt_validation_summary() -> Dict[str, Any]:
    """Get comprehensive validation summary."""
    tool_names = validate_tool_names_in_prompts()
    tool_params = validate_tool_parameters()
    tool_assignments = validate_tool_assignments()
    decision_trees = validate_decision_trees()
    
    all_issues = (
        tool_names.get("issues", []) +
        tool_params.get("issues", []) +
        tool_assignments.get("issues", []) +
        decision_trees.get("issues", [])
    )
    
    return {
        "tool_names": tool_names,
        "tool_parameters": tool_params,
        "tool_assignments": tool_assignments,
        "decision_trees": decision_trees,
        "all_issues": all_issues,
        "total_issues": len(all_issues),
        "high_severity_issues": len([i for i in all_issues if i.get("severity") == "high"]),
        "medium_severity_issues": len([i for i in all_issues if i.get("severity") == "medium"]),
        "low_severity_issues": len([i for i in all_issues if i.get("severity") == "low"]),
        # Don't count "tools_not_imported" or "tool_not_available" as validation failures - they're dependency issues
        "valid": len([i for i in all_issues if i.get("severity") in ["high", "medium"] and i.get("type") not in ["tools_not_imported", "tool_not_available"]]) == 0,
    }
