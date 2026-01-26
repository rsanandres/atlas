"""FastAPI router for agent endpoints."""

from __future__ import annotations

import os
import json
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.agent.graph import get_agent
from api.agent.models import AgentDocument, AgentQueryRequest, AgentQueryResponse
from api.agent.guardrails.validators import setup_guard
from api.agent.mcp.langsmith_config import configure_langsmith_tracing
from api.agent.pii_masker.factory import create_pii_masker
from api.session.store_dynamodb import build_store_from_env

router = APIRouter()

# Initialize singletons
_pii_masker = create_pii_masker()
_guard = setup_guard()
try:
    configure_langsmith_tracing()
except Exception:
    # Tracing is optional in local/dev environments.
    pass


def _build_sources(source_items: List[Dict[str, Any]]) -> List[AgentDocument]:
    sources: List[AgentDocument] = []
    for item in source_items:
        sources.append(
            AgentDocument(
                doc_id=item.get("doc_id", ""),
                content_preview=item.get("content_preview", ""),
                metadata=item.get("metadata", {}),
            )
        )
    return sources


def _guard_output(text: str) -> str:
    if _guard is None:
        return text
    try:
        result = _guard.validate(text)
        if hasattr(result, "validated_output"):
            return result.validated_output
        if isinstance(result, dict) and "validated_output" in result:
            return str(result["validated_output"])
    except Exception:
        return text
    return text


@router.post("/query", response_model=AgentQueryResponse)
async def query_agent(payload: AgentQueryRequest) -> AgentQueryResponse:
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query is required.")

    try:
        masked_query, _ = _pii_masker.mask_pii(payload.query)

        store = build_store_from_env()
        agent = get_agent()
        max_iterations = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))
        state = {
            "query": masked_query,
            "session_id": payload.session_id,
            "patient_id": payload.patient_id,
            "k_retrieve": payload.k_retrieve,
            "k_return": payload.k_return,
            "iteration_count": 0,
        }
        result = await agent.ainvoke(state, config={"recursion_limit": max_iterations})

        response_text = result.get("final_response") or result.get("researcher_output", "")

        response_text = _guard_output(response_text)
        response_text, _ = _pii_masker.mask_pii(response_text)

        tool_calls = result.get("tools_called", [])
        sources = _build_sources(result.get("sources", []))

        try:
            store.append_turn(payload.session_id, role="user", text=masked_query, meta={"masked": True})
            store.append_turn(
                payload.session_id,
                role="assistant",
                text=response_text,
                meta={
                    "tool_calls": tool_calls,
                    "sources": [{"doc_id": s.doc_id, "content_preview": s.content_preview, "metadata": s.metadata} for s in sources],
                    "researcher_output": result.get("researcher_output"),
                    "validator_output": result.get("validator_output"),
                    "validation_result": result.get("validation_result"),
                }
            )
        except Exception as store_error:
            # Log store errors but don't fail the request
            print(f"Warning: Failed to store session turn: {store_error}")

        return AgentQueryResponse(
            query=payload.query,
            response=response_text,
            sources=sources,
            tool_calls=tool_calls,
            session_id=payload.session_id,
            validation_result=result.get("validation_result"),
            researcher_output=result.get("researcher_output"),
            validator_output=result.get("validator_output"),
            iteration_count=result.get("iteration_count"),
        )
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in agent query: {type(e).__name__}: {str(e)}")
        print(f"Traceback: {error_details}")
        
        # Return a 500 with error details instead of crashing
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {type(e).__name__}: {str(e)}"
        )


@router.post("/query/stream")
async def query_agent_stream(payload: AgentQueryRequest):
    """Stream agent execution progress using Server-Sent Events."""
    
    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'start', 'message': 'Starting agent...'})}\n\n"
            
            masked_query, _ = _pii_masker.mask_pii(payload.query)
            
            store = build_store_from_env()
            agent = get_agent()
            max_iterations = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))
            
            state = {
                "query": masked_query,
                "session_id": payload.session_id,
                "patient_id": payload.patient_id,
                "k_retrieve": payload.k_retrieve,
                "k_return": payload.k_return,
                "iteration_count": 0,
            }
            
            yield f"data: {json.dumps({'type': 'status', 'message': '🔍 Researcher agent thinking...'})}\n\n"
            
            # Stream events from LangGraph
            async for event in agent.astream_events(state, config={"recursion_limit": max_iterations}, version="v1"):
                event_type = event.get("event")
                
                # Track node transitions
                if event_type == "on_chain_start":
                    name = event.get("name", "")
                    if "researcher" in name.lower():
                        yield f"data: {json.dumps({'type': 'status', 'message': '🔍 Researcher agent working...'})}\n\n"
                    elif "validator" in name.lower():
                        yield f"data: {json.dumps({'type': 'status', 'message': '✓ Validator reviewing...'})}\n\n"
                
                # Track tool calls
                elif event_type == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    yield f"data: {json.dumps({'type': 'tool', 'tool': tool_name, 'message': f'🔧 Tool: {tool_name}'})}\n\n"
                
                # Track LLM responses
                elif event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk", {})
                    if hasattr(chunk, "content") and chunk.content:
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk.content})}\n\n"
            
            # Get final result
            result = await agent.ainvoke(state, config={"recursion_limit": max_iterations})
            
            response_text = result.get("final_response") or result.get("researcher_output", "")
            response_text = _guard_output(response_text)
            response_text, _ = _pii_masker.mask_pii(response_text)
            
            tool_calls = result.get("tools_called", [])
            sources = _build_sources(result.get("sources", []))
            
            # Store in session
            try:
                store.append_turn(payload.session_id, role="user", text=masked_query, meta={"masked": True})
                store.append_turn(
                    payload.session_id,
                    role="assistant",
                    text=response_text,
                    meta={
                        "tool_calls": tool_calls,
                        "sources": [{"doc_id": s.doc_id, "content_preview": s.content_preview, "metadata": s.metadata} for s in sources],
                        "researcher_output": result.get("researcher_output"),
                        "validator_output": result.get("validator_output"),
                        "validation_result": result.get("validation_result"),
                    }
                )
            except Exception as store_error:
                print(f"Warning: Failed to store session turn: {store_error}")
            
            # Send final response
            final_data = {
                "type": "complete",
                "response": response_text,
                "researcher_output": result.get("researcher_output"),
                "validator_output": result.get("validator_output"),
                "validation_result": result.get("validation_result"),
                "tool_calls": tool_calls,
                "sources": [{"doc_id": s.doc_id, "content_preview": s.content_preview} for s in sources],
                "iteration_count": result.get("iteration_count"),
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in streaming agent query: {type(e).__name__}: {str(e)}")
            print(f"Traceback: {error_details}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}
