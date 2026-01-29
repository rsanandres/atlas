# Proposed Few-Shot Examples for prompts.yaml

These examples are designed to reinforce the new `include_full_json` rules and strict validation criteria.

---

## RESEARCHER AGENT EXAMPLES

### Example 1: Exhaustive List Request (MANDATORY `include_full_json=True`)

**User Query:**
"List all active conditions for patient 179713d4-..."

**Desired Researcher Behavior:**
```text
REASONING:
STEP 1 - UNDERSTAND: 
User wants a full list of "active conditions".
Resource Type: "Condition".
Intent: "List all" -> **MUST use include_full_json=True**.

STEP 2 - RETRIEVE:
search_patient_records(query="Condition", patient_id="179713d4...", include_full_json=True)

STEP 3 - SYNTHESIZE:
Found 3 conditions in full JSON bundle.
1. Hypertension (I10)
2. COPD (J44.9)
3. Chronic Sinusitis (J32.9)

FINDINGS:
Based on the patient's full medical record, the following active conditions are documented:

1. **Hypertension** (ICD-10: I10)
   - Onset: 2010-05-20
   - Source: [FHIR:Condition/c-123]

2. **Chronic obstructive pulmonary disease (COPD)** (ICD-10: J44.9)
   - Onset: 2012-08-15
   - Source: [FHIR:Condition/c-456]

3. **Chronic Sinusitis** (ICD-10: J32.9)
   - Onset: 2014-02-01
   - Source: [FHIR:Condition/c-789]

CONFIDENCE: HIGH
```

### Example 2: Specific Date Lookup (MANDATORY Date Extraction)

**User Query:**
"What was the patient's weight on 2010-12-07?"

**Desired Researcher Behavior:**
```text
REASONING:
STEP 1 - UNDERSTAND:
Target Data: Weight (Observation).
Target Date: "2010-12-07" -> **CRITICAL**.
Action: Must search for "Observation" AND specifically look for "2010-12-07".
Using include_full_json=True to ensure I don't miss the specific entry in vector chunks.

STEP 2 - RETRIEVE:
search_patient_records(query="Observation 2010-12-07", patient_id="...", include_full_json=True)

STEP 3 - CROSS-REFERENCE:
Found Observation resource with effectiveDateTime="2010-12-07".
Value: 75.3 kg.

FINDINGS:
On December 7, 2010, the patient's recorded body weight was **75.3 kg** (166.0 lbs).

SOURCES:
- [FHIR:Observation/obs-weight-2010] - Body Weight measured on 2010-12-07

CONFIDENCE: HIGH
```

### Example 3: Complex Reasoning & Safety

**User Query:**
"The patient is taking Warfarin. Can they take Aspirin for a headache?"

**Desired Researcher Behavior:**
```text
REASONING:
STEP 1 - UNDERSTAND:
Med 1: Warfarin (Anticoagulant).
Med 2: Aspirin (NSAID/Antiplatelet).
Task: Check interactions.
Tools needed: search_patient_records (to confirm prescriptions), cross_reference_meds.

STEP 2 - RETRIEVE:
1. search_patient_records(query="MedicationRequest status=active", include_full_json=True) -> Found: Warfarin.
2. cross_reference_meds(medication_list=["Warfarin", "Aspirin"]) -> Checks for interactions.

STEP 3 - ANALYSIS:
Interaction found: Warfarin + Aspirin = "Potential interaction: warfarin with aspirin may increase bleeding risk."

FINDINGS:
**SAFETY ALERT:** There is a significant interaction risk.

Combining **Warfarin** with **Aspirin** increases the risk of bleeding events.

**RECOMMENDATION:**
- Avoid Aspirin for pain relief if possible.
- Suggest Acetaminophen (Tylenol) as a safer alternative, but consult the physician.

SOURCES:
- [FHIR:MedicationRequest/med-war-1] - Warfarin prescription

CONFIDENCE: HIGH
```

---

## VALIDATOR AGENT EXAMPLES

### Example 1: PASS (Perfect Execution)

**User Query:** "What is the patient's latest creatinine?"
**Researcher Response:** "The latest creatinine is 1.2 mg/dL on 2023-05-10 [FHIR:Observation/555]."

**Validator Behavior:**
```text
VALIDATION_STATUS: PASS

VERIFIED_CLAIMS:
- Latest Creatinine 1.2 mg/dL: search_patient_records("Observation/555") -> CONFIRMED (Value matches, Date matches)

GROUNDING_CHECK:
- [FHIR:Observation/555]: Verified. Resource exists and belongs to patient.

ISSUES_FOUND: None.
```

### Example 2: NEEDS_REVISION (Hallucinated Citation)

**Researcher Response:** "Patient was diagnosed with Diabetes in 2015 [FHIR:Condition/999]."

**Validator Behavior:**
```text
VALIDATION_STATUS: NEEDS_REVISION

VERIFIED_CLAIMS:
- Diabetes Diagnosis: search_patient_records("Condition/999") -> **FAIL**.
  - Returned chunks IDs: [Condition/c555, Condition/c123]
  - Target ID [Condition/999] NOT found in returned context.

GROUNDING_CHECK:
- [FHIR:Condition/999]: **HALLUCINATION**. The tool returned related chunks, but NONE matched the specific ID cited.

ISSUES_FOUND:
- Hallucinated Citation: [HIGH] You cited 'Condition/999', but that record does not exist.

RECOMMENDATIONS:
- Find the correct ID from the actual search results (e.g., did you mean Condition/c555?).
- Do NOT invent IDs.
```

### Example 3: NEEDS_REVISION (PII Leak)

**Researcher Response:** "Ms. Sarah Jones (DOB 1980-01-01) was seen for..."

**Validator Behavior:**
```text
VALIDATION_STATUS: NEEDS_REVISION

ISSUES_FOUND:
- PII Leak: [HIGH] You included the patient's full name ("Sarah Jones") and specific DOB. This violates HIPAA instructions.

RECOMMENDATIONS:
- SCRUB the name to [PATIENT].
- SCRUB the DOB to "Age 44" or [DOB].
- Retain clinical data but anonymize identity.
```

### Example 4: FAIL (Safety Miss)

**Researcher Response:** "Lisinopril is safe to take with the patient's current Spironolactone."

**Validator Behavior:**
```text
VALIDATION_STATUS: FAIL

VERIFIED_CLAIMS:
- Interaction Safety: get_drug_interactions("Lisinopril") -> **CONTRADICTION FOUND**.
- Major interaction: ACE Inhibitors + Potassium-Sparing Diuretics = Hyperkalemia Risk.

ISSUES_FOUND:
- Safety Miss: [HIGH] You stated the combination is safe, but it carries a risk of life-threatening hyperkalemia.

RECOMMENDATIONS:
- You MUST report this interaction.
- Retract the "safe" claim immediately.
```
