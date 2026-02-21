"""Generate JSON and Markdown reports for evaluation runs."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from tabulate import tabulate

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from POC_RAGAS.config import CONFIG


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json_report(payload: Dict[str, Any], output_path: Path) -> Path:
    _ensure_dir(output_path)
    output_path.write_text(json.dumps(payload, indent=2))
    return output_path


def write_markdown_report(
    summary: Dict[str, Any],
    samples: Iterable[Dict[str, Any]],
    output_path: Path,
) -> Path:
    _ensure_dir(output_path)
    timestamp = summary.get("timestamp") or datetime.utcnow().isoformat()
    metrics = summary.get("metrics", {})
    progress = summary.get("progress", {})
    failed = summary.get("failed", [])

    rows: List[List[Any]] = []
    for metric_name, metric_data in metrics.items():
        if isinstance(metric_data, dict) and "score" in metric_data:
            rows.append([metric_name, metric_data.get("score")])
        elif isinstance(metric_data, dict) and "baseline_score" in metric_data:
            rows.append([metric_name, metric_data.get("baseline_score")])
            rows.append([f"{metric_name}_noisy", metric_data.get("noisy_score")])
            rows.append([f"{metric_name}_degradation", metric_data.get("degradation")])

    table = tabulate(rows, headers=["Metric", "Score"], tablefmt="github")

    sample_lines = []
    for sample in list(samples)[:5]:
        sample_lines.append(f"- Question: {sample.get('user_input') or sample.get('question')}")
        sample_lines.append(f"  Answer: {(sample.get('response') or sample.get('answer', ''))[:120]}")
        sample_lines.append(f"  Patient: {sample.get('patient_id')}")

    failed_lines = []
    if failed:
        for failed_item in failed[:10]:  # Show first 10 failed queries
            failed_lines.append(f"- **Question {failed_item.get('question_index', '?')}** ({failed_item.get('mode', 'unknown')}):")
            failed_lines.append(f"  - Question: {failed_item.get('question', 'N/A')[:100]}...")
            failed_lines.append(f"  - Error: {failed_item.get('error', 'Unknown error')}")
            failed_lines.append(f"  - Timestamp: {failed_item.get('timestamp', 'N/A')}")

    progress_info = ""
    if progress:
        total = progress.get("total_questions", 0)
        completed = progress.get("completed_questions", 0)
        failed_count = progress.get("failed_questions", 0)
        progress_info = f"""
## Progress Summary

- Total Questions: {total}
- Completed: {completed}
- Failed: {failed_count}
- Success Rate: {(completed / total * 100) if total > 0 else 0:.1f}%
"""

    failed_section = ""
    if failed:
        failed_section = f"""
## Failed Queries ({len(failed)} total)

{failed_lines[0] if failed_lines else "No failed queries."}
{chr(10).join(failed_lines[1:]) if len(failed_lines) > 1 else ""}

{f"*Showing first 10 of {len(failed)} failed queries*" if len(failed) > 10 else ""}
"""

    report = f"""# RAGAS Evaluation Report

Timestamp: {timestamp}
Run ID: {summary.get('run_id', 'N/A')}
Model: {CONFIG.ragas_model}
{progress_info}
## Summary Metrics

{table}

## Sample Results (first 5)
{chr(10).join(sample_lines)}
{failed_section}
"""
    output_path.write_text(report)
    return output_path
