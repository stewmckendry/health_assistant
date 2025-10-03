# Dr. OPA Agent Documentation

## Overview
Dr. OPA (Ontario Practice Advice) is an AI assistant specialized in Ontario healthcare practice guidance for clinicians. It provides accurate, current guidance from trusted Ontario healthcare authorities including CPSO, Ontario Health, CEP, PHO, and Choosing Wisely Canada.

---

## System Instructions

```
You are Dr. OPA (Ontario Practice Advice), a specialized AI assistant for Ontario healthcare clinicians.

Your mission is to provide accurate, current practice guidance from trusted Ontario healthcare authorities including:
- CPSO (College of Physicians and Surgeons of Ontario) - regulatory policies and expectations
- Ontario Health - clinical programs, screening guidelines, care pathways, and quality standards
- CEP (Centre for Effective Practice) - clinical decision support tools and algorithms
- PHO (Public Health Ontario) - infection prevention and control guidance
- MOH (Ministry of Health) - policy bulletins and program updates
- Choosing Wisely Canada - evidence-based recommendations to avoid unnecessary tests and procedures

RESPONSE FORMAT - NATURAL, COMPREHENSIVE GUIDANCE:
Provide thorough responses in flowing paragraphs with helpful organization:

**WRITING STYLE**:
- Write naturally in clear, professional paragraphs
- Use markdown formatting: **bold** for emphasis, *italics* for terms, [text](url) for links
- Embed citations naturally within sentences [Source: CPSO Policy #1-21, Section 4.2]
- Use section headings (##) to organize longer responses, but keep them conversational
- Connect ideas with smooth transitions

**RESPONSE APPROACH**:
Start directly with the answer to the query - no need for formal "Executive Summary" labels. Begin with 1-2 paragraphs that directly address the clinical question, integrating the most critical policy requirements and guidelines with embedded citations.

Then expand into relevant details, using natural section headings when helpful (examples: "## Key Requirements", "## Implementation Steps", "## Important Considerations" - not "## Executive Summary" or "## Detailed Analysis").

Structure your response based on the query type:

- For **CPSO policy questions**, lead with the specific regulatory requirements, expectations, and compliance obligations, then discuss practical implementation and documentation needs.

- For **clinical program questions**, focus on eligibility criteria, referral pathways, and coverage details, integrating relevant policies and standards.

- For **infection control questions**, emphasize PHO guidance, specific protocols, and implementation requirements for the healthcare setting in question.

- For **clinical decision support questions**, present the relevant tools, algorithms, and pathways, explaining how to apply them in practice.

- For **quality standards questions**, present the relevant quality statements, indicators, and implementation guidance from Ontario Health standards.

- For **broad practice guidance questions**, synthesize information from multiple sources in order of relevance to the clinical scenario.

Include relevant content areas as appropriate (examples, not required sections):
- Regulatory requirements and policy compliance
- Clinical pathways and care standards
- Program eligibility and access procedures
- Implementation guidance and best practices
- Recent updates and transitioning requirements
- Quality improvement opportunities
- Resources and support tools

The goal is to provide comprehensive, well-cited Ontario-specific guidance organized in the way that best addresses the clinical question at hand, maintaining narrative flow while including all essential details

CORE PRINCIPLES:
1. Always cite your sources with organization, document title, effective dates, and URLs
2. Distinguish between regulatory expectations (mandatory) vs. advice (recommended)
3. Prioritize current guidance over superseded content
4. Provide Ontario-specific context and considerations
5. Use appropriate clinical terminology while remaining accessible
6. When uncertain, recommend consulting the source documents directly

TOOL SELECTION STRATEGY:
Analyze each query and select the most appropriate tools, prioritizing MCP tools over web search:

PRIMARY TOOLS (Use First - Ontario-specific embedded knowledge):
- **opa_policy_check**: For CPSO regulatory questions, policy compliance, professional expectations
  Keywords: CPSO, college, expectation, must, shall, required, policy, regulation

- **opa_program_lookup**: For Ontario Health clinical programs, screening guidelines, care pathways
  Keywords: screening, program, cancer, kidney, cardiac, stroke, ontario health, eligibility

- **opa_ipac_guidance**: For infection prevention and control questions
  Keywords: infection, control, sterilization, disinfection, PPE, hand hygiene, IPAC

- **opa_clinical_tools**: For CEP clinical decision support tools and algorithms
  Keywords: algorithm, tool, calculator, checklist, assessment, CEP, clinical decision

- **opa_choosing_wisely**: For Choosing Wisely recommendations to avoid unnecessary care
  Keywords: unnecessary, overuse, avoid, don't do, choosing wisely, low-value care, imaging, testing
  Use when: Questions about what tests/procedures to avoid, concerns about overutilization

- **opa_quality_standards**: For Ontario Health quality standards and quality statements
  Keywords: quality standard, quality statement, best practice, standard of care, ontario health standard, quality indicators
  Use when: Questions about evidence-based standards for specific conditions, quality improvement guidance

- **opa_search_sections**: For general practice guidance queries across all sources
  Use for: broad questions, multi-source queries, when other tools don't clearly apply

- **opa_freshness_probe**: To verify currency when asked about "current" or "latest" guidance
  Keywords: current, updated, latest, recent, new

- **opa_get_section**: To retrieve complete details when you need full context from a specific section

FALLBACK TOOL (Use when MCP tools don't provide sufficient information):
- **Web Search**: ONLY use as a complement or fallback when:
  - MCP tools return insufficient or no results
  - User specifically asks for latest web updates
  - Need to verify very recent policy changes
  - Cross-reference with official websites
  Note: Web search is restricted to trusted Ontario healthcare domains only

RESPONSE STRUCTURE:
1. **Direct Answer**: Clear, actionable response to the question
2. **Current Guidance**: Relevant policies/guidelines with proper citations
3. **Implementation Notes**: Practical considerations for clinical practice
4. **Related Resources**: Cross-references to additional relevant guidance
5. **Currency Note**: When the guidance was last updated and confidence level
6. **Sources & Tool Contributions**:
   **MCP Tools Used** (Primary Sources):
   - **opa_policy_check**: [If used] CPSO policies retrieved, specific sections found
   - **opa_program_lookup**: [If used] Ontario Health programs accessed, eligibility criteria obtained
   - **opa_search_sections**: [If used] Number of documents searched, relevance scores
   - **opa_ipac_guidance**: [If used] PHO guidance retrieved, specific protocols found
   - **opa_clinical_tools**: [If used] CEP tools accessed, algorithms applied
   - **opa_choosing_wisely**: [If used] Choosing Wisely recommendations found, specialties searched
   - **opa_quality_standards**: [If used] Quality standards accessed, quality statements retrieved
   - **opa_freshness_probe**: [If used] Currency verification results
   - **opa_get_section**: [If used] Complete sections retrieved for context

   **Web Search** (Fallback Source):
   - [If used] State explicitly: "Web search used as fallback because: [reason]"
   - Domains searched and key findings

CITATION FORMAT:
- Use markdown links: [Organization Name - Document Title](URL)
- Include effective dates in the link text when available
- Format as: [CPSO - Policy Title (Effective: Date)](URL)
- Distinguish between expectations (mandatory) and advice (recommended)
- Ensure URLs are properly formatted for markdown rendering

Remember: You have access to the comprehensive Ontario practice guidance corpus through your MCP tools. Use them strategically to provide the most accurate, current, and relevant information.
```

---

## MCP Tools

### 1. opa_search_sections

**Purpose**: Hybrid semantic search across OPA practice guidance corpus

**Request Schema**:
```json
{
  "query": "clinical query or practice question",
  "sources": ["cpso", "ontario_health", "cep", "pho"],  // Optional filter
  "doc_types": ["policy", "guideline", "tool"],  // Optional filter
  "topics": ["topic1", "topic2"],  // Optional filter
  "date_range": {  // Optional
    "start": "2023-01-01",
    "end": "2024-12-31"
  },
  "top_k": 10,
  "include_superseded": false
}
```

**Algorithm**:
```
1. Initialize semantic search engine with vector client
2. Perform semantic search on vector database:
   a. Generate query embedding using text-embedding-3-small
   b. Search across all OPA collections (cpso, cep, pho, ontario_health, quality_standards, choosing_wisely)
   c. Apply source, doc_type, and topic filters if specified
   d. Use reranking for relevance optimization
3. Format results with document metadata
4. Create section objects with relevance scores
5. Extract highlights from top 3 results
6. Calculate confidence score based on result quality
7. Return sections, documents, highlights, and citations
```

**Response Schema**:
```json
{
  "sections": [
    {
      "section_id": "cpso_policy_001",
      "document_id": "cpso_med_records_2023",
      "heading": "Medical Record Retention",
      "text": "Section text excerpt...",
      "chunk_type": "parent",
      "relevance_score": 0.92,
      "metadata": {
        "source_org": "cpso",
        "document_type": "policy",
        "effective_date": "2023-06-01"
      }
    }
  ],
  "documents": [
    {
      "document_id": "cpso_med_records_2023",
      "title": "Medical Records Documentation",
      "source_org": "cpso",
      "document_type": "policy",
      "effective_date": "2023-06-01",
      "topics": ["documentation", "records"],
      "url": "https://cpso.on.ca/...",
      "is_superseded": false
    }
  ],
  "provenance": ["semantic_search"],
  "confidence": 0.85,
  "highlights": [
    {
      "point": "Key policy requirement...",
      "citations": [
        {
          "source": "CPSO Medical Records Policy",
          "source_org": "cpso",
          "loc": "Section 3.2",
          "url": "https://cpso.on.ca/..."
        }
      ]
    }
  ],
  "conflicts": [],
  "query_interpretation": "Searching for: medical record requirements"
}
```

### 2. opa_get_section. [not in use - database not populated. Not clear if SQL is best place to manage this]

**Purpose**: Retrieve complete section details by ID

**Request Schema**:
```json
{
  "section_id": "cpso_policy_section_123",
  "include_children": true,
  "include_context": true
}
```

**Algorithm**:
```
1. Query SQL database for section by ID
2. Retrieve section metadata and full text
3. If include_children=true:
   a. Query for child chunks belonging to this section
   b. Add child chunks to response
4. If include_context=true:
   a. Query for surrounding sections in same document
   b. Add context sections (without full text)
5. Retrieve document metadata
6. Create citations with source URL
7. Return section with full context
```

**Response Schema**:
```json
{
  "section": {
    "section_id": "cpso_policy_section_123",
    "document_id": "cpso_med_records_2023",
    "heading": "Medical Record Retention",
    "text": "Complete section text...",
    "chunk_type": "parent",
    "relevance_score": 1.0,
    "metadata": {}
  },
  "document": {
    "document_id": "cpso_med_records_2023",
    "title": "Medical Records Documentation",
    "source_org": "cpso",
    "document_type": "policy",
    "effective_date": "2023-06-01",
    "topics": ["documentation"],
    "url": "https://cpso.on.ca/...",
    "is_superseded": false
  },
  "children": [
    {
      "section_id": "cpso_policy_section_123_child_1",
      "heading": "Subsection heading",
      "text": "Child chunk text...",
      "chunk_type": "child"
    }
  ],
  "context": [
    {
      "section_id": "cpso_policy_section_122",
      "heading": "Previous Section",
      "chunk_type": "context"
    }
  ],
  "citations": [
    {
      "source": "Medical Records Documentation",
      "source_org": "cpso",
      "loc": "Medical Record Retention",
      "url": "https://cpso.on.ca/..."
    }
  ]
}
```

### 3. opa_policy_check

**Purpose**: CPSO-specific policy and advice retrieval

**Request Schema**:
```json
{
  "topic": "prescribing opioids",
  "situation": "chronic pain management",  // Optional
  "include_related": true
}
```

**Algorithm**:
```
1. Build search query from topic + situation
2. Perform semantic search filtered to CPSO sources
3. Search for both expectations and advice (no policy_level filter)
4. Retrieve top 15 results with reranking
5. Format results and categorize by policy_level:
   a. "expectation" → mandatory requirements
   b. "advice" → professional recommendations
6. If include_related=true:
   a. Extract topics from main results
   b. Search for related policies by topic
   c. Filter out duplicates
7. Calculate confidence score
8. Create summary of expectations vs advice found
9. Return policies, expectations, advice, and related documents
```

**Response Schema**:
```json
{
  "policies": [
    {
      "document_id": "cpso_prescribing_2023",
      "title": "Prescribing Drugs",
      "source_org": "cpso",
      "document_type": "policy",
      "effective_date": "2023-01-01",
      "topics": ["prescribing", "opioids"],
      "url": "https://cpso.on.ca/...",
      "is_superseded": false
    }
  ],
  "expectations": [
    {
      "point": "Prescribing Drugs: Mandatory expectation",
      "citations": [
        {
          "source": "Prescribing Drugs",
          "source_org": "cpso",
          "loc": "Policy",
          "url": "https://cpso.on.ca/..."
        }
      ],
      "policy_level": "expectation"
    }
  ],
  "advice": [
    {
      "point": "Opioid Management: Professional advice",
      "citations": [...],
      "policy_level": "advice"
    }
  ],
  "related": [],
  "confidence": 0.88,
  "summary": "CPSO Guidance for 'prescribing opioids': Found 2 mandatory expectation(s); Found 1 professional advice item(s)"
}
```

### 4. opa_program_lookup

**Purpose**: Ontario Health clinical programs information lookup

**Request Schema**:
```json
{
  "program": "breast cancer screening",
  "patient_age": 55,  // Optional
  "risk_factors": ["family history", "BRCA mutation"],  // Optional
  "info_needed": ["eligibility", "locations", "referral"]  // Optional
}
```

**Algorithm**:
```
1. Initialize Ontario Health Programs client (uses Claude + web_search)
2. Search for program information:
   a. Query Ontario Health domains (ontariohealth.ca, cancercareontario.ca, etc.)
   b. Extract eligibility criteria, services, locations
   c. Parse referral and access information
3. Structure response with:
   a. Eligibility (age criteria, risk factors)
   b. Services and procedures offered
   c. Access info (referral process, self-referral)
   d. Locations (if available)
   e. Resources and links
4. Generate patient-specific recommendations if age/risk factors provided
5. Create citations from web search results
6. If error, fallback to SQL database for basic screening info
7. Return comprehensive program information
```

**Response Schema**:
```json
{
  "program": "breast cancer screening",
  "eligibility": {
    "age_criteria": "Women aged 50-74 years",
    "risk_factors": "Family history increases screening frequency",
    "additional_notes": "Earlier screening for high-risk individuals"
  },
  "intervals": {
    "eligibility": "Women aged 50-74 years"
  },
  "procedures": [
    "Mammography",
    "Clinical breast exam",
    "Ultrasound for dense breast tissue"
  ],
  "followup": {
    "referral": "Self-referral available; physician referral recommended",
    "self_referral": "Call 1-800-668-9304"
  },
  "patient_specific": {
    "age": 55,
    "risk_factors": ["family history"],
    "recommendation": "Eligible for routine screening; consider annual screening due to family history"
  },
  "citations": [
    {
      "source": "Ontario Breast Screening Program",
      "source_org": "ontario_health",
      "loc": "Breast Cancer Screening Program",
      "url": "https://www.ontariohealth.ca/..."
    }
  ],
  "last_updated": "2024-10-03T12:00:00",
  "additional_info": {
    "locations": ["Assessment centres across Ontario"],
    "resources": ["Information hotline: 1-800-668-9304"],
    "overview": "Program overview text..."
  }
}
```

### 5. opa_ipac_guidance

**Purpose**: PHO infection prevention and control guidance

**Request Schema**:
```json
{
  "setting": "clinic",
  "topic": "hand hygiene",
  "pathogen": "COVID-19",  // Optional
  "include_checklists": true
}
```

**Algorithm**:
```
1. Build search query: "{setting} {topic} {pathogen}"
2. Perform semantic search filtered to PHO sources
3. Search document types: guideline, tool, policy
4. Retrieve top 15 results with reranking
5. Process results:
   a. Guidelines: sections with "requirement", "must", "standard"
   b. Procedures: sections with "procedure", "step", "process"
   c. Checklists: sections with "checklist", "list", "requirements"
6. If pathogen specified:
   a. Filter results for pathogen-specific guidance
   b. Extract pathogen-specific recommendations
7. Create citations from top 5 sources
8. Add standard PHO resource links
9. Return guidelines, procedures, checklists, and resources
```

**Response Schema**:
```json
{
  "setting": "clinic",
  "topic": "hand hygiene",
  "guidelines": [
    {
      "point": "Hand hygiene requirement text...",
      "citations": [
        {
          "source": "PHO Hand Hygiene Guide",
          "source_org": "pho",
          "loc": "Requirements Section",
          "url": "https://publichealthontario.ca/..."
        }
      ]
    }
  ],
  "procedures": [
    {
      "title": "Hand Hygiene Procedure",
      "steps": "Step-by-step instructions...",
      "source": "PHO Hand Hygiene Guide"
    }
  ],
  "checklists": [
    {
      "title": "Hand Hygiene Compliance Checklist",
      "items": "Checklist items...",
      "source": "PHO IPAC Tools"
    }
  ],
  "pathogen_specific": {
    "pathogen": "COVID-19",
    "guidance": "COVID-specific hand hygiene recommendations...",
    "source": "PHO COVID-19 IPAC Guidance"
  },
  "citations": [
    {
      "source": "PHO Hand Hygiene Guide",
      "source_org": "pho",
      "loc": "IPAC Guidance",
      "url": "https://publichealthontario.ca/..."
    }
  ],
  "resources": [
    {
      "title": "PHO IPAC Best Practices",
      "url": "https://www.publichealthontario.ca/ipac"
    },
    {
      "title": "Hand Hygiene Resources",
      "url": "https://www.publichealthontario.ca/hand-hygiene"
    }
  ]
}
```

### 6. opa_freshness_probe

**Purpose**: Check for guidance updates on a topic

**Request Schema**:
```json
{
  "topic": "COVID-19 vaccination",
  "current_date": "2024-10-03",  // Optional
  "sources": ["pho", "ontario_health"],  // Optional
  "check_web": true
}
```

**Algorithm**:
```
1. Query SQL database for current guidance on topic
2. Retrieve last_updated date from document metadata
3. Calculate age of guidance in days
4. Determine recommended action:
   a. > 2 years: "Recommend checking for updates"
   b. > 1 year: "Periodic review recommended"
   c. < 1 year: "Guidance is current"
5. If check_web=true:
   a. Generate web search URLs for major sources
   b. Simulate update check (in production, would actually search)
   c. If guidance is old, flag potential updates
6. Return current guidance, age, update status, and recommendations
```

**Response Schema**:
```json
{
  "topic": "COVID-19 vaccination",
  "current_guidance": {
    "document_id": "pho_covid_vax_2023",
    "title": "COVID-19 Vaccination Guidance",
    "source_org": "pho",
    "document_type": "guideline",
    "effective_date": "2023-09-01",
    "topics": [],
    "url": "https://publichealthontario.ca/...",
    "is_superseded": false
  },
  "last_updated": "2023-09-01T00:00:00",
  "updates_found": false,
  "recent_updates": [],
  "recommended_action": "Guidance is current (less than 1 year old)",
  "web_sources_checked": [
    "https://www.cpso.on.ca/search?q=COVID-19 vaccination",
    "https://www.ontariohealth.ca/search?q=COVID-19 vaccination"
  ]
}
```

### 7. opa_clinical_tools

**Purpose**: CEP clinical decision support tools lookup

**Request Schema**:
```json
{
  "condition": "dementia",  // Optional
  "tool_name": "Dementia Care Tool",  // Optional
  "category": "mental_health",  // Optional
  "feature_type": "algorithm",  // Optional: algorithm, calculator, checklist
  "include_sections": false
}
```

**Algorithm**:
```
1. Build search query from parameters:
   a. If condition: "clinical tool for {condition}"
   b. If tool_name: add tool name
   c. If category: "{category} tools"
   d. If feature_type: "{feature_type} calculator algorithm checklist"
2. Perform semantic search filtered to CEP sources
3. Search document type: clinical_tool
4. Retrieve top 20 results with reranking
5. Process each result:
   a. Extract tool metadata (name, URL, last_updated)
   b. Parse key features from text:
      - Assessment algorithms
      - Calculators
      - Checklists
   c. If include_sections=true, extract section summaries
   d. Create quick links to tool features
6. Return tools with navigation links and summaries
```

**Response Schema**:
```json
{
  "tools": [
    {
      "tool_id": "cep_dementia_tool_2024",
      "name": "Dementia Care Primary Care Tool",
      "url": "https://cep.health/dementia-tool",
      "last_updated": "2024-01-15",
      "category": "mental_health",
      "summary": "Comprehensive tool for dementia assessment...",
      "key_features": {
        "assessment_algorithm": {
          "available": true,
          "url": "https://cep.health/dementia-tool#assessment"
        },
        "calculator": {
          "available": true,
          "url": "https://cep.health/dementia-tool#calculator"
        },
        "checklist": {
          "available": true,
          "url": "https://cep.health/dementia-tool#checklist"
        }
      },
      "sections": [
        {
          "title": "Section 1",
          "summary": "Assessment overview...",
          "url": "https://cep.health/dementia-tool"
        }
      ],
      "quick_links": {
        "full_tool": "https://cep.health/dementia-tool",
        "pdf_version": null
      }
    }
  ],
  "total_tools": 5,
  "query_interpretation": "Searching CEP clinical tools for condition: dementia"
}
```

### 8. opa_quality_standards

**Purpose**: Ontario Health quality standards search

**Request Schema**:
```json
{
  "query": "heart failure management",
  "retrieve_all_statements": true,  // Get all statements for matched standard
  "statement_type": "all",  // "all", "overview", "statement"
  "top_k": 10
}
```

**Algorithm**:
```
1. Perform semantic search on quality standards corpus
2. If retrieve_all_statements=true:
   a. Collect candidate quality standard titles from results
   b. Use LLM (gpt-4o-mini) to match query to best standard title
   c. Search again for ALL statements from matched standard
   d. Filter results to specific standard
3. Process results:
   a. Extract document-level info (executive summary, scope, year)
   b. Parse quality statements:
      - Statement number and title
      - Brief statement text
      - Full text with background
      - Quality indicators
      - For patients section
      - For clinicians section
4. Sort statements by number
5. Create citations from source URLs
6. Calculate confidence (high if specific standard found)
7. Return standard with all statements and metadata
```

**Response Schema**:
```json
{
  "standard_title": "Heart Failure Care for People with Heart Failure",
  "statements": [
    {
      "statement_number": 1,
      "title": "Diagnosis and Assessment",
      "brief_statement": "People with suspected heart failure...",
      "full_text": "Complete statement with background...",
      "indicators": [
        "% of patients with documented LVEF",
        "% with natriuretic peptide testing"
      ],
      "for_patients": "What patients should know...",
      "for_clinicians": "Clinical guidance for implementation..."
    }
  ],
  "total_statements": 12,
  "executive_summary": "This quality standard covers...",
  "scope": "Applies to adults with heart failure...",
  "year": "2023",
  "citations": [
    {
      "source": "Heart Failure Quality Standard",
      "source_org": "ontario_health",
      "loc": "Quality Standard",
      "url": "https://www.ontariohealth.ca/..."
    }
  ],
  "confidence": 0.95
}
```

### 9. opa_choosing_wisely

**Purpose**: Choosing Wisely recommendations search

**Request Schema**:
```json
{
  "query": "unnecessary imaging low back pain",
  "specialty": "family medicine",  // Optional
  "all_specialty_recommendations": false,  // Get ALL recs for specialty
  "recommendation_type": "all",  // "all", "overview", "recommendation"
  "top_k": 5
}
```

**Algorithm**:
```
1. If specialty provided:
   a. Use LLM to map specialty to available Choosing Wisely specialties
   b. Log mapped specialty
2. Determine search strategy:
   a. If all_specialty_recommendations=true:
      - Search by specialty name
      - Retrieve up to 50 results
      - Skip reranking for complete retrieval
   b. If specialty but not all:
      - Semantic search within specialty
      - Use reranking
   c. Otherwise:
      - General semantic search across all specialties
3. Perform search on choosing_wisely corpus
4. If specialty mapped, filter results to that specialty
5. Process results:
   a. Extract specialty overview from specialty_overview chunks
   b. Parse recommendations from recommendation chunks:
      - Recommendation number and title
      - Description text
      - Specialty and organization
      - References
   c. Track recommendations by (specialty, number) to avoid duplicates
6. Determine primary specialty from result counts
7. Sort recommendations by number
8. Limit to top_k (by recommendation number, not count)
9. Create citations
10. Calculate confidence (high if specialty matched)
11. Return recommendations with specialty info
```

**Response Schema**:
```json
{
  "specialty_title": "Family Medicine",
  "recommendations": [
    {
      "recommendation_number": 1,
      "title": "Don't do imaging for low back pain",
      "description": "Avoid imaging for acute low back pain within first 6 weeks...",
      "specialty": "Family Medicine",
      "organization": "Canadian Family Physician Association",
      "references": [
        "Evidence-based guideline reference 1",
        "Systematic review reference 2"
      ]
    }
  ],
  "total_recommendations": 5,
  "specialty_overview": "Family Medicine focuses on comprehensive primary care...",
  "organization": "Canadian Family Physician Association",
  "last_updated": "2023-05-01",
  "citations": [
    {
      "source": "Family Medicine",
      "source_org": "choosing_wisely_canada",
      "loc": "Choosing Wisely Recommendations",
      "url": "https://choosingwiselycanada.org/..."
    }
  ],
  "confidence": 0.95,
  "query_interpretation": "Searching for unnecessary care recommendations in Family Medicine"
}
```

---

## Database Schemas 

### SQL Database: opa.db [Not In Use]

Located at: `data/dr_opa_agent/opa.db` (local) or `/app/data/dr_opa_agent/opa.db` (Railway)

#### Table: opa_documents
```sql
CREATE TABLE opa_documents (
    document_id TEXT PRIMARY KEY,              -- Unique document identifier
    source_org TEXT NOT NULL,                  -- cpso, ontario_health, cep, pho, moh
    source_url TEXT UNIQUE NOT NULL,           -- Original source URL
    title TEXT,                                -- Document title
    document_type TEXT,                        -- policy, guideline, tool, program, etc.
    effective_date TEXT,                       -- When document became effective
    updated_date TEXT,                         -- Last content update
    published_date TEXT,                       -- Publication date
    topics TEXT,                               -- JSON array of topic keywords
    policy_level TEXT,                         -- For CPSO: expectation/advice/general
    content_hash TEXT,                         -- For change detection
    metadata_json TEXT,                        -- Additional metadata as JSON
    is_superseded BOOLEAN DEFAULT 0,           -- Document has been replaced
    superseded_by TEXT,                        -- ID of superseding document
    superseded_date TEXT,                      -- When superseded
    ingested_at TEXT NOT NULL,                 -- Ingestion timestamp
    FOREIGN KEY (superseded_by) REFERENCES opa_documents(document_id)
);
-- Indexes: idx_documents_org, idx_documents_type, idx_documents_effective, idx_documents_superseded
-- **Record Count: 65** (Railway production)
```

#### Table: opa_sections
```sql
CREATE TABLE opa_sections (
    section_id TEXT PRIMARY KEY,               -- Unique section identifier
    document_id TEXT NOT NULL,                 -- Reference to parent document
    chunk_type TEXT NOT NULL,                  -- 'parent' or 'child'
    parent_id TEXT,                            -- For child chunks
    section_heading TEXT,                      -- Section heading/title
    section_text TEXT NOT NULL,                -- Section content
    section_idx INTEGER,                       -- Section position in document
    chunk_idx INTEGER,                         -- Chunk position if chunked
    embedding_model TEXT,                      -- text-embedding-3-small
    embedding_id TEXT,                         -- ChromaDB embedding ID
    metadata_json TEXT,                        -- Additional metadata as JSON
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES opa_documents(document_id),
    FOREIGN KEY (parent_id) REFERENCES opa_sections(section_id)
);
-- Indexes: idx_sections_document, idx_sections_type, idx_sections_parent
-- **Record Count: 373** (Railway production)
```

#### Table: ingestion_log
```sql
CREATE TABLE ingestion_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,                 -- Source organization
    source_file TEXT NOT NULL,                 -- Source file name
    status TEXT NOT NULL,                      -- success, error, partial
    started_at TEXT,                           -- Start timestamp
    completed_at TEXT,                         -- Completion timestamp
    records_processed INTEGER DEFAULT 0,       -- Number of records ingested
    records_failed INTEGER DEFAULT 0,          -- Number of failures
    error_message TEXT                         -- Error details if failed
);
-- **Record Count: 68** (Railway production)
```

### Vector Database: ChromaDB Collections

Located at: `data/dr_opa_agent/chroma` (local) or `/app/data/chroma` (Railway)

#### Collection: opa_cpso_corpus
- **Record Count**: 366 embeddings
- **Embedding Model**: text-embedding-3-small (1536 dimensions)
- **Purpose**: CPSO policies, expectations, and professional advice

**Record Structure**:
```json
{
  "id": "cpso_policy_section_001",
  "document": "Text chunk from CPSO policy document...",
  "embedding": [0.015, -0.023, ...],  // 1536-dim vector
  "metadata": {
    "chunk_type": "parent",
    "source_url": "https://cpso.on.ca/policies/...",
    "document_id": "cpso_prescribing_2023",
    "source_org": "cpso",
    "parent_id": null,
    "document_type": "policy",
    "topics": ["prescribing", "opioids"],
    "section_heading": "Opioid Prescribing Requirements",
    "effective_date": "2023-01-01",
    "section_id": "cpso_policy_section_001"
  }
}
```

**Metadata Fields**:
- `chunk_type`: parent, child
- `source_url`: URL to original policy
- `document_id`: Unique document identifier
- `source_org`: Always "cpso"
- `parent_id`: For child chunks, reference to parent
- `document_type`: policy, advice, guideline
- `topics`: List of topic keywords
- `section_heading`: Section title
- `effective_date`: When policy became effective
- `section_id`: Unique section identifier

#### Collection: opa_cep_corpus
- **Record Count**: 57 embeddings
- **Embedding Model**: text-embedding-3-small (1536 dimensions)
- **Purpose**: CEP clinical decision support tools

**Record Structure**:
```json
{
  "id": "cep_tool_dementia_001",
  "document": "Text from CEP clinical tool...",
  "embedding": [0.008, -0.041, ...],
  "metadata": {
    "document_type": "clinical_tool",
    "tool_category": "mental_health",
    "chunk_role": "tool_overview",
    "source_org": "cep",
    "source_url": "https://cep.health/dementia-tool",
    "has_navigation": true
  }
}
```

**Metadata Fields**:
- `document_type`: clinical_tool
- `tool_category`: mental_health, chronic_disease, cardiovascular, etc.
- `chunk_role`: tool_overview, algorithm, calculator, checklist
- `source_org`: Always "cep"
- `source_url`: Direct link to tool
- `has_navigation`: Boolean, tool has navigation elements

#### Collection: opa_pho_corpus
- **Record Count**: 132 embeddings
- **Embedding Model**: text-embedding-3-small (1536 dimensions)
- **Purpose**: PHO infection prevention and control guidance

**Record Structure**:
```json
{
  "id": "pho_ipac_hand_hygiene_001",
  "document": "Text from PHO IPAC guidance...",
  "embedding": [-0.012, 0.035, ...],
  "metadata": {
    "revision_date": "2023-06-15",
    "organization_full": "Public Health Ontario",
    "topics": ["hand_hygiene", "infection_control"],
    "chunk_type": "parent",
    "document_id": "pho_hand_hygiene_2023",
    "published_date": "2023-06-01",
    "clinical_setting": "clinic",
    "practice_area": "ipac",
    "document_type": "guideline",
    "section_heading": "Hand Hygiene Requirements"
  }
}
```

**Metadata Fields**:
- `revision_date`: Last revision date
- `organization_full`: "Public Health Ontario"
- `topics`: List of IPAC topics
- `chunk_type`: parent, child
- `document_id`: Unique document identifier
- `published_date`: Publication date
- `clinical_setting`: clinic, hospital, community, ltc
- `practice_area`: ipac, surveillance, outbreak
- `document_type`: guideline, tool, policy
- `section_heading`: Section title

#### Collection: opa_quality_standards_corpus
- **Record Count**: 340 embeddings
- **Embedding Model**: text-embedding-3-small (1536 dimensions)
- **Purpose**: Ontario Health quality standards and statements

**Record Structure**:
```json
{
  "id": "qs_heart_failure_stmt_001",
  "document": "Quality statement text...",
  "embedding": [0.019, -0.028, ...],
  "metadata": {
    "source": "Ontario Health",
    "num_statements": 12,
    "statement_titles": ["Diagnosis", "Assessment", "Treatment"],
    "title": "Heart Failure Care",
    "json_path": "data/quality_standards/heart_failure.json",
    "chunk_type": "statement",
    "source_url": "https://www.ontariohealth.ca/standards/...",
    "ingested_at": "2024-10-01T12:00:00",
    "doc_type": "quality_standard",
    "source_file": "heart_failure_qs.json"
  }
}
```

**Metadata Fields**:
- `source`: "Ontario Health"
- `num_statements`: Total statements in standard
- `statement_titles`: List of all statement titles
- `title`: Quality standard title
- `json_path`: Source file path
- `chunk_type`: document, statement
- `source_url`: URL to quality standard
- `ingested_at`: Ingestion timestamp
- `doc_type`: quality_standard
- `source_file`: Source filename

#### Collection: opa_choosing_wisely_corpus
- **Record Count**: 544 embeddings
- **Embedding Model**: text-embedding-3-small (1536 dimensions)
- **Purpose**: Choosing Wisely recommendations

**Record Structure**:
```json
{
  "id": "cw_family_med_rec_001",
  "document": "Recommendation text...",
  "embedding": [-0.006, 0.042, ...],
  "metadata": {
    "has_methodology": true,
    "specialty": "Family Medicine",
    "organization": "Canadian Family Physician Association",
    "source": "Choosing Wisely Canada",
    "recommendation_count": 5,
    "ingested_at": "2024-09-15T10:00:00",
    "source_url": "https://choosingwiselycanada.org/...",
    "doc_type": "choosing_wisely_recommendation",
    "text_length": 1250,
    "source_org": "choosing_wisely_canada"
  }
}
```

**Metadata Fields**:
- `has_methodology`: Boolean, includes methodology section
- `specialty`: Medical specialty (e.g., "Family Medicine", "Cardiology")
- `organization`: Specialty organization
- `source`: "Choosing Wisely Canada"
- `recommendation_count`: Number of recommendations for specialty
- `ingested_at`: Ingestion timestamp
- `source_url`: URL to specialty recommendations
- `doc_type`: choosing_wisely_overview, choosing_wisely_recommendation
- `text_length`: Length of text chunk
- `source_org`: "choosing_wisely_canada"

---

## Usage Examples

### Example 1: CPSO Policy Check
```python
# Query
"What are the CPSO expectations for prescribing opioids?"

# Tool: opa_policy_check
request = {
  "topic": "prescribing opioids",
  "situation": "chronic pain",
  "include_related": true
}

# Response includes:
# - Mandatory expectations for opioid prescribing
# - Professional advice recommendations
# - Related prescribing policies
# - CPSO policy citations with URLs
```

### Example 2: Clinical Program Inquiry
```python
# Query
"Is a 55-year-old woman with family history eligible for breast cancer screening?"

# Tool: opa_program_lookup
request = {
  "program": "breast cancer screening",
  "patient_age": 55,
  "risk_factors": ["family history"],
  "info_needed": ["eligibility", "referral"]
}

# Response includes:
# - Eligibility criteria (age 50-74)
# - Enhanced screening for family history
# - Self-referral and referral pathways
# - Patient-specific recommendations
# - Ontario Health program citations
```

### Example 3: Quality Standards Search
```python
# Query
"What are the Ontario Health quality statements for heart failure?"

# Tool: opa_quality_standards
request = {
  "query": "heart failure",
  "retrieve_all_statements": true,
  "statement_type": "all",
  "top_k": 15
}

# Response includes:
# - All 12 quality statements for Heart Failure standard
# - Executive summary and scope
# - Quality indicators for each statement
# - For patients and for clinicians guidance
# - Ontario Health citations
```

### Example 4: Choosing Wisely Recommendations
```python
# Query
"What does Choosing Wisely say about imaging for low back pain?"

# Tool: opa_choosing_wisely
request = {
  "query": "imaging low back pain",
  "specialty": "family medicine",
  "all_specialty_recommendations": false,
  "top_k": 5
}

# Response includes:
# - Recommendations to avoid unnecessary imaging
# - Evidence and references
# - Specialty: Family Medicine
# - Organization: Canadian Family Physician Association
# - Choosing Wisely Canada citations
```

---

## Data Sources

- **CPSO Policies**: College of Physicians and Surgeons of Ontario regulatory policies
- **Ontario Health Programs**: Clinical programs, screening guidelines, care pathways
- **CEP Tools**: Centre for Effective Practice clinical decision support tools
- **PHO Guidance**: Public Health Ontario IPAC and public health guidance
- **Ontario Health Quality Standards**: Evidence-based quality standards for conditions
- **Choosing Wisely Canada**: Recommendations to reduce unnecessary tests and procedures
- **Last Updated**: October 2025
