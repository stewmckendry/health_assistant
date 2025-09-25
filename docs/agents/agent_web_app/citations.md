# Agent Citation System

## Overview

A standardized citation system for all clinical AI agents that ensures transparency, trust, and verifiability of medical information. This system provides structured citations with trust indicators, direct source links, and proper attribution for all agent responses.

## Architecture

### Standard Citation Model

All agents use a unified citation structure:

```typescript
interface Citation {
  id: string;              // Unique citation identifier
  title: string;           // "CPSO Virtual Care Policy"
  source: string;          // Organization or publication name
  source_type: string;     // "policy" | "guideline" | "journal" | "website"
  url: string;             // Direct clickable URL
  domain: string;          // "cpso.on.ca" 
  is_trusted: boolean;     // True if in 97 trusted domains
  access_date: string;     // ISO timestamp when retrieved
  snippet?: string;        // Relevant excerpt (optional)
  relevance_score: float;  // 0.0-1.0 relevance to query
}

interface Highlight {
  point: string;           // Key information point
  citations: Citation[];   // Supporting citations
  confidence: float;       // Confidence in this point
}
```

### Enhanced Agent Response Schema

All agents return this standardized format:

```typescript
interface AgentResponse {
  response: string;           // Main text response
  tool_calls: ToolCall[];     // MCP tools executed
  tools_used: string[];       // Tool names for debugging
  citations: Citation[];      // Structured citations
  highlights: Highlight[];    // Key points with citations
  confidence: float;          // Overall response confidence (0.0-1.0)
  error?: string;             // Any errors encountered
}
```

## Trust & Verification System

### Trust Levels

Citations are classified into trust levels based on the 97 trusted medical domains:

#### Level 1: Verified Trusted Sources
- **Criteria**: Domain matches `domains.yaml` trusted list
- **Indicator**: Green shield icon, "Trusted Source" badge
- **Examples**: `cpso.on.ca`, `mayoclinic.org`, `nejm.org`
- **Display**: Prominent placement, full metadata shown

#### Level 2: Unverified Sources  
- **Criteria**: Domain not in trusted list
- **Indicator**: Gray icon, "External Source" badge
- **Examples**: General websites, blogs, forums
- **Display**: Lower in list, warning about verification needed

### Domain Validation

The system uses the comprehensive trusted domains list from `src/config/domains.yaml`:

```yaml
trusted_domains:
  # Canadian Healthcare Authorities (24 domains)
  - ontario.ca
  - cpso.on.ca
  - publichealthontario.ca
  
  # US Medical Centers (18 domains)  
  - mayoclinic.org
  - clevelandclinic.org
  
  # Medical Journals (15 domains)
  - nejm.org
  - thelancet.com
  
  # Global Health Organizations (12 domains)
  - who.int
  - cdc.gov
  
  # And 28 more categories...
```

## Agent-Specific Implementation

### Dr. OPA Agent Citations

Dr. OPA leverages existing MCP tool citation models:

```python
# Enhanced Dr. OPA response
{
  "response": "According to CPSO policy...",
  "citations": [
    {
      "id": "cpso_virtual_care_2024",
      "title": "CPSO Virtual Care Policy", 
      "source": "College of Physicians and Surgeons of Ontario",
      "source_type": "policy",
      "url": "https://www.cpso.on.ca/en/Physicians/Policies-Guidance/Policies/Virtual-Care",
      "domain": "cpso.on.ca",
      "is_trusted": true,
      "access_date": "2024-01-15T10:30:00Z",
      "snippet": "Physicians must obtain appropriate consent...",
      "relevance_score": 0.95
    }
  ],
  "highlights": [
    {
      "point": "Consent is required for virtual care",
      "citations": ["cpso_virtual_care_2024"], 
      "confidence": 0.98
    }
  ]
}
```

### Agent 97 Citations

Agent 97 extracts citations from web search results:

```python
# Enhanced Agent 97 response  
{
  "response": "Diabetes symptoms include...",
  "citations": [
    {
      "id": "mayo_diabetes_symptoms",
      "title": "Diabetes - Symptoms and causes",
      "source": "Mayo Clinic", 
      "source_type": "website",
      "url": "https://www.mayoclinic.org/diseases-conditions/diabetes/symptoms-causes/syc-20371444",
      "domain": "mayoclinic.org",
      "is_trusted": true,
      "access_date": "2024-01-15T10:45:00Z",
      "snippet": "Increased thirst, frequent urination...",
      "relevance_score": 0.92
    }
  ],
  "highlights": [
    {
      "point": "Common diabetes symptoms are increased thirst and frequent urination",
      "citations": ["mayo_diabetes_symptoms"],
      "confidence": 0.89
    }
  ]
}
```

## Web UI Implementation

### Citation Display Components

#### CitationList Component
- Groups citations by domain for easy scanning
- Shows trust indicators (green shield for trusted)
- Displays source metadata (organization, type)
- Provides clickable links to original sources
- Implements deduplication by URL

#### Citation Trust Indicators
```tsx
// Trust level styling
{citation.is_trusted ? (
  <Badge className="bg-green-100 text-green-800">
    <Shield className="h-3 w-3 mr-1" />
    Trusted Source
  </Badge>
) : (
  <Badge variant="outline" className="text-gray-600">
    <AlertTriangle className="h-3 w-3 mr-1" />
    External Source
  </Badge>
)}
```

#### Real-time Citation Updates
As agents stream responses, citations are:
1. Extracted from tool results
2. Validated against trusted domains
3. Deduplicated by URL
4. Added to live citation list
5. Grouped and sorted by trust level

### Citation Deduplication

Citations are deduplicated using multiple strategies:

```typescript
function createDeduplicationKey(citation: Citation): string {
  // Primary: Use URL if available
  if (citation.url && citation.url.startsWith('http')) {
    return normalizeUrl(citation.url);
  }
  
  // Fallback: Use title + domain
  return `${normalizeText(citation.title)}_${citation.domain}`;
}

function normalizeUrl(url: string): string {
  const parsed = new URL(url);
  // Remove query params and fragments
  return `${parsed.hostname}${parsed.pathname}`.toLowerCase();
}
```

## Streaming Citation Events

Citations are delivered via Server-Sent Events during streaming:

```typescript
// Citation streaming event
{
  type: 'citation',
  data: {
    id: 'citation_abc123',
    title: 'Mayo Clinic - Diabetes',
    source: 'Mayo Clinic',
    url: 'https://www.mayoclinic.org/...',
    domain: 'mayoclinic.org',
    is_trusted: true,
    // ... rest of citation data
  },
  timestamp: '2024-01-15T10:30:00Z'
}
```

## Implementation Guidelines

### For Agent Developers

When adding citation support to a new agent:

1. **Extract citations from MCP tools**: Modify tool responses to include structured citation data
2. **Use trusted domains**: Validate against `domains.yaml` 
3. **Include relevance scoring**: Rate how relevant each citation is to the query
4. **Provide direct URLs**: Ensure all citations have clickable links
5. **Add highlights**: Identify key points and their supporting citations

### For MCP Tool Developers

When building tools that should provide citations:

```python
def my_search_tool(query: str) -> dict:
    results = search_knowledge_base(query)
    
    citations = []
    for result in results:
        citations.append({
            'id': f"citation_{result.id}",
            'title': result.title,
            'source': result.organization,
            'source_type': result.document_type,
            'url': result.source_url,
            'domain': extract_domain(result.source_url),
            'is_trusted': is_trusted_domain(extract_domain(result.source_url)),
            'access_date': datetime.now().isoformat(),
            'snippet': result.excerpt,
            'relevance_score': result.score
        })
    
    return {
        'content': format_response(results),
        'citations': citations,
        'highlights': extract_key_points(results, citations)
    }
```

## Quality Assurance

### Citation Validation

All citations undergo validation:
- **URL accessibility**: Links are checked periodically
- **Domain verification**: Matched against trusted domains list
- **Duplicate detection**: Same sources consolidated
- **Freshness checking**: Policy documents checked for updates

### Trust Metrics

System tracks citation quality metrics:
- **Trust ratio**: % of citations from trusted sources
- **Link health**: % of citations with working URLs  
- **User feedback**: User reports on citation accuracy
- **Coverage**: % of responses that include citations

## Troubleshooting

### Common Issues

**No citations returned**
- Check if MCP tools are returning citation data
- Verify tool results include structured citations
- Ensure citation extraction logic is working

**Citations not marked as trusted**
- Verify domain is in `domains.yaml`
- Check domain normalization (www. removal)
- Confirm trusted domains loader is working

**Duplicate citations**  
- Check deduplication logic
- Verify URL normalization
- Consider title-based deduplication

**Broken citation links**
- Implement link checking
- Add fallback to archived versions
- Show link status in UI

## Future Enhancements

### Version 2 Features
- **Citation freshness indicators**: Show when policies were last updated
- **Citation clustering**: Group related citations by topic  
- **Citation export**: Allow users to export citation lists
- **Citation history**: Track which citations were most useful

### Advanced Trust Features
- **Peer review indicators**: Show if sources are peer-reviewed
- **Evidence levels**: Grade strength of evidence (A, B, C)
- **Conflict detection**: Flag when sources disagree
- **Update notifications**: Alert when cited policies change

## Conclusion

This standardized citation system provides:
- **Trust**: Clear indicators of source reliability
- **Transparency**: Full source attribution and links
- **Consistency**: Same format across all agents  
- **Extensibility**: Easy to add to new agents
- **Verification**: Users can check original sources

The system builds user confidence by making the knowledge sources of AI responses transparent and verifiable, which is critical for clinical decision support tools.