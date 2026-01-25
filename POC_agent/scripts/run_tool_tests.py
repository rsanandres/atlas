"""Main test runner for tool validation with JSON report generation."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from POC_agent.tests.utils.prompt_validator import get_prompt_validation_summary
from POC_agent.tests.utils.report_generator import generate_test_report


def get_python_executable() -> str:
    """Get the Python executable, preferring venv if available."""
    # Check if we're already in a venv
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        # Already in a venv
        return sys.executable
    
    # Check for .venv in repo root
    venv_python = _REPO_ROOT / ".venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    
    # Check for venv in repo root
    venv_python = _REPO_ROOT / "venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    
    # Fall back to current executable
    return sys.executable


def run_pytest_tests(test_files: list[str] = None) -> dict:
    """Run pytest tests and return results."""
    if test_files is None:
        test_files = [
            "POC_agent/tests/test_tool_functionality.py",
            "POC_agent/tests/test_tool_accuracy.py",
            "POC_agent/tests/test_prompt_configuration.py",
        ]
    
    # Get Python executable (prefer venv)
    python_exe = get_python_executable()
    
    # Run pytest (note: --json-report requires pytest-json-report plugin)
    # Fallback to regular pytest if plugin not available
    cmd = [
        python_exe,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
    ] + test_files
    
    # Try to use json-report if available
    try:
        import pytest_jsonreport
        cmd.extend([
            "--json-report",
            "--json-report-file",
            str(_REPO_ROOT / "pytest_report.json"),
        ])
    except ImportError:
        # Plugin not available, use regular pytest
        pass
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as e:
        return {
            "exit_code": 1,
            "error": str(e),
        }


async def run_llm_validation() -> dict:
    """Run LLM validation tests."""
    try:
        from POC_agent.tests.utils.llm_validator import get_llm_validation_summary
        from POC_agent.tests.utils.testset_parser import extract_queries_by_tool_type, load_testset
        
        testset = load_testset()
        categorized = extract_queries_by_tool_type(testset)
        
        test_queries = []
        if categorized.get("calculator"):
            test_queries.append({
                "query": categorized["calculator"][0].get("user_input", ""),
                "expected_tools": ["calculate_bmi"],
            })
        if categorized.get("retrieval"):
            test_queries.append({
                "query": categorized["retrieval"][0].get("user_input", ""),
                "expected_tools": ["search_patient_records"],
            })
        
        summary = await get_llm_validation_summary(test_queries)
        return {
            "success": True,
            "summary": summary,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def collect_test_results() -> dict:
    """Collect results from all test suites."""
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        },
        "tool_results": {},
        "failures": [],
        "recommendations": [],
        "test_details": {},
    }
    
    # Run pytest tests
    print("Running pytest tests...")
    pytest_result = run_pytest_tests()
    results["test_details"]["pytest"] = pytest_result
    
    # Parse pytest output to extract test counts
    # Since pytest-json-report plugin may not be available, parse stdout
    if pytest_result.get("stdout"):
        stdout = pytest_result["stdout"]
        import re
        
        # Look for test summary line - pytest format: "2 failed, 37 passed, 8 skipped in 8.43s"
        # Extract numbers with their labels using a more flexible pattern
        failed_match = re.search(r'(\d+)\s+failed', stdout)
        passed_match = re.search(r'(\d+)\s+passed', stdout)
        skipped_match = re.search(r'(\d+)\s+skipped', stdout)
        
        if failed_match:
            results["summary"]["failed"] = int(failed_match.group(1))
        if passed_match:
            results["summary"]["passed"] = int(passed_match.group(1))
        if skipped_match:
            results["summary"]["skipped"] = int(skipped_match.group(1))
        
        # Calculate total if we found any counts
        if failed_match or passed_match or skipped_match:
            results["summary"]["total_tests"] = (
                results["summary"]["failed"] +
                results["summary"]["passed"] +
                results["summary"]["skipped"]
            )
        
        # Extract failures from stdout - look for FAILURES section
        if "FAILURES" in stdout:
            failure_section = stdout.split("FAILURES")[1].split("short test summary")[0]
            # Extract test names that failed (format: TestClass::test_method)
            failure_matches = re.finditer(r'([A-Za-z0-9_]+::[A-Za-z0-9_]+::[A-Za-z0-9_]+)', failure_section)
            for match in failure_matches:
                test_name = match.group(1)
                if test_name not in [f["test"] for f in results["failures"]]:
                    results["failures"].append({
                        "test": test_name,
                        "error": "See pytest output for details",
                    })
    
    # Try to load pytest JSON report if available
    pytest_json_path = _REPO_ROOT / "pytest_report.json"
    if pytest_json_path.exists():
        try:
            with pytest_json_path.open("r") as f:
                pytest_data = json.load(f)
            
            summary = pytest_data.get("summary", {})
            if summary.get("total"):
                results["summary"]["total_tests"] = summary.get("total", 0)
                results["summary"]["passed"] = summary.get("passed", 0)
                results["summary"]["failed"] = summary.get("failed", 0)
                results["summary"]["skipped"] = summary.get("skipped", 0)
            
            # Extract failures
            for test in pytest_data.get("tests", []):
                if test.get("outcome") == "failed":
                    test_nodeid = test.get("nodeid", "")
                    if test_nodeid not in [f["test"] for f in results["failures"]]:
                        results["failures"].append({
                            "test": test_nodeid,
                            "error": test.get("call", {}).get("longrepr", ""),
                        })
        except Exception as e:
            # JSON parsing failed, but we already have stdout parsing
            pass
    
    # Run prompt validation
    print("Running prompt validation...")
    try:
        prompt_summary = get_prompt_validation_summary()
        results["test_details"]["prompt_validation"] = prompt_summary
        
        if prompt_summary.get("high_severity_issues", 0) > 0:
            results["recommendations"].append(
                f"Fix {prompt_summary['high_severity_issues']} high severity prompt issues"
            )
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        # Truncate long tracebacks
        if len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        results["failures"].append({
            "test": "prompt_validation",
            "error": error_msg,
        })
    
    # Run LLM validation (async)
    print("Running LLM validation...")
    try:
        llm_result = asyncio.run(run_llm_validation())
        results["test_details"]["llm_validation"] = llm_result
        
        if llm_result.get("success"):
            overall_accuracy = llm_result.get("summary", {}).get("overall_accuracy", 0)
            if overall_accuracy < 0.5:
                results["recommendations"].append(
                    f"LLM validation accuracy is low ({overall_accuracy*100:.1f}%). "
                    "Consider improving prompt clarity."
                )
    except Exception as e:
        results["failures"].append({
            "test": "llm_validation",
            "error": str(e),
        })
    
    return results


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run tool validation tests and generate JSON report")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for JSON report",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM validation tests (faster)",
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("Tool Testing and Validation System")
    print("=" * 60)
    print()
    
    # Collect test results
    results = collect_test_results()
    
    # Generate report
    report_path = generate_test_report(results, args.output)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Total tests: {results['summary']['total_tests']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Skipped: {results['summary']['skipped']}")
    print(f"\nReport saved to: {report_path}")
    
    if results["failures"]:
        print(f"\nFailures: {len(results['failures'])}")
        for failure in results["failures"][:5]:  # Show first 5
            print(f"  - {failure['test']}")
    
    if results["recommendations"]:
        print(f"\nRecommendations:")
        for rec in results["recommendations"]:
            print(f"  - {rec}")
    
    print("=" * 60)
    
    # Return exit code based on failures
    return 1 if results["summary"]["failed"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
