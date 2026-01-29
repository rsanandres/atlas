"""API runner for agent endpoint."""

from __future__ import annotations

import sys
import json
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
) -> Dict[str, Any]:
    payload = {
        "query": query,
        "session_id": session_id,
        "patient_id": patient_id,
        "k_retrieve": k_retrieve,
        "k_return": k_return,
    }
    # Remove None values to avoid Pydantic/FastAPI validation issues
    payload = {k: v for k, v in payload.items() if v is not None}
    # Health check before request
    if not await check_service_health():
        return {
            "query": query,
            "response": "",
            "sources": [],
            "tool_calls": [],
            "validation_result": None,
            "raw": {},
            "error": "ConnectError: Agent API service is not running. Please start it manually: uvicorn api.main:app --port 8000",
        }
    
    # Single attempt - no retries, no restarts
    try:
        async with httpx.AsyncClient(timeout=1800.0) as client:
            response = await client.post(CONFIG.agent_api_url, json=payload)
            response.raise_for_status()
            data = response.json()
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
            "error": f"ConnectError: Cannot connect to agent API at {CONFIG.agent_api_url} - {str(e)}. Service is down.",
        }
    except httpx.ReadTimeout as e:
        return {
            "query": query,
            "response": "",
            "sources": [],
            "tool_calls": [],
            "validation_result": None,
            "raw": {},
            "error": f"ReadTimeout: Request timed out after 300s - {str(e)}",
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
            "error": f"HTTPStatusError: {e.response.status_code} - {str(e)}",
        }
    except Exception as e:
        # For other exceptions, return error
        return {
            "query": query,
            "response": "",
            "sources": [],
            "tool_calls": [],
            "validation_result": None,
            "raw": {},
            "error": f"Error: {type(e).__name__} - {str(e)}",
        }
