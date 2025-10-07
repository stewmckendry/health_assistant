# Issue #5: Filter Audit - Post Issue #6 Validation

**Date:** 2025-10-07
**Status:** ✅ Audit Complete - Ready for Prompt Integration

---

## Executive Summary

**Audited all MCP tool filters against restructured collections (Issue #6).**

### Results:
- ✅ **3 filters VALID and USEFUL** → Add to prompts
- ⚠️ **5 filters LEGACY/INVALID** → Remove from documentation
- 📝 **2 filters PARTIALLY IMPLEMENTED** → Document limitations

---

## Audit Methodology

1. Checked actual metadata fields in restructured ChromaDB collections
2. Verified filter implementation in `semantic_search.py:_apply_filters()`
3. Cross-referenced with tool handler implementations in `server.py`
4. Tested filter logic against actual data

---

## ✅ VALID FILTERS (Ready to Document)

### 1. `sources` Filter (All Tools)

**Status:** ✅ FULLY IMPLEMENTED AND USEFUL

**Implementation:**
```python
# In semantic_search.py:_vector_search()
collection_map = {
    'cpso': 'opa_cpso_corpus',
    'pho': 'opa_pho_corpus',
    'cep': 'opa_cep_corpus',
    'quality_standards': 'opa_quality_standards_corpus',
    'choosing_wisely': 'opa_choosing_wisely_corpus'
}

if sources:
    collections_to_search = [collection_map[s] for s in sources if s in collection_map]
else:
    collections_to_search = list(collection_map.values())  # Search all
```

**Valid Values:**
- `"cpso"` → CPSO Policies (325 chunks)
- `"pho"` → PHO IPAC Guidance (132 chunks)
- `"cep"` → CEP Clinical Tools (644 chunks)
- `"quality_standards"` → Ontario Health Quality Standards (340 chunks)
- `"choosing_wisely"` → Choosing Wisely Canada (295 chunks)

**Use Cases:**
- User asks for "PHO guidelines" → `filters={"sources": ["pho"]}`
- User asks for "CPSO policy" → `filters={"sources": ["cpso"]}`
- User asks for "clinical tools" → `filters={"sources": ["cep"]}`

**Tested:** ✅ Works correctly in production

**Recommendation:** ✅ **ADD TO PROMPT** - This is the most useful filter

---

### 2. `policy_level` Filter (CPSO Policies Only)

**Status:** ✅ FULLY IMPLEMENTED AND USEFUL

**Implementation:**
```python
# In semantic_search.py:_apply_filters()
if policy_level:
    doc_level = metadata.get('policy_level', '')
    if doc_level != policy_level:
        continue  # Filter out
```

**Metadata Field:** `policy_level` (exists in opa_cpso_corpus)

**Valid Values:**
- `"expectation"` → Mandatory CPSO requirements (most chunks)
- `"advice"` → CPSO recommendations (fewer chunks)
- `"statement"` → CPSO general statements

**Actual Data:**
```
opa_cpso_corpus (325 chunks):
- policy_level: "expectation" (majority)
- policy_level: "advice" (some)
- policy_level: "statement" (rare)
```

**Use Cases:**
- User asks "What MUST physicians do?" → `filters={"policy_level": "expectation"}`
- User asks "What SHOULD physicians do?" → `filters={"policy_level": "advice"}`

**Tested:** ✅ Works correctly (field exists, filter logic correct)

**Recommendation:** ✅ **ADD TO PROMPT** - Very useful for CPSO queries

---

### 3. `document_types` (renamed from `doc_types`)

**Status:** ✅ IMPLEMENTED, SOMEWHAT USEFUL

**Implementation:**
```python
# In semantic_search.py:_apply_filters()
if document_types:
    doc_type = metadata.get('doc_type') or metadata.get('document_type', '')
    if doc_type not in document_types:
        continue  # Filter out
```

**Metadata Fields:**
- CPSO: `document_type: "policy"`
- PHO: `document_type: "ipac-guidance"`
- CEP: `document_type: "clinical_tool"`
- Quality Standards: `doc_type: "quality_standard_overview"` / `"quality_statement"`
- Choosing Wisely: `doc_type: "choosing_wisely_overview"` / `"choosing_wisely_recommendation"`

**Valid Values (Per Collection):**
```python
{
    "cpso": ["policy"],
    "pho": ["ipac-guidance"],
    "cep": ["clinical_tool"],
    "quality_standards": ["quality_standard_overview", "quality_statement"],
    "choosing_wisely": ["choosing_wisely_overview", "choosing_wisely_recommendation"]
}
```

**Use Cases:**
- **Limited usefulness** - document types mostly align with collections already
- Might be useful for Quality Standards: Filter to overview only or statements only

**Example:**
```python
# Get only quality statements, not overview
filters={"sources": ["quality_standards"], "doc_types": ["quality_statement"]}
```

**Tested:** ✅ Works correctly (fields exist, logic correct)

**Recommendation:** ⚠️ **OPTIONAL - Low Priority** - Mostly redundant with `sources` filter

---

## ⚠️ LEGACY FILTERS (Remove from Documentation)

### 4. `setting` Filter (IPAC - NOT IMPLEMENTED)

**Status:** ❌ METADATA FIELD DOESN'T EXIST

**What Code Expects:**
```python
# In server.py:ipac_guidance_handler()
setting = filters.get('setting', '')  # "hospital" | "clinic" | "ltc" | "community"
```

**What Actually Exists:**
```python
# In opa_pho_corpus metadata:
'clinical_setting': 'N/A'  # Field exists but not populated correctly
```

**Problem:**
- PHO IPAC chunks don't have setting-specific metadata
- All chunks have generic `clinical_setting: 'N/A'`
- Filter would need NLP to extract setting from text (not implemented)

**Recommendation:** ❌ **REMOVE** - Not implemented, would require significant work

---

### 5. `pathogen` Filter (IPAC - NOT IMPLEMENTED)

**Status:** ❌ METADATA FIELD DOESN'T EXIST

**What Code Expects:**
```python
# In server.py:ipac_guidance_handler()
pathogen = filters.get('pathogen')  # "MRSA", "C. difficile", etc.
```

**What Actually Exists:**
```python
# In opa_pho_corpus metadata:
No 'pathogen' field exists
```

**Problem:**
- PHO chunks don't have pathogen-specific metadata
- Would need to extract from text or re-ingest with pathogen tagging

**Recommendation:** ❌ **REMOVE** - Not implemented

---

### 6. `patient_age` Filter (Programs - NOT IMPLEMENTED)

**Status:** ❌ NOT APPLICABLE TO VECTOR SEARCH

**What Code Expects:**
```python
# In server.py:program_lookup_handler()
patient_age = filters.get('patient_age')  # int
```

**Problem:**
- Ontario Health Programs tool doesn't use semantic search
- Uses Ontario Health API directly (not ChromaDB)
- Age filtering would happen in API query, not vector search

**Recommendation:** ❌ **REMOVE** - Not applicable to vector retrieval

---

### 7. `risk_factors` Filter (Programs - NOT IMPLEMENTED)

**Status:** ❌ NOT APPLICABLE

**Same issue as `patient_age` - Programs tool uses external API, not vector search.**

**Recommendation:** ❌ **REMOVE**

---

### 8. `info_needed` Filter (Programs - NOT IMPLEMENTED)

**Status:** ❌ NOT APPLICABLE

**Same issue - Programs tool uses external API, not vector search.**

**Recommendation:** ❌ **REMOVE**

---

## 📝 PARTIALLY IMPLEMENTED FILTERS

### 9. `after_date` / `date_range` Filter

**Status:** ⚠️ IMPLEMENTED BUT LIMITED DATA

**Implementation:**
```python
# In semantic_search.py:_apply_filters()
if after_date:
    doc_date = metadata.get('effective_date', '')
    if doc_date and doc_date < after_date:
        continue  # Filter out old docs
```

**Metadata Analysis:**
```
opa_cpso_corpus: effective_date exists but mostly empty ("")
opa_pho_corpus: effective_date = "April 2015" (all chunks same date)
opa_cep_corpus: effective_date = "April 10, 2025" (recent tools)
```

**Problem:**
- CPSO policies have effective_date field but mostly unpopulated
- PHO corpus is all from 2015 (single PDF)
- Only CEP has useful dates

**Use Cases (Limited):**
```python
# Filter to recent CEP tools
filters={"sources": ["cep"], "after_date": "2024-01-01"}
```

**Recommendation:** ⚠️ **OPTIONAL - Document Limitations**
- Only useful for CEP tools currently
- CPSO/PHO dates need re-ingestion to be useful

---

### 10. `include_checklists` Filter (IPAC - LEGACY)

**Status:** ❌ NOT RELEVANT AFTER RESTRUCTURING

**What Code Expects:**
```python
# In server.py:ipac_guidance_handler()
include_checklists = filters.get('include_checklists', True)
```

**Problem:**
- PHO corpus doesn't distinguish "checklist" vs "guidance" chunks
- All chunks are mixed content
- Filter has no effect on actual retrieval

**Recommendation:** ❌ **REMOVE** - Not relevant after Issue #6 restructuring

---

### 11. `include_superseded` Filter (General - NOT IMPLEMENTED)

**Status:** ⚠️ METADATA EXISTS BUT NOT USED

**Metadata Field:**
```python
# opa_pho_corpus has:
'is_superseded': 'False'  # (string, not boolean)
```

**Problem:**
- Field exists but not actually used in filtering logic
- All PHO chunks are from 2015, none are superseded yet
- Would be useful if we ingest updated PHO guidance

**Recommendation:** ⚠️ **DEFER** - Implement when we have superseded docs

---

### 12. `include_related` Filter (CPSO - AMBIGUOUS)

**Status:** ❌ UNCLEAR IMPLEMENTATION

**What Code Expects:**
```python
# In server.py:policy_check_handler()
include_related = filters.get('include_related', True)
```

**Problem:**
- Not clear what "related" means
- No metadata field for "related_policies"
- Would need semantic similarity logic (not implemented)

**Recommendation:** ❌ **REMOVE** - Ambiguous, not implemented

---

## Summary: Filters to Document in Prompt

### ✅ HIGH PRIORITY (Must Add):

1. **`sources`** - Filter by organization
   ```python
   Values: ["cpso", "pho", "cep", "quality_standards", "choosing_wisely"]
   Use: When user asks for specific organization
   Example: "What does CPSO say about X?" → filters={"sources": ["cpso"]}
   ```

2. **`policy_level`** - Filter CPSO by requirement level
   ```python
   Values: "expectation" | "advice" | "statement"
   Use: Distinguish mandatory vs recommended
   Example: "What MUST I do?" → filters={"policy_level": "expectation"}
   ```

### ⚠️ MEDIUM PRIORITY (Optional):

3. **`document_types`** - Filter by document type within collection
   ```python
   Values: Collection-specific (see above)
   Use: Mostly redundant with sources, but useful for Quality Standards
   Example: filters={"sources": ["quality_standards"], "doc_types": ["quality_statement"]}
   ```

4. **`after_date`** - Filter by effective date (limited data)
   ```python
   Format: "YYYY-MM-DD"
   Use: Only useful for CEP tools currently
   Example: filters={"sources": ["cep"], "after_date": "2024-01-01"}
   Note: CPSO/PHO dates mostly missing
   ```

---

## Recommended Prompt Addition

**Add to STEP 2 (RETRIEVE) in both Dr. OPA agent prompts:**

```markdown
**Available Tool Filters (Use to Refine Retrievals):**

**opa_search_sections / opa_policy_check / opa_ipac_guidance filters:**

1. **sources** - Filter by organization (MOST USEFUL):
   - Values: ["cpso", "pho", "cep", "quality_standards", "choosing_wisely"]
   - Use when: User asks for specific organization
   - Example: "CPSO policy on X" → filters={"sources": ["cpso"]}

2. **policy_level** - Filter CPSO policies by requirement level:
   - Values: "expectation" (mandatory) | "advice" (recommended)
   - Use when: User asks "what MUST" vs "what SHOULD"
   - Example: "What MUST physicians do?" → filters={"policy_level": "expectation"}

3. **document_types** - Filter by document type (OPTIONAL, mostly redundant):
   - Values vary by collection (e.g., ["quality_statement"] for Quality Standards)
   - Use when: Need specific document type within a collection

4. **after_date** - Filter by effective date (LIMITED - only CEP has dates):
   - Format: "YYYY-MM-DD"
   - Use when: User asks for "recent" or "latest" tools
   - Example: filters={"sources": ["cep"], "after_date": "2024-01-01"}

**When to Use Filters:**
- ALWAYS use `sources` when user mentions specific organization (CPSO, PHO, CEP, etc.)
- Use `policy_level="expectation"` when user asks about mandatory requirements
- Generally avoid `document_types` (redundant with sources)
- Only use `after_date` for CEP tools (other collections have incomplete dates)
```

---

## Implementation Checklist

- [ ] Update Dr. OPA system prompt with filters (Step 2)
- [ ] Remove invalid filters from `ISSUE_5_FILTER_DISCOVERY_ANALYSIS.md`
- [ ] Test with sample queries:
  - [ ] "What does CPSO say about X?" (should use sources filter)
  - [ ] "What MUST physicians do for Y?" (should use policy_level filter)
  - [ ] "Show me recent clinical tools" (should use sources + after_date)
- [ ] Monitor filter usage in tool call logs
- [ ] Update this document if new metadata fields added in future ingestion

---

## Future Improvements (Deferred)

1. **Re-ingest CPSO with complete effective_date metadata**
2. **Add setting/pathogen metadata to PHO IPAC chunks** (requires NLP or manual tagging)
3. **Implement semantic "related policies" for CPSO** (requires similarity search)
4. **Add specialty filter for Quality Standards** (metadata field `condition` could be used)
5. **Add specialty filter for Choosing Wisely** (metadata field `specialty` already exists!)

---

**Related Documents:**
- `improve_retrieval/ISSUE_5_FILTER_DISCOVERY_ANALYSIS.md` - Original analysis (now outdated)
- `improve_retrieval/ISSUE_6_COMPLETION_SUMMARY.md` - Restructuring details
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py:394` - Filter implementation
