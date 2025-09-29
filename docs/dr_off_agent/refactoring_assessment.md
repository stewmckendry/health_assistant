# Dr. OFF Refactoring Assessment: Vector-First Search Strategy

## Executive Summary

Based on the search algorithm comparison document and analysis of Dr. OFF's current implementation, this assessment recommends a **selective refactoring approach**. Dr. OFF should maintain hybrid SQL+Vector search but with clear separation based on data type and enhanced logging for traceability.

---

## Current State Analysis

### Dr. OFF Tools Overview

| Tool | Current Approach | Primary Data Types |
|------|------------------|-------------------|
| **schedule.get** | SQL + Vector parallel | OHIP fee codes (structured) + Policy text (unstructured) |
| **odb.get** | SQL + Vector parallel | Drug DINs, interchangeables (structured) + Formulary docs (unstructured) |
| **adp.get** | SQL + Vector parallel | Device categories, funding % (structured) + Eligibility rules (unstructured) |
| **coverage.answer** | Orchestrates other tools | Mixed - routes to appropriate tools |
| **source.passages** | Vector only | Document chunks by ID |

### Current Implementation Pattern
All tools follow the same pattern:
1. **Parallel execution**: SQL and vector searches run simultaneously
2. **Result merging**: Combines results from both sources
3. **Conflict detection**: Identifies discrepancies between sources
4. **Confidence scoring**: Based on provenance (both sources = higher confidence)

### Problems Identified

1. **Inappropriate SQL Usage for Natural Language**
   - Example: `schedule.get(q="discharge codes admission Monday 2pm Thursday 10am")`
   - SQL LIKE query fails to find relevant discharge codes
   - Returns unrelated endoscopy codes (E6xx series)

2. **No Reranking**
   - Results are merged but not intelligently ranked
   - Distance scores from vector search not calibrated
   - No semantic relevance verification

3. **Missing Logging Granularity**
   - Current logging doesn't trace individual search steps
   - Can't identify which path (SQL vs vector) contributed to errors
   - No timing metrics for optimization

---

## Impact Assessment

### High Impact Areas (Need Refactoring)

#### 1. Natural Language Queries in schedule.get
- **Current**: SQL LIKE on free text fails consistently
- **Impact**: Returns wrong codes (e.g., E6xx instead of discharge codes)
- **Recommendation**: Vector-only for natural language, SQL for specific code lookups

#### 2. Drug Name Searches in odb.get
- **Current**: SQL exact/fuzzy match on brand/generic names
- **Impact**: Misses variations (Januvia vs sitagliptin)
- **Recommendation**: Vector for drug discovery, SQL for DIN/interchangeable lookups

#### 3. Device Description Searches in adp.get
- **Current**: SQL on device type strings
- **Impact**: Misses semantic matches (wheelchair vs mobility aid)
- **Recommendation**: Vector for device discovery, SQL for funding percentages

### Low Impact Areas (Keep As-Is)

#### 1. Structured Data Lookups
- DIN lookups in ODB
- Fee code lookups by exact code
- Device funding percentages
- **Keep SQL**: These are exact matches on structured fields

#### 2. source.passages Tool
- Already vector-only
- Works correctly for chunk retrieval
- **No changes needed**

---

## Recommended Refactoring Plan

### Phase 1: Query Classification Layer
Add intelligent routing based on query type:

```python
class QueryClassifier:
    """Determines optimal search strategy based on query characteristics"""
    
    def classify(self, query: str, tool: str) -> SearchStrategy:
        # Structured query patterns (use SQL)
        if self._is_code_lookup(query):  # "A123", "E680"
            return SearchStrategy.SQL_ONLY
        
        if self._is_din_lookup(query):  # 8-digit numbers
            return SearchStrategy.SQL_ONLY
            
        if self._has_structured_filters(query):  # "strength > 50mg"
            return SearchStrategy.SQL_PRIMARY
        
        # Natural language patterns (use Vector)
        if self._is_natural_language(query):
            return SearchStrategy.VECTOR_WITH_RERANK
            
        # Hybrid cases
        if tool in ['odb.get', 'adp.get'] and self._needs_both(query):
            return SearchStrategy.HYBRID_SMART
            
        return SearchStrategy.VECTOR_WITH_RERANK  # Default
```

### Phase 2: Add LLM Reranking
Implement reranking for vector search results:

```python
class LLMReranker:
    """Reranks search results using LLM for relevance"""
    
    async def rerank(
        self, 
        query: str, 
        candidates: List[Document],
        top_k: int = 10
    ) -> List[Document]:
        # Score each candidate
        scored = []
        for doc in candidates:
            score = await self._score_relevance(query, doc)
            scored.append((score, doc))
        
        # Sort by relevance
        scored.sort(reverse=True, key=lambda x: x[0])
        
        # Return top k
        return [doc for _, doc in scored[:top_k]]
```

### Phase 3: Enhanced Logging Architecture

```python
class SearchLogger:
    """Comprehensive logging for search operations"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.operation_id = None
        
    def start_operation(self, tool: str, query: str) -> str:
        self.operation_id = f"{tool}_{uuid.uuid4()[:8]}"
        self.log({
            "event": "search_start",
            "tool": tool,
            "query": query,
            "operation_id": self.operation_id
        })
        return self.operation_id
        
    def log_classification(self, strategy: SearchStrategy, reason: str):
        self.log({
            "event": "query_classified",
            "strategy": strategy.value,
            "reason": reason
        })
        
    def log_sql_search(self, query: str, results_count: int, duration_ms: float):
        self.log({
            "event": "sql_search",
            "query": query,
            "results_count": results_count,
            "duration_ms": duration_ms
        })
        
    def log_vector_search(self, query: str, results_count: int, duration_ms: float):
        self.log({
            "event": "vector_search", 
            "query": query,
            "results_count": results_count,
            "duration_ms": duration_ms
        })
        
    def log_reranking(self, input_count: int, output_count: int, duration_ms: float):
        self.log({
            "event": "llm_reranking",
            "input_count": input_count,
            "output_count": output_count,
            "duration_ms": duration_ms
        })
        
    def log_merge(self, sql_count: int, vector_count: int, final_count: int):
        self.log({
            "event": "result_merge",
            "sql_count": sql_count,
            "vector_count": vector_count,
            "final_count": final_count
        })
```

### Phase 4: Tool-Specific Refactoring

#### schedule.get Refactoring
```python
async def execute(self, request: ScheduleGetRequest) -> ScheduleGetResponse:
    # Classify query
    strategy = self.classifier.classify(request.q, "schedule.get")
    self.logger.log_classification(strategy, "query_pattern")
    
    if strategy == SearchStrategy.SQL_ONLY:
        # Direct code lookup
        results = await self._sql_code_lookup(request.codes)
        
    elif strategy == SearchStrategy.VECTOR_WITH_RERANK:
        # Natural language search
        candidates = await self._vector_search(request.q, top_k=50)
        self.logger.log_vector_search(request.q, len(candidates), duration)
        
        # Rerank for relevance
        reranked = await self.reranker.rerank(request.q, candidates, top_k=20)
        self.logger.log_reranking(50, 20, rerank_duration)
        
        results = reranked[:request.top_k]
    
    else:  # HYBRID_SMART
        # Use SQL for structured parts, vector for semantic
        sql_results = await self._sql_structured_search(request)
        vector_results = await self._vector_semantic_search(request)
        
        # Intelligent merge with reranking
        merged = await self._smart_merge(sql_results, vector_results)
        results = merged
```

#### odb.get Refactoring
```python
async def execute(self, request: ODBGetRequest) -> ODBGetResponse:
    # For ODB, maintain SQL for structured data
    coverage = None
    interchangeables = []
    
    # DIN/formulary lookup stays SQL
    if self._is_din(request.drug):
        coverage = await self._sql_din_lookup(request.drug)
        self.logger.log_sql_search(f"DIN={request.drug}", 1, duration)
    else:
        # Drug name search uses vector first
        candidates = await self._vector_drug_search(request.drug, top_k=30)
        self.logger.log_vector_search(request.drug, len(candidates), duration)
        
        # Rerank for exact drug match
        reranked = await self.reranker.rerank(
            f"drug name: {request.drug}",
            candidates,
            top_k=10
        )
        
        # Then SQL for structured data
        for drug_doc in reranked:
            din = drug_doc.metadata.get('din')
            if din:
                coverage = await self._sql_din_lookup(din)
                break
    
    # Interchangeables always from SQL
    if coverage and request.check_alternatives:
        interchangeables = await self._sql_interchangeable_lookup(
            coverage.din
        )
        self.logger.log_sql_search(
            f"interchangeable for {coverage.din}",
            len(interchangeables),
            duration
        )
```

---

## Implementation Priority

### Priority 1: Fix Critical Failures
1. **schedule.get** - Stop using SQL LIKE for natural language queries
2. **Add query classifier** - Route queries to appropriate search strategy
3. **Enhance logging** - Add operation tracking and timing

### Priority 2: Improve Relevance
1. **Add LLM reranking** - Ensure semantic relevance
2. **Implement smart merging** - Combine SQL and vector intelligently
3. **Add confidence scoring** - Based on search strategy success

### Priority 3: Optimize Performance
1. **Cache embeddings** - Reduce vector search latency
2. **Parallel reranking** - Batch LLM calls
3. **Query optimization** - Precompile common SQL patterns

---

## Testing Strategy

### Test Cases by Tool

#### schedule.get Tests
```python
test_cases = [
    # Should use SQL_ONLY
    {"q": "A123", "expected_strategy": "SQL_ONLY"},
    {"codes": ["A123", "B456"], "expected_strategy": "SQL_ONLY"},
    
    # Should use VECTOR_WITH_RERANK
    {"q": "discharge billing after 3 days", "expected_strategy": "VECTOR_WITH_RERANK"},
    {"q": "virtual care documentation", "expected_strategy": "VECTOR_WITH_RERANK"},
]
```

#### odb.get Tests
```python
test_cases = [
    # Should use SQL for DIN
    {"drug": "02388839", "expected_strategy": "SQL_ONLY"},
    
    # Should use Vector then SQL
    {"drug": "Januvia", "expected_strategy": "HYBRID_SMART"},
    {"drug": "metformin", "expected_strategy": "HYBRID_SMART"},
]
```

---

## Risk Mitigation

### Rollback Strategy
1. **Feature flags** - Enable new search strategies gradually
2. **A/B testing** - Compare old vs new approaches
3. **Fallback logic** - If new approach fails, use old

### Monitoring
1. **Success metrics** - Track relevance improvements
2. **Latency metrics** - Ensure performance doesn't degrade
3. **Error rates** - Monitor for new failure modes

---

## Conclusion

Dr. OFF requires **selective refactoring** rather than wholesale replacement:

1. **Keep SQL for structured data** (DINs, codes, percentages)
2. **Use Vector for natural language** with LLM reranking
3. **Add intelligent routing** based on query classification
4. **Implement comprehensive logging** at each step

This approach maintains Dr. OFF's strength in structured data lookups while fixing the critical failures in natural language processing, aligning with the broader search strategy while respecting Dr. OFF's unique requirements.