# Dr. OFF MCP Server - Testing Guide

## Overview
The Dr. OFF MCP server provides 5 tools for Ontario healthcare queries using FastMCP with dual-path retrieval (SQL + vector search in parallel).

## Prerequisites

### 1. Environment Setup
```bash
# REQUIRED: Activate the spacy environment
source ~/spacy_env/bin/activate

# Install dependencies
pip install fastmcp chromadb openai pydantic

# Set OpenAI API key (required for vector embeddings)
export OPENAI_API_KEY="your-key"
```

### 2. Database Verification
```bash
# Verify databases exist
ls -la data/ohip.db                    # Primary OHIP database
ls -la data/processed/dr_off/dr_off.db # ODB database
ls -la data/processed/dr_off/chroma/   # Vector store (correct path!)

# Check database contents
sqlite3 data/ohip.db "SELECT COUNT(*) FROM ohip_fee_schedule;"  # Expected: 4166
sqlite3 data/processed/dr_off/dr_off.db "SELECT COUNT(*) FROM odb_drugs;"  # Check ODB data
```

## Starting the MCP Server

### IMPORTANT: Run as Module
The server must be run as a module to handle imports correctly:

```bash
# From project root (NOT from mcp directory)
source ~/spacy_env/bin/activate
python -m src.agents.ontario_orchestrator.mcp.server

# Server logs will show:
# Starting Dr. OFF MCP server...
# Registered tools:
#   - coverage.answer: Main orchestrator for clinical questions
#   - schedule.get: OHIP Schedule lookup
#   - adp.get: ADP device eligibility and funding
#   - odb.get: ODB drug formulary lookup
#   - source.passages: Retrieve exact text chunks
```

## Testing Methods

### Method 1: Direct Python Testing (RECOMMENDED)
Create test scripts that call tool functions directly:

```python
#!/usr/bin/env python
import asyncio
import sys
sys.path.insert(0, '.')

from src.agents.ontario_orchestrator.mcp.tools.schedule import schedule_get
from src.agents.ontario_orchestrator.mcp.tools.odb import odb_get

async def test():
    # Test schedule lookup
    schedule_result = await schedule_get({
        "q": "diabetes management",
        "codes": [],
        "include": ["codes", "fee", "limits"],
        "top_k": 5
    })
    print(f"Found {len(schedule_result.get('items', []))} items")
    print(f"Confidence: {schedule_result.get('confidence', 0):.2f}")
    
    # Test ODB lookup
    odb_result = await odb_get({
        "drug": "metformin",
        "check_alternatives": True,
        "include_lu": True,
        "top_k": 3
    })
    print(f"Coverage: {odb_result.get('coverage_status')}")
    print(f"Confidence: {odb_result.get('confidence', 0):.2f}")

asyncio.run(test())
```

### Method 2: Bash Script Testing
Use the included test script:

```bash
# Run test script
bash test_mcp_cli.sh

# Or create your own:
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | \
  python -m src.agents.ontario_orchestrator.mcp.server 2>/dev/null | python -m json.tool
```

### Method 3: MCP CLI Testing (if installed)
```bash
# Install MCP CLI if not already installed
pip install mcp-cli

# Connect to the server
mcp-cli connect --command "python -m src.agents.ontario_orchestrator.mcp.server"

# List available tools
mcp-cli list-tools

# Call a tool
mcp-cli call schedule.get '{
  "q": "diabetes management",
  "codes": [],
  "include": ["codes", "fee", "limits"],
  "top_k": 5
}'

# Or use FastMCP dev mode
fastmcp dev src/agents/ontario_orchestrator/mcp/server.py
```

### Method 4: Comprehensive Test Suite
```bash
# Run the comprehensive test
python test_mcp_comprehensive.py 2>/dev/null
```

### Schedule.get Examples

#### 1. MRP Discharge Billing
```bash
mcp test schedule.get '{
  "q": "MRP billing day of discharge after 72hr admission",
  "codes": ["C124", "C122", "C123"],
  "include": ["codes", "fee", "limits", "documentation"]
}'
```

#### 2. Emergency Consultation
```bash
mcp test schedule.get '{
  "q": "internist consultation in emergency department",
  "codes": ["A135", "A935"],
  "include": ["fee", "specialty_restrictions"]
}'
```

#### 3. House Call with Premiums
```bash
mcp test schedule.get '{
  "q": "house call assessment elderly patient with premium",
  "codes": ["B998", "B992", "B994"],
  "include": ["fee", "premiums", "time_restrictions"]
}'
```

### ADP.get Examples

#### 1. Power Wheelchair with CEP Check
```bash
mcp test adp.get '{
  "device": {"category": "mobility", "type": "power_wheelchair"},
  "check": ["eligibility", "funding", "cep"],
  "patient_income": 19000
}'
```

#### 2. Scooter Batteries (Should be Excluded)
```bash
mcp test adp.get '{
  "device": {"category": "mobility", "type": "scooter_batteries"},
  "check": ["exclusions", "replacement_schedule"]
}'
```

#### 3. SGD for ALS Patient
```bash
mcp test adp.get '{
  "device": {"category": "comm_aids", "type": "SGD"},
  "check": ["eligibility", "funding", "forms"],
  "use_case": {"diagnosis": "ALS", "cognitive_intact": true}
}'
```

#### 4. Walker for Elderly
```bash
mcp test adp.get '{
  "device": {"category": "mobility", "type": "walker"},
  "check": ["eligibility", "funding"],
  "use_case": {"age": 85, "mobility_limited": true}
}'
```

#### 5. Car Substitute Check
```bash
mcp test adp.get '{
  "device": {"category": "mobility", "type": "power_scooter"},
  "check": ["eligibility", "exclusions"],
  "use_case": {
    "primary_use": "shopping and errands",
    "can_walk_indoors": true,
    "outdoor_only": true
  }
}'
```

## Direct Python Testing

### Test Script Example
```python
import asyncio
import json
from src.agents.ontario_orchestrator.mcp.tools.schedule import schedule_get
from src.agents.ontario_orchestrator.mcp.tools.adp import adp_get

async def test_tools():
    # Test schedule.get
    schedule_result = await schedule_get({
        "q": "C124 discharge billing",
        "codes": ["C124"],
        "include": ["codes", "fee", "documentation"]
    })
    print("Schedule Result:", json.dumps(schedule_result, indent=2))
    
    # Test adp.get
    adp_result = await adp_get({
        "device": {"category": "mobility", "type": "walker"},
        "check": ["eligibility", "funding"],
        "patient_income": 19000
    })
    print("ADP Result:", json.dumps(adp_result, indent=2))

# Run tests
asyncio.run(test_tools())
```

## Expected Response Structure

### Successful Response
All tools return:
- `provenance`: ["sql", "vector"] - Shows both paths ran
- `confidence`: 0.0-1.0 - Higher is better (0.9+ is very confident)
- `citations`: List of sources with page numbers
- Tool-specific data (items, eligibility, funding, etc.)

### Example Schedule.get Response
```json
{
  "provenance": ["sql", "vector"],
  "confidence": 0.93,
  "items": [
    {
      "code": "C124",
      "description": "Day of discharge from hospital by MRP",
      "fee": 31.00,
      "requirements": "Requires discharge summary documentation",
      "limits": null,
      "page_num": 45
    }
  ],
  "citations": [
    {
      "source": "schedule.pdf",
      "loc": "GP-C124",
      "page": 45
    }
  ],
  "conflicts": []
}
```

### Example ADP.get Response
```json
{
  "provenance": ["sql", "vector"],
  "confidence": 0.96,
  "eligibility": {
    "basic_mobility": true,
    "ontario_resident": true,
    "valid_prescription": true
  },
  "funding": {
    "client_share_percent": 25.0,
    "adp_contribution": 75.0,
    "repair_coverage": "Not covered"
  },
  "cep": {
    "income_threshold": 28000.0,
    "eligible": true,
    "client_share": 0.0
  },
  "citations": [...],
  "exclusions": []
}
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Import Errors
**Problem:** `ModuleNotFoundError: No module named 'src'`
**Solution:** Run server as module from project root:
```bash
python -m src.agents.ontario_orchestrator.mcp.server
```

#### 2. Vector Database Not Found
**Problem:** `Collection 'ohip_documents' not found`
**Solution:** 
- Correct Chroma path is `data/processed/dr_off/chroma/` (NOT `.chroma/`)
- Collections needed: `ohip_documents`, `adp_documents`, `odb_documents`
```bash
ls -la data/processed/dr_off/chroma/
```

#### 3. Embedding Dimension Mismatch
**Problem:** `Expected embedding dimension 1536, got 384`
**Solution:** Collections use OpenAI embeddings. Set API key:
```bash
export OPENAI_API_KEY="your-key"
# Key should be in .env file in project root
```

#### 4. SQL Column Errors
**Problem:** `no such column: ingredient`
**Solution:** Database schema differences. Correct mappings:
- `ingredient` → `generic_name`
- `brand` → `name`
- `form` → `dosage_form`
- `price` → `individual_price`
- `lowest_cost` → `is_lowest_cost`
- `group_id` → `interchangeable_group_id`

#### 5. ConfidenceScorer Parameter Errors
**Problem:** `TypeError: ConfidenceScorer.calculate() got an unexpected keyword argument 'has_sql'`
**Solution:** Use correct parameters:
```python
confidence = ConfidenceScorer.calculate(
    sql_hits=count,           # not has_sql
    vector_matches=count,     # correct
    has_conflict=boolean      # not conflicts
)
```

#### 6. FastMCP Tools Not Listed
**Problem:** Tools not appearing in JSON-RPC responses
**Solution:** 
- Tools must be registered with explicit names
- Server must have synchronous `mcp.run()` (not `await`)
- Run from project root as module

#### 7. Timeout Errors
- SQL timeout: 500ms default
- Vector timeout: 1000ms default
- Both run in parallel, so total ~1000ms not 1500ms
- Edit timeouts in `retrieval/sql_client.py` and `retrieval/vector_client.py`

#### 8. Low Confidence Scores
- < 0.6: No SQL results, vector only
- 0.6-0.7: Limited evidence
- 0.7-0.8: Some corroboration
- 0.8-0.9: SQL with vector support
- 0.9+: Strong agreement between sources

## Performance Expectations

- **Target p50 latency**: < 0.8 seconds
- **Target p95 latency**: < 1.5 seconds
- **Parallel execution**: SQL (500ms) + Vector (1000ms) = ~1000ms total (not 1500ms)
- **Confidence scores**:
  - 0.9+: SQL and vector agree
  - 0.8-0.9: SQL with some vector support
  - 0.7-0.8: Limited corroboration
  - < 0.7: Conflicts or limited evidence

## Test Coverage Areas

### Schedule.get
- ✅ Fee code lookups (C124, A135, etc.)
- ✅ Premium calculations (evening, weekend)
- ✅ Documentation requirements
- ✅ Specialty restrictions
- ✅ Virtual care codes

### ADP.get  
- ✅ Device eligibility (walkers, wheelchairs)
- ✅ Funding percentages (75/25 split)
- ✅ CEP eligibility ($28k/$39k thresholds)
- ✅ Exclusions (batteries, repairs)
- ✅ Car substitute detection
- ✅ Fast-track processes (ALS)

## Logging and Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### View SQL Queries
```bash
# Watch SQL queries in real-time
sqlite3 data/ohip.db
.mode column
.headers on
SELECT * FROM ohip_fee_schedule WHERE fee_code = 'C124';
```

### Check Vector Store
```python
import chromadb
client = chromadb.PersistentClient(path=".chroma")
collection = client.get_collection("ohip_chunks")
print(f"Total embeddings: {collection.count()}")
```

## Contact & Support

For issues or questions:
- Check `scratch_pad/dr_off_sync.md` for implementation status
- Review `scratch_pad/mcp_tools_test_results.md` for test cases
- See `docs/agents/ontario_orchestrator/dr_off_agent/mcp_tools_specification.md` for full specs