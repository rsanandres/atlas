"""Generate JSON reports from test results."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = _REPO_ROOT / "POC_agent" / "tests" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_test_report(
    test_results: Dict[str, Any],
    output_path: Path = None,
) -> Path:
    """Generate JSON test report from test results."""
    if output_path is None:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        output_path = REPORTS_DIR / f"tool_test_report_{timestamp}.json"
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": test_results.get("summary", {}),
        "tool_results": test_results.get("tool_results", {}),
        "failures": test_results.get("failures", []),
        "recommendations": test_results.get("recommendations", []),
        "test_details": test_results.get("test_details", {}),
    }
    
    output_path.write_text(json.dumps(report, indent=2))
    return output_path


def aggregate_pytest_results(pytest_json_path: Path) -> Dict[str, Any]:
    """Aggregate pytest JSON results into our report format."""
    if not pytest_json_path.exists():
        return {}
    
    with pytest_json_path.open("r") as f:
        pytest_data = json.load(f)
    
    summary = {
        "total_tests": pytest_data.get("summary", {}).get("total", 0),
        "passed": pytest_data.get("summary", {}).get("passed", 0),
        "failed": pytest_data.get("summary", {}).get("failed", 0),
        "skipped": pytest_data.get("summary", {}).get("skipped", 0),
    }
    
    failures = []
    tool_results = {}
    
    for test in pytest_data.get("tests", []):
        test_name = test.get("nodeid", "")
        outcome = test.get("outcome", "")
        
        # Extract tool name from test name if possible
        tool_name = None
        for tool in ["calculate_bmi", "calculate_gfr", "search_patient_records", "validate_dosage"]:
            if tool in test_name:
                tool_name = tool
                break
        
        if tool_name:
            if tool_name not in tool_results:
                tool_results[tool_name] = {
                    "functionality": "unknown",
                    "accuracy": "unknown",
                    "prompt_config": "unknown",
                    "llm_validation": "unknown",
                }
            
            # Map test outcome to status
            if outcome == "passed":
                if "functionality" in test_name.lower():
                    tool_results[tool_name]["functionality"] = "passed"
                elif "accuracy" in test_name.lower():
                    tool_results[tool_name]["accuracy"] = "passed"
            elif outcome == "failed":
                failures.append({
                    "test": test_name,
                    "error": test.get("call", {}).get("longrepr", ""),
                })
                if tool_name:
                    if "functionality" in test_name.lower():
                        tool_results[tool_name]["functionality"] = "failed"
                    elif "accuracy" in test_name.lower():
                        tool_results[tool_name]["accuracy"] = "failed"
    
    return {
        "summary": summary,
        "tool_results": tool_results,
        "failures": failures,
    }
