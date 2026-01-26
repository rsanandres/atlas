"""Unit tests for query classifier."""

import pytest
import time
from POC_agent.agent.query_classifier import (
    QueryClassifier,
    QueryType,
    ClassificationResult,
    classify_query,
)


class TestQueryClassifier:
    """Test suite for QueryClassifier."""
    
    @pytest.fixture
    def classifier(self):
        """Create default classifier instance."""
        return QueryClassifier()
    
    # ============== Conversational Query Tests ==============
    
    @pytest.mark.parametrize("query", [
        "hello",
        "hi",
        "hey",
        "hi there",
        "good morning",
        "good afternoon",
        "good evening",
        "goodbye",
        "bye",
        "see you later",
    ])
    def test_greeting_queries(self, classifier, query):
        """Test that greetings are classified as conversational."""
        result = classifier.classify(query)
        assert result.query_type == QueryType.CONVERSATIONAL, f"'{query}' should be CONVERSATIONAL"
        assert result.confidence >= 0.7
        assert result.method == "keyword"
    
    @pytest.mark.parametrize("query", [
        "what is your name?",
        "who are you?",
        "what are you?",
        "are you a bot?",
        "are you an AI?",
        "introduce yourself",
    ])
    def test_identity_queries(self, classifier, query):
        """Test that identity questions are classified as conversational."""
        result = classifier.classify(query)
        assert result.query_type == QueryType.CONVERSATIONAL, f"'{query}' should be CONVERSATIONAL"
    
    @pytest.mark.parametrize("query", [
        "what can you do?",
        "how can you help me?",
        "what do you know?",
        "help me",
    ])
    def test_capability_queries(self, classifier, query):
        """Test that capability questions are classified as conversational."""
        result = classifier.classify(query)
        assert result.query_type == QueryType.CONVERSATIONAL, f"'{query}' should be CONVERSATIONAL"
    
    @pytest.mark.parametrize("query", [
        "thank you",
        "thanks",
        "how are you?",
    ])
    def test_social_queries(self, classifier, query):
        """Test that social queries are classified as conversational."""
        result = classifier.classify(query)
        assert result.query_type == QueryType.CONVERSATIONAL, f"'{query}' should be CONVERSATIONAL"
    
    # ============== Medical Query Tests ==============
    
    @pytest.mark.parametrize("query", [
        "what is diabetes?",
        "what are the symptoms of diabetes?",
        "diabetes symptoms",
        "tell me about hypertension",
        "what causes heart disease?",
    ])
    def test_condition_queries(self, classifier, query):
        """Test that condition/disease queries are classified as medical."""
        result = classifier.classify(query)
        assert result.query_type == QueryType.MEDICAL, f"'{query}' should be MEDICAL"
    
    @pytest.mark.parametrize("query", [
        "check patient c3a04059-3728-4f03-90e4-ee3677c36f66",
        "patient 123 blood pressure",
        "what medications is patient abc taking?",
        "his diagnosis",
        "her medication list",
    ])
    def test_patient_queries(self, classifier, query):
        """Test that patient-specific queries are classified as medical."""
        result = classifier.classify(query)
        assert result.query_type == QueryType.MEDICAL, f"'{query}' should be MEDICAL"
    
    @pytest.mark.parametrize("query", [
        "calculate BMI for 70kg 175cm",
        "calculate GFR",
        "what is the creatinine clearance?",
        "analyze blood pressure trends",
    ])
    def test_calculation_queries(self, classifier, query):
        """Test that calculation queries are classified as medical."""
        result = classifier.classify(query)
        assert result.query_type == QueryType.MEDICAL, f"'{query}' should be MEDICAL"
    
    @pytest.mark.parametrize("query", [
        "validate ICD-10 code E11.9",
        "look up LOINC code 2345-7",
        "check RxNorm for metformin",
        "icd-10 code for diabetes",
    ])
    def test_code_queries(self, classifier, query):
        """Test that code-related queries are classified as medical."""
        result = classifier.classify(query)
        assert result.query_type == QueryType.MEDICAL, f"'{query}' should be MEDICAL"
    
    @pytest.mark.parametrize("query", [
        "what are drug interactions for metformin?",
        "medication side effects",
        "prescription for patient",
        "drug dosage information",
    ])
    def test_medication_queries(self, classifier, query):
        """Test that medication queries are classified as medical."""
        result = classifier.classify(query)
        assert result.query_type == QueryType.MEDICAL, f"'{query}' should be MEDICAL"
    
    # ============== Mixed Query Tests ==============
    
    @pytest.mark.parametrize("query", [
        "hello! what are diabetes symptoms?",
        "hi, can you check patient c3a04059-3728-4f03-90e4-ee3677c36f66's glucose?",
        "good morning, I need help calculating GFR",
        "hey, search for hypertension treatments",
        "hello, what medications is patient 123 on?",
    ])
    def test_mixed_queries(self, classifier, query):
        """Test that mixed queries (greeting + medical) are classified correctly."""
        result = classifier.classify(query)
        assert result.query_type == QueryType.MIXED, f"'{query}' should be MIXED"
        assert result.should_acknowledge_greeting == True
    
    # ============== Unclear/Edge Case Tests ==============
    
    def test_empty_query(self, classifier):
        """Test that empty queries are classified as unclear."""
        result = classifier.classify("")
        assert result.query_type == QueryType.UNCLEAR
        assert result.method == "empty"
    
    def test_whitespace_query(self, classifier):
        """Test that whitespace-only queries are classified as unclear."""
        result = classifier.classify("   ")
        assert result.query_type == QueryType.UNCLEAR
    
    def test_gibberish_query(self, classifier):
        """Test that gibberish defaults to medical (safer)."""
        result = classifier.classify("asdf qwer zxcv", use_llm_fallback=False)
        # Should be UNCLEAR without LLM, but default to MEDICAL
        assert result.query_type in [QueryType.UNCLEAR, QueryType.MEDICAL]
    
    # ============== Context-Aware Tests ==============
    
    def test_context_aware_medical_followup(self, classifier):
        """Test that unclear queries use session context."""
        session_context = {"last_query_type": "medical"}
        result = classifier.classify("tell me more", session_context=session_context)
        # Should use context to determine type
        assert result.query_type == QueryType.MEDICAL or result.method == "context"
    
    def test_context_aware_conversational_followup(self, classifier):
        """Test that unclear queries use session context for conversational."""
        session_context = {"last_query_type": "conversational"}
        result = classifier.classify("okay", session_context=session_context)
        # Should use context
        assert result.method in ["context", "keyword", "llm_fallback_default"]
    
    # ============== Performance Tests ==============
    
    def test_classification_performance(self, classifier):
        """Test that classification is fast (<100ms)."""
        queries = [
            "hello",
            "what is diabetes?",
            "hello! check patient 123",
            "calculate BMI for 70kg 175cm",
        ]
        
        for query in queries:
            result = classifier.classify(query, use_llm_fallback=False)
            assert result.processing_time_ms < 100, f"Query '{query}' took too long: {result.processing_time_ms}ms"
    
    def test_batch_classification_performance(self, classifier):
        """Test batch classification performance."""
        queries = ["hello", "what is diabetes?", "check patient 123"] * 100
        
        start_time = time.time()
        for query in queries:
            classifier.classify(query, use_llm_fallback=False)
        elapsed = (time.time() - start_time) * 1000
        
        # 300 queries should complete in under 1 second
        assert elapsed < 1000, f"Batch classification too slow: {elapsed}ms for 300 queries"
    
    # ============== Convenience Function Tests ==============
    
    def test_classify_query_function(self):
        """Test the convenience classify_query function."""
        result = classify_query("hello")
        assert result.query_type == QueryType.CONVERSATIONAL
        
        result = classify_query("what is diabetes?")
        assert result.query_type == QueryType.MEDICAL
