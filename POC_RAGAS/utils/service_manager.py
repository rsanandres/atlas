"""Service health checks for the production API."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from POC_RAGAS.config import CONFIG


async def check_service_health(url: str = None, timeout: float = 10.0) -> bool:
    """Check if agent API service is responding to health checks."""
    if url is None:
        health_url = CONFIG.agent_api_url.replace("/agent/query", "/agent/health")
    else:
        health_url = url

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(health_url)
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "ok"
            return False
    except Exception:
        return False
