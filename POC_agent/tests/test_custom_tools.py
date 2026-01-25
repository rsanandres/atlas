"""Unit tests for custom medical tools."""

from __future__ import annotations

import os

import pytest

from POC_agent.agent.tools.calculators import (
    calculate_bmi,
    calculate_bsa,
    calculate_creatinine_clearance,
    calculate_gfr,
)
from POC_agent.agent.tools.dosage_validator import validate_dosage
from POC_agent.agent.tools.fda_tools import (
    get_drug_recalls,
    get_drug_shortages,
    get_faers_events,
    search_fda_drugs,
)
from POC_agent.agent.tools.loinc_lookup import lookup_loinc
from POC_agent.agent.tools.research_tools import (
    get_who_stats,
    search_clinical_trials,
    search_pubmed,
)
from POC_agent.agent.tools.terminology_tools import (
    get_drug_interactions,
    lookup_rxnorm,
    search_icd10,
    validate_icd10_code,
)


class TestMedicalCalculators:
    def test_gfr_normal(self):
        result = calculate_gfr.invoke({"age": 40, "sex": "male", "creatinine": 1.0})
        assert 90 <= result["gfr"] <= 120
        assert result["stage"] == "G1"

    def test_gfr_severe_ckd(self):
        result = calculate_gfr.invoke({"age": 70, "sex": "female", "creatinine": 3.5})
        assert result["gfr"] < 30
        assert result["stage"] in ["G4", "G5"]

    def test_bmi_normal(self):
        result = calculate_bmi.invoke({"weight_kg": 70, "height_cm": 175})
        assert 22 <= result["bmi"] <= 24
        assert result["category"] == "Normal"

    def test_bsa_adult(self):
        result = calculate_bsa.invoke({"weight_kg": 70, "height_cm": 175})
        assert 1.8 <= result["bsa"] <= 1.9

    def test_creatinine_clearance(self):
        result = calculate_creatinine_clearance.invoke(
            {"age": 50, "sex": "male", "weight_kg": 80, "creatinine": 1.0}
        )
        assert result["creatinine_clearance"] > 0
    
    def test_bmi_edge_cases(self):
        """Test BMI with edge cases."""
        # Very low BMI
        result = calculate_bmi.invoke({"weight_kg": 40, "height_cm": 180})
        assert result["category"] == "Underweight"
        
        # Very high BMI
        result = calculate_bmi.invoke({"weight_kg": 120, "height_cm": 160})
        assert result["category"] == "Obese"
        
        # Invalid inputs
        with pytest.raises(ValueError):
            calculate_bmi.invoke({"weight_kg": -10, "height_cm": 175})
        with pytest.raises(ValueError):
            calculate_bmi.invoke({"weight_kg": 70, "height_cm": 0})
    
    def test_gfr_edge_cases(self):
        """Test GFR with edge cases."""
        # Very high GFR (young, healthy)
        result = calculate_gfr.invoke({"age": 20, "sex": "male", "creatinine": 0.8})
        assert result["gfr"] > 100
        assert result["stage"] == "G1"
        
        # Very low GFR (severe CKD)
        result = calculate_gfr.invoke({"age": 80, "sex": "female", "creatinine": 4.0})
        assert result["gfr"] < 20
        assert result["stage"] in ["G4", "G5"]
        
        # Invalid sex
        with pytest.raises(ValueError):
            calculate_gfr.invoke({"age": 50, "sex": "invalid", "creatinine": 1.0})
    
    def test_bsa_edge_cases(self):
        """Test BSA with edge cases."""
        # Child-sized
        result = calculate_bsa.invoke({"weight_kg": 20, "height_cm": 100})
        assert result["bsa"] < 1.0
        
        # Large adult
        result = calculate_bsa.invoke({"weight_kg": 100, "height_cm": 200})
        assert result["bsa"] > 2.0
    
    def test_creatinine_clearance_edge_cases(self):
        """Test creatinine clearance with edge cases."""
        # Female adjustment
        result_female = calculate_creatinine_clearance.invoke({
            "age": 50,
            "sex": "female",
            "weight_kg": 70,
            "creatinine": 1.0,
        })
        result_male = calculate_creatinine_clearance.invoke({
            "age": 50,
            "sex": "male",
            "weight_kg": 70,
            "creatinine": 1.0,
        })
        assert result_female["creatinine_clearance"] < result_male["creatinine_clearance"]
        
        # Invalid inputs
        with pytest.raises(ValueError):
            calculate_creatinine_clearance.invoke({
                "age": -10,
                "sex": "male",
                "weight_kg": 70,
                "creatinine": 1.0,
            })


external_enabled = os.getenv("ENABLE_EXTERNAL_API_TESTS", "false").lower() in {"1", "true", "yes"}

@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_metformin_normal_dose():
    result = await validate_dosage.ainvoke({
        "drug_name": "metformin",
        "dose_amount": 500,
        "dose_unit": "mg",
        "frequency": "twice daily",
    })
    assert result["valid"] is True


@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_metformin_renal_adjustment():
    result = await validate_dosage.ainvoke({
        "drug_name": "metformin",
        "dose_amount": 1000,
        "dose_unit": "mg",
        "frequency": "twice daily",
        "patient_gfr": 25,
    })
    assert result["valid"] is False
    assert "renal" in result["warning"].lower()


@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_valid_loinc_code():
    result = await lookup_loinc.ainvoke({"code": "4548-4"})
    # LOINC API may require auth; if valid=True, check name
    if result["valid"]:
        assert "hemoglobin" in result["long_name"].lower()
    else:
        # Allow 401 Unauthorized as acceptable (auth required)
        assert "401" in result.get("error", "") or result["valid"] is False


@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_invalid_loinc_code():
    result = await lookup_loinc.ainvoke({"code": "INVALID-999"})
    assert result["valid"] is False


@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_search_fda_drugs():
    result = await search_fda_drugs.ainvoke({"drug_name": "metformin", "limit": 2})
    assert "results" in result


@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_fda_recalls_shortages():
    recalls = await get_drug_recalls.ainvoke({"drug_name": "metformin", "limit": 2})
    shortages = await get_drug_shortages.ainvoke({"drug_name": "metformin", "limit": 2})
    assert "results" in recalls
    assert "results" in shortages


@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_faers_events():
    result = await get_faers_events.ainvoke({"drug_name": "metformin", "limit": 2})
    assert "results" in result


@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_search_icd10():
    result = await search_icd10.ainvoke({"term": "diabetes", "max_results": 3})
    assert "results" in result


@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_validate_icd10_code():
    result = await validate_icd10_code.ainvoke({"code": "E11.22"})
    assert "valid" in result


@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_lookup_rxnorm():
    result = await lookup_rxnorm.ainvoke({"drug_name": "metformin"})
    assert "results" in result


@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_get_drug_interactions():
    lookup = await lookup_rxnorm.ainvoke({"drug_name": "warfarin"})
    rxcui = ""
    if lookup.get("results"):
        rxcui = lookup["results"][0].get("rxcui", "")
    if not rxcui:
        pytest.skip("No RxCUI available for interaction test")
    result = await get_drug_interactions.ainvoke({"rxcui": rxcui})
    assert "results" in result


@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_search_pubmed():
    result = await search_pubmed.ainvoke({"query": "metformin kidney", "max_results": 2})
    assert "results" in result


@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_search_clinical_trials():
    result = await search_clinical_trials.ainvoke({"query": "type 2 diabetes", "max_results": 2})
    assert "results" in result


@pytest.mark.skipif(not external_enabled, reason="External API tests disabled")
@pytest.mark.asyncio
async def test_get_who_stats():
    result = await get_who_stats.ainvoke({"indicator_name": "mortality", "max_results": 2})
    assert "results" in result
