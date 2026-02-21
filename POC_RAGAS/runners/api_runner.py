"""API runner for agent endpoint with rate-limit awareness."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from POC_RAGAS.config import CONFIG
from POC_RAGAS.utils.service_manager import check_service_health


async def run_api_query(
    query: str,
    session_id: str,
    patient_id: Optional[str] = None,
    k_retrieve: Optional[int] = None,
    k_return: Optional[int] = None,
    cooldown: Optional[int] = None,
) -> Dict[str, Any]:
    payload = {
        "query": query,
        "session_id": session_id,
        "patient_id": patient_id,
        "k_retrieve": k_retrieve,
        "k_return": k_return,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    if not await check_service_health():
        return {
            "query": query,
            "response": "",
            "sources": [],
            "tool_calls": [],
            "validation_result": None,
            "raw": {},
            "error": f"ConnectError: Agent API service is not reachable at {CONFIG.agent_api_url}",
        }

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(CONFIG.agent_api_url, json=payload)

                # Handle rate limiting with backoff
                if response.status_code == 429:
                    if attempt < max_retries:
                        retry_after = int(response.headers.get("Retry-After", "15"))
                        print(f"  Rate limited (429). Waiting {retry_after}s before retry {attempt + 1}/{max_retries}...")
                        await asyncio.sleep(retry_after)
                        continue
                    return {
                        "query": query,
                        "response": "",
                        "sources": [],
                        "tool_calls": [],
                        "validation_result": None,
                        "raw": {},
                        "error": "RateLimited: 429 after max retries",
                    }

                response.raise_for_status()
                data = response.json()

            # Apply cooldown after successful request
            cd = cooldown if cooldown is not None else CONFIG.api_cooldown_seconds
            if cd > 0:
                await asyncio.sleep(cd)

            return {
                "query": data.get("query", query),
                "response": data.get("response", ""),
                "sources": data.get("sources", []),
                "tool_calls": data.get("tool_calls", []),
                "validation_result": data.get("validation_result"),
                "raw": data,
                "error": None,
            }
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            return {
                "query": query,
                "response": "",
                "sources": [],
                "tool_calls": [],
                "validation_result": None,
                "raw": {},
                "error": f"ConnectError: Cannot connect to agent API at {CONFIG.agent_api_url} - {e}",
            }
        except httpx.ReadTimeout as e:
            return {
                "query": query,
                "response": "",
                "sources": [],
                "tool_calls": [],
                "validation_result": None,
                "raw": {},
                "error": f"ReadTimeout: Request timed out after 120s - {e}",
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                print(f"\n[DEBUG] 422 Payload: {json.dumps(payload, indent=2)}")
                print(f"[DEBUG] 422 Response: {e.response.text}\n")
            return {
                "query": query,
                "response": "",
                "sources": [],
                "tool_calls": [],
                "validation_result": None,
                "raw": {},
                "error": f"HTTPStatusError: {e.response.status_code} - {e}",
            }
        except Exception as e:
            return {
                "query": query,
                "response": "",
                "sources": [],
                "tool_calls": [],
                "validation_result": None,
                "raw": {},
                "error": f"Error: {type(e).__name__} - {e}",
            }

    # Should not reach here, but just in case
    return {
        "query": query,
        "response": "",
        "sources": [],
        "tool_calls": [],
        "validation_result": None,
        "raw": {},
        "error": "Unexpected: exhausted retries",
    }
