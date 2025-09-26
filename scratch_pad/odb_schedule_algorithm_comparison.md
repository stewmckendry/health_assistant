# ODB vs Schedule Search Algorithm Comparison

## Key Architectural Differences

### ODB Tool (`odb.get`)
- **Strategy**: ALWAYS runs SQL and Vector in parallel (lines 69-77)
- **No query classification** - treats all queries the same way
- **Problem**: Passes entire natural language query to SQL LIKE operator
  - Example: `WHERE name LIKE '%Is Ozempic covered for type 2 diabetes%'` 
  - This will never match because it's looking for the entire phrase in the drug name field

### Schedule Tool (`schedule.get`)
- **Strategy**: Uses QueryClassifier to determine optimal approach
- **Has 5 strategies**:
  1. SQL_ONLY - for specific fee codes
  2. VECTOR_WITH_RERANK - for complex semantic queries
  3. HYBRID_SMART - combines both intelligently
  4. SQL_PRIMARY - SQL first, vector for enrichment
  5. VECTOR_ONLY - pure semantic search
- **Smart routing** based on query characteristics

## The Natural Language Problem

### Current Issue with ODB
When user asks: "Is Ozempic covered for type 2 diabetes?"
- ODB passes whole string to SQL: `ingredient LIKE '%Is Ozempic covered for type 2 diabetes%'`
- SQL finds nothing (no drug named that)
- Vector search works but SQL fails
- Result: Poor coverage information

### How Schedule Handles It
- QueryClassifier analyzes the query first
- Extracts fee codes if present
- Routes to appropriate strategy
- Can handle natural language better

## Solution Options for ODB

### Option 1: Simple Drug Name Extraction
Extract just the drug name from natural language queries:
```python
def extract_drug_name(query: str) -> str:
    # Remove common question words
    query_lower = query.lower()
    for phrase in ['is ', 'covered', 'for', 'type 2 diabetes', '?']:
        query_lower = query_lower.replace(phrase, '')
    return query_lower.strip()
```

### Option 2: Implement QueryClassifier (like Schedule)
- Add intelligent query classification
- Extract drug names, DINs, conditions separately
- Route to appropriate search strategy

### Option 3: Always Use Vector for Natural Language
- If query contains question words ("is", "can", "covered"), skip SQL
- Use vector search for semantic understanding
- Only use SQL for exact drug names/DINs

## Recommendation

The ODB tool should:
1. **Keep dual-path retrieval** (good for accuracy)
2. **Add simple drug name extraction** for SQL queries
3. **Let vector handle the full natural language** query
4. This way:
   - SQL finds the drug by extracted name
   - Vector provides context about coverage/conditions
   - Both results merge for comprehensive answer

## Code Changes Implemented ✅

### 1. Created `odb_drug_extractor.py`
- Uses simple pattern matching for common queries
- Falls back to GPT-3.5-turbo for complex extraction
- Extracts both drug name AND condition from queries
- Returns clean drug name for SQL matching

### 2. Updated `odb.py`
```python
# Now implemented (lines 151-159):
if raw_drug and not ingredient:
    extracted_drug, condition = self.drug_extractor.extract_drug_info(raw_drug)
    if extracted_drug:
        ingredient = extracted_drug
        logger.info(f"Extracted drug '{ingredient}' from query '{raw_drug}'")
    else:
        # Fall back to using the raw query
        ingredient = raw_drug
```

### 3. How It Works
- **Direct drug names**: "Ozempic" → passes through unchanged ✅
- **Simple patterns**: "Is Ozempic covered" → extracts "Ozempic" ✅  
- **Complex queries**: "Is Ozempic covered for type 2 diabetes?" → LLM extracts "Ozempic" and "type 2 diabetes" ✅
- **SQL gets**: Clean drug name for accurate matching
- **Vector gets**: Full query for semantic context

This allows ODB to handle natural language while maintaining accurate SQL lookups!