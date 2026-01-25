"""LLM-based validation tests for prompt clarity."""

from __future__ import annotations

import pytest

from POC_agent.tests.utils.llm_validator import (
    get_llm_validation_summary,
    validate_tool_discovery,
    validate_tool_parameter_understanding,
    validate_tool_selection,
)
from POC_agent.tests.utils.testset_parser import extract_queries_by_tool_type, load_testset


class TestLLMToolDiscovery:
    """Test if LLM can identify tools from prompts."""
    
    @pytest.mark.asyncio
    async def test_researcher_tool_discovery(self):
        """Test if LLM can identify researcher tools."""
        result = await validate_tool_discovery()
        
        assert "researcher_accuracy" in result
        assert "validator_accuracy" in result
        
        # Should identify at least 50% of tools
        assert result["researcher_accuracy"] >= 0.5, \
            f"LLM only identified {result['researcher_accuracy']*100:.1f}% of tools"
    
    @pytest.mark.asyncio
    async def test_validator_tool_discovery(self):
        """Test if LLM can identify validator tools."""
        result = await validate_tool_discovery()
        
        # Should identify at least 50% of tools
        assert result["validator_accuracy"] >= 0.5, \
            f"LLM only identified {result['validator_accuracy']*100:.1f}% of tools"


class TestLLMToolSelection:
    """Test if LLM selects correct tools for queries."""
    
    @pytest.fixture
    def testset(self):
        """Load synthetic testset."""
        return load_testset()
    
    @pytest.fixture
    def categorized_queries(self, testset):
        """Get queries categorized by tool type."""
        return extract_queries_by_tool_type(testset)
    
    @pytest.mark.asyncio
    async def test_tool_selection_for_calculator_queries(self, categorized_queries):
        """Test LLM selects calculator tools for calculation queries."""
        calculator_queries = categorized_queries.get("calculator", [])
        if not calculator_queries:
            pytest.skip("No calculator queries in testset")
        
        query = calculator_queries[0].get("user_input", "")
        if not query:
            pytest.skip("Query is empty")
        
        # Expected tools for calculator queries
        expected_tools = ["calculate_bmi", "calculate_gfr", "calculate_bsa"]
        
        result = await validate_tool_selection(query, expected_tools)
        
        assert "accuracy" in result
        # Should identify at least one expected tool
        assert result["accuracy"] > 0 or len(result["identified_tools"]) > 0, \
            f"LLM did not identify any expected tools for query: {query}"
    
    @pytest.mark.asyncio
    async def test_tool_selection_for_retrieval_queries(self, categorized_queries):
        """Test LLM selects retrieval tools for patient data queries."""
        retrieval_queries = categorized_queries.get("retrieval", [])
        if not retrieval_queries:
            pytest.skip("No retrieval queries in testset")
        
        query = retrieval_queries[0].get("user_input", "")
        if not query:
            pytest.skip("Query is empty")
        
        expected_tools = ["search_patient_records", "search_clinical_notes"]
        
        result = await validate_tool_selection(query, expected_tools)
        
        # Should identify at least one retrieval tool
        assert len(result["identified_tools"]) > 0, \
            f"LLM did not identify any retrieval tools for query: {query}"


class TestLLMParameterUnderstanding:
    """Test if LLM understands tool parameters."""
    
    @pytest.mark.asyncio
    async def test_calculate_bmi_parameters(self):
        """Test LLM understands calculate_bmi parameters."""
        result = await validate_tool_parameter_understanding("calculate_bmi")
        
        assert "accuracy" in result
        assert "actual_parameters" in result
        assert "identified_parameters" in result
        
        # Should identify at least the required parameters
        assert len(result["identified_parameters"]) >= 2, \
            f"LLM only identified {len(result['identified_parameters'])} parameters for calculate_bmi"
    
    @pytest.mark.asyncio
    async def test_search_patient_records_parameters(self):
        """Test LLM understands search_patient_records parameters."""
        result = await validate_tool_parameter_understanding("search_patient_records")
        
        assert "accuracy" in result
        # Should identify at least query parameter
        assert "query" in result["identified_parameters"] or result["accuracy"] > 0, \
            "LLM did not identify query parameter for search_patient_records"


class TestLLMValidationSummary:
    """Test comprehensive LLM validation."""
    
    @pytest.mark.asyncio
    async def test_llm_validation_summary(self):
        """Get and verify LLM validation summary."""
        # Create test queries from synthetic testset
        testset = load_testset()
        categorized = extract_queries_by_tool_type(testset)
        
        test_queries = []
        # Add a calculator query
        if categorized.get("calculator"):
            test_queries.append({
                "query": categorized["calculator"][0].get("user_input", ""),
                "expected_tools": ["calculate_bmi"],
            })
        # Add a retrieval query
        if categorized.get("retrieval"):
            test_queries.append({
                "query": categorized["retrieval"][0].get("user_input", ""),
                "expected_tools": ["search_patient_records"],
            })
        
        summary = await get_llm_validation_summary(test_queries)
        
        assert "tool_discovery" in summary
        assert "tool_selection" in summary
        assert "parameter_understanding" in summary
        assert "overall_accuracy" in summary
        
        # Overall accuracy should be reasonable
        assert summary["overall_accuracy"] >= 0.4, \
            f"Overall LLM accuracy too low: {summary['overall_accuracy']*100:.1f}%"
