# Ontario Health Quality Standards Integration Plan for Dr. OPA

## Executive Summary
Integration of Ontario Health Quality Standards into the Dr. OPA agent to provide evidence-based quality care standards for Ontario clinicians. This will add 41 comprehensive quality standards covering major clinical conditions and care transitions, defining what high-quality care looks like in Ontario.

## Data Overview
- **Source**: Ontario Health (formerly Health Quality Ontario)
- **Format**: 41 PDF documents (50-80 pages each)
- **Content**: Evidence-based quality statements defining optimal care
- **Topics**: Major conditions (diabetes, COPD, heart failure, mental health, chronic pain, etc.)
- **Structure**: 8-15 quality statements per standard, with rationale and indicators

---

## 1. 📄 EXTRACTION PHASE

### Document Structure Analysis
Each Quality Standard follows a consistent structure:
1. **Front Matter** (Pages 1-7)
   - Title, Summary, Table of Contents
   - About Quality Standards
   - Scope and Terminology
   - Why This Standard Is Needed
   - How Success Can Be Measured

2. **Quality Statements** (Pages 8-50+) - **CORE CONTENT**
   - Brief statement summary
   - Detailed statement with:
     - Background/rationale
     - Sources of evidence
     - What This Quality Statement Means sections:
       - For Patients
       - For Clinicians
       - For Health Services
     - Quality Indicators
     - Additional Resources

3. **Appendices** (Pages 50+) - **EXCLUDE**
   - Glossary, References, Acknowledgements

### LLM-Based Extraction Strategy

```python
# src/ai_agents/dr_opa_agent/ingestion/quality_standards/qs_extractor.py

import asyncio
from typing import List, Dict, Any
import PyPDF2
from openai import AsyncOpenAI
import re

class QualityStandardsExtractor:
    def __init__(self):
        self.client = AsyncOpenAI()
        self.extraction_prompt = """
        Extract the following from this Ontario Health Quality Standard section:
        
        1. Quality Statement Number and Title
        2. Brief statement (the bold summary)
        3. Full detailed statement
        4. Background/rationale
        5. What this means for:
           - Patients
           - Clinicians  
           - Health Services
        6. Quality Indicators (process and outcome measures)
        7. Sources/References cited
        
        Return as JSON:
        {
            "statement_number": 1,
            "title": "...",
            "brief_statement": "...",
            "full_statement": "...",
            "background": "...",
            "for_patients": "...",
            "for_clinicians": "...",
            "for_health_services": "...",
            "indicators": [...],
            "sources": [...]
        }
        """
    
    def extract_metadata(self, pdf_path: str) -> Dict:
        """Extract document metadata from front matter"""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Extract from first 5 pages
            front_matter = ""
            for i in range(min(5, len(reader.pages))):
                front_matter += reader.pages[i].extract_text()
            
            # Parse title, scope, summary
            title_match = re.search(r'^([^\n]+)\n', front_matter)
            
            return {
                "title": title_match.group(1) if title_match else "",
                "year": self.extract_year(pdf_path),
                "scope": self.extract_scope(front_matter),
                "total_pages": len(reader.pages)
            }
    
    def find_quality_statements_pages(self, pdf_path: str) -> List[tuple]:
        """Identify page ranges for each quality statement"""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            statement_pages = []
            current_statement = None
            
            for page_num in range(len(reader.pages)):
                text = reader.pages[page_num].extract_text()
                
                # Look for "Quality Statement N:" pattern
                statement_match = re.search(r'Quality Statement (\d+):', text)
                if statement_match:
                    if current_statement:
                        # Save previous statement's end page
                        statement_pages.append(current_statement)
                    # Start new statement
                    stmt_num = int(statement_match.group(1))
                    current_statement = (stmt_num, page_num, None)
                elif current_statement and not current_statement[2]:
                    # Look for next statement or appendix to mark end
                    if 'Quality Statement' in text or 'Appendix' in text or 'References' in text:
                        statement_pages.append((current_statement[0], current_statement[1], page_num - 1))
                        current_statement = None
            
            return statement_pages
    
    async def extract_quality_statement(self, pdf_path: str, pages: tuple) -> Dict:
        """Extract one quality statement using LLM"""
        stmt_num, start_page, end_page = pages
        
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Combine pages for this statement
            statement_text = ""
            for page_num in range(start_page, min(end_page + 1, len(reader.pages))):
                statement_text += reader.pages[page_num].extract_text() + "\n"
        
        # Use LLM to structure the content
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.extraction_prompt},
                {"role": "user", "content": statement_text}
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    async def extract_document(self, pdf_path: str) -> Dict:
        """Extract complete quality standard document"""
        metadata = self.extract_metadata(pdf_path)
        statement_pages = self.find_quality_statements_pages(pdf_path)
        
        # Extract statements in parallel batches
        statements = []
        batch_size = 5
        
        for i in range(0, len(statement_pages), batch_size):
            batch = statement_pages[i:i+batch_size]
            batch_results = await asyncio.gather(
                *[self.extract_quality_statement(pdf_path, pages) for pages in batch]
            )
            statements.extend(batch_results)
        
        return {
            "metadata": metadata,
            "quality_statements": statements,
            "source_file": pdf_path
        }
```

---

## 2. 🔄 INGESTION PHASE

### Simplified Chunking Strategy - Single Rich Chunks

#### One Comprehensive Chunk Per Quality Statement
```python
# src/ai_agents/dr_opa_agent/ingestion/quality_standards/qs_ingester.py

class QualityStandardsIngester:
    def __init__(self):
        self.vector_client = VectorClient(
            persist_directory="data/dr_opa_agent/chroma"
        )
    
    def create_chunks(self, doc_data: Dict) -> List[Dict]:
        """Create single comprehensive chunk per quality statement with ALL details"""
        chunks = []
        doc_title = doc_data['metadata']['title']
        
        for stmt in doc_data['quality_statements']:
            # Create one rich chunk with all statement content
            chunk = {
                "id": f"qs_{self.slugify(doc_title)}_stmt_{stmt['statement_number']}",
                "text": self.format_complete_statement(doc_title, stmt),
                "metadata": {
                    "source": "quality_standards",
                    "document": doc_title,
                    "statement_number": stmt['statement_number'],
                    "statement_title": stmt['title'],
                    "year": doc_data['metadata']['year']
                }
            }
            chunks.append(chunk)
        
        return chunks
    
    def format_complete_statement(self, doc_title: str, stmt: Dict) -> str:
        """Format complete quality statement with ALL details for rich search"""
        return f"""
[ORG=ontario_health] [TYPE=quality_standard] [CONDITION={doc_title}]

Quality Statement {stmt['statement_number']}: {stmt['title']}

STATEMENT: {stmt['brief_statement']}

BACKGROUND & RATIONALE:
{stmt.get('background', '')}

WHAT THIS MEANS FOR PATIENTS:
{stmt.get('for_patients', '')}

WHAT THIS MEANS FOR CLINICIANS:
{stmt.get('for_clinicians', '')}

WHAT THIS MEANS FOR HEALTH SERVICES:
{stmt.get('for_health_services', '')}

QUALITY INDICATORS:
{self.format_indicators(stmt.get('indicators', []))}

SOURCES: {', '.join(stmt.get('sources', []))}
"""
    
    def format_indicators(self, indicators: List) -> str:
        """Format quality indicators for inclusion in chunk"""
        if not indicators:
            return "No specific indicators defined"
        return "\n".join([f"- {ind}" for ind in indicators])
```

#### Why Single Rich Chunks Are Better:
1. **All content is searchable** - Nothing hidden in separate chunks
2. **Simpler implementation** - One chunk per statement
3. **Complete context** - Full statement provides comprehensive guidance
4. **Better retrieval** - Semantic search can match on any aspect (patient info, clinical guidance, indicators)
5. **No fragmentation** - Avoids splitting related information

### Vector Storage Configuration

```python
async def ingest_all_standards(self):
    """Ingest all quality standards into Chroma"""
    
    # Create dedicated collection
    collection = self.vector_client.client.get_or_create_collection(
        name="opa_quality_standards_corpus",
        embedding_function=self.vector_client.embedding_function  # text-embedding-3-small
    )
    
    # Process each PDF
    pdf_files = glob.glob("data/dr_opa_agent/raw/oh_quality_std/*.pdf")
    
    for pdf_path in pdf_files:
        # Extract document
        doc_data = await self.extractor.extract_document(pdf_path)
        
        # Create chunks
        chunks = self.create_chunks(doc_data)
        
        # Add to collection with embeddings
        documents = [chunk['text'] for chunk in chunks]
        metadatas = [chunk['metadata'] for chunk in chunks]
        ids = [chunk['id'] for chunk in chunks]
        
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"Ingested {len(chunks)} chunks from {pdf_path}")
```

---

## 3. 🛠️ MCP TOOL UPDATES

### 3.1 Update Existing Search Tool (Minimal Changes)

```python
# src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py

@mcp.tool(name="opa_search_sections", description="Hybrid search across OPA knowledge corpus including Quality Standards")
async def search_sections_handler(
    query: str,
    sources: Optional[List[str]] = None,  # Now includes "quality_standards"
    doc_types: Optional[List[str]] = None,
    top_k: int = 10,
    include_superseded: bool = False
) -> Dict[str, Any]:
    """Enhanced to search Quality Standards collection"""
    
    collections_to_search = []
    
    if sources is None or "cpso" in sources:
        collections_to_search.append("opa_cpso_corpus")
    if sources is None or "choosing_wisely" in sources:
        collections_to_search.append("opa_choosing_wisely_corpus")
    if sources is None or "quality_standards" in sources:
        collections_to_search.append("opa_quality_standards_corpus")
    
    # Simple search across collections - no complex filters
    results = await semantic_search.search_multiple_collections(
        query=query,
        collections=collections_to_search,
        doc_types=doc_types,
        top_k=top_k
    )
    
    return format_search_results(results)
```

### 3.2 Add Smart Quality Standards Tool

```python
@mcp.tool(name="opa_quality_standards", 
          description="Search Ontario Health Quality Standards - returns specific statements or ALL statements for a condition")
async def quality_standards_handler(
    query: str,
    return_all_statements: bool = False  # Simple flag for complete retrieval
) -> Dict[str, Any]:
    """
    Search quality standards with smart document detection.
    
    If return_all_statements=True, identifies relevant document(s) 
    and returns ALL quality statements from those documents.
    Otherwise, returns most relevant statements via semantic search.
    """
    
    if return_all_statements:
        # Step 1: Use LLM to classify which document(s) to retrieve
        classification = await classify_quality_standard_topic(query)
        
        # Step 2: Retrieve ALL statements from identified documents
        results = await vector_client.search(
            collection="opa_quality_standards_corpus",
            filter={"document": {"$in": classification['documents']}},
            top_k=50  # Get all statements (most docs have 8-15)
        )
        
        # Step 3: Sort by statement number within each document
        results = sorted(results, key=lambda x: (
            x.metadata['document'], 
            x.metadata['statement_number']
        ))
        
        return {
            "query": query,
            "identified_standards": classification['documents'],
            "total_statements": len(results),
            "quality_statements": [
                {
                    "document": r.metadata['document'],
                    "statement": f"Statement {r.metadata['statement_number']}: {r.metadata['statement_title']}",
                    "content": r.document,  # Full rich content
                    "confidence": r.score
                }
                for r in results
            ]
        }
    else:
        # Regular semantic search for most relevant statements
        results = await vector_client.search(
            collection="opa_quality_standards_corpus",
            query=query,
            top_k=5
        )
        
        return {
            "query": query,
            "quality_statements": [
                {
                    "document": r.metadata['document'],
                    "statement": f"Statement {r.metadata['statement_number']}: {r.metadata['statement_title']}",
                    "content": r.document,
                    "confidence": r.score
                }
                for r in results
            ]
        }


async def classify_quality_standard_topic(query: str) -> Dict[str, List[str]]:
    """
    Use LLM to identify which quality standard document(s) match the query.
    """
    
    # List of all available quality standards
    AVAILABLE_STANDARDS = [
        "Alcohol Use Disorder",
        "Anxiety Disorders", 
        "Asthma in Adults",
        "Asthma in Children and Adolescents",
        "Chronic Obstructive Pulmonary Disease",
        "Chronic Pain",
        "Delirium",
        "Dementia Care in the Community",
        "Diabetes in Pregnancy",
        "Diabetic Foot Ulcers",
        "Early Pregnancy Complications and Loss",
        "Eating Disorders",
        "Gender-Affirming Care for Adults",
        "Glaucoma",
        "Heart Failure",
        "Heavy Menstrual Bleeding",
        "Hip Fracture",
        "Hypertension",
        "Insomnia Disorder",
        "Low Back Pain",
        "Major Depression",
        "Medication Safety",
        "Obsessive-Compulsive Disorder",
        "Opioid Prescribing for Acute Pain",
        "Opioid Prescribing for Chronic Pain",
        "Opioid Use Disorder",
        "Osteoarthritis",
        "Palliative Care",
        "Prediabetes and Type 2 Diabetes",
        "Pressure Injuries",
        "Schizophrenia Care in Hospitals",
        "Schizophrenia Care in the Community",
        "Sickle Cell Disease",
        "Surgical Site Infections",
        "Transitions Between Hospital and Home",
        "Transitions from Youth to Adult Health Care Services",
        "Type 1 Diabetes",
        "Vaginal Birth After Caesarean",
        "Venous Leg Ulcers"
    ]
    
    prompt = f"""
    Given this clinical query: "{query}"
    
    Which of these Ontario Health Quality Standards documents are relevant?
    Return ONLY the exact document names that match, considering:
    - If asking about diabetes, include ALL diabetes-related standards
    - If asking about schizophrenia, include both hospital and community standards
    - If asking about transitions, include relevant transition standards
    
    Available standards:
    {json.dumps(AVAILABLE_STANDARDS, indent=2)}
    
    Return as JSON: {{"documents": ["exact name 1", "exact name 2"]}}
    """
    
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)
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
- Ontario Health - clinical programs, screening guidelines, care pathways, and **Quality Standards**
- CEP (Centre for Effective Practice) - clinical decision support tools and algorithms
- PHO (Public Health Ontario) - infection prevention and control guidance
- MOH (Ministry of Health) - policy bulletins and program updates
- Choosing Wisely Canada - evidence-based recommendations for reducing unnecessary tests and treatments

[... existing instructions ...]

ONTARIO HEALTH QUALITY STANDARDS:
Quality Standards define what high-quality care looks like for conditions where there has been a gap 
between the care patients should receive and the care they actually receive. When addressing clinical 
queries about specific conditions:

1. Check if a Quality Standard exists for the condition
2. Present relevant quality statements as evidence-based best practices
3. Include both clinical guidance and patient perspectives
4. Reference quality indicators when discussing care measurement
5. Format as: "Ontario Health Quality Standard for {Condition} states..."

Quality Standards cover major conditions including:
- Chronic conditions (diabetes, COPD, heart failure, hypertension, chronic pain)
- Mental health (depression, anxiety, OCD, schizophrenia, eating disorders)
- Transitions of care (hospital to home, youth to adult)
- Specific procedures (hip fracture, surgical site infections)
- Life stages (pregnancy, palliative care)

TOOL SELECTION STRATEGY:
[... existing tool strategies ...]

-- **opa_quality_standards**: For Ontario Health Quality Standards
  - Use with return_all_statements=True when user asks for:
    * "all quality standards for [condition]"
    * "complete quality standard for [condition]"
    * "what are the quality statements for [condition]"
  - Use with return_all_statements=False (default) for:
    * Specific clinical questions about care
    * "how should I assess/treat/manage [condition]"
    * "quality indicators for [aspect of care]"

-- **opa_search_sections**: Now enhanced to search Quality Standards
  - Automatically includes quality_standards collection in searches
  - Use sources=["quality_standards"] to search ONLY quality standards

[... rest of instructions ...]

INTEGRATING MULTIPLE SOURCES:
When a query relates to a specific condition, synthesize guidance from:
1. Quality Standards (what optimal care looks like)
2. CPSO policies (regulatory requirements)
3. Choosing Wisely (what to avoid/question)
4. Clinical tools (decision support)
This provides comprehensive, multi-faceted guidance.
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
    'Ontario Health Quality Standards'
  ],
  dataSources: [
    'CPSO Policies',
    'Ontario Health Programs',
    'Ontario Health Quality Standards',  // NEW
    'CEP Clinical Tools',
    'PHO IPAC Guidance',
    'Choosing Wisely Canada'
  ]
}
```

### 5.2 Welcome Message Update
```typescript
// web/components/agents/AgentChatInterface.tsx

welcomeContent = `Hello! I'm Dr. OPA (Ontario Practice Advice), your specialized assistant for Ontario healthcare guidance.

I provide practice guidance from CPSO policies, Ontario Health programs and Quality Standards, 
CEP clinical tools, PHO infection control, and Choosing Wisely Canada recommendations.

I can help you understand what high-quality care looks like for specific conditions, regulatory 
requirements, and evidence-based practices.

How can I assist with your clinical practice question today?`;
```

### 5.3 Suggested Prompts
```typescript
// web/config/prompts.config.ts

export const drOpaSuggestedPrompts = [
  "What are CPSO expectations for virtual care consent?",
  "What are the quality standards for managing chronic pain?",  // NEW
  "Is routine pre-operative chest X-ray necessary for low-risk surgery?",
  "What quality indicators should I track for diabetes care?",  // NEW
  "What are Ontario's colorectal cancer screening guidelines?"
];
```

---

## 6. 📊 IMPLEMENTATION TIMELINE

### Phase 1: Infrastructure Setup (Day 1)
- [ ] Create `quality_standards/` directory structure
- [ ] Set up `qs_extractor.py` with PDF parsing
- [ ] Set up `qs_ingester.py` with chunking strategy
- [ ] Configure Chroma collection

### Phase 2: Content Extraction (Days 2-3)
- [ ] Implement metadata extraction
- [ ] Implement quality statement page detection
- [ ] Implement LLM-based statement extraction
- [ ] Extract all 41 quality standards to JSON
- [ ] Validate extraction quality

### Phase 3: Vector Ingestion (Day 4)
- [ ] Implement hierarchical chunking
- [ ] Process parent and child chunks
- [ ] Generate embeddings using text-embedding-3-small
- [ ] Load into Chroma collection
- [ ] Test retrieval quality

### Phase 4: MCP Tool Integration (Day 5)
- [ ] Update `opa_search_sections` tool
- [ ] Implement `opa_quality_standards` tool
- [ ] Test tool responses
- [ ] Optimize retrieval and ranking

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
    # Condition-specific queries
    "What are the quality standards for COPD management?",
    "How should chronic pain be assessed according to quality standards?",
    "What are quality indicators for diabetes care?",
    
    # Role-specific queries
    "What should patients know about heart failure management?",
    "What are clinician requirements for depression screening?",
    
    # Cross-source queries
    "What are CPSO requirements and quality standards for palliative care?",
    "How do quality standards and Choosing Wisely align on imaging for low back pain?"
]
```

### Validation Criteria
- Quality statement accuracy
- Appropriate chunking and retrieval
- Component filtering works correctly
- Source attribution is clear
- Integration with other sources is seamless

---

## 8. 🚀 SPECIAL CONSIDERATIONS

### Chunking Strategy Rationale
1. **Parent chunks**: Full quality statements for comprehensive context
2. **Child chunks**: Components for targeted retrieval
3. **Control tokens**: Enhanced semantic matching
4. **Metadata richness**: Enables precise filtering

### Why Hierarchical Chunking?
- Quality statements are multi-faceted (patient, clinician, system perspectives)
- Users may query from different angles
- Enables both broad and specific retrieval
- Maintains context while allowing granular search

### Storage Optimization
- Exclude appendices to reduce noise
- Focus on actionable content (quality statements)
- Maintain document metadata for attribution
- Use consistent ID scheme for tracking

---

## 9. 📝 MAINTENANCE

### Update Frequency
- Ontario Health updates standards periodically
- Check quarterly for new or revised standards
- Version tracking in metadata
- Maintain change log

### Quality Assurance
- Regular spot checks on extraction quality
- Monitor retrieval relevance scores
- Track user query patterns
- Gather clinician feedback

---

## Success Criteria

1. ✅ All 41 quality standards extracted successfully
2. ✅ 400+ quality statements searchable
3. ✅ Hierarchical chunking improves retrieval
4. ✅ Role-based filtering works effectively
5. ✅ Clear attribution to Ontario Health
6. ✅ Natural integration with existing tools
7. ✅ Quality indicators accessible when needed

---

## Next Steps

1. Create GitHub issue with this plan
2. Create feature branch: `feat/quality-standards-integration`
3. Begin Phase 1 implementation
4. Daily progress updates in issue comments

---

## Appendix: Quality Standards List

### Current Quality Standards (41 documents):
1. Alcohol Use Disorder
2. Anxiety Disorders
3. Asthma in Adults (2025)
4. Asthma in Children and Adolescents (2025)
5. Behavioural Symptoms of Dementia (2024)
6. Chronic Obstructive Pulmonary Disease (2023)
7. Chronic Pain
8. Delirium
9. Dementia Care in the Community (2024)
10. Diabetes in Pregnancy
11. Diabetic Foot Ulcers
12. Early Pregnancy Complications and Loss
13. Eating Disorders
14. Gender-Affirming Care for Adults
15. Glaucoma
16. Heart Failure
17. Heavy Menstrual Bleeding (2024)
18. Hip Fracture (2024)
19. Hypertension
20. Insomnia Disorder
21. Low Back Pain (2025)
22. Major Depression (2024)
23. Medication Safety
24. Obsessive-Compulsive Disorder
25. Opioid Prescribing for Acute Pain
26. Opioid Prescribing for Chronic Pain
27. Opioid Use Disorder
28. Osteoarthritis (2024)
29. Palliative Care (2024)
30. Prediabetes and Type 2 Diabetes
31. Pressure Injuries
32. Schizophrenia Care in Hospitals
33. Schizophrenia Care in the Community
34. Sickle Cell Disease
35. Surgical Site Infections
36. Transitions Between Hospital and Home
37. Transitions from Youth to Adult Health Care Services
38. Type 1 Diabetes
39. Vaginal Birth After Caesarean (2024)
40. Venous Leg Ulcers

Each standard provides 8-15 quality statements defining optimal care delivery.