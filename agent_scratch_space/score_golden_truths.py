#!/usr/bin/env python3
"""
Run RAGAS evaluation on the verified golden truths file.
Compares agent_answer against golden_answer in offline mode.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_correctness,
)

# Add repo root to path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Load environment
from dotenv import load_dotenv
load_dotenv(_REPO_ROOT / ".env")

# Try loading config
try:
    from POC_RAGAS.config import CONFIG
except ImportError:
    class ConfigMock:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        ragas_model = "gpt-4o-mini"
    CONFIG = ConfigMock()

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Metrics to use
METRICS = [
    faithfulness,
    answer_correctness,
]


def load_verified_data(file_path: Path) -> List[Dict]:
    """Load the verified golden truths dataset."""
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return []
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    valid_data = []
    skipped = 0
    for item in data:
        golden = item.get("golden_answer", "").strip()
        agent = item.get("agent_answer", "").strip()
        
        if not golden or golden == "No relevant records found in the patient's data.":
            skipped += 1
            print(f"Skipping Q[{item.get('question_index', '?')}]: No valid golden answer")
            continue
        
        if not agent:
            skipped += 1
            print(f"Skipping Q[{item.get('question_index', '?')}]: No agent answer")
            continue
        
        valid_data.append(item)
    
    print(f"Loaded {len(valid_data)} valid items. Skipped {skipped} items.")
    return valid_data


def main():
    parser = argparse.ArgumentParser(description="Score verified golden truths with RAGAS.")
    parser.add_argument(
        "--input", 
        type=Path, 
        default=Path("verified_golden_truths.json"), 
        help="Path to verified JSON"
    )
    args = parser.parse_args()
    
    input_path = args.input
    if not input_path.is_absolute():
        input_path = Path(__file__).parent / input_path
    
    print(f"Loading verified data from {input_path}...")
    encounters = load_verified_data(input_path)
    
    if not encounters:
        print("No data to score.")
        sys.exit(0)
    
    # Prepare RAGAS dataset
    # For this evaluation:
    # - question: the original question
    # - answer: the agent's answer (what we're evaluating)
    # - contexts: empty (we don't have retrieved contexts stored)
    # - ground_truth: the golden answer from DB extraction
    ragas_data = {
        "question": [e["question"] for e in encounters],
        "answer": [e["agent_answer"] for e in encounters],
        "contexts": [e.get("agent_contexts", ["N/A"]) for e in encounters],

        "ground_truth": [e["golden_answer"] for e in encounters]
    }
    
    dataset = Dataset.from_dict(ragas_data)
    
    # Configure LLM
    print("Configuring OpenAI models...")
    if not CONFIG.openai_api_key:
        print("Error: OPENAI_API_KEY not found!")
        sys.exit(1)
    
    llm_model = CONFIG.ragas_model or "gpt-4o-mini"
    llm = ChatOpenAI(model=llm_model, api_key=CONFIG.openai_api_key)
    embeddings = OpenAIEmbeddings(api_key=CONFIG.openai_api_key)
    
    print(f"Running RAGAS evaluation with {llm_model}...")
    print(f"Evaluating {len(encounters)} questions...")
    
    results = evaluate(
        dataset=dataset,
        metrics=METRICS,
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=False
    )
    
    print("\nEvaluation Complete!")
    print(results)
    
    # Save Report
    output_file = input_path.parent / "golden_truths_report.md"
    df = results.to_pandas()
    means = df.mean(numeric_only=True)
    
    with open(output_file, "w") as f:
        f.write(f"# Golden Truths Evaluation Report\n\n")
        f.write(f"**Date:** {datetime.now().isoformat()}\n")
        f.write(f"**Input File:** {input_path.name}\n")
        f.write(f"**Total Questions:** {len(df)}\n\n")
        
        f.write("## Aggregate Metrics\n")
        for metric, score in means.items():
            f.write(f"- **{metric}:** {score:.4f}\n")
        
        f.write("\n## Detailed Results\n")
        f.write(df.to_markdown(index=False))
    
    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    main()
