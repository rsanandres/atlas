# Hallucination Bug Debug Plan

## Status: FIXES IMPLEMENTED

### Fixes Applied:
1. ✅ Replaced real medical data in prompts.yaml examples with placeholders
2. ✅ Added anti-hallucination instructions to Response Synthesizer
3. ✅ Strengthened Validator instructions to only validate codes from actual response
4. ✅ Updated citation format fragment to use obvious placeholders
5. ✅ Added debug logging (enable with `DEBUG_HALLUCINATION=true`)

### To Test:

**Step 1: Create low-temperature model variant**
```bash
# Create low-temp-llama3.1:8b with temperature 0.12
ollama create low-temp-llama3.1:8b -f - <<EOF
FROM llama3.1:8b
PARAMETER temperature 0.12
EOF
```

**Step 2: Update .env to use low-temp model**
```bash
LLM_MODEL=low-temp-llama3.1:8b
```

**Step 3: Restart backend with debug logging**
```bash
DEBUG_HALLUCINATION=true uvicorn api.main:app --reload --port 8000
```

---

## Summary
The agent system is hallucinating patient data by copying example conditions/codes from prompts.yaml into final responses, completely ignoring actual search results.

## Evidence

### What the search found:
- Acute bacterial sinusitis (SNOMED: 75498004)
- Polyp of colon (SNOMED: 68496003)

### What the response claimed:
- Type 2 Diabetes (ICD-10: E11.9)
- Hypertension (SNOMED: 38341003)

### Source of hallucinated data (prompts.yaml):
- Line 339: `"Hypertension (SNOMED: 38341003), onset: 2018-03-15, status: active"`
- Line 969: `"Type 2 Diabetes (ICD-10: E11.9)"`
- Line 1051-1052: Same conditions in example output

### Validator validating wrong codes:
- `validate_icd10_code("E11.9")` - NOT in researcher response, from prompt examples
- `lookup_loinc("12345-6")` - Placeholder from citation_format fragment
- `lookup_rxnorm("Aspirin")` - From drug interaction example

---

## Debug Steps (Sequential)

### Step 1: Add Tracing to Multi-Agent Graph
**File:** `api/agent/multi_agent_graph.py`

Add debug logging to trace what each node receives and outputs:
```python
# Before researcher node processes
print(f"[DEBUG] RESEARCHER INPUT: {state.get('messages', [])[-1] if state.get('messages') else 'EMPTY'}")

# After researcher node
print(f"[DEBUG] RESEARCHER OUTPUT: {response_text[:500]}")

# Before validator node
print(f"[DEBUG] VALIDATOR INPUT - Researcher said: {researcher_response[:500]}")

# Before response synthesizer
print(f"[DEBUG] SYNTHESIZER INPUT: {researcher_response[:500]}")
print(f"[DEBUG] SYNTHESIZER - Search results: {tool_results}")
```

### Step 2: Isolate the Hallucination Point
Run the query and check logs to determine WHERE the hallucination happens:
1. Is it in the Researcher output? (describes JSON vs extracts data)
2. Is it in the Validator output? (validates wrong codes)
3. Is it in the Response Synthesizer? (ignores research, copies examples)

### Step 3: Verify Model Temperature
Check if temperature is too high causing creative outputs:
```bash
# In .env or environment
LLM_TEMPERATURE=0.0  # For clinical accuracy
```

### Step 4: Check Model Limitations
Current model: `llama3.1:8b` - this is a small model prone to:
- Instruction confusion (mixing examples with task)
- Context window issues (losing search results)
- Example copying (treating few-shot examples as templates)

Consider testing with larger model or different provider.

---

## Fixes (By Priority)

### Fix 1: Remove Real Medical Data from Examples (HIGH PRIORITY)
**File:** `api/agent/prompts.yaml`

Replace all example conditions/codes with obvious placeholders:

```yaml
# BEFORE (Line 339):
- Condition: "Hypertension (SNOMED: 38341003), onset: 2018-03-15, status: active"

# AFTER:
- Condition: "[CONDITION_NAME] (SNOMED: [CODE]), onset: [DATE], status: [STATUS]"
```

```yaml
# BEFORE (Line 969):
Example: "Type 2 Diabetes (ICD-10: E11.9)"

# AFTER:
Example: "[Condition Name] (ICD-10: [CODE])"
```

```yaml
# BEFORE (Lines 1051-1052):
- Type 2 Diabetes (ICD-10: E11.9) - onset 2015
- Hypertension (SNOMED: 38341003) - onset March 2018

# AFTER:
- [Condition from search results] ([CODE_SYSTEM]: [CODE]) - onset [DATE]
```

### Fix 2: Add Explicit Anti-Hallucination Instructions (HIGH PRIORITY)
**File:** `api/agent/prompts.yaml`

Add to Response Synthesizer prompt:
```yaml
---
## ANTI-HALLUCINATION RULES (CRITICAL)
---

NEVER copy conditions or codes from these examples into your response.
ONLY use data that appears in the ACTUAL search results provided.

EXAMPLES ARE FOR FORMAT ONLY - NOT DATA:
- If example shows "Type 2 Diabetes (E11.9)" - this is NOT the patient's condition
- If example shows "Hypertension (38341003)" - this is NOT the patient's condition
- Extract ONLY conditions that appear in the research findings

VERIFICATION BEFORE OUTPUT:
For each condition you list, ask: "Did this appear in the search results?"
If NO → Do not include it
If YES → Include it with the exact code from search results
```

### Fix 3: Fix Validator to Only Validate Response Codes (MEDIUM)
**File:** `api/agent/prompts.yaml` - Validator section

Change:
```yaml
For ICD-10/LOINC/SNOMED CODE claims:
  → validate_icd10_code (for ICD-10 codes only)
  → lookup_loinc (for LOINC codes only)
```

To:
```yaml
For ICD-10/LOINC/SNOMED CODE claims:
  → ONLY validate codes that appear EXPLICITLY in the Researcher's response text
  → If Researcher used SNOMED codes (e.g., 75498004), do NOT call validate_icd10_code
  → If Researcher did not mention any ICD-10 codes, skip validate_icd10_code entirely
  → NEVER validate codes from examples in your prompt - only from actual response
```

### Fix 4: Add Grounding Check in Response Synthesizer (MEDIUM)
**File:** `api/agent/multi_agent_graph.py`

Before returning final response, add verification:
```python
def _verify_response_grounded(response: str, search_results: List[Dict]) -> bool:
    """Check if response claims match search results."""
    # Extract SNOMED/ICD-10 codes from response
    response_codes = re.findall(r'(?:SNOMED|ICD-10):\s*(\d+\.?\d*)', response)

    # Extract codes from search results
    search_codes = set()
    for result in search_results:
        content = result.get('content', '')
        found_codes = re.findall(r'"code":\s*"(\d+\.?\d*)"', content)
        search_codes.update(found_codes)

    # Check if all response codes are in search results
    for code in response_codes:
        if code not in search_codes:
            print(f"[WARNING] Response contains code {code} not found in search results!")
            return False
    return True
```

### Fix 5: Consider Model Upgrade (LOW - Cost Consideration)
If llama3.1:8b continues to hallucinate after prompt fixes:
1. Try llama3.1:70b or mixtral
2. Test with OpenAI GPT-4 or Anthropic Claude for comparison
3. Implement response caching to manage costs

---

## Verification Checklist

After implementing fixes:

1. [ ] Run query: "What are Danial Larson's active conditions?"
2. [ ] Verify search returns sinusitis and polyp (correct)
3. [ ] Verify Researcher extracts sinusitis and polyp (not describes JSON)
4. [ ] Verify Validator does NOT call validate_icd10_code with E11.9
5. [ ] Verify final response contains ONLY sinusitis and polyp
6. [ ] Verify no mention of Diabetes or Hypertension in response

---

## Quick Test Script

```bash
# Test the agent with debug logging
curl -X POST http://localhost:8000/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the active conditions?",
    "patient_id": "5e81d5b2-af01-4367-9b2e-0cdf479094a4",
    "session_id": "test-debug-session"
  }' | jq .
```

Expected result should contain:
- Acute bacterial sinusitis (SNOMED: 75498004)
- Polyp of colon (SNOMED: 68496003)

NOT:
- Type 2 Diabetes
- Hypertension
