# Agent Retrieval Depth & Completeness Improvements

**Issue**: Dr. OPA and Dr. OFF agents return shallow "bookmark-like" responses instead of comprehensive, detailed guidance.

**User Feedback Summary**:
- ❌ IPAC query: Missed detailed PHO sterilization requirements (autoclave specs, processing room requirements)
- ❌ Billing query: Missed several applicable house call billing codes
- ❌ Policy query: Good results (control case)
- ❌ General pattern: Acting like a "bookmark" rather than synthesizing deep content

---

## Root Cause Analysis

### 1. **Dr. OPA Agent Issues**

**Problem**: Returns summaries but misses granular implementation details

**Root Causes**:
- ✗ **Chunk truncation**: Sections truncated at 500 chars in search results (server.py:223)
- ✗ **Single-pass retrieval**: Agent doesn't follow up with `opa_get_section` for full details
- ✗ **Low top_k default**: Only retrieves 10 results, misses related subsections
- ✗ **No multi-hop**: Doesn't traverse to child sections or cross-references
- ✗ **Instructions lack depth emphasis**: Say "comprehensive" but don't mandate:
  - Using `opa_get_section` when summaries insufficient
  - Checking for child sections and related guidance
  - Searching multiple related terms

**Example Failure**:
```
Query: "IPAC sterilization requirements for medical office"
Retrieved: General summary about sterilization standards
Missed: Autoclave specifications, processing room requirements, PHO-specific protocols
Why: Only got 500-char summary, didn't retrieve full section with detailed annexes
```

### 2. **Dr. OFF Agent Issues**

**Problem**: Misses billing codes and doesn't provide comprehensive coverage

**Root Causes**:
- ✗ **No iterative search**: Doesn't search synonyms ("house call" + "home visit" + "domiciliary")
- ✗ **Low top_k in schedule_get**: Default 6 results misses edge cases
- ✗ **No code family expansion**: Doesn't look for base code + premiums + modifiers
- ✗ **Instructions lack completeness checks**: Don't require:
  - Checking all billing code variations
  - Including related fees (travel, premiums, after-hours)
  - Verifying full code coverage for the service

**Example Failure**:
```
Query: "Billing codes for house call"
Retrieved: 2-3 base visit codes
Missed: Travel premiums, after-hours codes, documentation requirements
Why: Only searched "house call", didn't try "domiciliary" or "home visit"
```

### 3. **Data Structure Limitations**

- **Chunk size**: 500-char truncation loses critical detail
- **No hierarchy**: Parent-child section relationships not leveraged
- **Flat retrieval**: Vector search returns isolated chunks without context
- **No overlap**: Adjacent chunks with related info aren't connected

---

## Improvement Plan

### 🔴 **Phase 1: Immediate Fixes** (< 1 hour implementation)

#### 1.1 Enhance Dr. OPA System Instructions

**File**: `src/ai_agents/dr_opa_agent/openai_agent.py` (around line 430)

**Add**:
```python
**RETRIEVAL STRATEGY FOR COMPREHENSIVE ANSWERS**:
When responding to queries requiring detailed implementation guidance:

1. **Initial Search**: Use opa_search_sections with appropriate filters
2. **Deep Dive**: For top 2-3 most relevant sections, use opa_get_section(include_children=True, include_context=True) to retrieve:
   - Full section text (not truncated)
   - Child subsections with implementation details
   - Related cross-references
3. **Breadth Check**: Search for synonyms and related terms (e.g., "sterilization" + "reprocessing" + "autoclave")
4. **Completeness Verification**: For procedural guidance, ensure you've retrieved:
   - Requirements AND implementation steps
   - Standards AND exceptions
   - Policy AND practical guidance

**CRITICAL FOR IPAC QUERIES**: PHO guidance often has detailed annexes and appendices - always retrieve full sections to capture equipment specifications, step-by-step protocols, and regulatory updates.

**Example Multi-Step Pattern**:
Query: "Sterilization requirements for medical office"
Step 1: opa_ipac_guidance(query="sterilization medical office") → Get overview
Step 2: opa_get_section(section_id=<top_result>, include_children=True) → Get full protocol
Step 3: opa_search_sections(query="autoclave specifications PHO") → Get equipment details
Step 4: Synthesize complete guidance from all retrieved sections
```

#### 1.2 Enhance Dr. OFF System Instructions

**File**: `src/ai_agents/dr_off_agent/openai_agent.py` (around line 490)

**Add**:
```python
**BILLING CODE COMPLETENESS REQUIREMENTS**:
For OHIP billing questions, ensure comprehensive code coverage:

1. **Base Service Code**: The primary procedure/visit code
2. **Premium Codes**: After-hours, on-call, travel, emergency
3. **Modifier Codes**: Age-based, complexity, location-based
4. **Related Services**: Complementary billable services in same encounter
5. **Synonyms Search**: Search multiple terms (e.g., "house call" + "home visit" + "domiciliary" + "community visit")
6. **Increase top_k**: Use top_k=15 for billing queries to ensure all applicable codes surface

**VERIFICATION STEP**: After retrieving codes, explicitly check: "Are there any related premium codes, travel fees, or time-based modifiers applicable to this service?"

**Example Multi-Search Pattern**:
Query: "House call billing codes"
Step 1: schedule_get(q="house call", top_k=15) → Get house call codes
Step 2: schedule_get(q="domiciliary visit", top_k=15) → Check synonym
Step 3: schedule_get(q="travel premium", top_k=15) → Get travel codes
Step 4: Combine all applicable codes with clear descriptions
```

#### 1.3 Remove Chunk Truncation

**File**: `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py` (line 223)

**Current**:
```python
text=data.get('section_text', data.get('text', ''))[:500],  # Truncates!
```

**Fix**:
```python
text=data.get('section_text', data.get('text', ''))[:1500],  # Triple the context
```

**Rationale**: 500 chars is too limiting for procedural guidance. 1500 chars provides enough context while keeping response sizes manageable.

#### 1.4 Increase Default top_k Values

**Dr. OPA**: `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py`
```python
# Line 156 - change default
top_k: int = 15  # Was 10
```

**Dr. OFF**: `src/ai_agents/dr_off_agent/mcp/server.py`
```python
# Line 139 - change default
top_k: int = 15  # Was 6
```

**Rationale**: More results = better chance of capturing all relevant codes/sections.

---

### 🟡 **Phase 2: Medium-Term Improvements** (This week)

#### 2.1 Add Few-Shot Examples to Agent Instructions

Add concrete examples showing multi-step retrieval patterns:

```python
**EXAMPLE: Comprehensive IPAC Query**
User: "What are the sterilization requirements for reusable medical devices?"

Step 1: opa_ipac_guidance(query="sterilization reusable medical devices")
Result: Overview of PHO sterilization standards

Step 2: opa_get_section(section_id="pho_sterilization_protocol", include_children=True)
Result: Full protocol including:
- Pre-cleaning requirements
- Autoclave specifications (steam, temperature, pressure)
- Processing room requirements
- Quality assurance testing
- Documentation requirements

Step 3: opa_search_sections(query="autoclave validation PHO")
Result: Validation protocols and monitoring requirements

Response: [Comprehensive synthesis of all retrieved information]
```

#### 2.2 Add Completeness Verification Prompts

Add to agent instructions:
```python
**COMPLETENESS SELF-CHECK**:
Before finalizing your response, verify:
□ Have I retrieved full section text, not just summaries?
□ Have I searched relevant synonyms and related terms?
□ For procedures: Do I have both requirements AND implementation steps?
□ For billing: Do I have base codes AND premiums/modifiers?
□ For policies: Do I have the rule AND the exceptions?

If any box is unchecked, perform additional searches before responding.
```

#### 2.3 Implement Query Expansion

**New utility**: `src/ai_agents/dr_opa_agent/dr_opa_mcp/utils/query_expansion.py`

```python
MEDICAL_SYNONYMS = {
    "sterilization": ["reprocessing", "disinfection", "cleaning", "decontamination"],
    "house call": ["home visit", "domiciliary visit", "community visit", "outreach"],
    # ... more mappings
}

def expand_query(query: str) -> List[str]:
    """Expand query with medical synonyms and related terms."""
    # Return original + expanded variations
```

---

### 🟢 **Phase 3: Long-Term Enhancements** (Next sprint)

#### 3.1 Implement `opa_deep_search` Tool

**New MCP tool**: Deep iterative retrieval

```python
@mcp.tool(name="opa_deep_search", description="Iterative deep search with auto-expansion")
async def deep_search_handler(
    query: str,
    follow_up_levels: int = 2,  # How many levels to dig
    expand_synonyms: bool = True,
    retrieve_full_sections: bool = True
) -> Dict[str, Any]:
    """
    Performs iterative deep search:
    1. Initial semantic search (top 20 results)
    2. Auto-expands with synonyms if enabled
    3. Retrieves full sections for top 5 results
    4. Extracts cross-references and child sections
    5. Searches again with discovered related terms
    6. Aggregates and deduplicates all findings

    Returns comprehensive results with completeness score.
    """
```

#### 3.2 Add Hierarchical Chunk Retrieval

**Approach**: When retrieving a child chunk, also retrieve:
- Parent section header
- Sibling chunks (adjacent content)
- Cross-referenced sections

**Implementation**:
```python
def get_chunk_with_hierarchy(chunk_id: str):
    chunk = get_chunk(chunk_id)
    parent = get_parent_section(chunk.parent_id)
    siblings = get_sibling_chunks(chunk.parent_id)
    cross_refs = get_cross_references(chunk.document_id)

    return {
        "chunk": chunk,
        "context": {
            "parent": parent,
            "siblings": siblings,
            "related": cross_refs
        }
    }
```

#### 3.3 Implement Graph-Based Retrieval

**Store relationships**:
- Parent-child sections
- Cross-references ("See also...")
- Updates/supersedes relationships
- Related guidance documents

**Query time**: Automatically traverse graph to pull related content

---

## Testing Strategy

### Test Cases (Re-run user's failing queries)

#### Test 1: IPAC Sterilization
```
Query: "What are Public Health Ontario requirements for sterilization in medical offices?"

Expected Results:
✓ General sterilization standards (overview)
✓ Autoclave specifications (temperature, pressure, steam type)
✓ Processing room requirements (ventilation, surfaces, workflow)
✓ Specific PHO protocols and monitoring requirements
✓ Equipment validation procedures
✓ Documentation requirements

Success Criteria: Agent retrieves ALL 6 components above
```

#### Test 2: House Call Billing
```
Query: "What are the billing codes for a house call?"

Expected Results:
✓ Base visit codes (comprehensive assessment, focused assessment)
✓ Travel premiums (distance-based)
✓ After-hours codes (evening, weekend, overnight)
✓ Documentation requirements
✓ Related modifier codes

Success Criteria: Agent retrieves base codes + ≥2 premium types
```

#### Test 3: Third-Party Forms (Control)
```
Query: "Time requirements for completing third-party forms"

Expected Results:
✓ Complete policy text with all timelines
✓ Exceptions and special circumstances
✓ CPSO expectations vs. advice distinction

Success Criteria: Response includes complete policy + exceptions
```

### Metrics to Track

**Before/After Comparison**:
| Metric | Before | Target |
|--------|--------|--------|
| Avg sections retrieved per query | 3-5 | 8-12 |
| Avg context chars per result | 500 | 1500 |
| Multi-search queries (%) | <10% | >60% |
| User satisfaction (completeness) | Low | High |
| Missing critical details (%) | 40-60% | <10% |

---

## Implementation Checklist

### Phase 1 (Immediate - Do Now)
- [ ] Update Dr. OPA system instructions with retrieval strategy
- [ ] Update Dr. OFF system instructions with completeness requirements
- [ ] Change chunk truncation from 500 → 1500 chars
- [ ] Increase top_k defaults (OPA: 10→15, OFF: 6→15)
- [ ] Test with 3 user queries

### Phase 2 (This Week)
- [ ] Add few-shot examples to both agents
- [ ] Implement completeness self-check prompts
- [ ] Create query expansion utility
- [ ] Re-test and measure improvements

### Phase 3 (Next Sprint)
- [ ] Design and implement `opa_deep_search` tool
- [ ] Implement hierarchical chunk retrieval
- [ ] Build knowledge graph for policy relationships
- [ ] Implement graph-based retrieval traversal

---

## Success Criteria

**Phase 1 Complete When**:
- ✓ IPAC queries return detailed protocols (not just summaries)
- ✓ Billing queries return comprehensive code lists (base + premiums)
- ✓ Agent uses multi-step retrieval pattern >50% of the time
- ✓ User feedback shows improved depth and completeness

**Final Success**:
- ✓ User reports agents provide "complete, actionable guidance"
- ✓ No more "bookmark" complaints
- ✓ Agents synthesize information from multiple sections automatically
- ✓ Retrieval depth matches user expectations for professional medical guidance

---

## Related Files

**Agent Instructions**:
- `src/ai_agents/dr_opa_agent/openai_agent.py` (line 380-515)
- `src/ai_agents/dr_off_agent/openai_agent.py` (line 397-558)

**MCP Servers**:
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py` (search_sections_handler, line 148-281)
- `src/ai_agents/dr_off_agent/mcp/server.py` (schedule_get_handler, line 134-190)

**Search Implementation**:
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py` (vector search + reranking)

**Test Scripts**:
- Create new: `tests/integration/test_agent_retrieval_depth.py`
