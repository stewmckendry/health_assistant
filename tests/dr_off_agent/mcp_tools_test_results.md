# Dr. OFF MCP Tools Test Results

## Test Date: 2025-01-25

## Test Objectives
- Validate MCP tool functionality for real-world Ontario healthcare scenarios
- Test coverage questions, OHIP billing, ADP device funding, and ODB drug formulary lookups
- Identify gaps, errors, and areas for improvement

## Test Scenarios

### Category 1: Complex Discharge Billing Scenarios

#### Test 1.1: Elderly Patient Discharge with MRP Billing
**Query**: "My 75yo patient is being discharged after 3 days. Can I bill C124 as MRP? Also needs a walker - what's covered?"

**Expected**: 
- C124 billing eligibility information
- MRP (Most Responsible Physician) requirements
- Walker ADP coverage details

**Tool Used**: `coverage_answer`
**Parameters**:
```json
{
  "question": "My 75yo patient is being discharged after 3 days. Can I bill C124 as MRP? Also needs a walker - what's covered?",
  "patient": {
    "age": 75,
    "admission_days": 3
  }
}
```

**Result**: 
```json
{
  "answer": "The requested service/code is billable under OHIP. Code A125 (Section: A Subsection: Laboratory Medicine (28) Page Reference: A125 Fee Codes (13 codes): A285: Consultation - $163) has a fee of $None. ADP covers 75.0% with client paying 25.0%.",
  "confidence": 0.87,
  "decision": "billable",
  "tools_used": ["schedule.get", "adp.get"]
}
```

**Analysis**:
- [❌] Correctly identified C124 billing code? - **Failed: Retrieved unrelated codes (A125, A285)**
- [❌] Provided MRP requirements? - **Failed: No MRP-specific information provided**
- [✅] Included walker ADP coverage? - **Partial: Mentioned 75/25 split but lacks detail**
- [✅] Citations provided? - **Yes, but incorrect page references**

---

#### Test 1.2: Admission/Discharge Timing for Billing
**Query**: "Patient admitted Monday 2pm, discharged Thursday 10am - which discharge codes apply?"

**Tool Used**: `schedule_get`
**Parameters**:
```json
{
  "q": "discharge codes admission Monday 2pm Thursday 10am",
  "include": ["codes", "fee", "limits", "documentation"]
}
```

**Result**:
```json
{
  "provenance": ["sql", "vector"],
  "confidence": 0.75,
  "items": [
    {"code": "E662", "description": "with intraductal cytology brushing or intraductal biopsy - $49"},
    {"code": "E666", "description": "with biliary tract manometry - $52"},
    {"code": "E668", "description": "with cannulation of minor papilla - $93"},
    {"code": "E669", "description": "with oesophagoscopy-gastroscopy and may include duodenoscopy - $102"},
    {"code": "E680", "description": "with insertion of first endobiliary prosthesis and/or pancreatic stent (maximum 1) - $82"},
    {"code": "E681", "description": "with insertion of each additional endobiliary prosthesis and/or pancreatic stent (maximum 3) - $43"}
  ]
}
```

**Analysis**:
- [❌] Identified correct discharge codes? - **Failed: Retrieved endoscopy codes (E6xx) instead of discharge codes**
- [❌] Considered time-based billing rules? - **Failed: No time-based analysis provided**
- [✅] Provided fee amounts? - **Yes, but for wrong procedures**

---

### Category 2: Drug Coverage & Alternatives

#### Test 2.1: Diabetes Drug Coverage
**Query**: "Is Januvia covered for my T2DM patient? Any cheaper alternatives?"

**Tool Used**: `odb_get`
**Parameters**:
```json
{
  "drug": "Januvia",
  "check_alternatives": true,
  "include_lu": true
}
```

**Result**:
```json
{
  "provenance": ["sql"],
  "confidence": 0.9,
  "coverage": {
    "covered": true,
    "din": "02388839",
    "strength": "25mg",
    "lu_required": false
  },
  "interchangeable": [],
  "lowest_cost": null
}
```

**Analysis**:
- [✅] Found Januvia coverage status? - **Yes, covered without LU**
- [❌] Listed cheaper alternatives? - **Failed: No alternatives provided despite request**
- [❌] Included interchangeable drugs? - **Failed: Empty interchangeable list**
- [✅] Provided DIN numbers? - **Yes: 02388839**

---

#### Test 2.2: Ozempic Coverage by Indication
**Query**: "Ozempic for obesity vs diabetes - different coverage?"

**Tool Used**: `odb_get`
**Parameters**:
```json
{
  "drug": "Ozempic",
  "check_alternatives": false,
  "include_lu": true
}
```

**Result**:
```json
{
  "provenance": ["sql", "vector"],
  "confidence": 0.95,
  "coverage": {
    "covered": true,
    "din": "02540258",
    "strength": "0.68mg/mL",
    "lu_required": false
  },
  "conflicts": [
    {"field": "coverage", "sql_value": "covered", "vector_value": "Please note that some OFI products may be covered under the ODB program through the EAP"}
  ]
}
```

**Analysis**:
- [❌] Differentiated coverage by indication? - **Failed: No distinction between obesity vs diabetes indication**
- [❌] Explained Limited Use criteria? - **Failed: Shows lu_required=false but doesn't explain criteria**
- [✅] Provided accurate coverage info? - **Partial: Shows coverage but lacks indication-specific details**

---

#### Test 2.3: Statin Without LU Requirements
**Query**: "What's the cheapest statin that's covered without LU?"

**Tool Used**: `coverage_answer`
**Parameters**:
```json
{
  "question": "What's the cheapest statin that's covered without LU?",
  "hints": {
    "drug_class": "statin"
  }
}
```

**Result**:
```json
{
  "answer": "Additional information is needed for a definitive answer.",
  "confidence": 0.5,
  "decision": "needs_more_info",
  "followups": [
    {"ask": "Does the patient have a valid prescription from an authorized prescriber?"},
    {"ask": "Has the patient tried other first-line treatments?"}
  ]
}
```

**Analysis**:
- [❌] Identified statins without LU? - **Failed: Did not search for statins**
- [❌] Found cheapest option? - **Failed: No cost comparison attempted**
- [❌] Provided cost comparison? - **Failed: Returned generic followup questions instead**

---

### Category 3: ADP Device Funding

#### Test 3.1: Power Wheelchair with CEP Eligibility
**Query**: "Patient with MS needs power wheelchair. Income $19,000 - CEP eligible?"

**Tool Used**: `adp_get`
**Parameters**:
```json
{
  "device": {
    "category": "mobility",
    "type": "power wheelchair"
  },
  "patient_income": 19000,
  "check": ["eligibility", "funding", "cep"]
}
```

**Result**:
```json
{
  "provenance": ["sql", "vector"],
  "confidence": 0.99,
  "funding": {
    "client_share_percent": 25.0,
    "adp_contribution": 75.0,
    "repair_coverage": "Not covered"
  },
  "cep": {
    "income_threshold": 28000.0,
    "eligible": true,
    "client_share": 0.0
  }
}
```

**Analysis**:
- [✅] Determined CEP eligibility? - **Yes: Eligible with $19k income < $28k threshold**
- [✅] Calculated funding percentage? - **Yes: 100% coverage through CEP (0% client share)**
- [✅] Included income threshold info? - **Yes: $28,000 threshold clearly stated**

---

#### Test 3.2: Scooter Repair Coverage
**Query**: "3-year-old scooter needs batteries and motor repair - what's covered?"

**Tool Used**: `adp_get`
**Parameters**:
```json
{
  "device": {
    "category": "mobility",
    "type": "scooter"
  },
  "use_case": {
    "age_years": 3,
    "repair_type": "batteries and motor"
  },
  "check": ["funding", "exclusions"]
}
```

**Result**:
```json
{
  "provenance": ["sql", "vector"],
  "confidence": 0.99,
  "exclusions": [
    "no application submitted for ADP funding when the scooter is recognized to be a benefit but not a basic mobility requirement: power_scooter"
  ],
  "funding": {
    "client_share_percent": 25.0,
    "adp_contribution": 75.0,
    "repair_coverage": "Not covered"
  }
}
```

**Analysis**:
- [✅] Identified repair coverage rules? - **Yes: "Not covered" for repairs**
- [❌] Checked device age eligibility? - **Failed: No age-specific analysis for 3-year-old device**
- [✅] Listed specific exclusions? - **Partial: Generic exclusion about scooters not being basic mobility**

---

#### Test 3.3: AAC Device for ALS Patient
**Query**: "AAC device for ALS patient - funding percentage and forms?"

**Tool Used**: `adp_get`
**Parameters**:
```json
{
  "device": {
    "category": "communication",
    "type": "AAC device"
  },
  "use_case": {
    "diagnosis": "ALS"
  },
  "check": ["eligibility", "funding", "forms"]
}
```

**Result**:
```
Not tested - skipped due to limited device categories in current implementation
```

**Analysis**:
- [❌] Provided funding percentage? - **Not tested**
- [❌] Listed required forms? - **Not tested**
- [❌] Included ALS-specific eligibility? - **Not tested**

---

### Category 4: OHIP Billing Complexities

#### Test 4.1: ER Consultation as Internist
**Query**: "Can I bill consultation in ER as internist?"

**Tool Used**: `schedule_get`
**Parameters**:
```json
{
  "q": "ER consultation internist billing",
  "include": ["codes", "limits", "documentation"]
}
```

**Result**:
```
[TO BE FILLED WITH ACTUAL TEST RESULTS]
```

**Analysis**:
- [ ] Found internist ER consultation codes?
- [ ] Explained billing restrictions?
- [ ] Provided fee amounts?

---

#### Test 4.2: House Call Premium Codes
**Query**: "House call for elderly patient - what premiums apply?"

**Tool Used**: `schedule_get`
**Parameters**:
```json
{
  "q": "house call elderly premiums",
  "include": ["codes", "fee", "documentation"]
}
```

**Result**:
```
[TO BE FILLED WITH ACTUAL TEST RESULTS]
```

**Analysis**:
- [ ] Identified house call codes?
- [ ] Listed applicable premiums?
- [ ] Included age-based modifiers?

---

#### Test 4.3: Virtual Care Billing
**Query**: "Virtual care follow-up - which codes are valid?"

**Tool Used**: `schedule_get`
**Parameters**:
```json
{
  "q": "virtual care follow-up billing codes",
  "include": ["codes", "limits", "documentation"]
}
```

**Result**:
```
[TO BE FILLED WITH ACTUAL TEST RESULTS]
```

**Analysis**:
- [ ] Found virtual care codes?
- [ ] Explained follow-up restrictions?
- [ ] Included pandemic-related changes?

---

### Category 5: Edge Cases & Complex Queries

#### Test 5.1: Multi-Domain Query
**Query**: "Patient needs CPAP machine and also starting on Metformin - what's covered?"

**Tool Used**: `coverage_answer`
**Parameters**:
```json
{
  "question": "Patient needs CPAP machine and also starting on Metformin - what's covered?",
  "hints": {
    "device": "CPAP",
    "drug": "Metformin"
  }
}
```

**Result**:
```
[TO BE FILLED WITH ACTUAL TEST RESULTS]
```

**Analysis**:
- [ ] Handled multi-domain query?
- [ ] Provided CPAP ADP info?
- [ ] Included Metformin ODB coverage?

---

## Summary of Test Results

### Success Metrics
- Total Tests Run: 12
- Successful: [TO BE FILLED]
- Partial Success: [TO BE FILLED]
- Failed: [TO BE FILLED]

### Key Findings
1. **Strengths**:
   - [TO BE FILLED]

2. **Weaknesses**:
   - [TO BE FILLED]

3. **Missing Functionality**:
   - [TO BE FILLED]

### Recommendations for Improvement
1. [TO BE FILLED]
2. [TO BE FILLED]
3. [TO BE FILLED]

## Next Steps
- [ ] Fix identified issues
- [ ] Add missing data sources
- [ ] Improve error handling
- [ ] Enhance citation accuracy
- [ ] Add more comprehensive test coverage