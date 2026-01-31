
import argparse
import json
import os
import sys
from glob import glob
from pathlib import Path
from typing import List, Dict

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    faithfulness,
    context_precision,
    context_recall,
)

# Import local modules
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Load environment variables explicitly
from dotenv import load_dotenv, find_dotenv
print(f"DEBUG: Script location: {Path(__file__).resolve()}")
print(f"DEBUG: Calculated REPO_ROOT: {_REPO_ROOT}")
env_path = _REPO_ROOT / ".env"
print(f"DEBUG: Expected .env path: {env_path}, Exists: {env_path.exists()}")

if not load_dotenv(env_path):
    print("DEBUG: load_dotenv returned False (failed to load or empty)")
    # Try finding it automatically
    print("DEBUG: Trying find_dotenv...")
    load_dotenv(find_dotenv())

print(f"DEBUG: OPENAI_API_KEY present: {'OPENAI_API_KEY' in os.environ}")

# Attempt to load config - handle potential import errors if environment isn't perfect
try:
    from POC_RAGAS.config import CONFIG
except ImportError:
    # Fallback/Mock config if module structure is tricky in scratch space
    print("Warning: Could not import POC_RAGAS.config. Using raw environment variables.")
    class ConfigMock:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        ragas_model = "gpt-4o-mini"
    CONFIG = ConfigMock()

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Define metrics
METRICS = [
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
]

def load_batch_results(batch_dir: Path) -> List[Dict]:
    """Load all result_*.json files and use AGENT RESPONSE as GROUND TRUTH."""
    results = []
    pattern = str(batch_dir / "result_*.json")
    files = sorted(glob(pattern))
    
    if not files:
        print(f"No result files found in {batch_dir}")
        return []
        
    print(f"Found {len(files)} result files.")
    
    for fpath in files:
        try:
            with open(fpath, 'r') as f:
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
            
            # Extract basic fields
            question = data.get("question")
            
            # Extract contexts from sources
            contexts = []
            for src in sources:
                if isinstance(src, dict):
                    contexts.append(src.get("content_preview", ""))
                elif isinstance(src, str):
                    contexts.append(src)
            
            # FALLBACK: If sources are empty, try to use researcher_output from raw response
            # This is critical because the Agent API seems to be returning empty sources currently,
            # but the researcher clearly found data.
            if not contexts:
                raw_data = response_data.get("raw", {})
                researcher_out = raw_data.get("researcher_output")
                if researcher_out:
                    print(f"  > Warning: Empty sources for Q[{data.get('question_index')}]. Using 'researcher_output' as context proxy.")
                    contexts.append(researcher_out)

            # CLEANING: If contexts is empty or just ["N/A"], metrics like Context Recall will fail or score 0.
            # But the user wants to see the score.
            final_contexts = contexts if contexts else ["N/A"]

            # GOLDEN ANSWER LOGIC:
            # Use the agent's answer as the ground truth
            ground_truth = answer
            
            print(f"Processing Q[{data.get('question_index')}]: Setting Ground Truth = Agent Answer ({len(answer)} chars)")
            
            results.append({
                "question": question,
                "answer": answer,
                "contexts": final_contexts,
                "ground_truth": ground_truth 
            })
            
        except Exception as e:
            print(f"Error loading {fpath}: {e}")
            
    return results

def main():
    parser = argparse.ArgumentParser(description="Score RAGAS batch results with Golden Answers.")
    parser.add_argument("--batch-dir", type=Path, required=True, help="Directory containing result_*.json files")
    args = parser.parse_args()
    
    if not args.batch_dir.exists():
        print(f"Directory not found: {args.batch_dir}")
        sys.exit(1)
        
    print(f"Loading results from {args.batch_dir}...")
    raw_results = load_batch_results(args.batch_dir)
    
    if not raw_results:
        print("No valid successful results to score.")
        sys.exit(0)
        
    # Prepare dataset for RAGAS
    ragas_data = {
        "question": [r["question"] for r in raw_results],
        "answer": [r["answer"] for r in raw_results],
        "contexts": [r["contexts"] for r in raw_results],
        "ground_truth": [r["ground_truth"] for r in raw_results]
    }
    
    dataset = Dataset.from_dict(ragas_data)
    
    # Configure OpenAI LLM and Embeddings
    print("Configuring OpenAI models (gpt-4o-mini)...")
    if not CONFIG.openai_api_key:
        print("Error: OPENAI_API_KEY not found in environment!")
        sys.exit(1)
        
    llm_model = CONFIG.ragas_model or "gpt-4o-mini"
    
    # Initialize OpenAI components
    llm = ChatOpenAI(model=llm_model, api_key=CONFIG.openai_api_key)
    embeddings = OpenAIEmbeddings(api_key=CONFIG.openai_api_key)
    
    print(f"Running RAGAS evaluation with LLM={llm_model}...")
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
    output_file = args.batch_dir / "golden_report.md"
    df = results.to_pandas()
    
    # Calculate averages safely using pandas
    means = df.mean(numeric_only=True)
    
    with open(output_file, "w") as f:
        f.write(f"# Batch Evaluation Report (Golden Answer Experiment)\n\n")
        f.write(f"**Date:** {datetime.now().isoformat()}\n")
        f.write(f"**Total Questions Scored:** {len(df)}\n")
        f.write(f"**Note:** Ground Truth was set to the Agent's Answer for this run.\n\n")
        
        f.write("## Aggregate Metrics\n")
        for metric, score in means.items():
             f.write(f"- **{metric}:** {score:.4f}\n")
            
        f.write("\n## Detailed Results\n")
        f.write(df.to_markdown(index=False))
        
    print(f"\nReport saved to: {output_file}")

if __name__ == "__main__":
    from datetime import datetime
    main()
