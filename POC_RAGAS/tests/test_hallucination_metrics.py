"""Evaluate hallucination metrics for agent responses (API mode only)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

import httpx
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from POC_RAGAS.config import CONFIG
from POC_RAGAS.evaluators.faithfulness import evaluate_faithfulness
from POC_RAGAS.evaluators.noise_sensitivity import evaluate_noise_sensitivity
from POC_RAGAS.evaluators.relevancy import evaluate_relevancy
from POC_RAGAS.runners.api_runner import run_api_query

# Richest patient in the dataset (317 chunks, 9 resource types)
TEST_PATIENT_ID = "3e80196f-06df-4568-a5e5-480b742b8639"


async def _check_api_health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(CONFIG.agent_api_url.replace("/agent/query", "/agent/health"))
            return resp.status_code == 200
    except Exception:
        return False


def _extract_contexts(sources: List[Dict[str, Any]]) -> List[str]:
    contexts = []
    for item in sources:
        if isinstance(item, dict):
            contexts.append(item.get("content_preview") or item.get("content") or "")
        else:
            contexts.append(str(item))
    return [ctx for ctx in contexts if ctx]


@pytest.mark.asyncio
async def test_hallucination_metrics(ragas_min_thresholds):
    if not CONFIG.openai_api_key:
        pytest.skip("OPENAI_API_KEY not configured.")

    if not await _check_api_health():
        pytest.skip("Agent API is not reachable.")

    query = "What is the birth date of patient 3e80196f-06df-4568-a5e5-480b742b8639?"
    result = await run_api_query(
        query=query,
        session_id="ragas-test-api",
        patient_id=TEST_PATIENT_ID,
    )

    if result.get("error"):
        pytest.skip(f"API returned error: {result['error']}")

    contexts = _extract_contexts(result.get("sources", []))
    if not contexts:
        pytest.skip("No contexts found for evaluation.")

    samples = [
        {
            "user_input": query,
            "response": result.get("response", ""),
            "retrieved_contexts": contexts,
            "patient_id": TEST_PATIENT_ID,
        }
    ]

    faith = await evaluate_faithfulness(samples)
    relevancy = await evaluate_relevancy(samples)

    # Use contexts as noise pool
    noise = await evaluate_noise_sensitivity(samples, contexts)

    assert 0.0 <= faith["score"] <= 1.0
    assert 0.0 <= relevancy["score"] <= 1.0
    assert 0.0 <= noise["baseline_score"] <= 1.0

    assert faith["score"] >= ragas_min_thresholds["faithfulness"]
    assert relevancy["score"] >= ragas_min_thresholds["relevancy"]
    assert noise["degradation"] <= ragas_min_thresholds["noise_degradation"]
