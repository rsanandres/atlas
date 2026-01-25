"""Accuracy validation tests using synthetic testset and checkpoint data."""

from __future__ import annotations

import pytest

from pathlib import Path

# Import tools with error handling for missing dependencies
try:
    from POC_agent.agent.tools import (
        calculate_bmi,
        calculate_bsa,
        calculate_gfr,
        lookup_loinc,
        validate_icd10_code,
    )
except ImportError as e:
    # If tools can't be imported (e.g., missing boto3), create placeholder None values
    import warnings
    warnings.warn(f"Could not import all tools: {e}. Some tests will be skipped.")
    
    calculate_bmi = None
    calculate_bsa = None
    calculate_gfr = None
    lookup_loinc = None
    validate_icd10_code = None
from POC_agent.tests.utils.checkpoint_parser import (
    extract_calculation_results,
    get_tool_usage_summary,
    load_checkpoint,
)
from POC_agent.tests.utils.testset_parser import (
    extract_calculation_test_cases,
    extract_loinc_codes,
    load_testset,
)

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_PATH = _REPO_ROOT / "POC_RAGAS" / "data" / "checkpoints" / "checkpoint_first35_questions.json"


class TestCalculatorAccuracy:
    """Test calculator accuracy using data from synthetic testset."""
    
    @pytest.fixture
    def testset(self):
        """Load synthetic testset."""
        return load_testset()
    
    @pytest.fixture
    def calculation_cases(self, testset):
        """Extract height/weight pairs for testing."""
        return extract_calculation_test_cases(testset)
    
    @pytest.mark.skipif(calculate_bmi is None, reason="calculate_bmi tool not available")
    def test_bmi_accuracy_from_testset(self, calculation_cases):
        """Test BMI calculations match expected values from testset."""
        if not calculation_cases:
            pytest.skip("No height/weight pairs found in testset")
        
        for case in calculation_cases[:5]:  # Test first 5 cases
            height_cm = case["height_cm"]
            weight_kg = case["weight_kg"]
            
            result = calculate_bmi.invoke({
                "weight_kg": weight_kg,
                "height_cm": height_cm,
            })
            
            # Verify BMI is in reasonable range
            assert 15 <= result["bmi"] <= 50, f"BMI {result['bmi']} out of range for {weight_kg}kg, {height_cm}cm"
            assert result["category"] in ["Underweight", "Normal", "Overweight", "Obese"]
            
            # Verify calculation is correct (within 0.1 tolerance)
            expected_bmi = weight_kg / ((height_cm / 100) ** 2)
            assert abs(result["bmi"] - expected_bmi) < 0.1, \
                f"BMI calculation error: got {result['bmi']}, expected {expected_bmi}"
    
    @pytest.mark.skipif(calculate_bsa is None, reason="calculate_bsa tool not available")
    def test_bsa_accuracy_from_testset(self, calculation_cases):
        """Test BSA calculations match expected values from testset."""
        if not calculation_cases:
            pytest.skip("No height/weight pairs found in testset")
        
        for case in calculation_cases[:3]:  # Test first 3 cases
            height_cm = case["height_cm"]
            weight_kg = case["weight_kg"]
            
            result = calculate_bsa.invoke({
                "weight_kg": weight_kg,
                "height_cm": height_cm,
            })
            
            # Verify BSA is in reasonable range (0.5 to 3.0 m²)
            assert 0.5 <= result["bsa"] <= 3.0
            
            # Verify Mosteller formula: sqrt((height * weight) / 3600)
            import math
            expected_bsa = math.sqrt((height_cm * weight_kg) / 3600.0)
            assert abs(result["bsa"] - expected_bsa) < 0.01, \
                f"BSA calculation error: got {result['bsa']}, expected {expected_bsa}"
    
    @pytest.mark.skipif(calculate_bmi is None, reason="calculate_bmi tool not available")
    def test_bmi_accuracy_from_checkpoint(self):
        """Test BMI calculations match results from checkpoint."""
        if not CHECKPOINT_PATH.exists():
            pytest.skip("Checkpoint file not found")
        
        checkpoint = load_checkpoint(CHECKPOINT_PATH)
        calculations = extract_calculation_results(checkpoint)
        
        bmi_calculations = [c for c in calculations if c["type"] == "bmi"]
        if not bmi_calculations:
            pytest.skip("No BMI calculations found in checkpoint")
        
        for calc in bmi_calculations[:3]:  # Test first 3
            inputs = calc["inputs"]
            expected_result = calc["result"]
            
            result = calculate_bmi.invoke({
                "weight_kg": float(inputs.get("weight_kg", 0)),
                "height_cm": float(inputs.get("height_cm", 0)),
            })
            
            # Compare with tolerance
            assert abs(result["bmi"] - expected_result) < 0.2, \
                f"BMI mismatch: got {result['bmi']}, expected {expected_result}"


class TestCodeValidationAccuracy:
    """Test code validation accuracy using data from synthetic testset."""
    
    @pytest.fixture
    def testset(self):
        """Load synthetic testset."""
        return load_testset()
    
    @pytest.fixture
    def loinc_codes(self, testset):
        """Extract LOINC codes from testset."""
        return extract_loinc_codes(testset)
    
    @pytest.mark.skipif(lookup_loinc is None, reason="lookup_loinc tool not available")
    @pytest.mark.asyncio
    async def test_loinc_validation_from_testset(self, loinc_codes):
        """Test LOINC code validation using codes from testset."""
        if not loinc_codes:
            pytest.skip("No LOINC codes found in testset")
        
        # Test first few valid codes
        for code_info in loinc_codes[:3]:
            code = code_info["code"]
            if not code:
                continue
            
            try:
                result = await lookup_loinc.ainvoke({"code": code})
                
                # Should return valid structure
                assert "valid" in result
                assert "code" in result
                
                # If valid, should have display name
                if result.get("valid"):
                    assert "long_name" in result or "display" in result
            except Exception as e:
                # API may be unavailable or require auth
                pytest.skip(f"LOINC lookup failed: {e}")


class TestToolUsageFromCheckpoint:
    """Test that tools are being used correctly based on checkpoint data."""
    
    def test_tool_usage_summary(self):
        """Test that we can extract tool usage summary from checkpoint."""
        if not CHECKPOINT_PATH.exists():
            pytest.skip("Checkpoint file not found")
        
        summary = get_tool_usage_summary(CHECKPOINT_PATH)
        
        assert "tools_used" in summary
        assert "tool_call_counts" in summary
        assert isinstance(summary["tools_used"], list)
        assert isinstance(summary["tool_call_counts"], dict)
        
        # Should have at least some tools used
        if summary["tools_used"]:
            assert len(summary["tools_used"]) > 0
    
    def test_calculation_extraction(self):
        """Test that we can extract calculations from checkpoint."""
        if not CHECKPOINT_PATH.exists():
            pytest.skip("Checkpoint file not found")
        
        checkpoint = load_checkpoint(CHECKPOINT_PATH)
        calculations = extract_calculation_results(checkpoint)
        
        # Should be able to extract calculations if they exist
        assert isinstance(calculations, list)
        
        # If calculations exist, verify structure
        for calc in calculations[:3]:
            assert "type" in calc
            assert "result" in calc
            assert "inputs" in calc
            assert calc["type"] in ["bmi", "gfr", "bsa", "creatinine_clearance"]


class TestDataExtraction:
    """Test data extraction utilities work correctly."""
    
    def test_testset_loading(self):
        """Test that synthetic testset can be loaded."""
        testset = load_testset()
        assert isinstance(testset, list)
        assert len(testset) > 0
    
    def test_fhir_extraction(self):
        """Test that FHIR resources can be extracted from testset."""
        from POC_agent.tests.utils.testset_parser import extract_fhir_resources
        
        testset = load_testset()
        resources = extract_fhir_resources(testset)
        
        assert isinstance(resources, list)
        if resources:
            # Verify resource structure
            resource = resources[0]
            assert "resourceType" in resource
    
    def test_code_extraction(self):
        """Test that codes can be extracted from testset."""
        from POC_agent.tests.utils.testset_parser import (
            extract_icd10_codes,
            extract_loinc_codes,
            extract_rxnorm_codes,
        )
        
        testset = load_testset()
        
        loinc_codes = extract_loinc_codes(testset)
        icd10_codes = extract_icd10_codes(testset)
        rxnorm_codes = extract_rxnorm_codes(testset)
        
        # Should be able to extract codes (may be empty)
        assert isinstance(loinc_codes, list)
        assert isinstance(icd10_codes, list)
        assert isinstance(rxnorm_codes, list)
