# Session Notes: February 4, 2026

## Summary
Debugged and addressed critical hallucination issues in the medical AI agent system where the LLM was copying example data from prompts into responses instead of using actual search results.

---

## Problem Discovered

**Symptom:** When asking "What are the patient's active conditions?", the agent returned:
- Type 2 Diabetes (ICD-10: E11.9)
- Hypertension (SNOMED: 38341003)

**Actual patient data:**
- Acute bacterial sinusitis (SNOMED: 75498004)
- Polyp of colon (SNOMED: 68496003)

**Root Cause:** The LLM (llama3.1:8b) was copying example conditions from `prompts.yaml` few-shot examples directly into responses, completely ignoring actual search results.

---

## Changes Made

### 1. Prompt Cleanup (`api/agent/prompts.yaml`)

Removed ALL real-looking medical data from examples:
- Removed `Type 2 Diabetes (E11.9)` from examples
- Removed `Hypertension (38341003)` from examples
- Removed `Metformin`, `Lisinopril` medication examples
- Removed `12345-6` LOINC placeholder
- Replaced with generic placeholders like `[CONDITION_NAME]`, `[CODE]`

**Key insight:** Even mentioning codes in "don't do this" warnings caused the model to use them. Small models can't distinguish negative examples.

### 2. Session History Injection Disabled

Added environment variable to disable session history injection:
```python
# api/agent/multi_agent_graph.py
if not os.getenv("ENABLE_SESSION_HISTORY", "").lower() == "true":
    return []  # Don't inject old session data
```

This prevents old hallucinated responses from polluting new sessions.

### 3. Debug Logging Added

Added `DEBUG_HALLUCINATION=true` flag that logs:
- What the Response Synthesizer receives as input
- What the final response contains
- Warnings if known hallucination patterns detected

### 4. Model Upgrade

Changed from `llama3.1:8b` to `qwen2.5:32b`:
- 8B models too small for complex medical prompts
- Can't distinguish examples from real data
- 32B models have better instruction following

---

## Files Modified

| File | Change |
|------|--------|
| `api/agent/prompts.yaml` | Removed all real medical data from examples |
| `api/agent/multi_agent_graph.py` | Added debug logging, disabled session history |
| `.env` | Changed LLM_MODEL to qwen2.5:32b |
| `CLAUDE.md` | Updated model recommendations |
| `MEMORY.md` | Added hallucination learnings |

---

## Research: Prompt Best Practices

Created `PLAN_PROMPT_BEST_PRACTICES.md` based on research:

### Key Findings

1. **Few-shot example contamination** - LLMs are pattern matchers that favor patterns over instructions. Examples with real data get copied.

2. **Solutions (priority order):**
   - Remove all few-shot examples (use zero-shot with detailed instructions)
   - Use structured output schemas (Pydantic)
   - Enforce grounding ("Source: chunk X")
   - Simplify or remove Validator (causes more harm with small models)

### Sources
- [PromptHub - Reduce Hallucinations](https://www.prompthub.us/blog/three-prompt-engineering-methods-to-reduce-hallucinations)
- [OpenAI Community - Few-shot Leaking](https://community.openai.com/t/few-shot-examples-leaking-into-responses-in-q-a-system/996675)
- [LangGraph Structured Output](https://langchain-ai.github.io/langgraph/how-tos/react-agent-structured-output/)

---

## Next Steps

1. **Test with qwen2.5:32b** - See if larger model resolves hallucination
2. **Remove remaining few-shot examples** - Replace with explicit extraction instructions
3. **Implement structured output** - Use Pydantic schemas between agent nodes
4. **Consider simple graph mode** - `AGENT_GRAPH_TYPE=simple` bypasses Validator

---

## Commands Reference

```bash
# Reload prompts without restart
curl -X POST http://localhost:8000/agent/reload-prompts

# Start with debug logging
DEBUG_HALLUCINATION=true uvicorn api.main:app --reload --port 8000

# Test patient query
curl -X POST http://localhost:8000/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the active conditions?", "patient_id": "5e81d5b2-af01-4367-9b2e-0cdf479094a4"}'
```

---

## Test Patient Reference

**Danial Larson** - `5e81d5b2-af01-4367-9b2e-0cdf479094a4`
- Actual conditions: Acute bacterial sinusitis (75498004), Polyp of colon (68496003)
- Use this patient to verify hallucination fixes
