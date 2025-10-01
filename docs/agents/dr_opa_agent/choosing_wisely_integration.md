# Choosing Wisely Canada Integration Plan for Dr. OPA

## Executive Summary
Integration of Choosing Wisely Canada's evidence-based recommendations into the Dr. OPA agent to help Ontario clinicians identify and reduce unnecessary tests, treatments, and procedures. This will add 70+ medical specialties with 350+ recommendations to the existing Dr. OPA knowledge base.

## Data Overview
- **Source**: Choosing Wisely Canada Collection (July 6, 2022)
- **Format**: 205-page PDF with structured sections per specialty
- **Content**: Evidence-based recommendations on "things to question" in clinical practice
- **Specialties**: 70+ medical societies and organizations
- **Recommendations**: ~5-7 per specialty (350+ total)

---

## 1. 📄 EXTRACTION PHASE

### PDF Processing Strategy

#### 1.1 Section Mapping
```python
# Create specialty-to-pages mapping
specialty_pages = {
    "Allergy & Clinical Immunology": (1, 2),
    "Anesthesiology": (3, 4),
    # ... map all 70+ specialties
}
```

#### 1.2 LLM-Based Extraction
```python
# src/ai_agents/dr_opa_agent/ingestion/choosing_wisely/cw_extractor.py

import asyncio
from typing import List, Dict, Any
import PyPDF2
from openai import AsyncOpenAI

class ChoosingWiselyExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.client = AsyncOpenAI()
        self.extraction_prompt = """
        Extract the following from this Choosing Wisely Canada specialty section:
        
        1. Specialty name
        2. Organization/Society name  
        3. Last updated date
        4. For each numbered recommendation:
           - Number (1-7)
           - Title (bold text)
           - Description (explanation text)
           - PMIDs from sources
        5. "How the list was created" section
        6. All source citations with PMIDs
        
        Return as JSON with this structure:
        {
            "specialty": "...",
            "organization": "...",
            "last_updated": "...",
            "recommendations": [
                {
                    "number": 1,
                    "title": "...",
                    "description": "...",
                    "pmids": ["PMID: 12345678", ...]
                }
            ],
            "methodology": "...",
            "all_sources": [...]
        }
        """
    
    async def extract_specialty(self, pages: List[str]) -> Dict:
        """Extract one specialty section using LLM"""
        combined_text = "\n".join(pages)
        
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.extraction_prompt},
                {"role": "user", "content": combined_text}
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    async def extract_all_specialties(self) -> List[Dict]:
        """Extract all specialties using parallel workers"""
        # Extract pages for each specialty
        specialty_texts = self.split_pdf_by_specialty()
        
        # Process in batches with async workers (10 parallel)
        results = []
        batch_size = 10
        
        for i in range(0, len(specialty_texts), batch_size):
            batch = specialty_texts[i:i+batch_size]
            batch_results = await asyncio.gather(
                *[self.extract_specialty(pages) for pages in batch]
            )
            results.extend(batch_results)
        
        return results
```

#### 1.3 Validation & Output
- Validate extraction completeness (all 70+ specialties)
- Save as JSON files per specialty for review
- Create extraction report with statistics

---

## 2. 🔄 INGESTION PHASE

### Vector-Only Approach (No SQL Database)

#### 2.1 Ingestion Pipeline
```python
# src/ai_agents/dr_opa_agent/ingestion/choosing_wisely/cw_ingester.py

from typing import List, Dict
import chromadb
from openai import OpenAI
import uuid

class ChoosingWiselyIngester:
    def __init__(self):
        # Reuse existing vector client configuration
        self.vector_client = VectorClient(
            persist_directory="data/dr_opa_agent/chroma"
        )
        self.openai_client = OpenAI()
        
    async def ingest_specialty(self, specialty_data: Dict):
        """Ingest one specialty into Chroma"""
        
        # Create collection for Choosing Wisely
        collection = self.vector_client.client.get_or_create_collection(
            name="opa_choosing_wisely_corpus",
            embedding_function=self.vector_client.embedding_function
        )
        
        documents = []
        metadatas = []
        ids = []
        
        # Process each recommendation as a separate document
        for rec in specialty_data['recommendations']:
            doc_id = f"cw_{specialty_data['specialty'].lower().replace(' ', '_')}_{rec['number']}"
            
            # Format document with control tokens for better retrieval
            doc_text = f"""
[ORG=choosing_wisely] [SPECIALTY={specialty_data['specialty']}] [TYPE=recommendation]

Specialty: {specialty_data['specialty']}
Organization: {specialty_data['organization']}

Recommendation #{rec['number']}: {rec['title']}

{rec['description']}

Evidence: {', '.join(rec.get('pmids', []))}
Last Updated: {specialty_data.get('last_updated', 'Unknown')}
"""
            
            documents.append(doc_text)
            ids.append(doc_id)
            metadatas.append({
                "source": "choosing_wisely",
                "specialty": specialty_data['specialty'],
                "organization": specialty_data['organization'],
                "recommendation_number": rec['number'],
                "title": rec['title'],
                "pmids": json.dumps(rec.get('pmids', [])),
                "last_updated": specialty_data.get('last_updated', ''),
                "document_type": "clinical_recommendation"
            })
        
        # Add to collection with embeddings
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        return len(documents)
```

#### 2.2 Chunking Strategy
- **Document Level**: Each recommendation as separate document
- **Parent Context**: Include specialty name and organization in each chunk
- **Control Tokens**: Add tokens for enhanced retrieval
- **Metadata**: Rich metadata for filtering and display

---

## 3. 🛠️ MCP TOOL UPDATES

### 3.1 Update Existing Search Tools

```python
# src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py

@mcp.tool(name="opa_search_sections", description="Hybrid search across OPA knowledge corpus including Choosing Wisely recommendations")
async def search_sections_handler(
    query: str,
    sources: Optional[List[str]] = None,  # Now includes "choosing_wisely"
    doc_types: Optional[List[str]] = None,  # Now includes "clinical_recommendation"
    specialty_filter: Optional[str] = None,  # NEW parameter
    top_k: int = 10,
    include_superseded: bool = False
) -> Dict[str, Any]:
    """Enhanced to search Choosing Wisely collection"""
    
    # Search both CPSO and Choosing Wisely collections
    collections_to_search = []
    
    if sources is None or "cpso" in sources:
        collections_to_search.append("opa_cpso_corpus")
    if sources is None or "choosing_wisely" in sources:
        collections_to_search.append("opa_choosing_wisely_corpus")
    
    # Perform parallel search across collections
    results = await semantic_search.search_multiple_collections(
        query=query,
        collections=collections_to_search,
        specialty_filter=specialty_filter,
        doc_types=doc_types,
        top_k=top_k
    )
    
    return format_search_results(results)


@mcp.tool(name="opa_get_section", description="Retrieve complete section details by ID from any OPA source")
async def get_section_handler(
    section_id: str,
    include_related: bool = False
) -> Dict[str, Any]:
    """Enhanced to handle Choosing Wisely sections"""
    
    # Determine source from section_id prefix
    if section_id.startswith("cw_"):
        collection = "opa_choosing_wisely_corpus"
    else:
        collection = "opa_cpso_corpus"
    
    # Retrieve from appropriate collection
    result = await vector_client.get_by_id(collection, section_id)
    return format_section_result(result)
```

### 3.2 Add Dedicated Choosing Wisely Tool

```python
@mcp.tool(name="opa_unnecessary_tests", description="Search Choosing Wisely Canada recommendations for reducing unnecessary tests and treatments")
async def unnecessary_tests_handler(
    query: str,
    specialty: Optional[str] = None,
    test_type: Optional[str] = None,  # imaging, lab, procedure, medication
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Specialized search for Choosing Wisely recommendations.
    
    Args:
        query: Clinical scenario or test/treatment in question
        specialty: Filter by medical specialty
        test_type: Type of intervention to check
        top_k: Number of recommendations to return
    
    Returns:
        Relevant Choosing Wisely recommendations with evidence
    """
    
    # Enhanced query with Choosing Wisely context
    enhanced_query = f"unnecessary test treatment {query}"
    
    # Search Choosing Wisely collection specifically
    results = await vector_client.search(
        collection="opa_choosing_wisely_corpus",
        query=enhanced_query,
        filter={
            "specialty": specialty,
            "document_type": "clinical_recommendation"
        } if specialty else {"document_type": "clinical_recommendation"},
        top_k=top_k
    )
    
    # Format with emphasis on the recommendation
    formatted = {
        "query": query,
        "specialty_filter": specialty,
        "recommendations": [],
        "message": "Choosing Wisely Canada recommendations for reducing unnecessary care:"
    }
    
    for result in results:
        formatted["recommendations"].append({
            "specialty": result.metadata.get("specialty"),
            "organization": result.metadata.get("organization"),
            "recommendation": result.metadata.get("title"),
            "rationale": result.document,
            "evidence": json.loads(result.metadata.get("pmids", "[]")),
            "confidence": result.score
        })
    
    return formatted
```

---

## 4. 🤖 AGENT INSTRUCTION UPDATES

### Update Dr. OPA System Instructions
```python
# src/ai_agents/dr_opa_agent/openai_agent.py

def _get_system_instructions(self) -> str:
    """Get comprehensive system instructions for the agent."""
    return """You are Dr. OPA (Ontario Practice Advice), a specialized AI assistant for Ontario healthcare clinicians.

Your mission is to provide accurate, current practice guidance from trusted Ontario healthcare authorities including:
- CPSO (College of Physicians and Surgeons of Ontario) - regulatory policies and expectations
- Ontario Health - clinical programs, screening guidelines, and care pathways  
- CEP (Centre for Effective Practice) - clinical decision support tools and algorithms
- PHO (Public Health Ontario) - infection prevention and control guidance
- MOH (Ministry of Health) - policy bulletins and program updates
- **Choosing Wisely Canada** - evidence-based recommendations for reducing unnecessary tests and treatments

[... existing instructions ...]

TOOL SELECTION STRATEGY:
[... existing tool strategies ...]

-- **opa_unnecessary_tests**: For questions about test appropriateness and reducing unnecessary care
  Keywords: unnecessary, appropriate, overuse, choosing wisely, reduce, avoid, question
  Use when: Clinician asks about whether a test/treatment is necessary or appropriate

[... rest of existing instructions ...]

CHOOSING WISELY INTEGRATION:
When queries relate to test/treatment appropriateness or reducing unnecessary care:
1. Use **opa_unnecessary_tests** tool first to check Choosing Wisely recommendations
2. Present recommendations as "Things to Question" not absolute contraindications
3. Emphasize shared decision-making and clinical judgment
4. Always cite the specialty society and evidence (PMIDs)
5. Format as: "Choosing Wisely Canada ({Society}, updated {Date}) recommends questioning..."

When both CPSO policy and Choosing Wisely guidance exist:
- Present both perspectives
- Clarify regulatory requirements (CPSO) vs. resource stewardship (Choosing Wisely)
- Note that Choosing Wisely focuses on reducing harm from unnecessary care
"""
```

---

## 5. 🖥️ WEB APP UI UPDATES

### 5.1 Agent Card Updates
```typescript
// web/config/agents.config.ts

export const drOpaAgent: AgentInfo = {
  // ... existing config ...
  tools: [
    // ... existing tools ...
    'Choosing Wisely Recommendations'
  ],
  dataSources: [
    // ... existing sources ...
    'Choosing Wisely Canada'
  ]
}
```

### 5.2 Main Page Footer
```typescript
// web/components/layout/Footer.tsx
// Add Choosing Wisely Canada to trusted sources list
```

### 5.3 Chat Welcome Message
```typescript
// web/components/agents/AgentChatInterface.tsx
// Update Dr. OPA welcome message to mention Choosing Wisely

welcomeContent = `Hello! I'm Dr. OPA (Ontario Practice Advice), your specialized assistant for Ontario healthcare guidance.

I provide practice guidance from CPSO policies, Ontario Health programs, CEP clinical tools, PHO infection control, and Choosing Wisely Canada recommendations for reducing unnecessary tests and treatments.

How can I assist with your clinical practice question today?`;
```

### 5.4 Suggested Prompts
```typescript
// web/config/prompts.config.ts

export const drOpaSuggestedPrompts = [
  "What are CPSO expectations for virtual care consent?",
  "Is routine pre-operative chest X-ray necessary for low-risk surgery?", // NEW
  "What are Ontario's colorectal cancer screening guidelines?",
  "Should I order specific IgG testing for food allergies?" // NEW
];
```

---

## 6. 📊 IMPLEMENTATION TIMELINE

### Phase 1: Infrastructure Setup (Day 1)
- [ ] Create `choosing_wisely/` directory structure
- [ ] Set up extractor and ingester classes
- [ ] Configure Chroma collection

### Phase 2: LLM-Based Extraction (Day 2-3)
- [ ] Map specialties to page ranges
- [ ] Implement async LLM extraction
- [ ] Extract all 70+ specialties to JSON
- [ ] Validate extraction quality

### Phase 3: Vector Ingestion (Day 4)
- [ ] Process JSON into vector documents
- [ ] Generate embeddings using text-embedding-3-small
- [ ] Load into Chroma collection
- [ ] Test retrieval quality

### Phase 4: MCP Tool Integration (Day 5)
- [ ] Update search_sections tool
- [ ] Update get_section tool
- [ ] Add unnecessary_tests tool
- [ ] Test tool responses

### Phase 5: Agent & UI Updates (Day 6)
- [ ] Update agent instructions
- [ ] Update web UI components
- [ ] Add suggested prompts
- [ ] Complete integration testing

---

## 7. 🧪 TESTING STRATEGY

### Test Queries
```python
test_cases = [
    "Is routine pre-operative CBC necessary?",
    "Should I order IgG testing for food allergies?",
    "When is CT appropriate for acute sinusitis?",
    "Are annual ECGs needed for asymptomatic patients?",
    "Should antibiotics be prescribed for uncomplicated sinusitis?"
]
```

### Validation Criteria
- Correct specialty attribution
- Accurate recommendation text
- PMID preservation
- Appropriate confidence scoring
- Natural integration with existing CPSO guidance

---

## 8. 🚀 DEPLOYMENT NOTES

### Environment Variables
- No new environment variables required
- Uses existing OPENAI_API_KEY for embeddings

### Storage Requirements
- Chroma collection: ~50MB additional
- JSON extracts: ~5MB (temporary, can delete after ingestion)

### Performance Considerations
- Extraction: ~2-3 hours with parallel LLM calls
- Ingestion: ~30 minutes for embeddings
- Query latency: No significant impact expected

---

## 9. 📝 MAINTENANCE

### Annual Updates
- Choosing Wisely releases annual updates
- Re-run extraction pipeline on new PDF
- Version tracking in metadata
- Consider keeping historical versions

### Monitoring
- Track query patterns for Choosing Wisely content
- Monitor for conflicts with CPSO guidance
- Log specialty coverage in queries

---

## Success Criteria

1. ✅ All 70+ specialties extracted successfully
2. ✅ 350+ recommendations searchable
3. ✅ PMIDs preserved and linked
4. ✅ Natural integration with existing tools
5. ✅ Clear attribution to Choosing Wisely Canada
6. ✅ Appropriate framing as "things to question"

---

## Next Steps

1. Create GitHub issue with this plan
2. Create feature branch: `feat/choosing-wisely-integration`
3. Begin Phase 1 implementation
4. Daily progress updates in issue comments