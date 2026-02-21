"""Faithfulness evaluation using RAGAS v0.4."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List

from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import Faithfulness

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from POC_RAGAS.config import CONFIG


def _build_scorer() -> Faithfulness:
    if not CONFIG.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for faithfulness evaluation.")
    client = AsyncOpenAI(api_key=CONFIG.openai_api_key)
    llm = llm_factory(CONFIG.ragas_model, client=client, max_tokens=16384)
    return Faithfulness(llm=llm)


async def _score_sample(
    scorer: Faithfulness, sample: Dict[str, Any]
) -> Dict[str, Any]:
    question = sample.get("user_input") or sample.get("question", "")
    response = sample.get("response") or sample.get("answer", "")
    contexts = sample.get("retrieved_contexts") or sample.get("contexts", [])
    result = await scorer.ascore(
        user_input=question,
        response=response,
        retrieved_contexts=contexts,
    )
    return {"score": result.value, "reason": getattr(result, "reason", None)}


async def _evaluate_faithfulness_async(
    samples: List[Dict[str, Any]],
) -> Dict[str, Any]:
    scorer = _build_scorer()
    per_sample: List[Dict[str, Any]] = []
    for sample in samples:
        result = await _score_sample(scorer, sample)
        per_sample.append(result)
    scores = [r["score"] for r in per_sample if r["score"] is not None]
    avg = sum(scores) / len(scores) if scores else 0.0
    return {"score": avg, "per_sample": per_sample}


async def evaluate_faithfulness(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate faithfulness of responses against retrieved contexts."""
    return await _evaluate_faithfulness_async(samples)
