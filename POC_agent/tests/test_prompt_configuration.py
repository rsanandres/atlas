"""Automated tests for prompt configuration validation."""

from __future__ import annotations

import pytest

from POC_agent.tests.utils.prompt_validator import (
    get_prompt_validation_summary,
    validate_decision_trees,
    validate_tool_assignments,
    validate_tool_names_in_prompts,
    validate_tool_parameters,
)


class TestPromptToolNames:
    """Test that tool names in prompts match code."""
    
    def test_all_prompt_tools_exist_in_code(self):
        """Verify all tools mentioned in prompts exist in code."""
        result = validate_tool_names_in_prompts()
        
        assert "valid" in result
        assert "issues" in result
        
        # Check for missing tools
        missing_issues = [i for i in result["issues"] if i["type"] == "missing_in_code"]
        if missing_issues:
            missing_tools = missing_issues[0]["tools"]
            pytest.fail(f"Tools mentioned in prompts but not in code: {missing_tools}")
    
    def test_all_code_tools_mentioned_in_prompts(self):
        """Verify all code tools are mentioned in prompts (warning, not error)."""
        result = validate_tool_names_in_prompts()
        
        missing_issues = [i for i in result["issues"] if i["type"] == "missing_in_prompts"]
        if missing_issues:
            missing_tools = missing_issues[0]["tools"]
            pytest.skip(f"Tools in code but not mentioned in prompts: {missing_tools}")


class TestPromptToolParameters:
    """Test that tool parameters in prompts match function signatures."""
    
    def test_tool_parameters_match_signatures(self):
        """Verify tool parameters in prompts match actual function signatures."""
        result = validate_tool_parameters()
        
        assert "valid" in result
        assert "issues" in result
        
        # Filter out dependency-related issues (tool_not_available)
        real_issues = [
            i for i in result["issues"]
            if i.get("type") != "tool_not_available"
        ]
        
        if real_issues:
            issues_str = "\n".join([
                f"  {i.get('tool', 'unknown')}: {i.get('prompt_param', i.get('note', 'unknown issue'))}" 
                for i in real_issues
            ])
            pytest.fail(f"Parameter mismatches found:\n{issues_str}")
        
        # If all issues are just dependency-related, that's acceptable
        if result["issues"] and all(i.get("type") == "tool_not_available" for i in result["issues"]):
            pytest.skip("All tools unavailable due to missing dependencies - parameter validation skipped")


class TestPromptToolAssignments:
    """Test that tools are assigned to correct agents."""
    
    def test_tool_assignments_valid(self):
        """Verify tools are properly assigned to researcher/validator agents."""
        result = validate_tool_assignments()
        
        assert "researcher_tools" in result
        assert "validator_tools" in result
        assert "issues" in result
        
        # Check for high/medium severity issues
        high_medium_issues = [
            i for i in result["issues"]
            if i.get("severity") in ["high", "medium"]
        ]
        if high_medium_issues:
            pytest.fail(f"Tool assignment issues found: {high_medium_issues}")


class TestPromptDecisionTrees:
    """Test that decision trees reference valid tools."""
    
    def test_decision_tree_tools_valid(self):
        """Verify all tools in decision trees exist in code."""
        result = validate_decision_trees()
        
        assert "decision_tree_tools" in result
        assert "issues" in result
        
        invalid_issues = [
            i for i in result["issues"]
            if i["type"] == "invalid_tool_in_decision_tree"
        ]
        if invalid_issues:
            invalid_tools = invalid_issues[0]["tools"]
            pytest.fail(f"Invalid tools in decision tree: {invalid_tools}")


class TestPromptValidationSummary:
    """Test comprehensive prompt validation."""
    
    def test_prompt_validation_summary(self):
        """Get and verify prompt validation summary."""
        summary = get_prompt_validation_summary()
        
        assert "tool_names" in summary
        assert "tool_parameters" in summary
        assert "tool_assignments" in summary
        assert "decision_trees" in summary
        assert "all_issues" in summary
        assert "total_issues" in summary
        assert "valid" in summary
        
        # Fail if there are high or medium severity issues
        if summary["high_severity_issues"] > 0:
            pytest.fail(
                f"Found {summary['high_severity_issues']} high severity issues. "
                f"See summary for details."
            )
        
        # Warn about medium severity issues but don't fail
        if summary["medium_severity_issues"] > 0:
            pytest.skip(
                f"Found {summary['medium_severity_issues']} medium severity issues. "
                f"Review recommended."
            )
