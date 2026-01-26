"""
Integration tests for conversational flow in the multi-agent graph.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from langchain_core.messages import AIMessage
from POC_agent.agent.multi_agent_graph import create_multi_agent_graph, AgentState

@pytest.fixture
def graph():
    return create_multi_agent_graph()

@pytest.mark.asyncio
async def test_conversational_greeting_flow(graph):
    """Test that greetings are routed to conversational responder and skip validation."""
    initial_state = {
        "query": "Hello there",
        "session_id": "test-greeting",
        "iteration_count": 0,
    }
    
    # Mock get_llm to return a mock LLM that returns a friendly response
    with patch("POC_agent.agent.multi_agent_graph.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        # Use real AIMessage
        mock_msg = AIMessage(content="Hello! I am a medical AI assistant. How can I help you?")
        # Make ainvoke an AsyncMock
        mock_llm.ainvoke = AsyncMock(return_value=mock_msg)
        mock_get_llm.return_value = mock_llm
        
        result = await graph.ainvoke(initial_state)
        
        # Verify Classification
        assert result["query_type"] == "conversational"
        assert result["classification_method"] == "keyword"
        
        # Verify Output
        assert result["final_response"] == "Hello! I am a medical AI assistant. How can I help you?"
        
        # Verify Routing
        assert result["validation_result"] == "PASS"

@pytest.mark.asyncio
async def test_identity_question_flow(graph):
    """Test identity question routing."""
    initial_state = {
        "query": "Who are you?",
        "session_id": "test-identity",
        "iteration_count": 0,
    }
    
    with patch("POC_agent.agent.multi_agent_graph.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_msg = AIMessage(content="I am a medical AI assistant.")
        mock_llm.ainvoke = AsyncMock(return_value=mock_msg)
        mock_get_llm.return_value = mock_llm
        
        result = await graph.ainvoke(initial_state)
        
        assert result["query_type"] == "conversational"
        assert result["validation_result"] == "PASS"
        assert "assistant" in result["final_response"].lower()

@pytest.mark.asyncio
async def test_mixed_query_routing(graph):
    """Test mixed query routes to medical but acknowledges greeting."""
    # Current logic: Mixed -> routes to researcher (medical path) via _route_after_classification
    # But classification result should have should_acknowledge_greeting=True
    
    initial_state = {
        "query": "Hello, what is the dosage for Aspirin?",
        "session_id": "test-mixed",
        "iteration_count": 0,
    }
    
    with patch("POC_agent.agent.multi_agent_graph._get_researcher_agent") as mock_get_researcher:
        # Mock researcher to return a dummy response immediately
        mock_agent = MagicMock()
        # Return dict as expected by _extract_response_text
        mock_agent.ainvoke = AsyncMock(return_value={"messages": [AIMessage(content="Research result")]})
        mock_get_researcher.return_value = mock_agent
        
        result = await graph.ainvoke(initial_state)
        
        assert result.get("query_type") == "mixed"
        assert result.get("should_acknowledge_greeting") is True
        # It should have gone to researcher
        assert result.get("researcher_output") == "Research result" 
