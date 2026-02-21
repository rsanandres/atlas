"""Score batch evaluation results using RAGAS v0.4 metrics."""

import argparse
import json
import sys
from glob import glob
from pathlib import Path
from typing import Any, Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from POC_RAGAS.config import CONFIG
from POC_RAGAS.evaluators.faithfulness import evaluate_faithfulness
from POC_RAGAS.evaluators.relevancy import evaluate_relevancy


def load_batch_results(batch_dir: Path) -> List[Dict[str, Any]]:
    """Load all result_*.json files from the directory."""
    pattern = str(batch_dir / "result_*.json")
    files = sorted(glob(pattern))

    if not files:
        print(f"No result files found in {batch_dir}")
        return []

    print(f"Found {len(files)} result files.")
    results: List[Dict[str, Any]] = []

    for fpath in files:
        try:
            with open(fpath) as f:
                data = json.load(f)

            if data.get("status") != "success":
                continue

            response_data = data.get("response", {})
            if isinstance(response_data, str):
                answer = response_data
                sources = []
            else:
                answer = response_data.get("response", "")
                sources = response_data.get("sources", [])

            question = data.get("question") or data.get("user_input", "")

            contexts = []
            for src in sources:
                if isinstance(src, dict):
                    contexts.append(src.get("content_preview", ""))
                elif isinstance(src, str):
                    contexts.append(src)

            results.append({
                "user_input": question,
                "response": answer,
                "retrieved_contexts": contexts if contexts else ["N/A"],
            })
        except Exception as e:
            print(f"Error loading {fpath}: {e}")

    return results


async def main() -> None:
    parser = argparse.ArgumentParser(description="Score RAGAS batch results.")
    parser.add_argument("--batch-dir", type=Path, required=True, help="Directory containing result_*.json files")
    args = parser.parse_args()

    if not args.batch_dir.exists():
        print(f"Directory not found: {args.batch_dir}")
        sys.exit(1)

    print(f"Loading results from {args.batch_dir}...")
    samples = load_batch_results(args.batch_dir)

    if not samples:
        print("No valid successful results to score.")
        sys.exit(0)

    if not CONFIG.openai_api_key:
        print("Error: OPENAI_API_KEY not found in environment!")
        sys.exit(1)

    print(f"Scoring {len(samples)} samples with RAGAS v0.4 (model: {CONFIG.ragas_model})...")
    faith = await evaluate_faithfulness(samples)
    relevancy = await evaluate_relevancy(samples)

    print(f"\nFaithfulness:  {faith['score']:.4f}")
    print(f"Relevancy:     {relevancy['score']:.4f}")

    # Write report
    from datetime import datetime, timezone

    output_file = args.batch_dir / "report.md"
    with open(output_file, "w") as f:
        f.write("# Batch Evaluation Report\n\n")
        f.write(f"**Date:** {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"**Model:** {CONFIG.ragas_model}\n")
        f.write(f"**Total Questions Scored:** {len(samples)}\n\n")
        f.write("## Metrics\n\n")
        f.write(f"| Metric | Score |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Faithfulness | {faith['score']:.4f} |\n")
        f.write(f"| Relevancy | {relevancy['score']:.4f} |\n")

        if faith.get("per_sample"):
            f.write("\n## Per-Sample Faithfulness\n\n")
            f.write("| # | Score | Question |\n")
            f.write("|---|-------|----------|\n")
            for i, ps in enumerate(faith["per_sample"]):
                q = samples[i]["user_input"][:60]
                f.write(f"| {i} | {ps['score']:.3f} | {q}... |\n")

    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
