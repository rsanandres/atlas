# Plan: Medical AI Agent Prompting Best Practices

## Research Summary

Based on research from multiple sources, the current prompting approach has several fundamental issues that cause hallucinations.

### Root Cause Analysis

**Problem 1: Few-Shot Example Contamination**
- LLMs are "pattern matchers" that favor patterns over instructions ([OpenAI Community](https://community.openai.com/t/few-shot-examples-leaking-into-responses-in-q-a-system/996675))
- When you show examples with real-looking medical data (E11.9, Hypertension), the model treats them as legitimate context
- The model cannot distinguish "this is an example of format" from "this is real data"
- Even mentioning codes in "don't do this" warnings causes the model to use them

**Problem 2: No Structured Output Enforcement**
- The Researcher returns free-form text that the Response Synthesizer must interpret
- No schema validation between agent nodes
- LangGraph best practice: Use dedicated formatting nodes with Pydantic schemas ([LangGraph Docs](https://langchain-ai.github.io/langgraph/how-tos/react-agent-structured-output/))

**Problem 3: No Grounding Enforcement**
- Researcher describes JSON structure instead of extracting data
- No "According to [source]" grounding requirement
- Response Synthesizer has no way to verify claims against actual search results

---

## Recommended Solutions

### Solution 1: Eliminate Real-Looking Examples (CRITICAL)

**Current Approach (Wrong):**
```yaml
**Tool Response:**
{"chunks": [{"content": "Condition: Hypertension, code: I10"}]}

**Response:**
Active conditions:
1. **Hypertension** (ICD-10: I10)
```

**Better Approach - Fantastical/Irrelevant Examples:**
```yaml
**Tool Response:**
{"chunks": [{"content": "Condition: EXAMPLE_CONDITION_A, code: EXAMPLE_CODE_A"}]}

**Response:**
Active conditions:
1. **[Name from search]** ([Code system]: [Code from search])
```

**Best Approach - No Examples, Use Structured Output:**
Remove few-shot examples entirely and enforce output structure via Pydantic schemas.

### Solution 2: Implement Structured Output Between Nodes

**Current Flow:**
```
Researcher → (free text) → Validator → (free text) → Response Synthesizer
```

**Recommended Flow:**
```
Researcher → (ResearcherOutput schema) → Validator → (ValidationResult schema) → Response Synthesizer → (FinalResponse schema)
```

**Pydantic Schemas:**
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class ExtractedCondition(BaseModel):
    name: str = Field(description="Condition name from FHIR data")
    code: str = Field(description="SNOMED or ICD-10 code")
    code_system: str = Field(description="SNOMED or ICD-10")
    status: str = Field(description="active/resolved/inactive")
    onset_date: Optional[str] = Field(description="Date from onsetDateTime field")
    source_chunk_id: str = Field(description="ID of the chunk this was extracted from")

class ResearcherOutput(BaseModel):
    """Structured output from Researcher agent."""
    conditions: List[ExtractedCondition] = Field(default_factory=list)
    medications: List[ExtractedMedication] = Field(default_factory=list)
    observations: List[ExtractedObservation] = Field(default_factory=list)
    raw_search_results: List[str] = Field(description="IDs of chunks searched")
    confidence: str = Field(description="HIGH/MEDIUM/LOW")
    uncertainties: List[str] = Field(default_factory=list)

class ValidationResult(BaseModel):
    """Structured output from Validator agent."""
    status: str = Field(description="PASS/NEEDS_REVISION/FAIL")
    verified_claims: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
```

### Solution 3: Chain-of-Verification (CoVE) Pattern

Based on [PromptHub research](https://www.prompthub.us/blog/three-prompt-engineering-methods-to-reduce-hallucinations), implement a 4-step verification:

1. **Generate**: Researcher produces initial answer
2. **Plan Verification**: Generate questions to verify claims
3. **Execute Verification**: Run verification questions through tools
4. **Final Answer**: Produce answer using verification results

**Implementation:**
```python
async def _verification_node(state: AgentState) -> AgentState:
    """Verify claims before passing to Response Synthesizer."""
    researcher_output = state.get("researcher_output")

    # Extract claimed conditions from structured output
    for condition in researcher_output.conditions:
        # Verify the chunk_id actually contains this condition
        chunk = get_chunk_by_id(condition.source_chunk_id)
        if condition.code not in chunk.content:
            # Flag as unverified
            condition.verified = False
```

### Solution 4: "According to..." Grounding

Force all claims to cite specific sources. Research shows this improves accuracy by up to 20%.

**Prompt Change:**
```yaml
OUTPUT REQUIREMENTS:
Every clinical claim MUST include a source reference.

Format: "[Claim] (Source: chunk ID [X])"

Example:
- "Patient has Acute bacterial sinusitis (Source: chunk b20106c0)"

If you cannot cite a specific chunk for a claim, DO NOT include that claim.
```

### Solution 5: Minimal or Zero Few-Shot Examples

**Option A: Zero-Shot with Strong Instructions**
Remove all examples, use detailed instructions instead:
```yaml
TASK: Extract conditions from the search results below.

EXTRACTION RULES:
1. Find JSON objects with "resourceType": "Condition"
2. Extract "code.coding[0].display" as the condition name
3. Extract "code.coding[0].code" as the code
4. Extract "clinicalStatus" for status
5. Only include conditions with clinicalStatus="active"
```

**Option B: Single Abstract Example**
Use ONE example with obviously fake data:
```yaml
EXAMPLE (format only, not real data):
Search result: {"code": {"display": "PLACEHOLDER"}, "clinicalStatus": "active"}
Output: PLACEHOLDER (code: XXXXX) - active

YOUR TASK: Apply this format to the REAL search results below.
```

---

## Implementation Plan

### Phase 1: Structured Output Schemas (High Impact)

**Files to modify:**
- `api/agent/output_schemas.py` - Add Pydantic schemas
- `api/agent/multi_agent_graph.py` - Use `with_structured_output()`
- `api/agent/prompts.yaml` - Update prompts to match schemas

**Steps:**
1. Create `ResearcherOutput`, `ValidationResult`, `FinalResponse` Pydantic models
2. Modify `_get_researcher_agent()` to use `llm.with_structured_output(ResearcherOutput)`
3. Update Researcher prompt to instruct structured extraction
4. Modify `_get_validator_agent()` to use `llm.with_structured_output(ValidationResult)`
5. Pass structured data between nodes instead of free text

### Phase 2: Remove All Few-Shot Examples

**Files to modify:**
- `api/agent/prompts.yaml` - Complete rewrite of examples sections

**Steps:**
1. Remove all few-shot examples from Researcher prompt
2. Remove all few-shot examples from Validator prompt
3. Remove all few-shot examples from Response Synthesizer prompt
4. Replace with detailed extraction instructions
5. Add explicit field-by-field extraction rules

### Phase 3: Grounding Enforcement

**Files to modify:**
- `api/agent/prompts.yaml` - Add grounding requirements
- `api/agent/multi_agent_graph.py` - Add verification step

**Steps:**
1. Require chunk ID citations for every claim
2. Add post-processing to verify citations exist
3. Strip any claims without valid citations

### Phase 4: Verification Node

**Files to modify:**
- `api/agent/multi_agent_graph.py` - Add verification node

**Steps:**
1. Add `_verification_node()` between Researcher and Response Synthesizer
2. Cross-check extracted data against raw search results
3. Flag/remove unverified claims

---

## Priority Order

1. **Phase 2: Remove Few-Shot Examples** - Quick win, immediate impact
2. **Phase 1: Structured Output** - Medium effort, high impact
3. **Phase 3: Grounding** - Medium effort, medium impact
4. **Phase 4: Verification Node** - Higher effort, ensures quality

---

## Sources

- [LLM Hallucinations Guide - Lakera](https://www.lakera.ai/blog/guide-to-hallucinations-in-large-language-models)
- [Three Methods to Reduce Hallucinations - PromptHub](https://www.prompthub.us/blog/three-prompt-engineering-methods-to-reduce-hallucinations)
- [Few-Shot Examples Leaking - OpenAI Community](https://community.openai.com/t/few-shot-examples-leaking-into-responses-in-q-a-system/996675)
- [LangGraph Structured Output - LangChain](https://langchain-ai.github.io/langgraph/how-tos/react-agent-structured-output/)
- [Task Contamination - ArXiv](https://arxiv.org/html/2312.16337v1)
- [LLM Agent Hallucinations Survey - ArXiv](https://arxiv.org/html/2509.18970v1)
