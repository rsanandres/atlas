"""CLI to run RAGAS evaluation against the production API."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from POC_RAGAS.config import CONFIG
from POC_RAGAS.evaluators.faithfulness import evaluate_faithfulness
from POC_RAGAS.evaluators.noise_sensitivity import evaluate_noise_sensitivity
from POC_RAGAS.evaluators.relevancy import evaluate_relevancy
from POC_RAGAS.runners.api_runner import run_api_query
from POC_RAGAS.utils.checkpoint import load_latest_checkpoint, save_checkpoint, should_checkpoint
from POC_RAGAS.utils.report_generator import write_json_report, write_markdown_report
from POC_RAGAS.utils.service_manager import check_service_health


UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation (API mode).")
    parser.add_argument(
        "--testset",
        type=Path,
        default=Path(CONFIG.testset_dir) / "smoke_test.json",
        help="Path to testset JSON.",
    )
    parser.add_argument(
        "--mode",
        choices=["api"],
        default="api",
        help="Evaluation mode (API only).",
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=None,
        help="Start evaluation from this question index (0-based).",
    )
    parser.add_argument(
        "--output-id",
        type=str,
        default=None,
        help="Optional identifier for output filenames.",
    )
    parser.add_argument(
        "--cooldown",
        type=int,
        default=None,
        help=f"Seconds between API requests (default: {CONFIG.api_cooldown_seconds} from config).",
    )
    return parser.parse_args()


def _extract_questions(testset_path: Path) -> List[Dict[str, Any]]:
    data = json.loads(testset_path.read_text())
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    if not isinstance(data, list):
        raise ValueError("Testset JSON format not recognized.")
    return data


def _get_question_text(item: Dict[str, Any]) -> str:
    return (
        item.get("user_input")
        or item.get("question")
        or item.get("query")
        or item.get("prompt")
        or ""
    )


def _get_patient_id(item: Dict[str, Any], question: str) -> str | None:
    """Extract patient_id from item metadata or question text."""
    meta = item.get("metadata", {})
    if meta.get("patient_id"):
        return meta["patient_id"]
    match = UUID_RE.search(question)
    return match.group(0) if match else None


def _build_sample(
    query: str, result: Dict[str, Any], patient_id: str | None
) -> Dict[str, Any] | None:
    contexts = []
    for source in result.get("sources", []):
        if isinstance(source, dict):
            contexts.append(source.get("content_preview") or source.get("content") or "")
        else:
            contexts.append(str(source))
    contexts = [ctx for ctx in contexts if ctx]
    if not contexts:
        return None
    return {
        "user_input": query,
        "response": result.get("response", ""),
        "retrieved_contexts": contexts,
        "patient_id": patient_id,
    }


async def main() -> int:
    args = parse_args()
    cooldown = args.cooldown if args.cooldown is not None else CONFIG.api_cooldown_seconds
    testset = _extract_questions(args.testset)

    # Pre-flight health check
    print(f"Checking API health at {CONFIG.agent_api_url}...")
    if not await check_service_health():
        print("ERROR: Agent API is not reachable.")
        return 1
    print("API is healthy.")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    samples: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    start_index = 0

    if args.start_from is not None:
        if args.start_from < 0 or args.start_from >= len(testset):
            print(f"ERROR: --start-from must be between 0 and {len(testset) - 1}")
            return 1
        start_index = args.start_from
        print(f"Starting from question {start_index}")
    else:
        checkpoint = load_latest_checkpoint()
        if checkpoint:
            samples = checkpoint.get("samples", [])
            failed = checkpoint.get("failed", [])
            progress = checkpoint.get("progress", {})
            start_index = progress.get("completed_questions", 0)
            print(f"Resumed from checkpoint: {len(samples)} samples, starting at question {start_index}")

    total = len(testset)
    for idx in range(start_index, total):
        item = testset[idx]
        question = _get_question_text(item)
        if not question:
            continue

        patient_id = _get_patient_id(item, question)
        session_id = f"ragas-{run_id}-{idx}"

        try:
            print(f"[{idx + 1}/{total}] {question[:70]}...")
            result = await run_api_query(
                query=question,
                session_id=session_id,
                patient_id=patient_id,
                cooldown=cooldown,
            )

            if result.get("error"):
                error_msg = result["error"]
                failed.append({
                    "question_index": idx,
                    "question": question,
                    "error": error_msg,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                print(f"  FAILED: {error_msg[:100]}")

                if "ConnectError" in error_msg or "not reachable" in error_msg.lower():
                    print("\nAPI is down — saving checkpoint and exiting.")
                    save_checkpoint(
                        run_id=run_id,
                        config={"testset": str(args.testset)},
                        samples=samples,
                        failed=failed,
                        total_questions=total,
                        completed_questions=idx,
                    )
                    return 1
            else:
                sample = _build_sample(question, result, patient_id)
                if sample:
                    samples.append(sample)
                    print(f"  OK ({len(result.get('sources', []))} sources)")
                else:
                    print("  WARN: no contexts returned")
        except Exception as e:
            failed.append({
                "question_index": idx,
                "question": question,
                "error": f"{type(e).__name__}: {e}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            print(f"  EXCEPTION: {type(e).__name__}: {e}")

        if should_checkpoint(len(samples), CONFIG.checkpoint_interval):
            save_checkpoint(
                run_id=run_id,
                config={"testset": str(args.testset)},
                samples=samples,
                failed=failed,
                total_questions=total,
                completed_questions=idx + 1,
            )

    if not samples:
        print("No samples collected — nothing to evaluate.")
        return 1

    # Score with RAGAS metrics
    print(f"\nScoring {len(samples)} samples with RAGAS v0.4...")
    faith = await evaluate_faithfulness(samples)
    relevancy = await evaluate_relevancy(samples)

    # Noise sensitivity (use first context from each sample as noise pool)
    noise_pool = []
    for s in samples:
        ctxs = s.get("retrieved_contexts") or s.get("contexts", [])
        if ctxs:
            noise_pool.append(ctxs[0])
    noise = await evaluate_noise_sensitivity(samples, noise_pool) if noise_pool else None

    summary: Dict[str, Any] = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {"testset": str(args.testset), "cooldown": cooldown},
        "progress": {
            "total_questions": total,
            "completed_questions": len(samples),
            "failed_questions": len(failed),
        },
        "metrics": {
            "faithfulness": {"score": faith["score"]},
            "relevancy": {"score": relevancy["score"]},
        },
        "failed": failed,
    }
    if noise:
        summary["metrics"]["noise_sensitivity"] = {
            "baseline_score": noise["baseline_score"],
            "noisy_score": noise["noisy_score"],
            "degradation": noise["degradation"],
        }

    suffix = f"_{args.output_id}" if args.output_id else ""
    results_path = Path(CONFIG.results_dir) / f"results{suffix}.json"
    report_path = Path(CONFIG.results_dir) / f"report{suffix}.md"
    write_json_report(summary, results_path)
    write_markdown_report(summary, samples, report_path)

    print(f"\nEvaluation complete!")
    print(f"  Faithfulness: {faith['score']:.3f}")
    print(f"  Relevancy:    {relevancy['score']:.3f}")
    if noise:
        print(f"  Noise degradation: {noise['degradation']:.3f}")
    print(f"  Results: {results_path}")
    print(f"  Report:  {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        raise SystemExit(1)
