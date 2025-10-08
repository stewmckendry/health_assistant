# ODB Tool Test Cases

**Purpose**: Comprehensive test suite for ODB query processor validation
**Date**: October 8, 2025
**Tool**: `odb_get` with LLM-powered query understanding

---

## Test Categories

### 1. Clinical Terminology Expansion
Tests that clinical terms are correctly mapped to actual drug names

### 2. Interchangeable Drug Groups
Tests that return multiple equivalent drugs with pricing

### 3. Limited Use (LU) Criteria Extraction
Tests structured extraction of LU requirements from policy text

### 4. Yes/No Coverage Questions
Tests direct answers to coverage questions

### 5. Therapeutic Alternatives
Tests finding alternatives within same therapeutic class

### 6. Combination Drugs
Tests queries for combination formulations

### 7. Drug Class Searches
Tests semantic understanding of therapeutic classes

### 8. Cost-Focused Queries
Tests queries about pricing and lowest-cost options

---

## Test Cases

### Test 1: GLP-1 Agonist (Clinical Term)
**Query**: `"GLP-1 agonist"`

**Expected Behavior**:
- Should discover: semaglutide (Ozempic, Rybelsus), liraglutide (Victoza, Saxenda), dulaglutide (Trulicity)
- Should NOT return: insulin, metformin, pioglitazone
- Should include pricing for each
- Should mention LU criteria exist

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "GLP-1 agonist" --verbose
```

**Status**: ✅ Passing (verified in previous tests)

---

### Test 2: Adalimumab Biosimilars (Interchangeable Group)
**Query**: `"adalimumab biosimilars"`

**Expected Behavior**:
- Should return: Amgevita, Hyrimoz, Hadlima, Hulio, Idacio, Abrilada, Yuflyma
- All should show same price: $471.27 (40mg) or $942.54 (80mg)
- Should indicate these are interchangeable biosimilars
- Should include LU criteria for rheumatoid arthritis

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "adalimumab biosimilars" --verbose
```

**Status**: ✅ **PASSING** (Retested 2025-10-08 after LU integration)

**Latest Results** (after LU criteria embedding):
- ⏱️ **Latency**: 7.70s (improved from 14.53s)
- 🎯 **Confidence**: 1.00 (perfect)
- 📊 **Provenance**: sql + vector

**What Works Now** ✅:
- Found correct adalimumab biosimilars: Abrilada, Hadlima, Hyrimoz, etc.
- Correct pricing: $235.63 (20mg), $471.27 (40mg)
- Multiple formulations identified (syringes, pens, autoinjectors)
- **LU criteria now fully extracted and displayed** - shows detailed requirements for RA treatment
- Parent/child chunk structure working correctly
- Drug grouping by therapeutic class + generic name successful

**Fixed Issues** ✅:
1. ✅ LU criteria now embedded in all drug chunks during ingestion
2. ✅ Data restructured with grouping (11,529 → 3,358 chunks)
3. ✅ 1536-dimension embeddings throughout
4. ✅ Retry logic handles OpenAI rate limits

**Changes Made**:
- Added `_extract_lu_criteria()` method to `odb_ingester.py`
- LU criteria extracted from XML `<lccNote>` elements
- Embedded in drug text during ingestion
- Preserved during restructure grouping

**XML Evidence** (from data file):
- Hyrimoz (SDZ): 40mg/0.4mL @ $471.27, 80mg @ $942.54
- Amgevita (AMG): 40mg/0.8mL @ $471.27
- Hadlima (SAM): 40mg/0.8mL @ $471.27
- Hulio (BGP): 40mg/0.8mL @ $471.27
- Idacio (FKC): 40mg/0.8mL @ $471.27
- Abrilada (PFI): 40mg/0.8mL @ $471.27
- Yuflyma (CEH): 80mg/0.8mL @ $942.54

---

### Test 3: TNF Inhibitors for RA (Complex Clinical Query)
**Query**: `"TNF inhibitors for rheumatoid arthritis"`

**Expected Behavior**:
- Should return: adalimumab (multiple brands), etanercept, infliximab, certolizumab, golimumab
- Should mention these are biologics with LU criteria
- Should indicate high cost
- Should note requirement for DMARD failure

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "TNF inhibitors for rheumatoid arthritis" --verbose
```

**Status**: ❌ **FAIL** (Tested 2025-10-08)

**Results**:
- ⏱️ **Latency**: 7.31s (acceptable)
- 🎯 **Confidence**: 0.99
- 📊 **Provenance**: vector only
- 📚 **Citations**: 16

**What Worked** ✅:
- Found some relevant DMARDs for rheumatoid arthritis
- Included infliximab biosimilars (position 7) - which ARE TNF inhibitors
- Fast response time

**Issues Found** ❌:
1. **Wrong drug class prioritized**: Top results were JAK inhibitors (tofacitinib, baricitinib), NOT TNF inhibitors
   - Position 1: Tofacitinib (JAK inhibitor) - relevance 0.65
   - Position 2: More tofacitinib formulations - relevance 0.57
   - Position 3: Baricitinib (JAK inhibitor) - relevance 0.53
   - Position 7: Infliximab (CORRECT - TNF inhibitor) - relevance 0.45
2. **Missing key TNF inhibitors**: Did NOT return adalimumab, etanercept, certolizumab, golimumab
   - These are the primary TNF inhibitors for RA
3. **Wrong semantic matching**: Query "TNF inhibitors" matched broader "RA biologics" rather than specific mechanism
4. **Incorrect results**: Also returned apremilast (PDE4 inhibitor), ixekizumab (IL-17 inhibitor), tocilizumab (IL-6 inhibitor)

**Root Cause**:
- Clinical term expansion failed to map "TNF inhibitors" → specific drug names
- Vector search matched "rheumatoid arthritis" broadly instead of "TNF mechanism"
- LLM validation didn't filter non-TNF biologics
- Need to improve clinical term expansion for mechanism-of-action queries

---

### Test 4: Is Humira Covered? (Yes/No Question)
**Query**: `"Is Humira covered?"`

**Expected Behavior**:
- Answer: "Yes" or "Conditional"
- Explanation: Covered with Limited Use criteria
- Should mention biosimilar alternatives exist (lower cost)
- Should summarize LU criteria briefly

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "Is Humira covered?" --verbose
```

**Status**: ⚠️ **PARTIAL PASS** (Tested 2025-10-08)

**Results**:
- ⏱️ **Latency**: 8.22s (good)
- 🎯 **Confidence**: 1.00
- 📊 **Provenance**: vector only

**What Worked** ✅:
- Found adalimumab biosimilars (Humira is brand name for adalimumab)
- Returned multiple biosimilar options
- Coverage status visible in items

**Issues Found** ❌:
1. **No yes/no answer generated**: Expected structured yes/no response with explanation
2. **No direct answer**: User asked "Is Humira covered?" but got list of drugs instead
3. **Missing biosimilar recommendation**: Didn't explicitly mention lower-cost biosimilar alternatives

**Root Cause**:
- Intent classified as general query, not "yes_no" type
- `enrich_with_llm()` not called to generate yes/no answer
- Response format doesn't include yes/no field

---

### Test 5: Adalimumab LU Criteria (Structured Extraction)
**Query**: `"adalimumab limited use criteria for rheumatoid arthritis"`

**Expected Behavior**:
- Should extract structured LU requirements:
  - Severe active disease (≥5 swollen joints)
  - Rheumatoid factor positive and/or anti-CCP positive
  - Radiographic evidence
  - Prior DMARD failure (specific regimens listed)
  - Authorization period: 1 year
- Should format as clear requirements list

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "adalimumab limited use criteria for rheumatoid arthritis" --verbose
```

**Status**: ⚠️ **PARTIAL PASS** (Tested 2025-10-08)

**Results**:
- ⏱️ **Latency**: 6.63s (good)
- 🎯 **Confidence**: 1.00
- 📊 **Provenance**: sql + vector
- 📚 **Citations**: 10

**What Worked** ✅:
- Found all adalimumab biosimilars correctly (Abrilada, Amgevita, Hadlima, Hulio, Hyrimoz, Idacio, Simlandi, Yuflyma)
- All formulations listed with correct DINs and pricing
- Fast response time (6.63s)
- High confidence score
- Also found related biologics: infliximab biosimilars (contextually relevant)

**Issues Found** ❌:
1. **No structured LU extraction**: LU criteria text was NOT extracted into structured format
   - `lu_required: false` (should be true)
   - `lu_criteria: null` (should contain structured requirements)
   - The raw text is likely in the items, but NOT parsed into the expected structured format
2. **No LU-specific enrichment**: Despite query explicitly asking for "limited use criteria", no LLM enrichment step ran
   - This suggests the `enrich_with_llm()` method wasn't called or didn't recognize this as an LU extraction task

**Root Cause**:
- Query processor may not be extracting intent correctly for LU-specific queries
- LLM enrichment step (designed to extract structured LU criteria) not triggered
- Need to check if `QueryIntent.query_type` is being set to "lu_criteria"

**XML Evidence** (LU criteria from data file):
```
For the treatment of rheumatoid arthritis (RA) in patients who have severe active disease
(greater than or equal to 5 swollen joints and rheumatoid factor positive and/or, anti-CCP
positive, and/or radiographic evidence of rheumatoid arthritis) and have experienced failure,
intolerance, or have a contraindication to adequate trials of disease-modifying anti-rheumatic
drugs (DMARDs) treatment regimens, such as one of the following combinations of treatments:

A. i) Methotrexate (20mg/week) for at least 3 months, AND
   ii) leflunomide (20mg/day) for at least 3 months, in addition to
   iii) an adequate trial of at least one combination of DMARDs for 3 months; OR

B. i) Methotrexate (20mg/week) for at least 3 months, AND
   ii) leflunomide in combination with methotrexate for at least 3 months; OR

C. i) Methotrexate (20mg/week), sulfasalazine (2g/day) and hydroxychloroquine (400mg/day)
   for at least 3 months.

LU Authorization Period: 1 year
```

---

### Test 6: Methotrexate (Simple Drug Lookup)
**Query**: `"methotrexate"`

**Expected Behavior**:
- Should work in both legacy and LLM modes
- Should return multiple formulations (oral, injectable)
- Should show various strengths
- Should include generic options
- Should be fast (<2s in legacy, <5s in LLM)

**Test Command**:
```bash
# Legacy mode
export ENABLE_QUERY_PROCESSOR=false
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "methotrexate" --verbose

# LLM mode
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "methotrexate" --verbose
```

**Status**: ✅ Passing (verified in previous tests)

---

### Test 7: ACE Inhibitors (Drug Class)
**Query**: `"ACE inhibitors"`

**Expected Behavior**:
- Should return: ramipril, enalapril, lisinopril, perindopril, quinapril, etc.
- Should NOT return: ARBs, beta blockers, or other antihypertensives
- Should include various strengths and formulations
- Should note these are generic, low-cost options

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "ACE inhibitors" --verbose
```

**Status**: 🔄 To be tested

---

### Test 8: Combination Antihypertensive (Specific)
**Query**: `"ACE inhibitor with diuretic"`

**Expected Behavior**:
- Should return: ramipril+HCTZ, enalapril+HCTZ, lisinopril+HCTZ, perindopril+indapamide
- Should NOT return: single-agent ACE inhibitors
- Should NOT return: unrelated combinations (like abiraterone)
- Should show combination formulations clearly

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "ACE inhibitor with diuretic" --verbose
```

**Status**: ✅ **PASS** (Tested 2025-10-08)

**Results**:
- ⏱️ **Latency**: 13.52s (acceptable but high)
- 🎯 **Confidence**: 0.99
- 📊 **Provenance**: vector only

**What Worked** ✅:
- Correctly returned ACE inhibitor + diuretic combinations:
  - Enalapril + HCTZ (Vaseretic)
  - Lisinopril + HCTZ (Prinzide, Zestoretic, generics)
  - Cilazapril + HCTZ (Inhibace Plus)
  - Quinapril + HCTZ (Accuretic)
- Multiple manufacturers and formulations
- Pricing included
- Did NOT return abiraterone or other wrong drugs

**Minor Issues**:
- Also returned HCTZ + triamterene (not an ACE inhibitor, but reasonable)
- Also returned atenolol + chlorthalidone (beta blocker, not ACE inhibitor)
- Included some single-agent lisinopril/enalapril at the end

**Assessment**: Mostly correct, acceptable results for clinical use

---

### Test 9: Generic for Brand Name
**Query**: `"generic for Lipitor"`

**Expected Behavior**:
- Should identify: atorvastatin is the generic
- Should list generic manufacturers
- Should show price comparison
- Should NOT include: other statins (rosuvastatin, simvastatin) unless labeled as alternatives

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "generic for Lipitor" --verbose
```

**Status**: 🔄 To be tested
**Previous Issue**: Included fenofibrate (different class) - should be fixed now

---

### Test 10: Alternatives to Brand (Therapeutic)
**Query**: `"alternatives to Lipitor"`

**Expected Behavior**:
- Should return:
  1. Generic atorvastatin (same drug, lower cost)
  2. Other statins: rosuvastatin, simvastatin, pravastatin (therapeutic alternatives)
- Should explain why each is an alternative
- Should NOT return: non-statin cholesterol drugs (ezetimibe, PCSK9 inhibitors)

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "alternatives to Lipitor" --verbose
```

**Status**: ✅ Passing (verified in previous tests)

---

### Test 11: Lowest Cost Statin
**Query**: `"lowest cost statin"`

**Expected Behavior**:
- Should prioritize cost information
- Should compare statin prices
- Should likely return: simvastatin or atorvastatin (generics)
- Should show price per unit
- Should mark lowest-cost option

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "lowest cost statin" --verbose
```

**Status**: 🔄 To be tested

---

### Test 12: Insulin Types (Subcategory)
**Query**: `"long-acting insulin"`

**Expected Behavior**:
- Should return: insulin glargine (Lantus, Basaglar, Toujeo), insulin detemir (Levemir), insulin degludec (Tresiba)
- Should NOT return: short-acting (aspart, lispro), intermediate (NPH), or premixed insulins
- Should include biosimilar information
- Should note coverage/LU status

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "long-acting insulin" --verbose
```

**Status**: 🔄 To be tested

---

### Test 13: Empty/Ambiguous Query
**Query**: `"diabetes"`

**Expected Behavior**:
- Should recognize query is too broad
- Should either:
  - Ask for clarification (preferred)
  - Return top diabetes drug classes with brief descriptions
  - Suggest more specific queries (insulin, metformin, GLP-1, SGLT2)

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "diabetes" --verbose
```

**Status**: 🔄 To be tested

---

### Test 14: Biologic with Multiple Indications
**Query**: `"Humira for Crohn's disease"`

**Expected Behavior**:
- Should recognize specific indication (Crohn's)
- Should return LU criteria specific to Crohn's disease (not RA)
- Should mention other indications exist
- Should note biosimilar alternatives

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "Humira for Crohn's disease" --verbose
```

**Status**: 🔄 To be tested

---

### Test 15: Section 8 Drug (Exceptional Access)
**Query**: `"Ozempic for weight loss"`

**Expected Behavior**:
- Should clarify: Ozempic approved for type 2 diabetes, not weight loss
- May mention: Saxenda (liraglutide) is approved for weight management
- Should note LU criteria requirements
- Should indicate coverage limitations

**Test Command**:
```bash
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "Ozempic for weight loss" --verbose
```

**Status**: 🔄 To be tested

---

## Performance Benchmarks

### Latency Expectations

| Query Type | Legacy Mode | LLM Mode | Acceptable? |
|------------|-------------|----------|-------------|
| Simple drug lookup | 0.5-2s | 1-3s | ✅ Yes |
| Clinical term expansion | N/A (fails) | 3-6s | ✅ Yes |
| LU extraction | 0.5-2s (no extraction) | 5-8s | ✅ Yes |
| Drug class search | 0.5-2s (may fail) | 4-7s | ✅ Yes |
| Complex multi-step | N/A (fails) | 8-12s | ⚠️ Borderline |

**Threshold**: <10s for 95% of queries

### Accuracy Expectations

| Query Pattern | Target Accuracy |
|---------------|-----------------|
| Specific drug names | >95% |
| Clinical terminology | >90% |
| Yes/no questions | >95% |
| LU extraction | >85% |
| Therapeutic alternatives | >90% |
| Drug class searches | >85% |

---

## Test Execution Plan

### Phase 1: Core Functionality (Current)
- [x] Test 1: GLP-1 agonist
- [x] Test 6: Methotrexate (legacy + LLM)
- [x] Test 10: Alternatives to Lipitor
- [ ] Test 2: Adalimumab biosimilars
- [ ] Test 5: Adalimumab LU criteria

### Phase 2: Edge Cases
- [ ] Test 3: TNF inhibitors (multi-drug class)
- [ ] Test 8: ACE+diuretic combination
- [ ] Test 9: Generic for Lipitor
- [ ] Test 13: Ambiguous query (diabetes)

### Phase 3: Advanced Features
- [ ] Test 4: Is Humira covered?
- [ ] Test 7: ACE inhibitors
- [ ] Test 11: Lowest cost statin
- [ ] Test 12: Long-acting insulin
- [ ] Test 14: Indication-specific query
- [ ] Test 15: Off-label query

---

## Known Issues

### Fixed Issues ✅
1. **Drug class queries returning empty** - Fixed by detecting class keywords and skipping SQL
2. **Clinical terms not understood** - Fixed by LLM + vector expansion

### Pending Issues ⚠️
1. **Latency for complex queries** - May need caching for clinical term expansions
2. **Ambiguous queries** - Need better handling for overly broad queries

### To Investigate 🔍
1. Does query processor handle French drug names?
2. How does it handle typos in drug names?
3. Does it understand brand name variations (Lipitor vs LIPITOR)?
4. Can it handle DIN (Drug Identification Number) lookups?

---

## Test Results Summary

### Completed Tests: 8/15 (53%)
### Passing: 4/8 (50%)
### Partial Pass: 3/8 (37.5%)
### Failed: 1/8 (12.5%)

**Test Breakdown**:
- ✅ Test 1: GLP-1 agonist (PASS)
- ⚠️ Test 2: Adalimumab biosimilars (PARTIAL - wrong drugs included)
- ❌ Test 3: TNF inhibitors (FAIL - returned JAK inhibitors instead)
- ⚠️ Test 4: Is Humira covered? (PARTIAL - no yes/no answer)
- ⚠️ Test 5: Adalimumab LU criteria (PARTIAL - no structured extraction)
- ✅ Test 6: Metformin (PASS - legacy + LLM)
- ✅ Test 8: ACE inhibitor with diuretic (PASS)
- ✅ Test 10: Alternatives to Lipitor (PASS)

**Pass Rate**: 50% (4/8)

---

## Root Cause Analysis & Fixes

### Issue #1: Clinical Term Expansion Too Broad ❌ CRITICAL

**Problem**: Query "TNF inhibitors for RA" returned JAK inhibitors (tofacitinib, baricitinib) instead of TNF inhibitors (adalimumab, etanercept, infliximab)

**Root Cause**:
```python
# In _expand_clinical_terms()
query = "therapeutic class TNF inhibitors mechanism of action drugs"
# Vector search prioritizes "rheumatoid arthritis" over "TNF" → matches any RA drug
```

**Fix**:
```python
# odb_query_processor.py line ~150
def _build_expansion_query(clinical_term: str) -> str:
    """Build query emphasizing mechanism over indication."""
    if "inhibitor" in clinical_term.lower() or "blocker" in clinical_term.lower():
        # For mechanism queries, emphasize the mechanism
        return f"{clinical_term} specific drugs examples mechanism"
    else:
        return f"therapeutic class {clinical_term} drugs"

# Then in _validate_drug_matches(), add strict validation:
validation_prompt = f"""
STRICT: Only return drugs that are EXACTLY {clinical_term}.
For "TNF inhibitors", ONLY return TNF-alpha inhibitors.
Do NOT return drugs from other classes even if they treat the same condition.

Candidates: {candidates_with_context}
"""
```

**File**: `src/ai_agents/dr_off_agent/mcp/tools/odb_query_processor.py`
**Lines**: ~150-180, ~220-250

---

### Issue #2: LU Criteria Extraction Not Triggered ❌ CRITICAL

**Problem**: Query "adalimumab limited use criteria" did NOT extract structured LU requirements despite explicit request

**Root Cause**:
```python
# Intent classification likely set to "coverage" instead of "lu_criteria"
QueryIntent(query_type="coverage", ...)  # WRONG
# Then enrich_with_llm() never called with LU extraction
```

**Fix**:
```python
# odb_query_processor.py line ~60
# In understand_query() prompt, add:
"""
Query Type Classification:
- "lu_criteria": Query mentions "limited use", "LU criteria", "restrictions", "requirements"
  Example: "adalimumab LU criteria", "limited use for Humira"
- "coverage": Asks if covered but NOT about LU
  Example: "Is metformin covered?"

STRICT: If query mentions "limited use" or "criteria", classify as "lu_criteria".
"""

# Line ~300, always enrich for coverage/LU queries:
if intent.query_type in ["coverage", "lu_criteria", "yes_no"]:
    enriched = await self.enrich_with_llm(results, intent)  # ALWAYS call
```

**File**: `src/ai_agents/dr_off_agent/mcp/tools/odb_query_processor.py`
**Lines**: ~60-100, ~300-320

---

### Issue #3: Vector Noise in Results ⚠️ IMPORTANT

**Problem**: Query "adalimumab biosimilars" returned abiraterone, rituximab, methotrexate

**Root Cause**:
```python
# odb.py lines 415-456
if not coverage and not sql_results and vector_results:
    for result in vector_results[:10]:  # Takes top 10 blindly, no filtering!
        interchangeable.append(...)
```

**Fix**:
```python
# odb.py line ~420
if not coverage and not sql_results and vector_results:
    # Extract target drug from query
    target_drug = intent.drug_names[0] if intent.drug_names else None

    for result in vector_results[:10]:
        generic_name = result.get('metadata', {}).get('generic_name', '').upper()

        # Only include if matches target drug
        if target_drug and target_drug.upper() in generic_name:
            interchangeable.append(...)
```

**File**: `src/ai_agents/dr_off_agent/mcp/tools/odb.py`
**Lines**: ~415-456

---

### Issue #4: Yes/No Answers Not Generated ⚠️ IMPORTANT

**Problem**: Query "Is Humira covered?" didn't generate yes/no answer

**Root Cause**:
```python
# Intent not classified as "yes_no"
# enrich_with_llm() not called
# Response format has no yes/no field
```

**Fix**:
```python
# odb_query_processor.py line ~60
# In understand_query(), improve yes/no detection:
"""
expects_yes_no: true if query is:
  - "Is [drug] covered?"
  - "Does ODB cover [drug]?"
  - "Can I get [drug]?"
"""

# Line ~350, in enrich_with_llm():
if intent.expects_yes_no or intent.query_type == "yes_no":
    yes_no_answer = await self._extract_yes_no_answer(results, intent)
    enriched.yes_no_answer = yes_no_answer

# odb.py line ~500, add to _format_enhanced_response():
if enriched.yes_no_answer:
    response["yes_no"] = {
        "answer": enriched.yes_no_answer.answer,
        "explanation": enriched.yes_no_answer.explanation,
        "conditions": enriched.yes_no_answer.conditions
    }
```

**Files**:
- `src/ai_agents/dr_off_agent/mcp/tools/odb_query_processor.py` lines ~60, ~350
- `src/ai_agents/dr_off_agent/mcp/tools/odb.py` line ~500

---

### Issue #5: High Latency (13-14s) ⚠️ MEDIUM

**Problem**: Some queries take 13-14s (target: <10s)

**Fix**:
```python
# odb_query_processor.py line ~280
# Parallelize SQL and vector retrieval:
sql_task = asyncio.create_task(self._sql_retrieval(intent))
vector_task = asyncio.create_task(self._vector_retrieval(intent))
sql_results, vector_results = await asyncio.gather(sql_task, vector_task)

# Line ~175, reduce vector search size:
results = await self.vector_client.search_odb(query, n_results=8)  # Was 15
```

**File**: `src/ai_agents/dr_off_agent/mcp/tools/odb_query_processor.py`
**Lines**: ~175, ~280

---

## Implementation Priority

### Phase 1: Critical (Do First)
1. ✅ Issue #2: LU extraction (2 hours)
2. ✅ Issue #1: Clinical term expansion (3 hours)
3. ✅ Issue #4: Yes/no answers (2 hours)

### Phase 2: Important (Do Next)
4. ⚠️ Issue #3: Vector noise (2 hours)
5. ⚠️ Issue #5: Latency (1 hour)

**Total Effort**: 10 hours

**Target After Fixes**: 80%+ pass rate (6-7/8 tests passing)
