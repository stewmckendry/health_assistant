# Dr. OFF Collections - Inspection Report

**Date:** October 6, 2025
**Path:** `data/dr_off_agent/processed/dr_off/chroma`

## Executive Summary

**Collections Found:** 4 total
- `ohip_documents`: 6,983 chunks (OHIP Schedule of Benefits)
- `odb_documents`: 10,815 chunks (Ontario Drug Benefit Formulary)
- `adp_documents`: 610 chunks (Assistive Devices Program)
- `ohip_documents_cosine`: 1 chunk (test collection - ignore)

**Key Findings:**
1. ✅ **Good Metrics:** Dr. OFF has good retrieval metrics (mentioned by user)
2. ⚠️ **Missing Metadata:** ALL collections missing `section_path`, `section_title`, `chunk_type`, `parent_id`
3. ⚠️ **Small Chunk Sizes:** OHIP (avg 26 words) and ADP (avg 48 words) have very small chunks
4. ⚠️ **Variable Chunk Sizes:** ODB has inconsistent sizing (4.3% are 501-800 words, 94.6% are <50 words)

**Recommendation:**
While metrics are currently good, adding enriched metadata (`section_path`, `chunk_type`) would:
- Improve AI agent response formatting (show hierarchy and source authority)
- Enable parent/child context enrichment
- Maintain consistency with Dr. OPA collections
- Prepare for future semantic search enhancements

---

## Collection Details

### 1. OHIP Documents (Schedule of Benefits)

**Total Chunks:** 6,983

**Chunk Size Distribution:**
- **Average:** 25.9 words
- **Median:** 24 words
- **Range:** 17-169 words
- **97.7%** are 0-50 words (very small chunks)
- Only 2.3% are >50 words

**Metadata Fields (100% coverage):**
- `document_type`: Document category
- `source_document`: Source PDF/file
- `source_type`: Type of source
- `page_ref`: Page reference
- `pages`: Page numbers
- `parent_section`: Parent section heading

**Metadata Fields (99% coverage):**
- `fee_code`: OHIP billing code
- `fee_codes_list`: Related codes
- `category`: Service category
- `specialty`: Medical specialty code
- `fee_amount`: Fee amount
- `has_conditions`: Whether fee has conditions
- `has_units`: Whether fee has units

**Metadata Fields (Low coverage):**
- `has_notes`: 1% (notes metadata)
- `has_rules`: 1% (business rules)
- `has_tables`: 1% (tabular data)
- `referenced_codes`: 1% (cross-referenced codes)

**Missing Critical Metadata:**
- ✗ `section_path`: 0%
- ✗ `section_title`: 0%
- ✗ `chunk_type`: 0%
- ✗ `parent_id`: 0%

**Sample Chunks:**
```
Chunk 1: 57 words, no specialty listed
Chunk 2: 19 words, specialty "S" (Surgery)
Chunk 3: 24 words, specialty "S" (Surgery)
```

**Analysis:**
- Very granular chunking (avg 26 words = 1-2 sentences)
- Good domain-specific metadata (fee codes, specialties, conditions)
- Missing hierarchical metadata (section_path)
- Structure: `parent_section` field exists but not used consistently

**Potential Section Path Structure:**
```
"OHIP Schedule of Benefits > {parent_section} > {specialty} > Fee Code {fee_code}"

Example:
"OHIP Schedule of Benefits > Consultations > Surgery (S) > Fee Code A135A"
```

---

### 2. ODB Documents (Drug Benefit Formulary)

**Total Chunks:** 10,815

**Chunk Size Distribution:**
- **Average:** 57.6 words
- **Median:** 31 words
- **Range:** 28-643 words
- **94.6%** are 0-50 words (small chunks)
- **4.3%** are 501-800 words (large chunks - likely need parent/child split)
- Bimodal distribution: very small or very large

**Metadata Fields (100% coverage):**
- `document_type`: Document category
- `source_document`: Source file
- `source_type`: Type of source

**Metadata Fields (95.1% coverage):**
- `din`: Drug Identification Number (unique drug identifier)
- `brand_name`: Brand name of medication
- `generic_name`: Generic/chemical name
- `therapeutic_class`: Drug therapeutic category
- `is_lowest_cost`: Cost comparison flag

**Metadata Fields (Low coverage):**
- `source_file`: 4.9%
- `chunk_index`: 4.8% (for multi-chunk drugs)

**Missing Critical Metadata:**
- ✗ `section_path`: 0%
- ✗ `section_title`: 0%
- ✗ `chunk_type`: 0%
- ✗ `parent_id`: 0%

**Sample Chunks:**
```
Chunk 1: 379 words
Chunk 2: 613 words (large - needs parent/child split)
Chunk 3: 615 words (large - needs parent/child split)
```

**Analysis:**
- Inconsistent chunk sizes (bimodal: very small or large)
- Excellent drug-specific metadata (DIN, brand, generic, therapeutic class)
- 4.3% of chunks (465 chunks) are 501-800 words → candidates for parent/child split
- Missing hierarchical metadata

**Potential Section Path Structure:**
```
"Ontario Drug Benefit Formulary > {therapeutic_class} > {generic_name} ({brand_name})"

Example:
"Ontario Drug Benefit Formulary > Cardiovascular Agents > Atorvastatin (LIPITOR)"
```

**Parent/Child Opportunity:**
- Large drug monographs (501-800 words) could be split:
  - **Parent:** Drug overview + indications + dosing (400-600 words)
  - **Child 1:** Contraindications + warnings (150-250 words)
  - **Child 2:** Adverse effects + interactions (150-250 words)

---

### 3. ADP Documents (Assistive Devices Program)

**Total Chunks:** 610

**Chunk Size Distribution:**
- **Average:** 47.7 words
- **Median:** 30 words
- **Range:** 1-464 words
- **70.0%** are 0-50 words (small chunks)
- **18.4%** are 51-100 words
- **11.6%** are >100 words

**Metadata Fields (100% coverage):**
- `adp_doc`: ADP document type (e.g., "core_manual", "insulin_pump_manual")
- `policy_uid`: Unique policy identifier
- `section_id`: Section reference number
- `title`: Policy section title
- `topics`: Extracted topics (as JSON array)
- `page_num`: Source page number

**Metadata Fields (85.6% coverage):**
- `part`: Document part number (e.g., Part 2, Part 3)

**Metadata Fields (Low coverage):**
- `funding_count`: 31.0% (number of funding rules)
- `exclusion_count`: 32.8% (number of exclusions)

**Missing Critical Metadata:**
- ✗ `section_path`: 0%
- ✗ `section_title`: 0%
- ✗ `chunk_type`: 0%
- ✗ `parent_id`: 0%

**Sample Chunks:**
```
Chunk 1: 7 words, "The ADP provides coverage for the Real-Time Continuous Glucose" (truncated title)
Chunk 2: 43 words, eligibility criteria
Chunk 3: 14 words, supplies coverage
```

**Analysis:**
- Small average chunk size (48 words = 2-3 sentences)
- Good policy-specific metadata (policy_uid, section_id, part, topics)
- Has `part` field (document section) but not used for section_path
- Title field appears truncated in some cases
- Funding and exclusion counts could enable specialized retrieval

**Potential Section Path Structure:**
```
"Assistive Devices Program > {adp_doc} > Part {part} > Section {section_id}"

Example:
"Assistive Devices Program > Core Manual > Part 2 > Section 200.01"
```

**Existing Structure:**
- The ingester already creates a hierarchical structure:
  - Document → Part → Section
  - This maps naturally to section_path

---

## Comparison: Dr. OPA vs Dr. OFF

| Aspect | Dr. OPA (After Issue #6) | Dr. OFF (Current) |
|--------|--------------------------|-------------------|
| **section_path** | 100% coverage (all 5 collections) | 0% coverage (all 3 collections) |
| **section_title** | 100% coverage | 0% coverage |
| **chunk_type** | 100% (parent/child structure) | 0% coverage |
| **parent_id** | Used for child chunks | Not applicable |
| **Chunk Sizes** | Optimized (200-800 words) | Small (26-58 words avg) |
| **Retrieval Metrics** | Improved (0%→75% Recall, 10%→95% Faithfulness) | Good (per user) |
| **Metadata Richness** | Excellent (hierarchical + domain-specific) | Good (domain-specific only) |

**Key Differences:**
1. **Dr. OPA:** Focuses on clinical guidance (policies, standards, recommendations)
   - Requires rich context and hierarchy for clinical decision-making
   - Benefits from parent/child chunking for complex guidelines

2. **Dr. OFF:** Focuses on administrative data (billing codes, drug formularies, device coverage)
   - More transactional/lookup queries ("What's the fee code for X?", "Is drug Y covered?")
   - Smaller chunks acceptable for specific data retrieval
   - Good metrics despite missing hierarchical metadata

---

## Issues Identified

### 1. Missing section_path Metadata (All Collections)

**Impact:**
- ✗ AI agents cannot show hierarchical source citations
- ✗ Cannot display "OHIP Schedule > Surgery > Fee Code A135A"
- ✗ Inconsistent with Dr. OPA collections
- ✗ Harder to implement cross-tool response formatting enhancements

**Severity:** Medium (works now, but limits future enhancements)

**Recommendation:** Add section_path using existing metadata:
- **OHIP:** `parent_section` + `specialty` + `fee_code`
- **ODB:** `therapeutic_class` + `generic_name` + `brand_name`
- **ADP:** `adp_doc` + `part` + `section_id`

---

### 2. Small Chunk Sizes (OHIP, ADP)

**Impact:**
- OHIP avg 26 words (1-2 sentences per chunk)
- ADP avg 48 words (2-3 sentences per chunk)
- May lack sufficient context for semantic understanding
- However, user reports **good metrics** - so this may be acceptable for transactional data

**Severity:** Low (metrics are good despite small chunks)

**Recommendation:**
- **Monitor:** If future evaluation shows Faithfulness issues, consider combining related chunks
- **No immediate action needed** since metrics are good

---

### 3. Large Chunks in ODB (4.3% are 501-800 words)

**Impact:**
- 465 chunks (4.3%) are 501-800 words
- May contain multiple concepts (indications, contraindications, dosing, interactions)
- Could benefit from parent/child split for better retrieval granularity

**Severity:** Low (only 4.3% of chunks affected)

**Recommendation:**
- **Optional:** Split large drug monographs into parent/child structure:
  - Parent: Drug overview + core information
  - Children: Specific sections (contraindications, interactions, etc.)
- **No immediate action needed** since metrics are good

---

### 4. Missing chunk_type and parent_id (All Collections)

**Impact:**
- Cannot implement parent context enrichment (Issue #6 enhancement)
- No parent/child relationships to leverage for retrieval
- Inconsistent with Dr. OPA structure

**Severity:** Low (not needed for current flat structure)

**Recommendation:**
- Add `chunk_type: "flat"` to all chunks (indicates no parent/child relationship)
- Only add parent/child structure if ODB large chunks are split

---

## Recommended Actions

### Priority 1: Add section_path Metadata (All Collections)

**Why:**
- Enables consistent response formatting across Dr. OPA and Dr. OFF
- Improves AI agent citation quality
- Minimal effort (use existing metadata fields)

**Implementation:**

**OHIP:**
```python
# Use existing parent_section + specialty + fee_code
section_path = f"OHIP Schedule of Benefits > {parent_section} > {specialty} > Fee Code {fee_code}"

Example: "OHIP Schedule of Benefits > Consultations > Surgery (S) > Fee Code A135A"
```

**ODB:**
```python
# Use therapeutic_class + generic_name + brand_name
section_path = f"Ontario Drug Benefit Formulary > {therapeutic_class} > {generic_name} ({brand_name})"

Example: "Ontario Drug Benefit Formulary > Cardiovascular Agents > Atorvastatin (LIPITOR)"
```

**ADP:**
```python
# Use adp_doc + part + section_id
section_path = f"Assistive Devices Program > {adp_doc.replace('_', ' ').title()} > Part {part} > Section {section_id}"

Example: "Assistive Devices Program > Core Manual > Part 2 > Section 200.01"
```

**Script Template:** Similar to `scripts/fix_pho_section_path.py` (update metadata in-place)

---

### Priority 2: Add chunk_type Metadata (All Collections)

**Why:**
- Consistent with Dr. OPA collections
- Enables future parent context enrichment
- Minimal effort

**Implementation:**
```python
# Add to all existing chunks
metadata['chunk_type'] = 'flat'  # Indicates no parent/child relationship
```

---

### Priority 3: (Optional) Split Large ODB Chunks

**Why:**
- 465 chunks (4.3%) are 501-800 words
- Could improve retrieval granularity for complex drug monographs
- Only recommended if future evaluation shows Faithfulness issues

**When to Implement:**
- After re-running evaluation on Dr. OFF
- If Faithfulness drops below 90% for drug-related queries

---

## Scripts to Create

### 1. `scripts/add_section_path_dr_off.py`

Add section_path metadata to all Dr. OFF collections using existing metadata fields.

```python
"""Add section_path metadata to Dr. OFF collections."""

import chromadb
from datetime import datetime

def add_section_path_ohip():
    """Add section_path to OHIP documents."""
    client = chromadb.PersistentClient(path="data/dr_off_agent/processed/dr_off/chroma")
    collection = client.get_collection("ohip_documents")

    results = collection.get(include=['metadatas'])

    for chunk_id, metadata in zip(results['ids'], results['metadatas']):
        parent_section = metadata.get('parent_section', 'Unknown Section')
        specialty = metadata.get('specialty', '')
        fee_code = metadata.get('fee_code', '')

        if specialty and fee_code:
            section_path = f"OHIP Schedule of Benefits > {parent_section} > {specialty} > Fee Code {fee_code}"
        elif fee_code:
            section_path = f"OHIP Schedule of Benefits > {parent_section} > Fee Code {fee_code}"
        else:
            section_path = f"OHIP Schedule of Benefits > {parent_section}"

        metadata['section_path'] = section_path
        metadata['chunk_type'] = 'flat'
        collection.update(ids=[chunk_id], metadatas=[metadata])

    print(f"Updated {len(results['ids'])} OHIP chunks with section_path")

def add_section_path_odb():
    """Add section_path to ODB documents."""
    client = chromadb.PersistentClient(path="data/dr_off_agent/processed/dr_off/chroma")
    collection = client.get_collection("odb_documents")

    results = collection.get(include=['metadatas'])

    for chunk_id, metadata in zip(results['ids'], results['metadatas']):
        therapeutic_class = metadata.get('therapeutic_class', 'Unknown Class')
        generic_name = metadata.get('generic_name', '')
        brand_name = metadata.get('brand_name', '')

        if generic_name and brand_name:
            section_path = f"Ontario Drug Benefit Formulary > {therapeutic_class} > {generic_name} ({brand_name})"
        elif generic_name:
            section_path = f"Ontario Drug Benefit Formulary > {therapeutic_class} > {generic_name}"
        else:
            section_path = f"Ontario Drug Benefit Formulary > {therapeutic_class}"

        metadata['section_path'] = section_path
        metadata['chunk_type'] = 'flat'
        collection.update(ids=[chunk_id], metadatas=[metadata])

    print(f"Updated {len(results['ids'])} ODB chunks with section_path")

def add_section_path_adp():
    """Add section_path to ADP documents."""
    client = chromadb.PersistentClient(path="data/dr_off_agent/processed/dr_off/chroma")
    collection = client.get_collection("adp_documents")

    results = collection.get(include=['metadatas'])

    for chunk_id, metadata in zip(results['ids'], results['metadatas']):
        adp_doc = metadata.get('adp_doc', 'unknown').replace('_', ' ').title()
        part = metadata.get('part', '')
        section_id = metadata.get('section_id', '')

        if part and section_id:
            section_path = f"Assistive Devices Program > {adp_doc} > Part {part} > Section {section_id}"
        elif section_id:
            section_path = f"Assistive Devices Program > {adp_doc} > Section {section_id}"
        else:
            section_path = f"Assistive Devices Program > {adp_doc}"

        metadata['section_path'] = section_path
        metadata['chunk_type'] = 'flat'
        collection.update(ids=[chunk_id], metadatas=[metadata])

    print(f"Updated {len(results['ids'])} ADP chunks with section_path")

if __name__ == "__main__":
    print("Adding section_path metadata to Dr. OFF collections...")
    add_section_path_ohip()
    add_section_path_odb()
    add_section_path_adp()
    print("Done!")
```

---

## Conclusion

**Dr. OFF Collections Status:**
- ✅ Good retrieval metrics (per user)
- ✅ Strong domain-specific metadata (fee codes, DINs, policy IDs)
- ⚠️ Missing hierarchical metadata (section_path, chunk_type)
- ⚠️ Small chunk sizes (acceptable for transactional data)
- ⚠️ Some large chunks in ODB (4.3% are 501-800 words)

**Recommendation:**
1. **Immediate:** Add section_path and chunk_type metadata to all collections
   - Low effort, high value for AI agent response formatting
   - Maintains consistency with Dr. OPA collections

2. **Monitor:** Track retrieval metrics after section_path addition
   - If Faithfulness remains >90%, no further action needed
   - If Faithfulness drops, consider parent/child chunking for large ODB chunks

3. **Future Enhancement:** Implement parent context enrichment (Issue #6 enhancement)
   - Will work seamlessly once section_path metadata is added

**Next Steps:**
1. Create `scripts/add_section_path_dr_off.py`
2. Run script to update all 18,408 chunks
3. Validate with sample queries
4. Document changes in backlog
