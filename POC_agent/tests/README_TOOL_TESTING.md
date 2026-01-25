# Tool Testing and Validation System

Comprehensive testing framework for validating all 24 agent tools are working correctly, producing accurate results, and that prompts.yaml is properly configured.

## Overview

This testing system validates:
1. **Tool Functionality**: All 24 tools execute without errors
2. **Tool Accuracy**: Results match expected outputs (using synthetic testset and checkpoint data)
3. **Prompt Configuration**: prompts.yaml correctly documents tools for LLM usage

## Test Structure

```
POC_agent/tests/
├── test_tool_functionality.py      # Unit tests for all 24 tools
├── test_tool_accuracy.py           # Accuracy validation using testset/checkpoint data
├── test_prompt_configuration.py    # Automated prompt validation
├── test_prompt_llm_validation.py   # LLM-based prompt clarity checks
├── test_custom_tools.py            # Extended edge case tests
└── utils/
    ├── testset_parser.py           # Parse synthetic testset
    ├── checkpoint_parser.py        # Parse checkpoint data
    ├── prompt_validator.py         # Validate prompts.yaml
    ├── llm_validator.py            # LLM-based validation
    └── report_generator.py         # JSON report generation
```

## Running Tests

### Run All Tests with JSON Report

```bash
python POC_agent/scripts/run_tool_tests.py
```

This will:
- Run all pytest test suites
- Validate prompt configuration
- Run LLM-based validation (optional)
- Generate JSON report in `POC_agent/tests/reports/`

### Run Specific Test Suites

```bash
# Functionality tests only
pytest POC_agent/tests/test_tool_functionality.py -v

# Accuracy tests only
pytest POC_agent/tests/test_tool_accuracy.py -v

# Prompt configuration tests only
pytest POC_agent/tests/test_prompt_configuration.py -v

# LLM validation tests (requires LLM)
pytest POC_agent/tests/test_prompt_llm_validation.py -v
```

### Enable External API Tests

For tests that require external APIs (FDA, PubMed, etc.):

```bash
ENABLE_EXTERNAL_API_TESTS=true pytest POC_agent/tests/test_tool_functionality.py -v
```

## Test Data Sources

1. **Synthetic Testset** (`POC_RAGAS/data/testsets/synthetic_testset.json`)
   - 120+ test questions with FHIR data
   - Used for accuracy validation and tool selection testing

2. **Checkpoint Data** (`POC_RAGAS/data/checkpoints/checkpoint_first35_questions.json`)
   - Real-world tool usage patterns
   - Used for accuracy validation

## Test Coverage

### Tool Functionality Tests
- ✅ All 24 tools tested
- ✅ Edge cases (invalid inputs, boundary values)
- ✅ Error handling
- ✅ Return structure validation

### Accuracy Tests
- ✅ Calculator accuracy (BMI, GFR, BSA, CrCl)
- ✅ Code validation (LOINC, ICD-10, RxNorm)
- ✅ Comparison with checkpoint data

### Prompt Configuration Tests
- ✅ Tool names match between prompts and code
- ✅ Parameter documentation matches function signatures
- ✅ Tools assigned to correct agents
- ✅ Decision trees reference valid tools

### LLM Validation Tests
- ✅ Tool discovery (can LLM identify tools from prompts?)
- ✅ Tool selection (does LLM choose correct tools for queries?)
- ✅ Parameter understanding (does LLM know required parameters?)

## JSON Report Format

Reports are saved to `POC_agent/tests/reports/tool_test_report_YYYYMMDDTHHMMSSZ.json`:

```json
{
  "timestamp": "2026-01-22T...",
  "summary": {
    "total_tests": 150,
    "passed": 142,
    "failed": 5,
    "skipped": 3
  },
  "tool_results": {
    "calculate_bmi": {
      "functionality": "passed",
      "accuracy": "passed",
      "prompt_config": "passed",
      "llm_validation": "passed"
    }
  },
  "failures": [...],
  "recommendations": [...]
}
```

## Configuration

Environment variables:
- `ENABLE_EXTERNAL_API_TESTS`: Enable/disable real API tests (default: false)
- `OPENFDA_API_KEY`: For FDA tool tests
- `LOINC_API_KEY`: For LOINC tool tests (if required)
- `RERANKER_SERVICE_URL`: For retrieval tool tests (default: http://localhost:8001/rerank)

## Success Criteria

1. ✅ All 24 tools pass functionality tests
2. ✅ Accuracy tests match testset/checkpoint data (within tolerance)
3. ✅ Prompt configuration validation passes (all tools documented)
4. ✅ LLM validation shows >50% tool identification accuracy
5. ✅ JSON report generated successfully
