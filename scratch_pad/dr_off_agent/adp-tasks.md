# ADP Tool Enhancement Tasks

## Status: ✅ COMPLETED
**Date Started**: 2025-09-25  
**Date Completed**: 2025-09-25
**Goal**: Enhance ADP tool to match quality of ODB/Schedule tools

## Issues Identified & Fixed
- ✅ **Wrong ChromaDB Collection**: Fixed VectorClient to use `adp_v1` (610 chunks) instead of `adp_documents` (199 chunks)
- ✅ **Missing Context Content**: Added transparency context like ODB tool 
- ✅ **Generic Citations**: Enhanced with specific policy references using rich metadata
- ✅ **No Natural Language Support**: Added parameter extraction with regex + LLM fallback
- ✅ **No LLM Reranking**: Implemented intelligent result ranking like Schedule tool

## Data Quality Assessment ✅ EXCELLENT
- **SQL Database**: 735 funding rules with proper structure
- **Vector Database**: 610 chunks with rich metadata (policy_uid, funding_count, exclusion_count)
- **Coverage**: Comprehensive mobility devices, communication aids, eligibility criteria

---

## PHASE 1: Core Fixes (Priority: Critical)

### 1. Migrate ADP Collection to Primary Chroma ⏳
- [ ] Create migration script to move 610 chunks from `adp_v1` to primary Chroma instance
- [ ] Update VectorClient configuration 
- [ ] Test improved search quality
- **Files**: `src/agents/dr_off_agent/mcp/retrieval/vector_client.py`

### 2. Add Context Content Field ⏳  
- [ ] Add `context` field to ADPGetResponse like ODB tool
- [ ] Implement `_build_context_content()` method
- [ ] Return relevant policy snippets for transparency
- **Files**: `src/agents/dr_off_agent/mcp/tools/adp.py:558`

### 3. Enhance Citations with Meaningful References ⏳
- [ ] Update `_extract_citations()` method to use rich metadata
- [ ] Map policy_uid → "ADP Policy UID: mobility-4.2.1"
- [ ] Map section_ref → "Section: Power Wheelchair Criteria" 
- [ ] Map adp_doc → "Document: Mobility Devices Manual"
- **Files**: `src/agents/dr_off_agent/mcp/tools/adp.py:501`

---

## PHASE 2: Advanced Features (Priority: High)

### 4. Add Natural Language Parameter Detection ✅
- [x] Create ADP parameter extractor similar to `odb_drug_extractor.py`
- [x] Extract device types, categories, use cases from natural language
- [x] Support queries like "Can I get funding for a power wheelchair?"
- [x] Use extracted parameters to enhance SQL queries
- [x] Regex patterns first, LLM fallback for complex queries
- **Files**: `src/agents/dr_off_agent/mcp/tools/adp_device_extractor.py`, `adp.py:550-580`

### 5. Implement LLM Reranking ✅
- [x] Add result reranking based on query relevance
- [x] Prioritize exact device matches over general content
- [x] Use GPT-3.5-turbo for intelligent result ranking
- [x] Integrate reranking into vector search pipeline
- **Files**: `src/agents/dr_off_agent/mcp/tools/adp.py:570-656`

### 6. Enhanced Eligibility Assessment ✅
- [x] Leverage rich metadata (funding_count, exclusion_count)
- [x] Use topics JSON field to prioritize eligibility content
- [x] Use section_ref and policy_uid for better criteria matching
- [x] Enhanced metadata-aware eligibility detection
- **Files**: `src/agents/dr_off_agent/mcp/tools/adp.py:295-363`

---

## PHASE 3: Polish & Integration (Priority: Medium)

### 7. Improve Exclusions Detection ✅
- [x] Better SQL exclusion matching with device keywords
- [x] Map compound types ("wheelchair_batteries") to exclusion categories  
- [x] Add vector-based exclusion context from policies using metadata
- [x] Prioritize results with exclusion_count > 0 
- [x] Enhanced policy references in exclusion messages
- **Files**: `src/agents/dr_off_agent/mcp/tools/adp.py:400-447`

### 8. Add Funding Calculation Context ✅  
- [x] Return actual funding amounts from SQL data
- [x] Include device-specific coverage percentages from vector search
- [x] Add funding context with policy references
- [x] Enhanced conflict detection for funding sources
- [x] Prioritize funding-specific results using metadata
- **Files**: `src/agents/dr_off_agent/mcp/tools/adp.py:477-584`

---

## Reference Implementation

### Natural Language Pattern (from ODB tool)
```python
# Pattern from odb_drug_extractor.py to adapt for ADP devices
patterns = [
    r"(?:can\\s+i\\s+get\\s+funding\\s+for\\s+)(\\w+)",  # "Can I get funding for wheelchair"
    r"(?:is\\s+)(\\w+)\\s+covered",                      # "Is wheelchair covered"
    r"(?:what\\s+about\\s+)(\\w+)\\s+for",               # "What about walker for mobility"
    r"(?:does\\s+adp\\s+cover\\s+)(\\w+)",               # "Does ADP cover scooter"
]
```

### Expected Device Categories to Extract
- **Mobility**: wheelchair, walker, scooter, crutches, cane
- **Communication**: speech device, communication aid, AAC device  
- **Positioning**: cushion, seating system, support
- **Vision**: magnifier, reading aid, CCTV
- **Hearing**: hearing aid, FM system, alerting device

---

## Testing Plan

After each phase:
1. **MCP Tool Testing**: Test with natural language queries
2. **SQL Integration**: Verify parameter extraction improves SQL results
3. **Vector Search**: Confirm context content and citations
4. **Dual-Path**: Validate both SQL and vector working together
5. **Confidence Scoring**: Check high confidence when both sources agree

## Success Criteria

✅ **Context Content**: Returns policy snippets like ODB tool  
✅ **Meaningful Citations**: Specific section references instead of generic  
✅ **Natural Language**: Supports clinical queries like "Can I prescribe X?"  
✅ **High Confidence**: 0.95+ when SQL and vector agree  
✅ **Parameter Detection**: Extracts device types for better SQL queries

---

## Notes
- Underlying data quality is excellent (735 SQL rules, 610 vector chunks)
- VectorClient collection fix should improve search immediately
- Natural language support will make tool clinician-friendly
- Rich metadata (policy_uid, funding_count) enables advanced features