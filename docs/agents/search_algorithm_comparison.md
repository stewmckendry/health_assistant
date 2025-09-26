# Search Algorithm Comparison: Current vs. Revised Approach

## Executive Summary

This document compares the current hybrid SQL+Vector search approach with a revised Vector-first approach for natural language queries in medical knowledge retrieval systems. The revised approach is recommended for document-based searches where users ask questions in natural language, while SQL remains optimal for structured data lookups (DINs, OHIP codes, etc.).

---

## Current Approach: SQL + Vector Hybrid

### How It Works

```python
# Current implementation pseudocode
async def current_search(query: str):
    # 1. Parallel SQL and Vector searches
    sql_results = sql_db.search("WHERE text LIKE '%{query}%'")
    vector_results = vector_db.similarity_search(query)
    
    # 2. Merge results (often with conflicts)
    combined = merge(sql_results, vector_results)
    
    # 3. Return combined results
    return combined
```

### Problems with Current Approach

1. **SQL LIKE Searches Fail on Natural Language**
   - Query: "telemedicine documentation requirements"
   - SQL: `WHERE text LIKE '%telemedicine documentation requirements%'`
   - Result: ❌ No matches (exact phrase doesn't exist)

2. **No Semantic Understanding in SQL**
   - Can't match synonyms: "virtual care" ≠ "telemedicine"
   - Can't understand intent: "how to document" ≠ "documentation requirements"

3. **Redundant Processing**
   - Both databases store same documents
   - Duplicate searches increase latency
   - Complex merge logic with conflicts

4. **Poor Relevance Ranking**
   - SQL: Binary match (found/not found)
   - Vector: Distance scores not calibrated
   - No intelligent reranking

---

## Revised Approach: Vector → Rerank → Filter

### How It Works

```python
# Revised implementation pseudocode
async def revised_search(query: str, filters: dict = None):
    # 1. VECTOR SEARCH: Cast wide net for semantic matches
    candidates = vector_db.similarity_search(
        query=query,
        top_k=50,  # Get more than needed
        include_metadata=True
    )
    
    # 2. RERANK: Use LLM to score relevance
    reranked = await llm_rerank(
        query=query,
        documents=candidates,
        top_k=20  # Narrow down
    )
    
    # 3. FILTER: Apply metadata constraints
    filtered = apply_filters(
        documents=reranked,
        filters=filters  # source, date, type, etc.
    )
    
    return filtered[:10]  # Final results
```

### Detailed Algorithm Steps

#### Step 1: Vector Search (Maximize Recall)
```python
# Semantic search across all documents
results = chroma_db.query(
    query_texts=[query],
    n_results=50,  # Oversample
    include=['documents', 'metadatas', 'distances']
)
```
**Purpose**: Find all potentially relevant documents regardless of exact wording

#### Step 2: LLM Reranking (Optimize Precision)
```python
async def llm_rerank(query: str, documents: List[Document]) -> List[Document]:
    # Use LLM to score each document's relevance
    for doc in documents:
        prompt = f"""
        Score the relevance of this document to the query (0-10):
        
        Query: {query}
        
        Document Title: {doc.metadata.get('title')}
        Document Excerpt: {doc.text[:500]}
        
        Consider:
        - Direct answer to query
        - Topical relevance
        - Practical applicability
        
        Score (0-10):
        """
        
        doc.relevance_score = await llm.complete(prompt)
    
    # Sort by LLM-assigned relevance
    return sorted(documents, key=lambda x: x.relevance_score, reverse=True)
```
**Purpose**: Use LLM's understanding to identify truly relevant documents

#### Step 3: Metadata Filtering (Apply Constraints)
```python
def apply_filters(documents: List[Document], filters: dict) -> List[Document]:
    filtered = []
    for doc in documents:
        # Check each filter condition
        if filters.get('source_org'):
            if doc.metadata.get('source_org') != filters['source_org']:
                continue
                
        if filters.get('document_type'):
            if doc.metadata.get('document_type') != filters['document_type']:
                continue
                
        if filters.get('after_date'):
            doc_date = parse_date(doc.metadata.get('effective_date'))
            if doc_date < filters['after_date']:
                continue
                
        filtered.append(doc)
    
    return filtered
```
**Purpose**: Apply hard constraints without affecting relevance ranking

---

## Comparison Table

| Aspect | Current Approach | Revised Approach |
|--------|-----------------|------------------|
| **Primary Search** | SQL LIKE + Vector | Vector only |
| **Semantic Understanding** | Vector only | Vector for all |
| **Query Interpretation** | Exact text matching in SQL | Embedding-based semantic search |
| **Relevance Ranking** | Distance scores | LLM-based reranking |
| **Metadata Filtering** | During search | After ranking |
| **Latency** | Two database queries | Single vector query + LLM calls |
| **Accuracy** | Low for natural language | High for natural language |
| **Maintenance** | Two systems to maintain | Single vector DB |

---

## When to Use Each Approach

### Use Revised (Vector-First) Approach For:
✅ Natural language questions: "What are the documentation requirements for virtual care?"
✅ Semantic searches: "How to handle patient consent in telemedicine"
✅ Topic exploration: "Best practices for infection control"
✅ Document retrieval: Policy documents, guidelines, advice

### Keep SQL Approach For:
✅ Exact lookups: Drug by DIN, procedure by OHIP code
✅ Structured queries: "All drugs with strength > 50mg"
✅ Range queries: "Fees between $100-$200"
✅ Aggregations: COUNT, SUM, GROUP BY operations
✅ Relational data: Joining drug → manufacturer → contact info

---

## Implementation Benefits

### 1. **Better Search Results**
- Understands intent, not just keywords
- Finds related concepts and synonyms
- LLM reranking ensures relevance

### 2. **Simpler Architecture**
- Single search path
- No complex merge logic
- Cleaner codebase

### 3. **Improved Performance**
- Single database query
- Parallel LLM reranking
- Cacheable embeddings

### 4. **Easier Maintenance**
- One search system to optimize
- Consistent behavior
- Simpler debugging

---

## Migration Path

### Phase 1: Update Search Functions
```python
# Replace all semantic search functions
- sql_client.search_sections()  → vector_client.semantic_search()
- sql_client.search_policies()   → vector_client.semantic_search()
- sql_client.search_programs()   → vector_client.semantic_search()
```

### Phase 2: Add LLM Reranking
```python
# Add reranking step after vector search
results = await vector_client.semantic_search(query)
reranked = await llm_reranker.rerank(query, results)
```

### Phase 3: Optimize Metadata
```python
# Ensure all documents have standard metadata
metadata = {
    'source_org': 'cpso',      # For filtering
    'document_type': 'policy',  # For categorization
    'effective_date': '2024-01-01',  # For currency
    'policy_level': 'expectation',   # For importance
    'topics': ['virtual-care', 'consent']  # For discovery
}
```

---

## Example: Before and After

### Query: "requirements for documenting virtual care visits"

#### Before (Current Approach):
```python
# SQL Search
sql_query = "WHERE text LIKE '%requirements for documenting virtual care visits%'"
sql_results = []  # ❌ No exact match

# Vector Search  
vector_results = [
    "Virtual Care Policy",
    "Telemedicine Guidelines"
]

# Merged Results
final = vector_results  # SQL contributed nothing
```

#### After (Revised Approach):
```python
# Vector Search (Semantic)
candidates = [
    "Virtual Care Policy",
    "Medical Records Documentation", 
    "Telemedicine Guidelines",
    "Consent to Treatment",
    "Privacy and Electronic Records",
    # ... 45 more candidates
]

# LLM Reranking
reranked = [
    "Virtual Care Policy - Section 3: Documentation Requirements",  # Score: 9.5
    "Medical Records Documentation - Virtual Visits",  # Score: 9.2
    "Telemedicine Guidelines - Record Keeping",  # Score: 8.8
    # ... rest sorted by relevance
]

# Filter (if source specified)
filtered = [doc for doc in reranked if doc.source == 'cpso']

# Final Results: Highly relevant, properly ranked
```

---

## Recommendations

### For Dr. OPA (Document Search):
- Implement revised Vector → Rerank → Filter approach
- Remove SQL text search entirely
- Keep SQL only for metadata queries

### For Dr. OFF (Structured + Document Search):
- Keep SQL for structured data (DINs, codes, fees)
- Use revised approach for document/guidance searches
- Maintain hybrid system with clear separation

### Key Principles:
1. **Vector for Semantics**: All natural language queries
2. **SQL for Structure**: Exact codes, IDs, structured data
3. **LLM for Relevance**: Final ranking of results
4. **Metadata for Filtering**: Post-ranking constraints

---

## Conclusion

The revised Vector → Rerank → Filter approach significantly improves search quality for natural language queries while simplifying the system architecture. It's particularly well-suited for medical knowledge retrieval where users ask questions in natural language rather than searching for exact terms.

For systems like Dr. OFF that handle both structured data (drug codes, fee schedules) and documents, a hybrid approach makes sense - but with clear separation: SQL for structured lookups, Vector for semantic search, never both for the same query.