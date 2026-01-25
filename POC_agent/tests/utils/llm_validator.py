"""LLM-based validation of prompt clarity and tool understanding."""

from __future__ import annotations

from typing import Any, Dict, List

from POC_agent.agent.config import get_llm
from POC_agent.agent.prompt_loader import get_researcher_prompt, get_validator_prompt
from POC_agent.tests.utils.prompt_validator import TOOL_MAP


async def ask_llm_about_tools(prompt_text: str, question: str) -> str:
    """Ask LLM a question about tools based on prompt."""
    llm = get_llm()
    
    full_prompt = f"""{prompt_text}

Based on the prompt above, answer this question:
{question}

Provide a clear, concise answer."""
    
    try:
        response = await llm.ainvoke(full_prompt)
        if hasattr(response, "content"):
            return response.content
        return str(response)
    except Exception as e:
        return f"Error: {str(e)}"


async def validate_tool_discovery() -> Dict[str, Any]:
    """Test if LLM can identify all available tools from prompt."""
    researcher_prompt = get_researcher_prompt()
    validator_prompt = get_validator_prompt()
    
    question = "List all the tools available to you. Provide only the tool names, one per line."
    
    researcher_response = await ask_llm_about_tools(researcher_prompt, question)
    validator_response = await ask_llm_about_tools(validator_prompt, question)
    
    # Extract tool names from responses (simple parsing)
    def extract_tool_names(text: str) -> List[str]:
        tools = []
        lines = text.lower().split("\n")
        for line in lines:
            line = line.strip()
            # Remove numbering, bullets, etc.
            line = line.lstrip("0123456789.-) ")
            # Check if it matches a tool name
            for tool_name in TOOL_MAP.keys():
                if tool_name.lower() in line or line in tool_name.lower():
                    if tool_name not in tools:
                        tools.append(tool_name)
        return tools
    
    researcher_tools = extract_tool_names(researcher_response)
    validator_tools = extract_tool_names(validator_response)
    
    # Calculate accuracy
    all_tools = set(TOOL_MAP.keys())
    researcher_accuracy = len(set(researcher_tools) & all_tools) / len(all_tools) if all_tools else 0
    validator_accuracy = len(set(validator_tools) & all_tools) / len(all_tools) if all_tools else 0
    
    return {
        "researcher_response": researcher_response,
        "validator_response": validator_response,
        "researcher_tools_identified": researcher_tools,
        "validator_tools_identified": validator_tools,
        "researcher_accuracy": researcher_accuracy,
        "validator_accuracy": validator_accuracy,
        "all_tools": list(all_tools),
    }


async def validate_tool_selection(query: str, expected_tools: List[str]) -> Dict[str, Any]:
    """Test if LLM selects correct tools for a given query."""
    researcher_prompt = get_researcher_prompt()
    
    question = f"""Given this user query: "{query}"

Which tool(s) would you use to answer this query? List the tool names only."""
    
    response = await ask_llm_about_tools(researcher_prompt, question)
    
    # Extract tool names from response
    identified_tools = []
    response_lower = response.lower()
    for tool_name in TOOL_MAP.keys():
        if tool_name.lower() in response_lower:
            identified_tools.append(tool_name)
    
    # Check if expected tools are identified
    expected_found = [t for t in expected_tools if t in identified_tools]
    accuracy = len(expected_found) / len(expected_tools) if expected_tools else 0
    
    return {
        "query": query,
        "expected_tools": expected_tools,
        "identified_tools": identified_tools,
        "expected_found": expected_found,
        "accuracy": accuracy,
        "response": response,
    }


async def validate_tool_parameter_understanding(tool_name: str) -> Dict[str, Any]:
    """Test if LLM understands tool parameters."""
    if tool_name not in TOOL_MAP:
        return {"error": f"Tool {tool_name} not found"}
    
    researcher_prompt = get_researcher_prompt()
    
    question = f"""What parameters does the tool "{tool_name}" require? List the parameter names."""
    
    response = await ask_llm_about_tools(researcher_prompt, question)
    
    # Get actual parameters from tool
    from POC_agent.tests.utils.prompt_validator import get_tool_signature
    tool_obj = TOOL_MAP[tool_name]
    actual_params = get_tool_signature(tool_obj)
    actual_param_names = set(actual_params.keys())
    
    # Extract parameter names from response
    identified_params = []
    response_lower = response.lower()
    for param_name in actual_param_names:
        if param_name.lower() in response_lower:
            identified_params.append(param_name)
    
    accuracy = len(identified_params) / len(actual_param_names) if actual_param_names else 0
    
    return {
        "tool": tool_name,
        "actual_parameters": list(actual_param_names),
        "identified_parameters": identified_params,
        "accuracy": accuracy,
        "response": response,
    }


async def get_llm_validation_summary(test_queries: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get comprehensive LLM validation summary."""
    tool_discovery = await validate_tool_discovery()
    
    tool_selection_results = []
    if test_queries:
        for query_info in test_queries[:5]:  # Test first 5 queries
            query = query_info.get("query", "")
            expected_tools = query_info.get("expected_tools", [])
            if query and expected_tools:
                result = await validate_tool_selection(query, expected_tools)
                tool_selection_results.append(result)
    
    # Test parameter understanding for a few key tools
    key_tools = ["calculate_bmi", "search_patient_records", "validate_dosage"]
    parameter_results = []
    for tool_name in key_tools:
        if tool_name in TOOL_MAP:
            result = await validate_tool_parameter_understanding(tool_name)
            parameter_results.append(result)
    
    return {
        "tool_discovery": tool_discovery,
        "tool_selection": tool_selection_results,
        "parameter_understanding": parameter_results,
        "overall_accuracy": (
            tool_discovery.get("researcher_accuracy", 0) +
            tool_discovery.get("validator_accuracy", 0)
        ) / 2 if tool_discovery else 0,
    }
