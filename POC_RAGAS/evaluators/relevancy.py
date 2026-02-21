"""Response relevancy evaluation using RAGAS v0.4."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List

from openai import AsyncOpenAI
from ragas.embeddings import OpenAIEmbeddings
from ragas.llms import llm_factory
from ragas.metrics.collections import AnswerRelevancy

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from POC_RAGAS.config import CONFIG


def _build_scorer() -> AnswerRelevancy:
    if not CONFIG.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for relevancy evaluation.")
    client = AsyncOpenAI(api_key=CONFIG.openai_api_key)
    llm = llm_factory(CONFIG.ragas_model, client=client, max_tokens=16384)
    embeddings = OpenAIEmbeddings(
        client=client,
        model="text-embedding-3-small",
    )
    return AnswerRelevancy(llm=llm, embeddings=embeddings)


async def _score_sample(
    scorer: AnswerRelevancy, sample: Dict[str, Any]
) -> Dict[str, Any]:
    question = sample.get("user_input") or sample.get("question", "")
    response = sample.get("response") or sample.get("answer", "")
    result = await scorer.ascore(
        user_input=question,
        response=response,
    )
    return {"score": result.value, "reason": getattr(result, "reason", None)}


async def _evaluate_relevancy_async(
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


async def evaluate_relevancy(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate relevancy of responses to user questions."""
    return await _evaluate_relevancy_async(samples)
