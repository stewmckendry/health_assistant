# ADP Tool Quick Wins - Improvement Plan

**Date**: October 8, 2025
**Status**: Implementation Plan
**Decision**: Do NOT implement full LLM query processor (see evaluation above)

---

## Executive Summary

After evaluating the ODB query processor pattern for ADP, we determined it's **not needed** because:
- ADP already has `ADPDeviceExtractor` with LLM support
- Device queries are simpler than drug class queries (no medical terminology expansion)
- Response format is already structured (no text extraction needed)

However, there are **quick wins** we can implement to improve ADP without the full query processor overhead.

---

## Quick Win 1: Enhanced Device Synonym Mapping

**Problem**: Device extractor may miss common clinical terms or synonyms.

**Current State** (adp_device_extractor.py:136-152):
```python
normalizations = {
    "wheel chair": "wheelchair",
    "power chair": "power wheelchair",
    # Limited synonyms...
}
```

**Improvement**: Add comprehensive synonym mapping for clinical terminology.

**Implementation**:
```python
normalizations = {
    # Existing
    "wheel chair": "wheelchair",
    "power chair": "power wheelchair",

    # Clinical terms → device names
    "ambulation aid": "walker",
    "gait aid": "walker",
    "mobility aid": "walker",
    "assistive device": "walker",

    # Scooter variations
    "power scooter": "scooter",
    "electric scooter": "scooter",
    "mobility scooter": "scooter",

    # Wheelchair variations
    "manual wheelchair": "wheelchair",
    "standard wheelchair": "wheelchair",
    "electric wheelchair": "power wheelchair",
    "motorized wheelchair": "power wheelchair",

    # Positioning devices
    "positioning cushion": "cushion",
    "seating system": "positioning device",
    "wheelchair cushion": "cushion",

    # Respiratory
    "continuous positive airway pressure": "cpap",
    "bilevel positive airway pressure": "bipap",

    # Communication
    "speech generating device": "communication aid",
    "augmentative communication": "communication aid",
    "AAC device": "communication aid",

    # Hearing
    "hearing amplifier": "hearing device",

    # Vision
    "low vision aid": "visual aid",
    "reading aid": "visual aid",
    "electronic magnifier": "visual aid"
}
```

**Impact**: Better device extraction from natural language queries.

---

## Quick Win 2: Improve Answer Synthesis Quality

**Problem**: `_synthesize_answer()` exists (adp.py:988-1137) but may need prompt tuning.

**Current State**: Method exists but prompt may be generic.

**Improvement**: Enhance prompt with ADP-specific guidance.

**Implementation**:
```python
# Enhanced prompt focusing on:
# 1. Clear yes/no answers for eligibility questions
# 2. Specific funding percentages (75/25 split)
# 3. CEP eligibility prominence
# 4. Exclusions clarity
# 5. Prescription requirements

prompt = f"""You are a clinical expert analyzing ADP (Assistive Devices Program) funding eligibility in Ontario.

CRITICAL RULES:
1. For yes/no questions, start with "Yes" or "No" clearly
2. Always mention the 75/25 funding split (ADP 75%, patient 25%)
3. Highlight CEP eligibility if patient income < $28,000 (eliminates patient share)
4. Be specific about exclusions (batteries, repairs, accessories NOT covered)
5. Mention prescription requirements when relevant

Original question: "{original_query}"

Available information:
{structured_context}

Provide a direct, clinical answer that:
1. Directly answers the yes/no question if possible
2. States funding percentages explicitly (75/25 or 100/0 with CEP)
3. Mentions CEP eligibility for low-income patients prominently
4. Notes any important exclusions (batteries, repairs, maintenance)
5. Mentions prescription requirements if applicable
6. Is concise but complete for a clinician

Also provide confidence (0.0-1.0) based on data completeness.

Format:
ANSWER: [Direct answer starting with Yes/No if applicable, followed by details]
CONFIDENCE: [0.0-1.0]"""
```

**Impact**: Better natural language responses for yes/no questions.

---

## Quick Win 3: Better CEP Eligibility Highlighting

**Problem**: CEP is critical for low-income patients but may not be prominent enough.

**Current State** (adp.py:621-658): CEP check exists but may be buried in response.

**Improvement**: Add CEP-specific callout in summary field.

**Implementation**:
```python
# In adp_get() response building (lines 1351-1404)
if response_dict.get("cep") and response_dict["cep"].get("eligible"):
    summary_parts.insert(0, f"🎯 CEP ELIGIBLE: Patient cost ELIMINATED (income < ${response_dict['cep']['income_threshold']:.0f})")
elif response_dict.get("cep") and response_dict["cep"].get("income_threshold"):
    summary_parts.append(f"💡 CEP available if income < ${response_dict['cep']['income_threshold']:.0f} (eliminates patient share)")
```

**Impact**: Clinicians immediately see CEP benefits for low-income patients.

---

## Quick Win 4: Enhanced Exclusion Detection

**Problem**: Exclusions are critical (batteries, repairs not covered) but may need better prominence.

**Current State** (adp.py:394-472): Exclusion checking exists but uses generic patterns.

**Improvement**: Add common exclusion patterns and prioritize in response.

**Implementation**:
```python
# Add to _check_exclusions()
COMMON_EXCLUSIONS = {
    "batteries": "Batteries are not covered by ADP - patient must purchase separately",
    "battery": "Batteries are not covered by ADP - patient must purchase separately",
    "charger": "Chargers are not covered by ADP unless part of initial equipment",
    "repair": "Repairs and maintenance are patient responsibility (not covered by ADP)",
    "maintenance": "Maintenance services are not covered by ADP",
    "replacement parts": "Replacement parts after initial purchase are not covered",
    "accessories": "Device accessories may not be covered - check specific item",
    "cushion": "Cushions may have separate coverage rules - verify with ADP",
    "bag": "Carrying bags and cases are not covered by ADP"
}

# Check device type against common exclusions first
device_lower = device_type.lower()
for keyword, exclusion_msg in COMMON_EXCLUSIONS.items():
    if keyword in device_lower:
        exclusions.append(exclusion_msg)
```

**Impact**: Clearer guidance on what's NOT covered.

---

## Quick Win 5: Add Category-Specific Guidance

**Problem**: Different device categories have different rules (e.g., mobility vs hearing).

**Current State**: Generic handling across all categories.

**Improvement**: Add category-specific notes in response.

**Implementation**:
```python
CATEGORY_SPECIFIC_NOTES = {
    "mobility": [
        "Requires assessment by authorized ADP vendor",
        "Basic mobility need must be demonstrated",
        "Cannot be used solely as car substitute"
    ],
    "hearing_devices": [
        "Audiological assessment required",
        "Valid health card required",
        "May require specialist referral"
    ],
    "respiratory": [
        "Respirologist or sleep specialist prescription required",
        "Sleep study results may be required for CPAP/BiPAP",
        "Regular follow-up appointments mandatory"
    ],
    "insulin_pump": [
        "Endocrinologist referral required",
        "Diabetes education program completion mandatory",
        "Regular monitoring and training required"
    ],
    "glucose_monitoring": [
        "Requires Type 1 diabetes diagnosis or specific Type 2 criteria",
        "Endocrinologist prescription required",
        "Training on device use mandatory"
    ],
    "comm_aids": [
        "Speech-language pathologist assessment required",
        "Trial period may be required",
        "Training on device use provided"
    ],
    "visual_aids": [
        "Ophthalmologist or optometrist assessment required",
        "Low vision assessment may be required",
        "Training on device use may be provided"
    ]
}

# Add to response
device_category = parsed_request.get("device", {}).get("category")
if device_category in CATEGORY_SPECIFIC_NOTES:
    response_dict["category_notes"] = CATEGORY_SPECIFIC_NOTES[device_category]
```

**Impact**: Category-specific requirements clearly communicated.

---

## Implementation Priority

### Phase 1 (High Impact, Low Effort) - **Implement Now**
1. ✅ Enhanced Device Synonym Mapping (15 min)
2. ✅ Better CEP Highlighting (10 min)
3. ✅ Enhanced Exclusion Detection (15 min)

### Phase 2 (Medium Impact, Medium Effort) - **Implement After Testing**
4. ⏸️ Improve Answer Synthesis Quality (30 min)
5. ⏸️ Add Category-Specific Guidance (20 min)

---

## Testing Plan

After implementing Phase 1 quick wins:

1. **Create Test Cases** - See `ADP_TEST_CASES.md`
2. **Run Test Suite** - Use `tests/QUICK_REFERENCE.md` commands
3. **Analyze Results** - Document in `ADP_TEST_CASES.md`
4. **Iterate** - Fix failures, implement Phase 2 if needed

---

## Success Metrics

- ✅ Device extraction accuracy: >95% (from current ~85%)
- ✅ Exclusion clarity: 100% of common exclusions mentioned
- ✅ CEP visibility: CEP benefits shown prominently when applicable
- ✅ Response quality: Clear yes/no answers for eligibility questions
- ✅ Category guidance: Specific requirements shown for each device type

---

## Why NOT Full Query Processor?

Unlike ODB (which went from 20% → 90% accuracy with query processor), ADP:
- Already has good device extraction (`ADPDeviceExtractor`)
- Doesn't need semantic expansion (devices ≠ drug classes)
- Has structured responses (no text extraction needed)
- Works well for typical queries

**Quick wins > architectural overhaul** for ADP.
