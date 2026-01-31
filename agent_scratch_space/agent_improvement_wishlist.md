# Agent Improvement Wishlist

> Future enhancements tracked for later implementation  
> Created: 2026-01-30

---

## 🚨 URGENT (Fix in Current Sprint)

### 1. Few-Shot Examples Don't Match Tool Output
**Status:** 🔴 CRITICAL — Currently in implementation_plan.md  
**Problem:** Examples show `[FHIR:Condition/c-123]` format but actual `search_patient_records` returns `{"chunks": [{"id": "...", "content": "..."}]}`  
**Impact:** Agent is confused about expected response format  
**Fix:** Rewrite all 3 examples to show actual tool input/output

### 2. Example 2 Missing patient_id
**Status:** 🔴 CRITICAL — Currently in implementation_plan.md  
**Problem:** Example doesn't include patient_id parameter, violating core requirement  
**Fix:** Add patient context inference + explicit patient_id in tool call

### 3. Example 3 Doesn't Check Existing Meds
**Status:** 🔴 CRITICAL — Currently in implementation_plan.md  
**Problem:** Drug interaction check only checks user-mentioned drugs, not patient's full medication list  
**Fix:** Show 2-step process: get meds first, then cross-reference

---

## 🔴 High Priority (Deferred for Complexity)

### 1. Multi-Patient Query Support
**Status:** Out of scope for v1  
**Description:** Handle queries across multiple patient IDs in a single request.
- Side-by-side comparisons
- Aggregate statistics (with proper authorization)
- Table-formatted multi-patient outputs
**Why Deferred:** Single-patient workflows need to be solid first.

### 2. Calculator Loop Prevention
**Status:** Needs testing framework  
**Description:** Clinical calculators (GFR, BMI, etc.) sometimes loop indefinitely.
- Add circuit breaker / max iteration limits
- Create dedicated test suite for calculators
- Log inputs/outputs for debugging

---

## 🟡 Medium Priority (Quality of Life)

### 3. Citation Hyperlinks
**Status:** Wishlist  
**Description:** Make FHIR citations clickable links to actual resources.
- `[FHIR:Observation/123]` → hyperlink to FHIR viewer
- Requires frontend integration

### 4. External Patient Picker UI
**Status:** Discussion needed  
**Description:** Consider a UI for selecting patients before asking questions, rather than the agent parsing patient IDs from natural language.
- **Pros:** Removes ambiguity, guarantees valid patient context
- **Cons:** Less conversational, may feel clunky
- **Open Question:** Does this defeat the purpose of a RAG agent?

### 5. Web Search MCP Integration
**Status:** Blocked (HIPAA concerns)  
**Description:** Add MCP for general web search capabilities.
- Would enable real-time drug lookups, current guidelines
- **Blocker:** PHI could leak to external search services
- **Workaround:** Consider curated, approved medical APIs only

---

## 🟢 Low Priority (Nice to Have)

### 6. Guardrails Package Integration
**Status:** Investigate existing setup  
**Description:** User mentioned having Guardrails for hallucination/PII detection.
- Verify if already integrated
- If not, add as validation layer
- May reduce validator complexity

### 7. Improved Patient ID vs ICD Code Detection
**Status:** Consider tool-level implementation  
**Description:** Currently relies on prompt guidance; could be more robust.
- UUIDs (hyphens, alphanumeric) → patient ID
- Short codes (letter + digits) → ICD-10
- Option: Add pre-processing validation function

### 8. Response Format Alignment with Tool Output
**Status:** Needs investigation  
**Description:** Few-shot examples show formats that don't match actual `search_patient_records` output.
- Review actual tool response schema
- Update examples to reflect real output format

---

## 📝 Notes

- This list will be updated as we iterate on the prompt system
- Items move up in priority based on user feedback and testing results
