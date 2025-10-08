# Filter Simplification Summary

**Date:** 2025-10-07
**Status:** ✅ Complete
**Impact:** Simplified filter implementation, cleaner agent prompts

---

## Changes Made

### Problem Identified
- MCP tools exposed 12+ filters in request schema
- Most filters were legacy (pre-Issue #6 restructuring) and non-functional
- Agents had no way to discover which filters were valid
- Risk of bloated prompts documenting unused filters

### Solution: Keep Only Essential Filters

**Dr. OPA:** Keep only `sources` filter
**Dr. OFF:** Keep `codes`, `din`, `ingredient`, `drug_class`, `device_category` filters

**Rationale:**
- Dr. OPA `sources`: Filter by organization (CPSO, PHO, CEP, etc.) - fully implemented
- Dr. OFF filters: Enable direct SQL lookup for known codes/DINs - critical for performance

---

## Implementation Details

### 1. Updated Agent System Prompts ✅

#### Dr. OPA Agent
**File:** `src/ai_agents/dr_opa_agent/openai_agent.py` (lines 471-484)

**Added to STEP 2 (RETRIEVE):**
```markdown
**Sources Filter (Target Specific Organizations):**

All tools support a `sources` filter to search specific organizations:
- `filters={"sources": ["cpso"]}` → CPSO policies only
- `filters={"sources": ["pho"]}` → PHO IPAC guidance only
- `filters={"sources": ["cep"]}` → CEP clinical tools only
- `filters={"sources": ["quality_standards"]}` → Quality standards only
- `filters={"sources": ["choosing_wisely"]}` → Choosing Wisely only

**When to Use Sources Filter:**
- User asks "What does CPSO say about X?" → Use `filters={"sources": ["cpso"]}`
- User asks "PHO guidelines for Y" → Use `filters={"sources": ["pho"]}`
- User asks "clinical tools for Z" → Use `filters={"sources": ["cep"]}`
- User asks broad question → Omit filter (searches all sources)
```

#### Dr. OFF Agent
**File:** `src/ai_agents/dr_off_agent/openai_agent.py` (lines 472-491)

**Added to STEP 2 (RETRIEVE):**
```markdown
**Useful Filters (When You Know Specific Codes/Names):**

**schedule_get filters:**
- `codes`: List[str] - Direct OHIP code lookup (e.g., ["E083A", "E083B"])
- Use when: You know specific fee codes from query or previous retrieval

**odb_get filters:**
- `din`: str - Direct DIN lookup (e.g., "02247162")
- `ingredient`: str - Active ingredient name
- `drug_class`: str - Therapeutic class
- Use when: You know specific DIN or ingredient name

**adp_get filters:**
- `device_category`: str - Device type (e.g., "wheelchair", "walker")
- Use when: Query mentions specific device type

**When to Use Filters:**
- Use `codes` filter for follow-up queries when you already know the OHIP codes
- Use `din` or `ingredient` for drug queries with specific names
- Generally start with NO filters (let tools find relevant info first)
```

---

### 2. Simplified semantic_search.py ✅

**File:** `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py`

**Changes:**
- ❌ Removed `document_types` parameter
- ❌ Removed `policy_level` parameter
- ❌ Removed `after_date` parameter
- ❌ Removed `_apply_filters()` method (entire function deleted)
- ✅ Kept `sources` parameter only
- ✅ Sources filter applied at collection selection (before retrieval)

**Before:**
```python
async def search(
    self,
    query: Optional[str] = None,
    sources: Optional[List[str]] = None,
    document_types: Optional[List[str]] = None,  # ❌ Removed
    policy_level: Optional[str] = None,          # ❌ Removed
    after_date: Optional[str] = None,            # ❌ Removed
    k: Optional[int] = None,
    ...
):
    # ... retrieval ...
    filtered = self._apply_filters(              # ❌ Removed
        documents=reranked,
        document_types=document_types,
        policy_level=policy_level,
        after_date=after_date
    )
    enriched = await self._enrich_with_parent_context(filtered[:k])
```

**After:**
```python
async def search(
    self,
    query: Optional[str] = None,
    sources: Optional[List[str]] = None,  # ✅ Only filter kept
    k: Optional[int] = None,
    ...
):
    # ... retrieval ...
    enriched = await self._enrich_with_parent_context(reranked[:k])  # Direct enrichment
```

---

### 3. Updated server.py Handlers ✅

**File:** `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py`

**Changes Applied to:**
- `search_sections_handler()` - Line 163-167
- `policy_check_handler()` - Line 441-447

**Pattern:**
```python
# Before:
filters = filters or {}
sources = filters.get('sources')
doc_types = filters.get('doc_types')
policy_level = filters.get('policy_level', 'both')
after_date = filters.get('after_date')
# ... complex filter logic ...

# After:
filters = filters or {}
sources = filters.get('sources')  # Only extract sources
# All other filters are passthrough (ignored)
```

**Note:** Request schema still accepts other filters (backwards compatibility), but they are ignored internally.

---

## Filters Removed

### ❌ Removed from Implementation:

1. **`document_types` / `doc_types`**
   - Reason: Redundant with `sources` filter
   - Metadata exists but not useful

2. **`policy_level`**
   - Reason: Metadata field exists but mostly unpopulated
   - Would require post-retrieval filtering (too late for ranking)

3. **`after_date` / `date_range`**
   - Reason: Only CEP has dates; CPSO/PHO dates missing
   - Would filter out most results

4. **`setting`** (IPAC)
   - Reason: Metadata field not populated correctly

5. **`pathogen`** (IPAC)
   - Reason: Metadata field doesn't exist

6. **`include_checklists`** (IPAC)
   - Reason: Not relevant after Issue #6 restructuring

7. **`include_superseded`**
   - Reason: Field exists but no superseded docs yet

8. **`include_related`** (CPSO)
   - Reason: Ambiguous, no implementation

9. **`patient_age`** (Programs)
   - Reason: Programs tool uses API, not vector search

10. **`risk_factors`** (Programs)
    - Reason: Programs tool uses API, not vector search

11. **`info_needed`** (Programs)
    - Reason: Programs tool uses API, not vector search

12. **`topics`**
    - Reason: Not implemented in search logic

---

## Benefits of Simplification

### 1. **Cleaner Agent Prompts**
- Before: Would need ~100 lines to document all filters
- After: 14 lines for `sources` filter only
- Agents can focus on one simple, useful filter

### 2. **Reduced Complexity**
- Removed 50+ lines of filter logic from `semantic_search.py`
- Removed `_apply_filters()` method
- No more post-retrieval filtering (better performance)

### 3. **Better Agent UX**
- One clear filter that always works
- No confusion about which filters apply to which tools
- Easy to understand: "Want CPSO? Use sources=['cpso']"

### 4. **Maintainability**
- Less code to maintain
- Filter behavior is predictable (collection selection)
- No metadata dependencies to track

---

## Future Enhancements (Deferred)

If additional filters are needed in the future, they should:

1. ✅ **Have complete metadata** in restructured collections
2. ✅ **Provide clear value** beyond `sources` filter
3. ✅ **Be easy to explain** in agent prompts
4. ✅ **Work at collection selection time** (not post-retrieval)

**Candidates for Future:**
- `specialty` filter for Choosing Wisely (metadata exists, field: `specialty`)
- `condition` filter for Quality Standards (metadata exists, field: `condition`)

---

## Testing Required

### Manual Tests:

1. **Sources Filter Usage:**
   ```python
   # Query: "What does CPSO say about virtual care consent?"
   # Expected: Agent uses filters={"sources": ["cpso"]}
   # Verify: Tool call logs show filter usage
   ```

2. **Multi-Source Query:**
   ```python
   # Query: "What do CPSO and PHO say about hand hygiene?"
   # Expected: Agent uses filters={"sources": ["cpso", "pho"]}
   # Verify: Results from both collections
   ```

3. **Broad Query (No Filter):**
   ```python
   # Query: "Best practices for infection control"
   # Expected: Agent omits filter (searches all sources)
   # Verify: Results from multiple sources
   ```

### Automated Tests:
- Run Issue #5 evaluation after implementation
- Check tool call logs for filter usage rate
- Monitor Coverage/Helpfulness metrics (should not regress)

---

## Related Documents

- `improve_retrieval/ISSUE_5_FILTER_AUDIT.md` - Detailed filter analysis
- `improve_retrieval/ISSUE_5_FILTER_DISCOVERY_ANALYSIS.md` - Original discovery issue
- `improve_retrieval/ISSUE_5_IMPLEMENTATION_SUMMARY.md` - Issue #5 main implementation

---

## Rollback Plan

If simplification causes issues:

1. **Revert semantic_search.py:**
   ```bash
   git checkout HEAD~1 src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py
   ```

2. **Revert server.py:**
   ```bash
   git checkout HEAD~1 src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py
   ```

3. **Remove filter docs from prompt:**
   ```bash
   git checkout HEAD~1 src/ai_agents/dr_opa_agent/openai_agent.py
   ```

---

**Status:** ✅ Complete - Ready for evaluation
