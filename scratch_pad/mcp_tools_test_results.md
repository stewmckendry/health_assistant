# Dr. OFF Agent MCP Tools - Test Results

## Issue Found & Fixed

### Problem
The Dr. OFF Agent's `schedule_get` tool was returning semantically irrelevant results for medical queries.

### Root Cause Analysis

1. **ChromaDB Distance Metric Issue** (Fixed Previously)
   - Collection was using L2 distance instead of cosine similarity
   - Fixed by migrating to cosine similarity metric

2. **Embedding Model Mismatch** (Fixed Now)
   - VectorClient was using wrong embedding model
   - Collection created with: `text-embedding-3-small`
   - VectorClient was using: `text-embedding-ada-002` (then falling back to ChromaDB default)
   - **This was the main issue causing poor semantic search results**

### Fix Applied
Updated `/src/agents/dr_off_agent/mcp/retrieval/vector_client.py`:
- Changed from ChromaDB's embedding functions to direct OpenAI API calls
- Now using correct model: `text-embedding-3-small`
- Properly generates embeddings that match the collection

## Test Results

### Before Fix (Poor Relevance)
Query: "hospital admission assessment"
- Returns: Surgical procedures (septal perforation repair, etc.)

Query: "consultation internal medicine"  
- Returns: Lacrimal tract surgery, ear procedures

### After Fix (Good Relevance)
Query: "hospital admission assessment"
- ✅ W562: Admission assessment - Type 1 ($69.35)
- ✅ G556: ICU/NICU admission assessment ($136.40)
- ✅ W862: Type 1 Admission assessment - Nephrology ($69.35)

Query: "consultation internal medicine"
- ✅ A130: Comprehensive internal medicine consultation ($310.45)
- ✅ C135: Consultation - Internal Medicine ($164.90)
- ✅ W130: Comprehensive internal medicine consultation ($310.45)

Query: "emergency department visit"
- ✅ A100: General/Family Physician Emergency Department Assessment
- ✅ H065: Consultation by physicians in emergency department
- ✅ H055: Emergency Medicine Consultation ($106.80)

## Metadata Extraction
All metadata fields are now properly extracted and included:
- Fee amounts
- Medical specialties
- Categories
- Service descriptions
- Time requirements
- Billing conditions

## Next Steps for MCP Server
The MCP server needs to be restarted to pick up the VectorClient changes for the fix to take effect in the `schedule_get` tool.
