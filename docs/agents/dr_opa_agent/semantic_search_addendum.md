# Semantic Search Engine Addition

## Semantic Search Engine

### Overview
The semantic search engine (`src/agents/dr_opa_agent/mcp/search/semantic_search.py`) implements the Vector → Rerank → Filter algorithm used by most MCP tools.

### Architecture
```python
class SemanticSearchEngine:
    def __init__(self, vector_client, openai_api_key):
        self.vector_client = vector_client  # ChromaDB client
        self.openai_client = AsyncOpenAI()  # For reranking
    
    async def search(
        query: str,
        sources: Optional[List[str]] = None,
        document_types: Optional[List[str]] = None,
        top_k: int = 10,
        use_reranking: bool = True
    ) -> List[Dict[str, Any]]
```

### Search Pipeline

1. **Vector Search (Maximize Recall)**
   - Queries ChromaDB collections using OpenAI embeddings (text-embedding-3-small)
   - Retrieves 5x more candidates than needed (e.g., 50 for top_k=10)
   - Searches across multiple collections: opa_cpso_corpus, opa_pho_corpus, opa_cep_corpus

2. **LLM Reranking (Optimize Precision)**
   - Uses GPT-4o-mini for fast, cost-effective relevance scoring
   - Scores each document 0-10 based on:
     - Direct answer to query (9-10)
     - Highly relevant to topic (7-8)
     - Related but indirect (5-6)
     - Tangentially related (3-4)
     - Not relevant (0-2)
   - Processes documents in parallel for efficiency

3. **Metadata Filtering (Apply Constraints)**
   - Applied AFTER ranking to preserve relevance order
   - Filters by:
     - `document_types`: policy, guideline, advice, clinical_tool
     - `policy_level`: expectation, advice
     - `effective_date`: Filter outdated guidance
     - `source_org`: cpso, pho, cep, ontario_health

### Logging
Each stage logs detailed information:
```
=== SEMANTIC SEARCH START ===
Query: telemedicine documentation requirements
Step 1: Vector Search - Retrieving candidates...
Vector search returned 50 candidates
Step 2: LLM Reranking - Scoring relevance...
Top 3 reranked results: [9.2, 8.7, 8.3]
Step 3: Metadata Filtering - Applying constraints...
=== SEMANTIC SEARCH COMPLETE: Returning 5 results ===
```

### Performance Characteristics
- **Latency**: ~1-2 seconds for typical queries
- **Token Usage**: ~500-1000 tokens per query for reranking
- **Accuracy**: Significantly improved over SQL LIKE queries
- **Semantic Understanding**: Handles synonyms, related concepts, and intent

### Tools Using Semantic Search
- `opa.search_sections` - General guidance search
- `opa.policy_check` - CPSO policy retrieval
- `opa.ipac_guidance` - PHO infection control guidance
- `opa.clinical_tools` - CEP clinical tool discovery

### Tools Using SQL (Structured Data)
- `opa.get_section` - Direct ID lookup
- `opa.program_lookup` - Structured program data
- `opa.freshness_probe` - Metadata checks