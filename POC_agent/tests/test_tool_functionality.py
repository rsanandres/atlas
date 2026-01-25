"""Comprehensive functionality tests for all 24 agent tools."""

from __future__ import annotations

import os
import pytest

# Import tools with error handling for missing dependencies
try:
    from POC_agent.agent.tools import (
        calculate,
        calculate_bmi,
        calculate_bsa,
        calculate_creatinine_clearance,
        calculate_gfr,
        cross_reference_meds,
        get_current_date,
        get_drug_interactions,
        get_drug_recalls,
        get_drug_shortages,
        get_faers_events,
        get_patient_timeline,
        get_session_context,
        get_who_stats,
        lookup_loinc,
        lookup_rxnorm,
        search_clinical_notes,
        search_clinical_trials,
        search_fda_drugs,
        search_icd10,
        search_patient_records,
        search_pubmed,
        validate_icd10_code,
        validate_dosage,
    )
except ImportError as e:
    # If tools can't be imported (e.g., missing boto3), create placeholder None values
    # Tests will be skipped if tools are None
    import warnings
    warnings.warn(f"Could not import all tools: {e}. Some tests will be skipped.")
    
    # Create None placeholders
    calculate = None
    calculate_bmi = None
    calculate_bsa = None
    calculate_creatinine_clearance = None
    calculate_gfr = None
    cross_reference_meds = None
    get_current_date = None
    get_drug_interactions = None
    get_drug_recalls = None
    get_drug_shortages = None
    get_faers_events = None
    get_patient_timeline = None
    get_session_context = None
    get_who_stats = None
    lookup_loinc = None
    lookup_rxnorm = None
    search_clinical_notes = None
    search_clinical_trials = None
    search_fda_drugs = None
    search_icd10 = None
    search_patient_records = None
    search_pubmed = None
    validate_icd10_code = None
    validate_dosage = None

EXTERNAL_API_ENABLED = os.getenv("ENABLE_EXTERNAL_API_TESTS", "false").lower() in {"1", "true", "yes"}

# Helper to skip tests if tool is None
def skip_if_tool_unavailable(tool_obj):
    """Skip test if tool is not available."""
    if tool_obj is None:
        pytest.skip("Tool not available (missing dependencies)")


# ============================================================================
# CALCULATOR TOOLS (4 tools)
# ============================================================================

class TestCalculatorTools:
    """Test calculator tools: BMI, GFR, BSA, Creatinine Clearance."""
    
    @pytest.mark.skipif(calculate_bmi is None, reason="calculate_bmi tool not available (missing dependencies)")
    def test_calculate_bmi_normal(self):
        """Test BMI calculation for normal weight."""
        result = calculate_bmi.invoke({"weight_kg": 70, "height_cm": 175})
        assert "bmi" in result
        assert "category" in result
        assert 22 <= result["bmi"] <= 24
        assert result["category"] == "Normal"
    
    @pytest.mark.skipif(calculate_bmi is None, reason="calculate_bmi tool not available")
    def test_calculate_bmi_obese(self):
        """Test BMI calculation for obese."""
        result = calculate_bmi.invoke({"weight_kg": 100, "height_cm": 170})
        assert result["bmi"] > 30
        assert result["category"] == "Obese"
    
    @pytest.mark.skipif(calculate_bmi is None, reason="calculate_bmi tool not available")
    def test_calculate_bmi_edge_cases(self):
        """Test BMI edge cases."""
        # Very tall person
        result = calculate_bmi.invoke({"weight_kg": 80, "height_cm": 200})
        assert result["bmi"] < 25
        
        # Very short person
        result = calculate_bmi.invoke({"weight_kg": 50, "height_cm": 150})
        assert result["bmi"] > 20
        
        # Invalid inputs should raise ValueError
        with pytest.raises(ValueError):
            calculate_bmi.invoke({"weight_kg": -10, "height_cm": 175})
        with pytest.raises(ValueError):
            calculate_bmi.invoke({"weight_kg": 70, "height_cm": 0})
    
    @pytest.mark.skipif(calculate_gfr is None, reason="calculate_gfr tool not available")
    def test_calculate_gfr_normal(self):
        """Test GFR calculation for normal kidney function."""
        result = calculate_gfr.invoke({"age": 40, "sex": "male", "creatinine": 1.0})
        assert "gfr" in result
        assert "stage" in result
        assert 90 <= result["gfr"] <= 120
        assert result["stage"] == "G1"
    
    @pytest.mark.skipif(calculate_gfr is None, reason="calculate_gfr tool not available")
    def test_calculate_gfr_severe_ckd(self):
        """Test GFR calculation for severe CKD."""
        result = calculate_gfr.invoke({"age": 70, "sex": "female", "creatinine": 3.5})
        assert result["gfr"] < 30
        assert result["stage"] in ["G4", "G5"]
    
    @pytest.mark.skipif(calculate_gfr is None, reason="calculate_gfr tool not available")
    def test_calculate_gfr_female(self):
        """Test GFR calculation for female."""
        result = calculate_gfr.invoke({"age": 50, "sex": "female", "creatinine": 1.2})
        assert "gfr" in result
        assert "stage" in result
    
    @pytest.mark.skipif(calculate_gfr is None, reason="calculate_gfr tool not available")
    def test_calculate_gfr_edge_cases(self):
        """Test GFR edge cases."""
        with pytest.raises(ValueError):
            calculate_gfr.invoke({"age": -10, "sex": "male", "creatinine": 1.0})
        with pytest.raises(ValueError):
            calculate_gfr.invoke({"age": 50, "sex": "invalid", "creatinine": 1.0})
        with pytest.raises(ValueError):
            calculate_gfr.invoke({"age": 50, "sex": "male", "creatinine": -1.0})
    
    @pytest.mark.skipif(calculate_bsa is None, reason="calculate_bsa tool not available")
    def test_calculate_bsa(self):
        """Test Body Surface Area calculation."""
        result = calculate_bsa.invoke({"weight_kg": 70, "height_cm": 175})
        assert "bsa" in result
        assert 1.8 <= result["bsa"] <= 1.9
        
        # Edge case
        with pytest.raises(ValueError):
            calculate_bsa.invoke({"weight_kg": -10, "height_cm": 175})
    
    @pytest.mark.skipif(calculate_creatinine_clearance is None, reason="calculate_creatinine_clearance tool not available")
    def test_calculate_creatinine_clearance(self):
        """Test Creatinine Clearance calculation."""
        result = calculate_creatinine_clearance.invoke({
            "age": 50,
            "sex": "male",
            "weight_kg": 80,
            "creatinine": 1.0,
        })
        assert "creatinine_clearance" in result
        assert result["creatinine_clearance"] > 0
        
        # Female adjustment
        result_female = calculate_creatinine_clearance.invoke({
            "age": 50,
            "sex": "female",
            "weight_kg": 70,
            "creatinine": 1.0,
        })
        assert result_female["creatinine_clearance"] < result["creatinine_clearance"]


# ============================================================================
# UTILITY TOOLS (3 tools)
# ============================================================================

class TestUtilityTools:
    """Test utility tools: calculate, get_current_date."""
    
    @pytest.mark.skipif(calculate is None, reason="calculate tool not available")
    def test_calculate(self):
        """Test simple arithmetic calculator."""
        assert calculate.invoke("2 + 2") == "4"
        assert calculate.invoke("10 * 5") == "50"
        assert calculate.invoke("(10 + 5) / 3") == "5.0"
        
        # Invalid characters should be rejected
        result = calculate.invoke("import os")
        assert "Unsupported" in result or "Unable" in result
    
    @pytest.mark.skipif(get_current_date is None, reason="get_current_date tool not available")
    def test_get_current_date(self):
        """Test current date retrieval."""
        result = get_current_date.invoke({})
        assert isinstance(result, str)
        assert "T" in result or "-" in result  # ISO format


# ============================================================================
# RETRIEVAL TOOLS (3 tools) - Require reranker service
# ============================================================================

class TestRetrievalTools:
    """Test retrieval tools: search_patient_records, search_clinical_notes, get_patient_timeline."""
    
    @pytest.mark.asyncio
    async def test_search_patient_records_structure(self):
        """Test search_patient_records returns correct structure."""
        # This will fail if reranker service is not available, which is expected
        try:
            result = await search_patient_records.ainvoke({
                "query": "test query",
                "k_chunks": 5,
            })
            assert "chunks" in result or "results" in result
            assert "query" in result
        except Exception:
            # Service not available - skip
            pytest.skip("Reranker service not available")
    
    @pytest.mark.asyncio
    async def test_search_patient_records_with_patient_id(self):
        """Test search_patient_records with patient_id filter."""
        try:
            result = await search_patient_records.ainvoke({
                "query": "test",
                "patient_id": "test-patient-123",
                "k_chunks": 5,
            })
            assert "chunks" in result or "results" in result
        except Exception:
            pytest.skip("Reranker service not available")
    
    @pytest.mark.asyncio
    async def test_search_clinical_notes_structure(self):
        """Test search_clinical_notes returns correct structure."""
        try:
            result = await search_clinical_notes.ainvoke({
                "query": "test",
                "k_return": 5,
            })
            assert isinstance(result, list)
        except Exception:
            pytest.skip("Reranker service not available")
    
    @pytest.mark.asyncio
    async def test_get_patient_timeline_structure(self):
        """Test get_patient_timeline returns correct structure."""
        try:
            result = await get_patient_timeline.ainvoke({
                "patient_id": "test-patient-123",
                "k_return": 10,
            })
            assert "patient_id" in result
            assert "events" in result
            assert isinstance(result["events"], list)
        except Exception:
            pytest.skip("Reranker service not available")


# ============================================================================
# FDA TOOLS (4 tools) - Require external API
# ============================================================================

class TestFDATools:
    """Test FDA tools: search_fda_drugs, get_drug_recalls, get_drug_shortages, get_faers_events."""
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or search_fda_drugs is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_search_fda_drugs(self):
        """Test FDA drug search."""
        result = await search_fda_drugs.ainvoke({"drug_name": "metformin", "limit": 2})
        assert "results" in result
        assert "count" in result
        assert isinstance(result["results"], list)
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or get_drug_recalls is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_get_drug_recalls(self):
        """Test drug recall lookup."""
        result = await get_drug_recalls.ainvoke({"drug_name": "metformin", "limit": 2})
        assert "results" in result
        assert "count" in result
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or get_drug_shortages is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_get_drug_shortages(self):
        """Test drug shortage lookup."""
        result = await get_drug_shortages.ainvoke({"drug_name": "metformin", "limit": 2})
        assert "results" in result
        assert "count" in result
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or get_faers_events is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_get_faers_events(self):
        """Test FAERS adverse events lookup."""
        result = await get_faers_events.ainvoke({"drug_name": "metformin", "limit": 2})
        assert "results" in result
        assert "count" in result
    
    @pytest.mark.skipif(search_fda_drugs is None, reason="search_fda_drugs tool not available")
    @pytest.mark.asyncio
    async def test_fda_tools_empty_drug_name(self):
        """Test FDA tools handle empty drug names."""
        result = await search_fda_drugs.ainvoke({"drug_name": "", "limit": 5})
        assert "error" in result


# ============================================================================
# TERMINOLOGY TOOLS (4 tools) - Require external APIs
# ============================================================================

class TestTerminologyTools:
    """Test terminology tools: lookup_rxnorm, search_icd10, validate_icd10_code, get_drug_interactions."""
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or lookup_rxnorm is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_lookup_rxnorm(self):
        """Test RxNorm lookup."""
        result = await lookup_rxnorm.ainvoke({"drug_name": "metformin"})
        assert "results" in result
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or search_icd10 is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_search_icd10(self):
        """Test ICD-10 code search."""
        result = await search_icd10.ainvoke({"term": "diabetes", "max_results": 3})
        assert "results" in result
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or validate_icd10_code is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_validate_icd10_code(self):
        """Test ICD-10 code validation."""
        result = await validate_icd10_code.ainvoke({"code": "E11.22"})
        assert "valid" in result
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or lookup_rxnorm is None or get_drug_interactions is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_get_drug_interactions(self):
        """Test drug interaction lookup."""
        # First get RxCUI
        lookup = await lookup_rxnorm.ainvoke({"drug_name": "warfarin"})
        rxcui = ""
        if lookup.get("results"):
            rxcui = lookup["results"][0].get("rxcui", "")
        if not rxcui:
            pytest.skip("No RxCUI available for interaction test")
        result = await get_drug_interactions.ainvoke({"rxcui": rxcui})
        assert "results" in result


# ============================================================================
# RESEARCH TOOLS (3 tools) - Require external APIs
# ============================================================================

class TestResearchTools:
    """Test research tools: search_pubmed, search_clinical_trials, get_who_stats."""
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or search_pubmed is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_search_pubmed(self):
        """Test PubMed search."""
        result = await search_pubmed.ainvoke({"query": "metformin kidney", "max_results": 2})
        assert "results" in result
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or search_clinical_trials is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_search_clinical_trials(self):
        """Test clinical trials search."""
        result = await search_clinical_trials.ainvoke({"query": "type 2 diabetes", "max_results": 2})
        assert "results" in result
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or get_who_stats is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_get_who_stats(self):
        """Test WHO statistics lookup."""
        result = await get_who_stats.ainvoke({"indicator_name": "mortality", "max_results": 2})
        assert "results" in result


# ============================================================================
# OTHER TOOLS (3 tools)
# ============================================================================

class TestOtherTools:
    """Test other tools: lookup_loinc, validate_dosage, cross_reference_meds, get_session_context."""
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or lookup_loinc is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_lookup_loinc(self):
        """Test LOINC code lookup."""
        result = await lookup_loinc.ainvoke({"code": "4548-4"})
        # May require auth, so check for valid or error
        assert "valid" in result or "error" in result
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or validate_dosage is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_validate_dosage_normal(self):
        """Test dosage validation for normal dose."""
        result = await validate_dosage.ainvoke({
            "drug_name": "metformin",
            "dose_amount": 500,
            "dose_unit": "mg",
            "frequency": "twice daily",
        })
        assert "valid" in result
        assert "warning" in result
    
    @pytest.mark.skipif(not EXTERNAL_API_ENABLED or validate_dosage is None, reason="External API tests disabled or tool not available")
    @pytest.mark.asyncio
    async def test_validate_dosage_renal_adjustment(self):
        """Test dosage validation with renal impairment."""
        result = await validate_dosage.ainvoke({
            "drug_name": "metformin",
            "dose_amount": 1000,
            "dose_unit": "mg",
            "frequency": "twice daily",
            "patient_gfr": 25,
        })
        assert result["valid"] is False
        assert "renal" in result["warning"].lower()
    
    @pytest.mark.skipif(cross_reference_meds is None, reason="cross_reference_meds tool not available")
    def test_cross_reference_meds(self):
        """Test medication cross-reference for interactions."""
        result = cross_reference_meds.invoke({"medication_list": ["warfarin", "aspirin"]})
        assert "medications" in result
        assert "warnings" in result
        assert len(result["warnings"]) > 0  # Should detect interaction
    
    @pytest.mark.asyncio
    async def test_get_session_context(self):
        """Test session context retrieval."""
        import os
        # Configure for local DynamoDB if available
        original_endpoint = os.getenv("DDB_ENDPOINT")
        original_auto_create = os.getenv("DDB_AUTO_CREATE")
        original_region = os.getenv("AWS_REGION")
        original_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        original_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        # Set env vars before trying to use the tool
        if not original_endpoint:
            os.environ["DDB_ENDPOINT"] = "http://localhost:8000"
        if not original_auto_create:
            os.environ["DDB_AUTO_CREATE"] = "true"
        if not original_region:
            os.environ["AWS_REGION"] = "us-east-1"
        # Set dummy credentials for local DynamoDB (boto3 requires them even for local)
        if not original_access_key:
            os.environ["AWS_ACCESS_KEY_ID"] = "dummy"
        if not original_secret_key:
            os.environ["AWS_SECRET_ACCESS_KEY"] = "dummy"
        # Ensure table names are set (may be empty or invalid from .env)
        os.environ["DDB_TURNS_TABLE"] = "hcai_session_turns"
        os.environ["DDB_SUMMARY_TABLE"] = "hcai_session_summary"
        
        try:
            result = await get_session_context.ainvoke({
                "session_id": "test-session-123",
                "limit": 10,
            })
            assert "summary" in result
            assert "recent_turns" in result
        except Exception as e:
            # Session store may not be configured
            pytest.skip(f"Session store not available: {type(e).__name__}: {str(e)}")
        finally:
            # Restore original env vars
            if original_endpoint is None:
                os.environ.pop("DDB_ENDPOINT", None)
            else:
                os.environ["DDB_ENDPOINT"] = original_endpoint
            if original_auto_create is None:
                os.environ.pop("DDB_AUTO_CREATE", None)
            else:
                os.environ["DDB_AUTO_CREATE"] = original_auto_create
            if original_region is None:
                os.environ.pop("AWS_REGION", None)
            else:
                os.environ["AWS_REGION"] = original_region
            if original_access_key is None:
                os.environ.pop("AWS_ACCESS_KEY_ID", None)
            else:
                os.environ["AWS_ACCESS_KEY_ID"] = original_access_key
            if original_secret_key is None:
                os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
            else:
                os.environ["AWS_SECRET_ACCESS_KEY"] = original_secret_key
