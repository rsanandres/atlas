"""Parse checkpoint data to extract tool usage patterns and results."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKPOINT_DIR = _REPO_ROOT / "POC_RAGAS" / "data" / "checkpoints"


def load_checkpoint(path: Path) -> Dict[str, Any]:
    """Load checkpoint JSON file."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_checkpoint_files() -> List[Path]:
    """Find all checkpoint JSON files."""
    if not CHECKPOINT_DIR.exists():
        return []
    return list(CHECKPOINT_DIR.glob("checkpoint_*.json"))


def extract_tool_calls_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract tool calls from text (JSON format or function call format)."""
    tool_calls = []
    
    # Pattern 1: JSON format {"name": "tool_name", "parameters": {...}}
    json_pattern = r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"parameters"\s*:\s*(\{[^}]+\})\s*\}'
    matches = re.finditer(json_pattern, text, re.IGNORECASE)
    for match in matches:
        try:
            tool_name = match.group(1)
            params_str = match.group(2)
            params = json.loads(params_str)
            tool_calls.append({
                "tool": tool_name,
                "parameters": params,
                "format": "json",
            })
        except (json.JSONDecodeError, IndexError):
            continue
    
    # Pattern 2: Function call format tool_name(param1=value1, param2=value2)
    func_pattern = r'(\w+)\(([^)]+)\)'
    matches = re.finditer(func_pattern, text)
    for match in matches:
        tool_name = match.group(1)
        params_str = match.group(2)
        # Try to parse parameters
        params = {}
        param_pairs = re.findall(r'(\w+)\s*=\s*([^,]+)', params_str)
        for key, value in param_pairs:
            value = value.strip().strip('"\'')
            # Try to convert to appropriate type
            try:
                if value.lower() in ("true", "false"):
                    params[key] = value.lower() == "true"
                elif value.replace(".", "").isdigit():
                    params[key] = float(value) if "." in value else int(value)
                else:
                    params[key] = value
            except ValueError:
                params[key] = value
        
        if params:
            tool_calls.append({
                "tool": tool_name,
                "parameters": params,
                "format": "function",
            })
    
    return tool_calls


def extract_tool_usage_from_checkpoint(checkpoint: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Extract all tool usage from checkpoint samples."""
    tool_usage = {}
    samples = checkpoint.get("samples", [])
    
    for sample in samples:
        answer = sample.get("answer", "")
        if not answer:
            continue
        
        tool_calls = extract_tool_calls_from_text(answer)
        for call in tool_calls:
            tool_name = call["tool"]
            if tool_name not in tool_usage:
                tool_usage[tool_name] = []
            tool_usage[tool_name].append({
                "parameters": call["parameters"],
                "question": sample.get("question", ""),
                "context": sample.get("contexts", []),
            })
    
    return tool_usage


def extract_calculation_results(checkpoint: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract calculation results (BMI, GFR, etc.) from checkpoint."""
    calculations = []
    samples = checkpoint.get("samples", [])
    
    for sample in samples:
        answer = sample.get("answer", "")
        question = sample.get("question", "")
        
        # Look for BMI calculations
        bmi_pattern = r'BMI[:\s=]+([\d.]+)|bmi[:\s=]+([\d.]+)'
        bmi_matches = re.finditer(bmi_pattern, answer, re.IGNORECASE)
        for match in bmi_matches:
            bmi_value = float(match.group(1) or match.group(2))
            # Try to extract weight and height from parameters or context
            tool_calls = extract_tool_calls_from_text(answer)
            for call in tool_calls:
                if call["tool"] == "calculate_bmi":
                    params = call["parameters"]
                    calculations.append({
                        "type": "bmi",
                        "result": bmi_value,
                        "inputs": params,
                        "question": question,
                    })
                    break
        
        # Look for GFR calculations
        gfr_pattern = r'GFR[:\s=]+([\d.]+)|gfr[:\s=]+([\d.]+)'
        gfr_matches = re.finditer(gfr_pattern, answer, re.IGNORECASE)
        for match in gfr_matches:
            gfr_value = float(match.group(1) or match.group(2))
            tool_calls = extract_tool_calls_from_text(answer)
            for call in tool_calls:
                if call["tool"] == "calculate_gfr":
                    params = call["parameters"]
                    calculations.append({
                        "type": "gfr",
                        "result": gfr_value,
                        "inputs": params,
                        "question": question,
                    })
                    break
    
    return calculations


def get_tool_usage_summary(checkpoint_path: Optional[Path] = None) -> Dict[str, Any]:
    """Get summary of tool usage from checkpoint(s)."""
    if checkpoint_path:
        checkpoints = [checkpoint_path]
    else:
        checkpoints = find_checkpoint_files()
    
    all_tool_usage = {}
    all_calculations = []
    
    for cp_path in checkpoints:
        try:
            checkpoint = load_checkpoint(cp_path)
            tool_usage = extract_tool_usage_from_checkpoint(checkpoint)
            calculations = extract_calculation_results(checkpoint)
            
            for tool, calls in tool_usage.items():
                if tool not in all_tool_usage:
                    all_tool_usage[tool] = []
                all_tool_usage[tool].extend(calls)
            
            all_calculations.extend(calculations)
        except Exception as e:
            print(f"Warning: Failed to parse checkpoint {cp_path}: {e}")
            continue
    
    return {
        "tools_used": list(all_tool_usage.keys()),
        "tool_call_counts": {tool: len(calls) for tool, calls in all_tool_usage.items()},
        "tool_usage": all_tool_usage,
        "calculations": all_calculations,
    }
