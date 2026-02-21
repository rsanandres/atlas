"""Health checks for the production API."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from POC_RAGAS.config import CONFIG


async def check_http(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            return response.status_code == 200
    except Exception:
        return False


async def main() -> int:
    base_url = CONFIG.agent_api_url.replace("/agent/query", "")
    agent_health = await check_http(f"{base_url}/agent/health")

    print(f"API URL:        {CONFIG.agent_api_url}")
    print(f"Agent health:   {'OK' if agent_health else 'FAILED'}")
    print(f"RAGAS model:    {CONFIG.ragas_model}")
    print(f"API cooldown:   {CONFIG.api_cooldown_seconds}s")
    print(f"OpenAI key set: {'yes' if CONFIG.openai_api_key else 'NO'}")
    return 0 if agent_health else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
