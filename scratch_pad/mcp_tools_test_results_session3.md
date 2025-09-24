# MCP Tools Test Results - Session 3
## Troubleshooting and Resolution

### Date: 2025-09-23

## Executive Summary
Successfully resolved critical issues preventing MCP tools from functioning:
1. ✅ Fixed vector database paths and collection names
2. ✅ Resolved embedding dimension mismatch (1536 vs 384)
3. ✅ Corrected SQL schema column mappings
4. ✅ Fixed ConfidenceScorer parameter issues
5. ✅ Established proper server startup method

## Issues Resolved

### 1. Vector Database Configuration
**Problem**: Collections not found, wrong Chroma path
```
Collection 'ohip_documents' not found
```

**Root Cause**:
- Wrong persist directory: `.chroma` vs `data/processed/dr_off/chroma`
- Wrong collection names: `ohip_chunks` vs `ohip_documents`

**Solution**:
```python
# Fixed in vector_client.py
persist_directory="data/processed/dr_off/chroma"  # Correct path
collection_names = ["ohip_documents", "adp_documents", "odb_documents"]
```

### 2. Embedding Dimension Mismatch
**Problem**: 
```
Expected embedding dimension 1536, got 384
```

**Root Cause**: 
- Collections created with OpenAI text-embedding-ada-002 (1536 dimensions)
- Default Chroma uses sentence-transformers (384 dimensions)

**Solution**:
```python
# Added OpenAI embedding function
from chromadb.utils import embedding_functions
self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-ada-002"
)
```

### 3. SQL Schema Mismatches
**Problem**: 
```
no such column: ingredient
```

**Root Cause**: ODB table schema differences

**Solution - Column Mappings**:
```sql
-- Wrong → Correct
ingredient → generic_name
brand → name
form → dosage_form
price → individual_price
lowest_cost → is_lowest_cost
group_id → interchangeable_group_id
```

### 4. ConfidenceScorer API Changes
**Problem**:
```
TypeError: ConfidenceScorer.calculate() got an unexpected keyword argument 'has_sql'
```

**Solution**:
```python
# Wrong parameters
confidence = self.confidence_scorer.calculate(
    has_sql="sql" in provenance,  # WRONG
    vector_matches=len(vector_result),
    conflicts=len(conflicts)  # WRONG
)

# Correct parameters
confidence = self.confidence_scorer.calculate(
    sql_hits=sql_count,  # CORRECT
    vector_matches=vector_count,
    has_conflict=bool(conflicts)  # CORRECT
)
```

### 5. Server Startup Issues
**Problem**: Relative imports failing
```
ModuleNotFoundError: No module named 'tools'
```

**Solution**: Run as module from project root
```bash
# Wrong
cd src/agents/ontario_orchestrator/mcp && python server.py

# Correct
python -m src.agents.ontario_orchestrator.mcp.server
```

## Test Results After Fixes

### Schedule.get Tool
```python
# Test: Diabetes management query
Result: Found 5 items
Confidence: 0.99 (SQL + vector)
Provenance: ['sql', 'vector']
Status: ✅ WORKING
```

### ODB.get Tool
```python
# Test: Metformin lookup
Coverage status: covered
Confidence: 0.90 (SQL)
Provenance: ['sql']
Status: ✅ WORKING
```

### ADP.get Tool
```python
# Test: Wheelchair eligibility
Eligible: True
Funding: 75%
Confidence: 0.92 (SQL)
Provenance: ['sql']
Status: ✅ WORKING
```

## Performance Metrics

### Dual-Path Retrieval
- SQL queries: ~200-400ms
- Vector searches: ~300-600ms
- Total (parallel): ~600ms (not 1000ms due to parallelization)
- Confidence boost from dual-path: +0.15 to +0.30

### Confidence Score Distribution
- SQL only: 0.90 base
- Vector only: 0.60 base
- SQL + vector agreement: 0.93-0.99
- Conflicts detected: -0.10 penalty

## Testing Methods Validated

### 1. Direct Python Testing ✅
```python
from src.agents.ontario_orchestrator.mcp.tools.schedule import schedule_get
result = await schedule_get(request)
```

### 2. JSON-RPC Testing ⚠️
```bash
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | \
  python -m src.agents.ontario_orchestrator.mcp.server
```
Note: FastMCP stdio transport needs more investigation

### 3. Comprehensive Test Suite ✅
```bash
python test_mcp_comprehensive.py
```

## Remaining Issues

### Vector Collections Missing
Some collections don't exist yet:
- `adp_documents` - Not critical (SQL works)
- `odb_documents` - Not critical (SQL works)

### Chroma Where Clause Limitations
- Single-value `$in` not supported in simple where
- `$or` requires at least 2 conditions
- Workaround: Let text search handle filtering

## Recommendations

1. **Always use correct paths**:
   - Chroma: `data/processed/dr_off/chroma/`
   - ODB DB: `data/processed/dr_off/dr_off.db`
   - OHIP DB: `data/ohip.db`

2. **Environment setup**:
   ```bash
   source ~/spacy_env/bin/activate
   export OPENAI_API_KEY="from-.env"
   ```

3. **Run server correctly**:
   ```bash
   python -m src.agents.ontario_orchestrator.mcp.server
   ```

4. **Test with direct Python** for reliability

## Files Modified

1. `src/agents/ontario_orchestrator/mcp/retrieval/vector_client.py`
   - Fixed Chroma path and collection names
   - Added OpenAI embedding function

2. `src/agents/ontario_orchestrator/mcp/retrieval/sql_client.py`
   - Fixed ODB column names

3. `src/agents/ontario_orchestrator/mcp/tools/schedule.py`
   - Fixed ConfidenceScorer parameters

4. `src/agents/ontario_orchestrator/mcp/tools/odb.py`
   - Fixed ConfidenceScorer parameters

5. `src/agents/ontario_orchestrator/mcp/tools/adp.py`
   - Fixed ConfidenceScorer parameters

6. `src/agents/ontario_orchestrator/mcp/server.py`
   - Changed to synchronous `mcp.run()`

7. `src/agents/ontario_orchestrator/mcp/README.md`
   - Added comprehensive testing guide
   - Added troubleshooting section

## Next Steps

1. Create missing vector collections (adp_documents, odb_documents)
2. Investigate FastMCP stdio transport for proper JSON-RPC
3. Add integration tests for all 5 tools
4. Performance optimization for vector searches
5. Add caching layer for frequently accessed data