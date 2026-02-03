#!/usr/bin/env python3
"""Quick RAGAS scoring for the 9 working questions"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_correctness
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
import os

# Load data
with open(Path(__file__).parent / "golden_testset_candidate.json", 'r') as f:
    data = json.load(f)

# Filter out the failed question (index 6, the BMI one)
valid_items = []
for i, item in enumerate(data):
    if item['agent_answer'].startswith('ERROR'):
        print(f"Skipping Q[{i}]: {item['question'][:60]}... (ERROR)")
        continue
    if not item.get('original_reference'):
        print(f"Skipping Q[{i}]: No reference answer")
        continue
    valid_items.append(item)

print(f"\nScoring {len(valid_items)} questions...")

# Prepare RAGAS dataset
ragas_data = {
    "question": [item["question"] for item in valid_items],
    "answer": [item["agent_answer"] for item in valid_items],
    "contexts": [item.get("agent_contexts", ["N/A"]) for item in valid_items],
    "ground_truth": [item["original_reference"] for item in valid_items]
}

dataset = Dataset.from_dict(ragas_data)

# Run RAGAS
api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key)
embeddings = OpenAIEmbeddings(api_key=api_key)

print("Running RAGAS evaluation...")
results = evaluate(
    dataset=dataset,
    metrics=[faithfulness, answer_correctness],
    llm=llm,
    embeddings=embeddings,
    raise_exceptions=False
)

print("\n" + "="*60)
print("EVALUATION COMPLETE!")
print("="*60)
print(results)

# Save report
df = results.to_pandas()
output_file = Path(__file__).parent / "ragas_report_9q.md"
with open(output_file, "w") as f:
    f.write(f"# RAGAS Evaluation Report (9 Working Questions)\n\n")
    f.write(f"**Date:** {datetime.now().isoformat()}\n")
    f.write(f"**Questions Evaluated:** {len(df)}\n\n")
    f.write("## Aggregate Metrics\n")
    for metric, score in df.mean(numeric_only=True).items():
        f.write(f"- **{metric}:** {score:.4f}\n")
    f.write("\n## Detailed Results\n")
    f.write(df.to_markdown(index=False))

print(f"\n✓ Report saved to: {output_file}")
