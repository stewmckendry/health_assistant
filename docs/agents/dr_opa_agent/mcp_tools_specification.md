# Dr. OPA MCP Tools Specification

## Implementation Status

| Tool | Status | Files |
|------|--------|-------|
| opa.search_sections | ✅ Implemented | `server.py` |
| opa.get_section | ✅ Implemented | `server.py` |
| opa.policy_check | ✅ Implemented | `server.py` |
| opa.program_lookup | ✅ Implemented | `server.py` |
| opa.ipac_guidance | ✅ Implemented | `server.py` |
| opa.freshness_probe | ✅ Implemented | `server.py` |
| opa.clinical_tools | ✅ Implemented | `server.py` |
| **Shared Utilities** | | |
| SQL Client | ✅ Implemented | `retrieval/sql_client.py` |
| Vector Client | ✅ Implemented | `retrieval/vector_client.py` |
| Confidence Scorer | ✅ Implemented | `utils/confidence.py` |
| Citation Formatter | ✅ Implemented | `utils/citations.py` |

## Overview

The Dr. OPA MCP server provides 7 specialized tools for Ontario practice guidance queries. Each tool implements **dual-path retrieval**, running SQL and vector searches in parallel to ensure accuracy, provide citations, and maintain currency of guidance.

**Server Location**: `src/agents/dr_opa_agent/mcp/server.py`  
**Base URL**: `http://localhost:8001` (when running)  
**Protocol**: FastMCP

---

## Tool 1: opa.search_sections

### Purpose
Hybrid search across all OPA knowledge sources with metadata filtering to find relevant guidance sections.

### Clinical Use Cases
- **General guidance queries**: "What are the documentation requirements for virtual care?"
- **Topic-specific searches**: "Infection control for instrument reprocessing"
- **Date-aware searches**: "Current cervical screening guidelines"
- **Organization-filtered queries**: "CPSO policies on consent"

### Request Schema
```python
{
    "query": str,                      # Required: Search query text
    "source_org": str,                 # Optional: "cpso", "ontario_health", "cep", "pho", "moh"
    "document_type": str,              # Optional: "policy", "guideline", "bulletin", "tool"
    "topics": [str],                   # Optional: Filter by topics
    "include_superseded": bool,        # Include outdated docs (default false)
    "n_results": int,                  # Number of results (default 5, max 20)
    "search_mode": str                 # "hybrid", "vector", "keyword" (default "hybrid")
}
```

### Response Schema
```python
{
    "provenance": ["sql", "vector"],   # Data sources used
    "confidence": float,                # 0.0-1.0 confidence score
    "sections": [
        {
            "section_id": str,          # Unique section identifier
            "document_id": str,         # Parent document ID
            "chunk_type": str,          # "parent" or "child"
            "text": str,                # Section text (truncated)
            "score": float,             # Relevance score
            "source_org": str,          # Organization
            "source_url": str,          # Original document URL
            "document_title": str,      # Document title
            "section_heading": str,     # Section heading
            "effective_date": str,      # When guidance takes effect
            "updated_date": str,        # Last update date
            "topics": [str],            # Document topics
            "policy_level": str,        # CPSO: "expectation", "advice", null
            "is_superseded": bool       # If document is outdated
        }
    ],
    "total_matches": int,               # Total results found
    "citations": [                      # Formatted citations
        {
            "source": str,              # Document name
            "loc": str,                 # Section reference
            "page": int                 # Optional page number
        }
    ],
    "conflicts": []                     # SQL/vector conflicts if any
}
```

### Algorithm

1. **Parallel Retrieval**:
   ```python
   async def search():
       sql_task = asyncio.create_task(sql_client.search_sections())
       vector_task = asyncio.create_task(vector_client.search_opa())
       
       sql_result, vector_result = await asyncio.gather(
           sql_task, vector_task, return_exceptions=True
       )
   ```

2. **Metadata Filtering**:
   - SQL: WHERE clauses on source_org, document_type, is_superseded
   - Vector: Chroma metadata filters using $eq, $in operators
   - Topics: Match any provided topic using JSON containment

3. **Re-ranking**:
   - Combine SQL and vector results by section_id
   - Boost scores for:
     - Exact phrase matches (+50%)
     - Title matches (+30%)
     - CPSO expectations (+20%)
     - Recent documents (decay over 5 years)
   - Penalize superseded documents (-70%)

4. **Confidence Scoring**:
   - Base 0.9 for SQL hits with vector corroboration
   - Base 0.6 for vector-only results
   - +0.03 per additional corroborating passage
   - -0.1 for conflicts between sources

---

## Tool 2: opa.get_section

### Purpose
Retrieve complete section details with full context, parent-child relationships, and formatted citations.

### Clinical Use Cases
- **Full text retrieval**: Get complete section text for reading
- **Context expansion**: Retrieve parent chunk for child results
- **Citation verification**: Access exact source text
- **Document navigation**: Get all child chunks of a parent

### Request Schema
```python
{
    "section_id": str,                 # Required: Section identifier
    "include_parent": bool,            # Include parent if child (default true)
    "include_children": bool,          # Include children if parent (default false)
    "include_document_metadata": bool  # Full document metadata (default true)
}
```

### Response Schema
```python
{
    "section": {
        "section_id": str,
        "chunk_type": str,              # "parent" or "child"
        "text": str,                    # Full section text
        "section_heading": str,
        "section_idx": int,
        "chunk_idx": int                # For child chunks
    },
    "parent": {...},                    # Parent section if requested
    "children": [...],                  # Child sections if requested
    "document": {
        "document_id": str,
        "title": str,
        "source_org": str,
        "source_url": str,
        "document_type": str,
        "effective_date": str,
        "updated_date": str,
        "published_date": str,
        "topics": [str],
        "policy_level": str,            # CPSO only
        "is_superseded": bool,
        "superseded_by": str            # If superseded
    },
    "citation": {
        "text": str,                    # Formatted citation text
        "url": str,                     # URL with anchor
        "anchor": str                   # Section anchor
    }
}
```

### Algorithm

1. **Section Retrieval**:
   - Query `opa_sections` table by section_id
   - Join with `opa_documents` for document metadata
   - Fetch text, metadata, and relationships

2. **Relationship Resolution**:
   - If child chunk requested with include_parent=true:
     - Fetch parent using parent_id foreign key
   - If parent chunk requested with include_children=true:
     - Fetch all children WHERE parent_id = section_id

3. **Citation Formatting**:
   - Build citation: "{Org}. {Title}, {Section} [Effective: {Date}]"
   - Generate anchor from section_heading (slugified)
   - Construct URL: source_url + "#" + anchor

---

## Tool 3: opa.policy_check

### Purpose
CPSO-specific policy retrieval with focus on regulatory expectations vs. advice.

### Clinical Use Cases
- **Regulatory compliance**: "What are CPSO expectations for consent?"
- **Policy clarification**: "Is email communication allowed for results?"
- **Professional obligations**: "Documentation requirements for virtual care"
- **Practice standards**: "Continuity of care requirements when leaving practice"

### Request Schema
```python
{
    "query": str,                      # Required: Policy-related query
    "policy_level": str,               # Optional: "expectation", "advice", "all"
    "include_advice": bool,            # Include advice sections (default true)
    "n_results": int                   # Number of results (default 3)
}
```

### Response Schema
```python
{
    "provenance": ["sql", "vector"],
    "confidence": float,
    "policies": [
        {
            "section_id": str,
            "policy_number": str,        # e.g., "4-21"
            "policy_title": str,
            "policy_level": str,         # "expectation" or "advice"
            "text": str,                 # Policy text
            "relevance_score": float,
            "effective_date": str,
            "review_date": str,          # Next review date
            "source_url": str
        }
    ],
    "expectations_found": int,          # Count of expectations
    "advice_found": int,                # Count of advice items
    "citations": [...],
    "conflicts": [...]
}
```

### Algorithm

1. **CPSO-Specific Search**:
   - Filter source_org = 'cpso' in both SQL and vector
   - Prioritize policy_level = 'expectation' if specified
   - Search policy text for "must", "shall", "required" (expectations)

2. **Policy Level Detection**:
   - SQL: Query policy_level field directly
   - Vector: Analyze text for regulatory language
   - Expectations: "physicians must", "physicians shall"
   - Advice: "physicians should", "it is advisable"

3. **Ranking**:
   - Expectations ranked higher than advice
   - Recent policies ranked higher
   - Exact policy number matches boosted

---

## Tool 4: opa.program_lookup

### Purpose
Ontario Health screening program and clinical pathway guidance retrieval.

### Clinical Use Cases
- **Screening intervals**: "Cervical screening for 30-year-old patient"
- **Eligibility criteria**: "Who qualifies for breast screening?"
- **Referral pathways**: "How to refer for colonoscopy"
- **Program changes**: "New HPV testing guidelines March 2025"

### Request Schema
```python
{
    "program": str,                    # Required: "cervical", "breast", "colorectal", "lung"
    "query_type": str,                 # Required: "intervals", "eligibility", "pathway", "referral"
    "patient_age": int,                # Optional: For age-based criteria
    "risk_factors": [str]              # Optional: High-risk indicators
}
```

### Response Schema
```python
{
    "provenance": ["sql", "vector"],
    "confidence": float,
    "program": str,
    "guidance_type": str,
    "recommendations": [
        {
            "text": str,                # Recommendation text
            "category": str,            # "screening", "diagnostic", "referral"
            "age_range": [int, int],    # Age applicability
            "frequency": str,           # e.g., "every 5 years"
            "conditions": [str],        # Qualifying conditions
            "source_section_id": str
        }
    ],
    "algorithms": [                    # Decision algorithms if available
        {
            "name": str,
            "description": str,
            "steps": [str],
            "decision_points": [dict],
            "source_url": str
        }
    ],
    "effective_date": str,             # When guidance takes effect
    "next_review": str,                # Next review date
    "citations": [...],
    "conflicts": [...]
}
```

### Algorithm

1. **Program Mapping**:
   - Map program names to Ontario Health collections
   - Cervical → HPV Hub, OCSP documents
   - Breast → OBSP guidelines
   - Colorectal → ColonCancerCheck

2. **Age-Based Filtering**:
   - Extract age ranges from guidance text
   - Match patient_age to applicable ranges
   - Flag if outside screening age

3. **Pathway Extraction**:
   - Identify sequential steps in screening pathways
   - Extract decision points (e.g., "if positive, then...")
   - Format as structured algorithm

---

## Tool 5: opa.ipac_guidance

### Purpose
PHO infection prevention and control guidance for clinical office practice.

### Clinical Use Cases
- **Reprocessing requirements**: "How to sterilize reusable instruments"
- **PPE guidelines**: "When are N95 masks required?"
- **Environmental cleaning**: "Disinfection between patients"
- **Specific equipment**: "Reprocessing requirements for spirometer"

### Request Schema
```python
{
    "topic": str,                      # Required: "reprocessing", "ppe", "hand_hygiene", "environmental"
    "setting": str,                    # Optional: "office", "clinic", "procedure_room" (default "office")
    "specific_item": str,              # Optional: Specific equipment/procedure
    "include_checklists": bool        # Include checklists (default true)
}
```

### Response Schema
```python
{
    "provenance": ["sql", "vector"],
    "confidence": float,
    "topic": str,
    "setting": str,
    "requirements": [
        {
            "level": str,               # "must", "should", "may"
            "text": str,                # Requirement text
            "rationale": str,           # Why required
            "source_section_id": str
        }
    ],
    "best_practices": [str],           # Best practice recommendations
    "checklists": [
        {
            "name": str,
            "frequency": str,           # "daily", "weekly", "per_use"
            "items": [
                {
                    "item": str,
                    "required": bool,
                    "notes": str
                }
            ]
        }
    ],
    "references": [                    # PHO references
        {
            "title": str,
            "url": str,
            "date": str
        }
    ],
    "citations": [...],
    "conflicts": [...]
}
```

### Algorithm

1. **PHO Document Filtering**:
   - Filter source_org = 'pho'
   - Focus on IPAC best practices documents
   - Include Provincial Infectious Diseases Advisory Committee (PIDAC) guidance

2. **Requirement Level Extraction**:
   - "Must" → mandatory requirements
   - "Should" → strongly recommended
   - "May" → optional practices
   - Extract rationale following requirements

3. **Checklist Extraction**:
   - Identify bulleted lists in IPAC documents
   - Convert to structured checklist format
   - Determine frequency from context

---

## Tool 6: opa.freshness_probe

### Purpose
Check for updates to guidance documents and detect stale content.

### Clinical Use Cases
- **Currency verification**: "Is this cervical screening guidance current?"
- **Update detection**: "Any updates to CPSO telemedicine policy?"
- **Corpus maintenance**: Regular freshness checks
- **Change alerts**: Notify when key guidance changes

### Request Schema
```python
{
    "document_ids": [str],             # Optional: Specific documents to check
    "source_orgs": [str],              # Optional: Organizations to check
    "topics": [str],                   # Optional: Topics to check
    "check_web": bool                  # Perform web search for updates (default false)
}
```

### Response Schema
```python
{
    "documents_checked": int,
    "stale_documents": [
        {
            "document_id": str,
            "title": str,
            "last_updated": str,
            "days_old": int,
            "topics": [str]
        }
    ],
    "potential_updates": [             # If check_web=true
        {
            "source_org": str,
            "indication": str,          # What suggests an update
            "url": str,
            "detected_date": str
        }
    ],
    "last_corpus_update": str,         # When corpus last refreshed
    "recommendations": [str]           # Suggested actions
}
```

### Algorithm

1. **Staleness Detection**:
   - Documents > 1 year without update → potentially stale
   - Documents > 2 years → likely stale
   - Superseded documents → definitely stale

2. **Web Checking** (if enabled):
   - Query source websites for "last updated" dates
   - Compare with stored updated_date
   - Flag discrepancies

3. **Recommendations**:
   - Generate re-ingestion list for stale documents
   - Prioritize by clinical importance
   - Suggest corpus refresh schedule

---

## Shared Components

### SQL Client (`retrieval/sql_client.py`)

```python
class OPASQLClient:
    async def search_sections(
        query: str,
        source_org: str = None,
        document_type: str = None,
        include_superseded: bool = False
    ) -> List[Dict]:
        """Search opa_sections with filters."""
        
    async def get_section(section_id: str) -> Dict:
        """Get section by ID with document join."""
        
    async def get_document(document_id: str) -> Dict:
        """Get document metadata."""
        
    async def check_staleness(days_threshold: int) -> List[Dict]:
        """Find documents older than threshold."""
```

### Vector Client (`retrieval/vector_client.py`)

```python
class OPAVectorClient:
    async def search_opa(
        query: str,
        collection: str,
        n_results: int = 5,
        where: Dict = None
    ) -> List[Dict]:
        """Vector search with metadata filtering."""
        
    async def get_by_ids(
        chunk_ids: List[str],
        collection: str
    ) -> List[Dict]:
        """Retrieve specific chunks by ID."""
```

### Confidence Scorer (`utils/confidence.py`)

```python
def calculate_confidence(
    has_sql: bool,
    has_vector: bool,
    num_sql_results: int,
    num_vector_results: int,
    has_conflicts: bool
) -> float:
    """Calculate confidence score 0.0-1.0."""
    
    base = 0.9 if has_sql else 0.6
    boost = min(0.15, 0.03 * num_vector_results)
    penalty = 0.1 if has_conflicts else 0.0
    
    return min(1.0, base + boost - penalty)
```

### Citation Formatter (`utils/citations.py`)

```python
def format_citation(
    document: Dict,
    section: Dict = None
) -> Dict:
    """Format proper medical citation."""
    
    org_names = {
        'cpso': 'College of Physicians and Surgeons of Ontario',
        'ontario_health': 'Ontario Health (Cancer Care Ontario)',
        'cep': 'Centre for Effective Practice',
        'pho': 'Public Health Ontario',
        'moh': 'Ministry of Health'
    }
    
    text = f"{org_names[document['source_org']]}. {document['title']}"
    
    if section:
        text += f", {section['section_heading']}"
    
    if document['effective_date']:
        text += f" [Effective: {document['effective_date']}]"
    
    return {
        'text': text,
        'url': document['source_url'],
        'anchor': slugify(section['section_heading']) if section else None
    }
```

---

## FastMCP Server Implementation

### Server Setup (`mcp/server.py`)

```python
from fastmcp import FastMCP
import asyncio
from typing import Optional, List

# Import tool implementations
from .tools import (
    search, section, policy, 
    program, ipac, freshness
)

# Initialize FastMCP server
app = FastMCP("Dr. OPA Agent", version="1.0.0")

# Register tools
@app.tool()
async def search_sections(
    query: str,
    source_org: Optional[str] = None,
    document_type: Optional[str] = None,
    topics: Optional[List[str]] = None,
    include_superseded: bool = False,
    n_results: int = 5,
    search_mode: str = "hybrid"
):
    """Search Ontario practice guidance documents."""
    return await search.execute(
        query=query,
        source_org=source_org,
        document_type=document_type,
        topics=topics,
        include_superseded=include_superseded,
        n_results=n_results,
        search_mode=search_mode
    )

@app.tool()
async def get_section(
    section_id: str,
    include_parent: bool = True,
    include_children: bool = False,
    include_document_metadata: bool = True
):
    """Retrieve complete section details."""
    return await section.execute(
        section_id=section_id,
        include_parent=include_parent,
        include_children=include_children,
        include_document_metadata=include_document_metadata
    )

@app.tool()
async def policy_check(
    query: str,
    policy_level: Optional[str] = None,
    include_advice: bool = True,
    n_results: int = 3
):
    """Check CPSO policies and expectations."""
    return await policy.execute(
        query=query,
        policy_level=policy_level,
        include_advice=include_advice,
        n_results=n_results
    )

@app.tool()
async def program_lookup(
    program: str,
    query_type: str,
    patient_age: Optional[int] = None,
    risk_factors: Optional[List[str]] = None
):
    """Look up Ontario screening program guidance."""
    return await program.execute(
        program=program,
        query_type=query_type,
        patient_age=patient_age,
        risk_factors=risk_factors
    )

@app.tool()
async def ipac_guidance(
    topic: str,
    setting: str = "office",
    specific_item: Optional[str] = None,
    include_checklists: bool = True
):
    """Get PHO infection control guidance."""
    return await ipac.execute(
        topic=topic,
        setting=setting,
        specific_item=specific_item,
        include_checklists=include_checklists
    )

@app.tool()
async def freshness_probe(
    document_ids: Optional[List[str]] = None,
    source_orgs: Optional[List[str]] = None,
    topics: Optional[List[str]] = None,
    check_web: bool = False
):
    """Check guidance document freshness."""
    return await freshness.execute(
        document_ids=document_ids,
        source_orgs=source_orgs,
        topics=topics,
        check_web=check_web
    )

# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

---

## Testing Strategy

### Completed Tests
- ✅ `tests/dr_opa_agent/test_scripts/test_mcp_tools.py`: All 6 tools tested
- ✅ `tests/dr_opa_agent/test_scripts/test_sql_queries.py`: SQL retrieval verified
- ✅ `tests/dr_opa_agent/test_scripts/test_vector_fixed.py`: Vector search working
- ✅ `tests/dr_opa_agent/test_scripts/test_hybrid_search.py`: Parallel execution

### Planned Tests
- `tests/dr_opa_agent/integration/test_parallel_execution.py`: Verify dual-path
- `tests/dr_opa_agent/integration/test_mcp_server.py`: Server endpoints
- `tests/dr_opa_agent/integration/test_citation_formatting.py`: Citations

### Clinical Scenarios
- Cervical screening transition to HPV testing
- CPSO virtual care documentation requirements
- PHO reprocessing for reusable devices
- CEP clinical algorithms and tools

### Performance Targets
- p50 latency: < 500ms
- p95 latency: < 1000ms
- Parallel execution must complete within timeouts

---

## Database Dependencies

### SQLite Database: `data/processed/dr_opa/opa.db`
- `opa_documents`: Document metadata and versioning
- `opa_sections`: Parent and child chunks
- `ingestion_log`: Processing history
- `query_cache`: Performance optimization

### Chroma Collections: `data/processed/dr_opa/chroma/`
- `opa_cpso_corpus`: CPSO policies and guidance
- `opa_ontario_health_corpus`: Screening programs
- `opa_cep_corpus`: Clinical tools and algorithms
- `opa_pho_corpus`: IPAC guidance
- `opa_moh_corpus`: MOH bulletins and updates

---

## Error Handling

Each tool implements resilient error handling:

1. **Partial Failures**: If SQL fails but vector succeeds, return partial results
2. **Timeout Handling**: SQL timeout 500ms, Vector timeout 1000ms
3. **Conflict Resolution**: Surface conflicts, don't hide them
4. **Graceful Degradation**: Lower confidence better than error

---

## Future Enhancements

1. **Query Expansion**: Improve semantic search with medical synonyms
2. **Cross-Reference**: Link related guidance across organizations
3. **Change Detection**: Track guidance changes over time
4. **Feedback Loop**: Learn from user interactions
5. **Multi-Language**: Support French language guidance

---

## Tool 7: opa.clinical_tools

### Purpose
CEP clinical decision support tools lookup with navigation-focused retrieval for interactive web-based clinical tools.

### Clinical Use Cases
- **Tool discovery**: "What CEP tools are available for dementia assessment?"
- **Feature search**: "Find clinical tools with calculators"
- **Condition-specific**: "Tools for managing chronic pain"
- **Category browsing**: "All mental health assessment tools"

### Request Schema
```python
{
    "condition": str,           # Optional: Clinical condition (e.g., "dementia")
    "tool_name": str,           # Optional: Specific tool name
    "category": str,            # Optional: Tool category (mental_health, chronic_disease)
    "feature_type": str,        # Optional: Feature type (algorithm, calculator, checklist)
    "include_sections": bool    # Include section summaries (default false)
}
```

### Response Schema
```python
{
    "tools": [
        {
            "tool_id": str,                    # Unique tool identifier
            "name": str,                       # Tool name
            "url": str,                        # Direct URL to CEP tool
            "last_updated": str,               # Last update date
            "category": str,                   # Tool category
            "summary": str,                    # Tool overview/description
            "key_features": {
                "assessment_algorithm": {
                    "available": bool,
                    "url": str                  # Deep link to algorithm section
                },
                "calculator": {
                    "available": bool,
                    "url": str
                },
                "checklist": {
                    "available": bool,
                    "url": str
                },
                "screening_tools": [str]        # List of tools mentioned
            },
            "sections": [                       # If include_sections=true
                {
                    "title": str,
                    "summary": str,
                    "url": str                  # Section anchor URL
                }
            ],
            "quick_links": {
                "full_tool": str,               # Main tool URL
                "pdf_version": str              # PDF if available (usually null)
            }
        }
    ],
    "total_tools": int,
    "query_interpretation": str
}
```

### Implementation Notes
- Returns lightweight navigation data rather than full content
- Provides deep links to specific tool features
- Optimized for tool discovery and navigation
- Currently indexes 6 CEP tools (expanding to full catalog)

### Example Usage
```python
# Find dementia assessment tools
result = await clinical_tools_handler(condition="dementia")

# Get all tools with algorithms
result = await clinical_tools_handler(feature_type="algorithm")

# Browse mental health category with sections
result = await clinical_tools_handler(
    category="mental_health",
    include_sections=True
)
```
