"""Integration test for reranker + ReAct agent + tools."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import requests
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from POC_agent.agent.graph import get_agent
from POC_agent.agent.tools import (
    calculate,
    cross_reference_meds,
    get_current_date,
    get_patient_timeline,
    get_session_context,
    search_clinical_notes,
)


DEFAULT_RERANKER_URL = "http://localhost:8001/rerank"
MAX_AGENT_STEPS = 5

TOOL_REGISTRY = {
    search_clinical_notes.name: search_clinical_notes,
    get_patient_timeline.name: get_patient_timeline,
    cross_reference_meds.name: cross_reference_meds,
    get_session_context.name: get_session_context,
    calculate.name: calculate,
    get_current_date.name: get_current_date,
}


def test_reranker_service(query: str) -> List[dict]:
    payload = {"query": query, "k_retrieve": 10, "k_return": 5}
    response = requests.post(DEFAULT_RERANKER_URL, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])
    print(f"[RERANKER] Returned {len(results)} documents")
    for idx, doc in enumerate(results, start=1):
        preview = doc.get("content", "")[:120].replace("\n", " ")
        print(f"  {idx}. {doc.get('id')} | {preview}")
    return results


def _extract_tool_calls(message: AIMessage) -> List[Dict[str, Any]]:
    tool_calls = []
    if getattr(message, "tool_calls", None):
        tool_calls.extend(message.tool_calls)
    additional = getattr(message, "additional_kwargs", {}) or {}
    if additional.get("tool_calls"):
        tool_calls.extend(additional["tool_calls"])

    if not tool_calls:
        content = getattr(message, "content", "") or ""
        match = re.search(r"```json\s*(\{.*?\})\s*```", content, flags=re.DOTALL)
        raw = match.group(1) if match else content.strip()
        if raw.startswith("{") and raw.endswith("}"):
            try:
                tool_calls.append(json.loads(raw))
            except json.JSONDecodeError:
                pass

    return tool_calls


def _normalize_tool_call(tool_call: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if "function" in tool_call:
        func = tool_call.get("function") or {}
        name = func.get("name")
        arguments = func.get("arguments")
        tool_call_id = tool_call.get("id")
    else:
        name = tool_call.get("name")
        arguments = tool_call.get("arguments") or tool_call.get("args")
        tool_call_id = tool_call.get("id") or name

    if not name:
        return None

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {"input": arguments}

    if arguments is None:
        arguments = {}

    return {"id": tool_call_id or name, "name": name, "arguments": arguments}


def _run_tool_call(tool_call: Dict[str, Any]) -> Optional[ToolMessage]:
    normalized = _normalize_tool_call(tool_call)
    if not normalized:
        return None

    tool = TOOL_REGISTRY.get(normalized["name"])
    if not tool:
        return ToolMessage(content=f"Unknown tool: {normalized['name']}", name=normalized["name"], tool_call_id=normalized["id"])

    result = tool.invoke(normalized["arguments"])
    payload = json.dumps(result, ensure_ascii=True, default=str)
    return ToolMessage(content=payload, name=normalized["name"], tool_call_id=normalized["id"])


def _last_ai_message(messages: Sequence[Any]) -> Optional[AIMessage]:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message
    return None


def test_agent_with_tools(query: str) -> Any:
    agent = get_agent()
    messages: List[Any] = [HumanMessage(content=query)]

    for step in range(1, MAX_AGENT_STEPS + 1):
        result = agent.invoke({"messages": messages}, config={"recursion_limit": 10})
        messages = result.get("messages", messages)
        last_ai = _last_ai_message(messages)
        if not last_ai:
            break

        tool_calls = _extract_tool_calls(last_ai)
        if not tool_calls:
            print(f"[AGENT] Step {step}: no tool calls; stopping.")
            break

        print(f"[AGENT] Step {step}: executing {len(tool_calls)} tool call(s).")
        for tool_call in tool_calls:
            tool_message = _run_tool_call(tool_call)
            if tool_message:
                messages.append(tool_message)

    tool_call_names = [msg.name for msg in messages if isinstance(msg, ToolMessage)]
    print(f"[AGENT] Tool calls: {tool_call_names}")
    if messages:
        last = messages[-1]
        print(f"[AGENT] Response: {getattr(last, 'content', str(last))[:500]}")
    return {"messages": messages}


def test_full_workflow(query: str) -> None:
    print("\n[WORKFLOW] Testing reranker first...")
    test_reranker_service(query)

    print("\n[WORKFLOW] Testing agent tool usage...")
    test_agent_with_tools(query)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python POC_agent/test_agent_integration.py \"your query here\"")
        return 1
    query = sys.argv[1]
    test_full_workflow(query)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
