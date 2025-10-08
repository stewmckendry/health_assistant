# Lightweight Decisional Query Support for Dr. OPA Tools

**Date:** 2025-10-08
**Author:** AI Assistant
**Status:** ✅ **RECOMMENDED** - Minimal surgery, high impact

---

## Executive Summary

Enable Dr. OPA tools to handle **decisional queries** (compliance checks, treatment validation, binary recommendations) by adding a **lightweight post-retrieval synthesis layer** rather than a full query processor.

### Strategy
```
Current:  Query → Triage → Filtered Retrieval → Return Results
Enhanced: Query → Triage* → Filtered Retrieval → Synthesis** → Return Answer

          * Triage detects decisional vs informational intent
          ** Synthesis activates ONLY for decisional queries
```

**Impact:**
- ✅ Supports all 3 decisional query types
- ✅ Minimal latency increase (~500ms for decisional queries only)
- ✅ No change to informational queries (backward compatible)
- ✅ ~50 lines of code per tool

---

## Architecture: Post-Retrieval Synthesis Layer

### Design Pattern
```python
# Step 1: Enhanced Triage (detect decisional vs informational)
classification = await classify_query(query, openai_client)
# NEW FIELD: classification['is_decisional'] = True/False

# Step 2: Standard Retrieval (unchanged)
results = await retrieve_with_filters(semantic_search, query, classification)

# Step 3: Conditional Synthesis (NEW - only if decisional)
if classification['is_decisional']:
    synthesized_answer = await synthesize_decisional_answer(
        query=query,
        classification=classification,
        retrieved_chunks=results,
        llm_client=openai_client
    )
    return {
        'decisional_answer': synthesized_answer,  # Structured answer
        'supporting_evidence': results,            # Raw chunks for transparency
        'classification': classification
    }
else:
    # Informational query - return as before
    return {
        'items': results,
        'classification': classification
    }
```

**Key principles:**
1. **Conditional activation**: Synthesis layer only runs for decisional queries
2. **Transparent**: Always return raw evidence alongside synthesis
3. **Backward compatible**: Informational queries unchanged
4. **Tool-agnostic**: Same pattern works for all OPA tools

---

## Implementation: 3 Decisional Query Types

### 1. Cross-Policy Compliance (CPSO)

#### Example Query
```
"Does this practice comply with CPSO requirements?
- Virtual consult for new patient (no prior in-person visit)
- Patient located in another province
- Prescribing controlled substance (opioid for chronic pain)"
```

#### Enhanced Triage Detection
```python
# In cpso_triage.py - add decisional detection
async def classify_cpso_policy_query(query: str, openai_client) -> Dict:
    # Existing classification...

    # NEW: Detect decisional intent
    decisional_keywords = [
        "does this comply", "can i", "should i", "is this allowed",
        "do i need to", "am i required", "is it okay to"
    ]
    is_decisional = any(keyword in query.lower() for keyword in decisional_keywords)

    # Also detect if query describes a specific scenario/practice
    has_scenario = "?" in query and len(query.split("\n")) > 1  # Multi-line scenario

    return {
        **existing_classification,
        "is_decisional": is_decisional or has_scenario,
        "query_type": "compliance_check" if is_decisional else "policy_lookup"
    }
```

#### Synthesis Function
```python
# In cpso_helpers.py - add synthesis function
async def synthesize_compliance_answer(
    query: str,
    classification: Dict,
    retrieved_chunks: List[Dict],
    llm_client
) -> Dict:
    """
    Synthesize compliance answer from multiple policy chunks.

    Returns:
        {
            "compliant": "yes" | "no" | "partial" | "unclear",
            "reasoning": "Brief explanation referencing specific policies",
            "requirements": ["List of requirements that must be met"],
            "non_compliance_risks": ["List of areas where practice may not comply"],
            "recommendations": ["Suggested actions to ensure compliance"],
            "relevant_policies": [{"policy": "Virtual Care", "section": "3.2", ...}],
            "confidence": 0.0-1.0
        }
    """
    # Build context from retrieved chunks
    policy_context = []
    for chunk in retrieved_chunks[:10]:  # Top 10 most relevant
        policy_context.append({
            'policy': chunk.get('document_title', 'Unknown'),
            'policy_level': chunk.get('policy_level', 'unknown'),
            'section': chunk.get('section_heading', ''),
            'text': chunk.get('text', '')[:1000]  # Limit context per chunk
        })

    prompt = f"""You are a CPSO policy compliance advisor. Analyze this clinical practice scenario for compliance.

Scenario/Question:
{query}

Relevant CPSO Policy Excerpts:
{json.dumps(policy_context, indent=2)}

Analyze compliance and respond with JSON:
{{
    "compliant": "yes" | "no" | "partial" | "unclear",
    "reasoning": "<1-2 sentence explanation citing specific policy requirements>",
    "requirements": ["<list ALL requirements from policies that apply to this scenario>"],
    "non_compliance_risks": ["<areas where scenario may not comply>"],
    "recommendations": ["<specific actions to ensure compliance>"],
    "relevant_policies": [
        {{"policy": "<policy name>", "section": "<section ref>", "requirement_level": "expectation|advice"}}
    ],
    "confidence": <0.0-1.0>
}}

Guidelines:
- "yes" = practice clearly complies with all applicable policies
- "no" = practice clearly violates at least one expectation-level policy
- "partial" = complies with some requirements but not others
- "unclear" = insufficient information in policies or scenario to determine

Be conservative - if unclear, say so. Cite specific policy requirements in reasoning."""

    try:
        response = await llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        logger.error(f"Compliance synthesis error: {e}")
        return {
            "compliant": "unclear",
            "reasoning": "Error during compliance analysis",
            "requirements": [],
            "non_compliance_risks": [],
            "recommendations": ["Please consult CPSO policies directly"],
            "relevant_policies": [],
            "confidence": 0.0
        }
```

#### Response Format
```json
{
  "decisional_answer": {
    "compliant": "no",
    "reasoning": "Virtual care policy requires in-person assessment for new patients before prescribing controlled substances. Prescribing policy requires verification of patient location and provincial licensing.",
    "requirements": [
      "Initial in-person assessment for new patients (Virtual Care Policy, Expectation 3.2)",
      "Verification of patient location and physician licensing in that jurisdiction (Prescribing Policy, Expectation 2.1)",
      "Controlled substance prescribing requires established physician-patient relationship (Prescribing Policy, Expectation 4.3)"
    ],
    "non_compliance_risks": [
      "No prior in-person visit for new patient",
      "Patient in different province (licensing jurisdiction unclear)",
      "Controlled substance prescription without established relationship"
    ],
    "recommendations": [
      "Require in-person initial assessment before any controlled substance prescription",
      "Verify provincial licensing for patient's location",
      "Establish physician-patient relationship through in-person visit before opioid prescription"
    ],
    "relevant_policies": [
      {"policy": "Virtual Care", "section": "3.2", "requirement_level": "expectation"},
      {"policy": "Prescribing Drugs", "section": "2.1, 4.3", "requirement_level": "expectation"}
    ],
    "confidence": 0.9
  },
  "supporting_evidence": [
    {/* raw policy chunks */}
  ]
}
```

---

### 2. Evidence-Based Practice Validation (Quality Standards)

#### Example Query
```
"Is this treatment aligned with quality standards?
- Patient: Type 2 diabetes, HbA1c 8.5%
- Current treatment: Metformin 1000mg BID
- Considering: Adding GLP-1 agonist (semaglutide)
- Question: Does this align with Ontario Health diabetes quality standards?"
```

#### Enhanced Triage Detection
```python
# In qs_triage.py - add decisional detection
async def classify_quality_standards_query(query: str, openai_client) -> Dict:
    # Existing classification...

    # NEW: Detect practice validation queries
    validation_keywords = [
        "is this aligned", "does this meet", "is this appropriate",
        "should i", "is this recommended", "does this follow"
    ]
    is_decisional = any(keyword in query.lower() for keyword in validation_keywords)

    # Detect clinical scenario description
    has_patient_scenario = any(word in query.lower() for word in ["patient", "treatment", "considering"])

    return {
        **existing_classification,
        "is_decisional": is_decisional or has_patient_scenario,
        "query_type": "practice_validation" if is_decisional else "standard_lookup"
    }
```

#### Synthesis Function
```python
# In qs_helpers.py - add synthesis function
async def synthesize_validation_answer(
    query: str,
    classification: Dict,
    retrieved_chunks: List[Dict],
    llm_client
) -> Dict:
    """
    Validate clinical practice against quality standards.

    Returns:
        {
            "aligned": "yes" | "no" | "partial" | "insufficient_info",
            "reasoning": "Explanation citing specific quality statements",
            "supporting_statements": ["Quality statements that support this practice"],
            "gaps": ["Areas where practice deviates from standards"],
            "recommendations": ["Actions to improve alignment with standards"],
            "relevant_standards": [{"standard": "Diabetes", "statement": "3.2", ...}],
            "confidence": 0.0-1.0
        }
    """
    # Build context from quality standard statements
    standard_context = []
    for chunk in retrieved_chunks[:10]:
        standard_context.append({
            'standard': chunk.get('document_title', 'Unknown'),
            'statement_number': chunk.get('metadata', {}).get('statement_number', ''),
            'statement_type': chunk.get('metadata', {}).get('statement_type', ''),
            'text': chunk.get('text', '')[:1000]
        })

    prompt = f"""You are a quality standards advisor. Evaluate this clinical practice against Ontario Health quality standards.

Clinical Practice Scenario:
{query}

Relevant Quality Standard Statements:
{json.dumps(standard_context, indent=2)}

Analyze alignment and respond with JSON:
{{
    "aligned": "yes" | "no" | "partial" | "insufficient_info",
    "reasoning": "<1-2 sentence explanation citing specific quality statements>",
    "supporting_statements": ["<quality statements that support this practice>"],
    "gaps": ["<areas where practice deviates from or doesn't address standards>"],
    "recommendations": ["<specific actions to improve alignment>"],
    "relevant_standards": [
        {{"standard": "<standard name>", "statement": "<statement number>", "statement_type": "<type>"}}
    ],
    "confidence": <0.0-1.0>
}}

Guidelines:
- "yes" = practice clearly aligns with quality statements
- "no" = practice contradicts quality statements
- "partial" = practice aligns with some aspects but misses others
- "insufficient_info" = quality standards don't address this specific scenario

Focus on evidence-based recommendations, not absolute requirements."""

    try:
        response = await llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        logger.error(f"Validation synthesis error: {e}")
        return {
            "aligned": "insufficient_info",
            "reasoning": "Error during practice validation",
            "supporting_statements": [],
            "gaps": [],
            "recommendations": ["Please consult quality standards directly"],
            "relevant_standards": [],
            "confidence": 0.0
        }
```

#### Response Format
```json
{
  "decisional_answer": {
    "aligned": "yes",
    "reasoning": "Diabetes quality standard Statement 3.2 recommends intensifying therapy (including GLP-1 agonists) when HbA1c remains >7% despite metformin. Patient's HbA1c of 8.5% on metformin indicates need for additional therapy.",
    "supporting_statements": [
      "Statement 3.2: Intensify pharmacological therapy when glycemic targets not met with metformin monotherapy",
      "Statement 3.4: Consider GLP-1 agonists for patients with inadequate glycemic control and cardiovascular risk factors",
      "Statement 4.1: Target HbA1c ≤7% for most adults with type 2 diabetes"
    ],
    "gaps": [],
    "recommendations": [
      "Consider cardiovascular risk assessment to determine if GLP-1 agonist with CV benefit preferred",
      "Ensure patient education on GLP-1 agonist administration and side effects (Statement 5.2)",
      "Plan for HbA1c monitoring in 3 months to assess therapy effectiveness (Statement 6.1)"
    ],
    "relevant_standards": [
      {"standard": "Type 2 Diabetes", "statement": "3.2", "statement_type": "pharmacological_therapy"},
      {"standard": "Type 2 Diabetes", "statement": "3.4", "statement_type": "medication_selection"}
    ],
    "confidence": 0.95
  },
  "supporting_evidence": [
    {/* raw quality standard chunks */}
  ]
}
```

---

### 3. Choosing Wisely Binary Recommendations

#### Example Query
```
"Should I order imaging for this patient?
- 35-year-old with acute low back pain
- No red flags (no trauma, no neurological deficits, no fever)
- Pain for 5 days
- No prior episodes
- Patient requesting MRI"
```

#### Enhanced Triage Detection
```python
# In choosing_wisely_triage.py - add decisional detection
async def classify_choosing_wisely_query(query: str, openai_client) -> Dict:
    # Existing classification...

    # NEW: Detect binary recommendation queries
    binary_keywords = [
        "should i order", "should i perform", "should i do",
        "is this test necessary", "do i need to", "is imaging indicated"
    ]
    is_decisional = any(keyword in query.lower() for keyword in binary_keywords)

    # Detect patient scenario
    has_patient_scenario = "patient" in query.lower() and any(
        word in query.lower() for word in ["year", "old", "symptom", "complain", "history"]
    )

    return {
        **existing_classification,
        "is_decisional": is_decisional or has_patient_scenario,
        "query_type": "binary_recommendation" if is_decisional else "recommendation_lookup"
    }
```

#### Synthesis Function
```python
# In choosing_wisely_helpers.py - add synthesis function
async def synthesize_binary_recommendation(
    query: str,
    classification: Dict,
    retrieved_chunks: List[Dict],
    llm_client
) -> Dict:
    """
    Provide binary recommendation (do/don't) based on Choosing Wisely guidelines.

    Returns:
        {
            "recommendation": "avoid" | "consider" | "recommended" | "insufficient_info",
            "reasoning": "Explanation citing Choosing Wisely recommendations",
            "supporting_recommendations": ["CW recommendations that apply"],
            "red_flags": ["Scenarios where recommendation would change"],
            "alternative_approaches": ["What to do instead if avoiding test/treatment"],
            "relevant_specialties": [{"specialty": "...", "recommendation": "..."}],
            "confidence": 0.0-1.0
        }
    """
    # Build context from Choosing Wisely recommendations
    cw_context = []
    for chunk in retrieved_chunks[:8]:
        cw_context.append({
            'specialty': chunk.get('specialty', 'Unknown'),
            'organization': chunk.get('organization', ''),
            'recommendation': chunk.get('text', '')[:800]
        })

    prompt = f"""You are a Choosing Wisely advisor. Evaluate whether this test/treatment/procedure is appropriate.

Clinical Scenario:
{query}

Relevant Choosing Wisely Recommendations:
{json.dumps(cw_context, indent=2)}

Provide recommendation in JSON:
{{
    "recommendation": "avoid" | "consider" | "recommended" | "insufficient_info",
    "reasoning": "<1-2 sentence explanation citing Choosing Wisely recommendations>",
    "supporting_recommendations": ["<CW recommendations that apply to this scenario>"],
    "red_flags": ["<clinical scenarios where recommendation would change>"],
    "alternative_approaches": ["<what to do instead if avoiding the test/treatment>"],
    "relevant_specialties": [
        {{"specialty": "<specialty>", "recommendation_summary": "<brief summary>"}}
    ],
    "confidence": <0.0-1.0>
}}

Guidelines:
- "avoid" = Choosing Wisely explicitly recommends against in this scenario
- "consider" = May be appropriate depending on additional factors
- "recommended" = Scenario falls outside Choosing Wisely "avoid" categories (appropriate to order)
- "insufficient_info" = Choosing Wisely doesn't address this specific scenario

Remember: Choosing Wisely identifies tests/treatments to AVOID. If scenario doesn't match avoidance criteria, it may be appropriate."""

    try:
        response = await llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        logger.error(f"Binary recommendation synthesis error: {e}")
        return {
            "recommendation": "insufficient_info",
            "reasoning": "Error during recommendation analysis",
            "supporting_recommendations": [],
            "red_flags": [],
            "alternative_approaches": [],
            "relevant_specialties": [],
            "confidence": 0.0
        }
```

#### Response Format
```json
{
  "decisional_answer": {
    "recommendation": "avoid",
    "reasoning": "Choosing Wisely (Family Medicine, Radiology) explicitly recommends against imaging for acute low back pain without red flags in first 6 weeks. Patient has no red flags and symptom duration is only 5 days.",
    "supporting_recommendations": [
      "Family Medicine: Don't do imaging for low back pain within the first six weeks, unless red flags are present",
      "Radiology: Don't routinely order spinal imaging for acute non-specific low back pain",
      "Emergency Medicine: Avoid lumbar spine imaging in the emergency department for adults with non-traumatic back pain unless red flags are present"
    ],
    "red_flags": [
      "Trauma or significant injury",
      "Progressive neurological deficits (bowel/bladder dysfunction, saddle anesthesia)",
      "Fever or signs of infection",
      "History of cancer",
      "Unexplained weight loss",
      "Age >50 with new onset pain (concern for fracture)",
      "Symptoms persisting >6 weeks despite conservative management"
    ],
    "alternative_approaches": [
      "Reassurance and patient education about natural history (90% resolve within 6 weeks)",
      "Non-pharmacological management: remain active, avoid bed rest",
      "Analgesia: acetaminophen or NSAIDs as needed",
      "Physiotherapy referral if not improving in 2-3 weeks",
      "Re-evaluate in 6 weeks - imaging if symptoms persist or worsen"
    ],
    "relevant_specialties": [
      {"specialty": "Family Medicine", "recommendation_summary": "Avoid imaging <6 weeks without red flags"},
      {"specialty": "Radiology", "recommendation_summary": "Don't routinely image acute non-specific low back pain"},
      {"specialty": "Emergency Medicine", "recommendation_summary": "Avoid lumbar imaging for non-traumatic pain without red flags"}
    ],
    "confidence": 0.95
  },
  "supporting_evidence": [
    {/* raw Choosing Wisely recommendation chunks */}
  ]
}
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (1-2 hours per tool)

#### 1. Add Decisional Detection to Triage
```python
# Pattern for all tools (cpso_triage.py, qs_triage.py, choosing_wisely_triage.py, cep_triage.py)

def detect_decisional_intent(query: str) -> bool:
    """
    Detect if query expects a decisional answer vs informational lookup.
    """
    # Decisional keywords
    decisional_patterns = [
        r"should\s+i",           # "should I order"
        r"can\s+i",              # "can I prescribe"
        r"do\s+i\s+need",        # "do I need to"
        r"does\s+this\s+comply", # "does this comply"
        r"is\s+this\s+aligned",  # "is this aligned"
        r"is\s+this\s+appropriate",
        r"am\s+i\s+required"
    ]

    import re
    for pattern in decisional_patterns:
        if re.search(pattern, query.lower()):
            return True

    # Multi-line scenario descriptions (patient cases)
    if "\n" in query and len(query.split("\n")) > 2:
        return True

    return False

# Add to existing classify_* functions:
classification['is_decisional'] = detect_decisional_intent(query)
classification['query_type'] = "decisional_..." if is_decisional else "lookup_..."
```

#### 2. Create Synthesis Functions
```python
# In each helper file (cpso_helpers.py, qs_helpers.py, etc.)

async def synthesize_decisional_answer(
    query: str,
    classification: Dict,
    retrieved_chunks: List[Dict],
    llm_client,
    synthesis_type: str  # "compliance" | "validation" | "recommendation"
) -> Dict:
    """
    Route to appropriate synthesis function based on type.
    """
    if synthesis_type == "compliance":
        return await synthesize_compliance_answer(query, classification, retrieved_chunks, llm_client)
    elif synthesis_type == "validation":
        return await synthesize_validation_answer(query, classification, retrieved_chunks, llm_client)
    elif synthesis_type == "recommendation":
        return await synthesize_binary_recommendation(query, classification, retrieved_chunks, llm_client)
    else:
        raise ValueError(f"Unknown synthesis type: {synthesis_type}")
```

#### 3. Update Tool Functions
```python
# In server.py - update each tool function (policy_check, quality_standards, etc.)

async def policy_check(request: StandardToolRequest) -> dict:
    """CPSO policy compliance and lookup tool."""
    # Step 1: Triage (NOW DETECTS DECISIONAL)
    classification = await classify_cpso_policy_query(request.query, openai_client)

    # Step 2: Retrieval (unchanged)
    if classification['intent'] == 'policy_discovery':
        results = await retrieve_policy_overviews(...)
    else:
        results = await retrieve_detailed_chunks(...)

    # Step 3: CONDITIONAL SYNTHESIS (NEW)
    if classification.get('is_decisional', False):
        decisional_answer = await synthesize_decisional_answer(
            query=request.query,
            classification=classification,
            retrieved_chunks=results,
            llm_client=openai_client,
            synthesis_type="compliance"
        )

        return {
            'decisional_answer': decisional_answer,
            'supporting_evidence': results,
            'classification': classification,
            'response_type': 'decisional'
        }
    else:
        # Informational query - return as before
        return format_policy_response(results, classification, request.query)
```

---

### Phase 2: Testing & Validation

#### Test Cases for Each Tool

**CPSO Policy:**
```python
decisional_test_cases = [
    {
        "query": "Can I prescribe antibiotics over the phone for a patient I've never seen?",
        "expected_recommendation": "no",
        "expected_policies": ["prescribing", "virtual_care"]
    },
    {
        "query": """Does this comply with CPSO requirements?
        - Telemedicine consult for established patient
        - Patient requesting sick note
        - No physical examination performed""",
        "expected_recommendation": "partial",
        "expected_policies": ["virtual_care", "third_party_forms"]
    }
]
```

**Quality Standards:**
```python
decisional_test_cases = [
    {
        "query": """Is this treatment plan aligned with quality standards?
        Patient: CHF with EF 35%
        Current: ACE inhibitor, beta-blocker
        Question: Should I add spironolactone?""",
        "expected_recommendation": "yes",
        "expected_standards": ["heart_failure"]
    }
]
```

**Choosing Wisely:**
```python
decisional_test_cases = [
    {
        "query": "Should I order annual ECG for asymptomatic 45-year-old with no cardiac risk factors?",
        "expected_recommendation": "avoid",
        "expected_specialties": ["cardiology", "family_medicine"]
    }
]
```

---

## Performance Impact

### Informational Queries (No Change)
```
Query → Triage (400ms) → Retrieval (600ms) → Format (50ms) = 1050ms
Cost: $0.0002 (1 LLM call)
```

### Decisional Queries (New Path)
```
Query → Triage (400ms) → Retrieval (600ms) → Synthesis (500ms) → Format (50ms) = 1550ms
Cost: $0.0004 (2 LLM calls: triage + synthesis)
```

**Impact:**
- ✅ +500ms latency for decisional queries only (~50% increase)
- ✅ 2x cost for decisional queries (but still cheap: $0.0004 vs $0.0008 for full query processor)
- ✅ 0ms impact for informational queries (backward compatible)

---

## Advantages Over Full Query Processor

| Feature | Full Query Processor | Post-Retrieval Synthesis |
|---------|---------------------|-------------------------|
| **Latency** | +2-3s | +0.5s (decisional only) |
| **Cost** | 4x ($0.0008) | 2x ($0.0004, decisional only) |
| **Complexity** | ~500 lines/tool | ~50 lines/tool |
| **LLM Calls** | 4 calls | 2 calls |
| **Backward Compatible** | ❌ No | ✅ Yes |
| **Supports Decisional** | ✅ Yes | ✅ Yes |
| **Supports Informational** | ✅ Yes | ✅ Yes (unchanged) |

---

## Code Example: End-to-End

```python
# server.py - Updated quality_standards tool

async def quality_standards(request: StandardToolRequest) -> dict:
    """
    Ontario Health quality standards search with decisional support.

    Now supports:
    - Informational: "What are the diabetes quality standards?"
    - Decisional: "Is my treatment plan aligned with quality standards?"
    """
    logger.info(f"Quality standards query: {request.query}")

    # Step 1: Enhanced triage (detects decisional vs informational)
    classification = await classify_quality_standards_query(
        query=request.query,
        openai_client=openai_client
    )

    logger.info(f"Classification: intent={classification['intent']}, "
                f"is_decisional={classification.get('is_decisional', False)}")

    # Step 2: Retrieval based on intent (unchanged)
    if classification['intent'] == 'standard_discovery':
        results = await retrieve_standard_overviews(
            semantic_search=semantic_search,
            query=request.query,
            standard_ids=classification['relevant_standards'],
            k=request.k
        )
    else:
        results = await retrieve_detailed_statements(
            semantic_search=semantic_search,
            query=request.query,
            standard_ids=classification['relevant_standards'],
            query_focus=classification['query_focus'],
            k=request.k
        )

    logger.info(f"Retrieved {len(results)} chunks")

    # Step 3: CONDITIONAL SYNTHESIS (NEW)
    if classification.get('is_decisional', False):
        logger.info("Decisional query detected - synthesizing practice validation")

        decisional_answer = await synthesize_validation_answer(
            query=request.query,
            classification=classification,
            retrieved_chunks=results,
            llm_client=openai_client
        )

        # Return decisional format
        return {
            'decisional_answer': decisional_answer,
            'supporting_evidence': [
                semantic_search.format_results(results)  # Format chunks for readability
            ],
            'classification': classification,
            'response_type': 'decisional',
            'query_interpretation': f"Practice validation for: {request.query}"
        }

    else:
        # Informational query - return standard format (backward compatible)
        logger.info("Informational query - returning standard format")

        return format_qs_response(
            chunks=results,
            classification=classification,
            query=request.query
        )
```

---

## Rollout Strategy

### Week 1: CPSO Policy (Highest Impact)
1. Add decisional detection to `cpso_triage.py`
2. Implement `synthesize_compliance_answer()` in `cpso_helpers.py`
3. Update `policy_check()` in `server.py`
4. Test with 10 decisional queries
5. Deploy behind feature flag: `CPSO_DECISIONAL_ENABLED=true`

### Week 2: Choosing Wisely (High Clinical Value)
1. Add decisional detection to `choosing_wisely_triage.py`
2. Implement `synthesize_binary_recommendation()` in `choosing_wisely_helpers.py`
3. Update `choosing_wisely()` in `server.py`
4. Test with 10 binary recommendation queries
5. Deploy behind feature flag: `CW_DECISIONAL_ENABLED=true`

### Week 3: Quality Standards (Practice Validation)
1. Add decisional detection to `qs_triage.py`
2. Implement `synthesize_validation_answer()` in `qs_helpers.py`
3. Update `quality_standards()` in `server.py`
4. Test with 10 validation queries
5. Deploy behind feature flag: `QS_DECISIONAL_ENABLED=true`

### Week 4: CEP Tools (Clinical Decision Support)
1. Similar pattern for CEP clinical tools
2. Synthesis type: "tool_recommendation" (e.g., "Should I use Wells score for this patient?")

---

## Monitoring & Evaluation

### Metrics to Track
```python
# Add to response metadata
{
    "decisional_synthesis_metadata": {
        "synthesis_time_ms": 485,
        "synthesis_model": "gpt-4o-mini",
        "synthesis_cost": 0.0002,
        "chunks_used": 8,
        "confidence": 0.9,
        "synthesis_version": "v1.0"
    }
}
```

### Success Criteria
- ✅ Decisional queries return structured answers (not just raw chunks)
- ✅ Confidence scores >0.7 for clear scenarios
- ✅ Synthesis time <600ms (95th percentile)
- ✅ Zero degradation for informational queries
- ✅ Positive clinician feedback on decisional answers

---

## Example Responses (Before & After)

### Before (Informational Only)
```json
{
  "items": [
    {"text": "Virtual care policy section 3.2: Physicians must obtain...", ...},
    {"text": "Prescribing policy section 4.1: Controlled substances...", ...}
  ],
  "classification": {"intent": "policy_lookup", ...}
}
```
**Problem:** Clinician must synthesize answer from multiple chunks themselves.

### After (Decisional Support)
```json
{
  "decisional_answer": {
    "compliant": "no",
    "reasoning": "Virtual care policy requires in-person assessment...",
    "requirements": [...],
    "non_compliance_risks": [...],
    "recommendations": [...]
  },
  "supporting_evidence": [
    {/* same chunks as before, for transparency */}
  ],
  "response_type": "decisional"
}
```
**Benefit:** Clear, actionable answer + supporting evidence for verification.

---

## Conclusion

**Recommendation: ✅ Implement post-retrieval synthesis layer**

**Why this approach wins:**
1. ✅ **Minimal surgery**: ~50 lines per tool, no architecture changes
2. ✅ **Backward compatible**: Informational queries unchanged
3. ✅ **Conditional cost**: Synthesis only for decisional queries
4. ✅ **High impact**: Enables compliance checking, practice validation, binary recommendations
5. ✅ **Incremental rollout**: Feature-flag per tool, gradual deployment
6. ✅ **Transparent**: Always returns raw evidence alongside synthesis

**Next Steps:**
1. Implement CPSO decisional synthesis (Week 1)
2. Test with 10 real compliance scenarios
3. Gather clinician feedback
4. Roll out to Choosing Wisely (Week 2)
5. Expand to Quality Standards (Week 3)

**Expected Impact:**
- Transforms OPA tools from **informational** to **decisional**
- Enables compliance checking, practice validation, clinical decision support
- Maintains speed advantage over full query processor (1.5s vs 3-4s)
- Preserves backward compatibility for existing informational use cases

---

**End of Enhancement Plan**
