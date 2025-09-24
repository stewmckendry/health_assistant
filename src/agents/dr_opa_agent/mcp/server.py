"""
FastMCP server for Dr. OPA practice guidance tools.
Provides 6 tools for Ontario practice advice queries.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastmcp import FastMCP

# Import retrieval clients
from .retrieval import SQLClient, VectorClient

# Import utilities
from .utils import calculate_confidence, resolve_conflicts
from .utils.confidence import OPAConfidenceScorer
from .utils.conflicts import OPAConflictResolver

# Import models
from .models.request import (
    SearchSectionsRequest,
    GetSectionRequest,
    PolicyCheckRequest,
    ProgramLookupRequest,
    IPACGuidanceRequest,
    FreshnessProbeRequest
)

from .models.response import (
    SearchSectionsResponse,
    GetSectionResponse,
    PolicyCheckResponse,
    ProgramLookupResponse,
    IPACGuidanceResponse,
    FreshnessProbeResponse,
    Section,
    Document,
    Citation,
    Highlight,
    Conflict,
    Update
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("dr-opa-server")

# Initialize shared clients (lazy loading)
_sql_client = None
_vector_client = None


def get_sql_client() -> SQLClient:
    """Get or create SQL client singleton."""
    global _sql_client
    if _sql_client is None:
        _sql_client = SQLClient()
    return _sql_client


def get_vector_client() -> VectorClient:
    """Get or create vector client singleton."""
    global _vector_client
    if _vector_client is None:
        _vector_client = VectorClient()
    return _vector_client


@mcp.tool(name="opa.search_sections", description="Hybrid search across OPA knowledge corpus")
async def search_sections_handler(
    query: str,
    sources: Optional[List[str]] = None,
    doc_types: Optional[List[str]] = None,
    topics: Optional[List[str]] = None,
    date_range: Optional[Dict[str, str]] = None,
    top_k: int = 10,
    include_superseded: bool = False
) -> Dict[str, Any]:
    """
    Hybrid search across OPA practice guidance corpus.
    Combines SQL full-text search and vector semantic search.
    
    Args:
        query: Clinical query or practice question
        sources: Specific sources to search
        doc_types: Document types to include
        topics: Topics to filter by
        date_range: Date range filter
        top_k: Number of results
        include_superseded: Include superseded documents
    
    Returns:
        Matching sections with documents, highlights, and confidence
    """
    logger.info(f"opa.search_sections called with query: {query[:100]}...")
    
    sql_client = get_sql_client()
    vector_client = get_vector_client()
    
    # Run SQL and vector searches in parallel
    sql_task = sql_client.search_sections(
        query=query,
        sources=sources,
        doc_types=doc_types,
        topics=topics,
        limit=top_k,
        include_superseded=include_superseded
    )
    
    vector_task = vector_client.search_sections(
        query=query,
        sources=sources,
        doc_types=doc_types,
        topics=topics,
        n_results=top_k,
        include_superseded=include_superseded
    )
    
    sql_results, vector_results = await asyncio.gather(sql_task, vector_task)
    
    # Resolve conflicts and merge results
    resolved_data, conflicts = resolve_conflicts(sql_results, vector_results)
    
    # Convert to response format
    sections = []
    documents_map = {}
    
    for data in resolved_data.values():
        # Create section
        section = Section(
            section_id=data.get('section_id', data.get('chunk_id', '')),
            document_id=data.get('document_id', ''),
            heading=data.get('section_heading', ''),
            text=data.get('section_text', data.get('text', ''))[:500],  # Truncate for response
            chunk_type=data.get('chunk_type', 'unknown'),
            relevance_score=data.get('similarity_score', 0.8),
            metadata=data.get('metadata', {})
        )
        sections.append(section)
        
        # Track unique documents
        doc_id = data.get('document_id')
        if doc_id and doc_id not in documents_map:
            documents_map[doc_id] = Document(
                document_id=doc_id,
                title=data.get('document_title', data.get('title', '')),
                source_org=data.get('source_org', ''),
                document_type=data.get('document_type', ''),
                effective_date=data.get('effective_date'),
                topics=data.get('topics', []),
                url=data.get('source_url'),
                is_superseded=data.get('is_superseded', False)
            )
    
    # Create highlights from top results
    highlights = []
    for section in sections[:3]:
        highlight = Highlight(
            point=section.text[:200] + "...",
            citations=[Citation(
                source=section.metadata.get('title', 'Unknown'),
                source_org=section.metadata.get('source_org', ''),
                loc=section.heading,
                url=section.metadata.get('source_url')
            )]
        )
        highlights.append(highlight)
    
    # Calculate confidence
    confidence = OPAConfidenceScorer.calculate(
        sql_hits=len(sql_results),
        vector_matches=len(vector_results),
        sources=sources,
        doc_types=doc_types,
        has_conflict=len(conflicts) > 0
    )
    
    # Create response
    response = SearchSectionsResponse(
        sections=sections[:top_k],
        documents=list(documents_map.values()),
        provenance=['sql'] if sql_results else [] + ['vector'] if vector_results else [],
        confidence=confidence,
        highlights=highlights,
        conflicts=[Conflict(
            field=c.get('fields', ['unknown'])[0],
            source1={'type': 'sql', 'value': str(c.get('sql_source', {}))[:100]},
            source2={'type': 'vector', 'value': str(c.get('vector_source', {}))[:100]},
            resolution=c.get('resolution', 'SQL preferred')
        ) for c in conflicts[:3]],
        query_interpretation=f"Searching for: {query}"
    )
    
    return response.dict()


@mcp.tool(name="opa.get_section", description="Retrieve complete section details by ID")
async def get_section_handler(
    section_id: str,
    include_children: bool = True,
    include_context: bool = True
) -> Dict[str, Any]:
    """
    Retrieve complete section details by ID.
    
    Args:
        section_id: Section ID to retrieve
        include_children: Include child chunks
        include_context: Include surrounding sections
    
    Returns:
        Section with full content, document metadata, and context
    """
    logger.info(f"opa.get_section called for: {section_id}")
    
    sql_client = get_sql_client()
    
    # Get section with optional children and context
    section_data = await sql_client.get_section_by_id(
        section_id=section_id,
        include_children=include_children,
        include_context=include_context
    )
    
    if not section_data:
        return {
            "error": f"Section {section_id} not found",
            "section": None
        }
    
    # Create section object
    section = Section(
        section_id=section_data.get('section_id'),
        document_id=section_data.get('document_id'),
        heading=section_data.get('section_heading', ''),
        text=section_data.get('section_text', ''),
        chunk_type=section_data.get('chunk_type', 'unknown'),
        relevance_score=1.0,  # Direct retrieval
        metadata=section_data.get('metadata_json', {})
    )
    
    # Create document object
    document = Document(
        document_id=section_data.get('document_id'),
        title=section_data.get('document_title', ''),
        source_org=section_data.get('source_org', ''),
        document_type=section_data.get('document_type', ''),
        effective_date=section_data.get('effective_date'),
        topics=section_data.get('topics', []),
        url=section_data.get('source_url'),
        is_superseded=False
    )
    
    # Process children if included
    children = []
    if include_children and section_data.get('children'):
        for child_data in section_data['children']:
            children.append(Section(
                section_id=child_data.get('section_id'),
                document_id=child_data.get('document_id'),
                heading=child_data.get('section_heading', ''),
                text=child_data.get('section_text', ''),
                chunk_type='child',
                relevance_score=1.0,
                metadata={}
            ))
    
    # Process context if included
    context = []
    if include_context and section_data.get('context'):
        for ctx_data in section_data['context']:
            context.append(Section(
                section_id=ctx_data.get('section_id'),
                document_id=section_data.get('document_id'),
                heading=ctx_data.get('section_heading', ''),
                text='',  # Don't include full text for context
                chunk_type='context',
                relevance_score=0.8,
                metadata={'section_idx': ctx_data.get('section_idx')}
            ))
    
    # Create citations
    citations = [Citation(
        source=document.title,
        source_org=document.source_org,
        loc=section.heading,
        url=document.url
    )]
    
    # Create response
    response = GetSectionResponse(
        section=section,
        document=document,
        children=children,
        context=context,
        citations=citations
    )
    
    return response.dict()


@mcp.tool(name="opa.policy_check", description="CPSO-specific policy and advice retrieval")
async def policy_check_handler(
    topic: str,
    situation: Optional[str] = None,
    policy_level: str = "both",
    include_related: bool = True
) -> Dict[str, Any]:
    """
    CPSO-specific policy and advice retrieval.
    
    Args:
        topic: Clinical topic or practice area
        situation: Specific situation or context
        policy_level: 'expectation', 'advice', or 'both'
        include_related: Include related policies
    
    Returns:
        Relevant policies, expectations, advice with confidence
    """
    logger.info(f"opa.policy_check called for topic: {topic}")
    
    sql_client = get_sql_client()
    
    # Search for CPSO policies
    search_query = f"{topic} {situation}" if situation else topic
    
    policies_data = await sql_client.search_policies(
        topic=search_query,
        policy_level=policy_level if policy_level != "both" else None,
        include_related=include_related
    )
    
    # Organize results
    policies = []
    expectations = []
    advice_items = []
    
    for policy_data in policies_data:
        # Create document
        doc = Document(
            document_id=policy_data.get('document_id'),
            title=policy_data.get('title'),
            source_org='cpso',
            document_type=policy_data.get('document_type'),
            effective_date=policy_data.get('effective_date'),
            topics=policy_data.get('topics', []),
            url=policy_data.get('source_url'),
            is_superseded=False
        )
        policies.append(doc)
        
        # Categorize by policy level
        level = policy_data.get('policy_level')
        if level == 'expectation':
            expectations.append(Highlight(
                point=f"{policy_data.get('title')}: Mandatory expectation",
                citations=[Citation(
                    source=policy_data.get('title'),
                    source_org='cpso',
                    loc='Policy',
                    url=policy_data.get('source_url')
                )],
                policy_level='expectation'
            ))
        elif level == 'advice':
            advice_items.append(Highlight(
                point=f"{policy_data.get('title')}: Professional advice",
                citations=[Citation(
                    source=policy_data.get('title'),
                    source_org='cpso',
                    loc='Advice',
                    url=policy_data.get('source_url')
                )],
                policy_level='advice'
            ))
    
    # Find related documents if requested
    related = []
    if include_related and policies:
        # Get topics from main results
        all_topics = set()
        for p in policies:
            all_topics.update(p.topics)
        
        # Search for related by topics
        for related_topic in list(all_topics)[:3]:  # Limit to 3 topics
            related_data = await sql_client.search_policies(
                topic=related_topic,
                policy_level=None,
                include_related=False
            )
            
            for r_data in related_data[:2]:  # Limit to 2 per topic
                if r_data.get('document_id') not in [p.document_id for p in policies]:
                    related.append(Document(
                        document_id=r_data.get('document_id'),
                        title=r_data.get('title'),
                        source_org='cpso',
                        document_type=r_data.get('document_type'),
                        effective_date=r_data.get('effective_date'),
                        topics=r_data.get('topics', []),
                        url=r_data.get('source_url'),
                        is_superseded=False
                    ))
    
    # Calculate confidence
    confidence = OPAConfidenceScorer.calculate(
        sql_hits=len(policies_data),
        vector_matches=0,
        sources=['cpso'],
        doc_types=['policy', 'advice'],
        has_conflict=False
    )
    
    # Create summary
    summary_parts = []
    if expectations:
        summary_parts.append(f"Found {len(expectations)} mandatory expectation(s)")
    if advice_items:
        summary_parts.append(f"Found {len(advice_items)} professional advice item(s)")
    if not summary_parts:
        summary_parts.append("No specific CPSO guidance found for this topic")
    
    summary = f"CPSO Guidance for '{topic}': " + "; ".join(summary_parts)
    
    # Create response
    response = PolicyCheckResponse(
        policies=policies,
        expectations=expectations,
        advice=advice_items,
        related=related[:5],  # Limit related to 5
        confidence=confidence,
        summary=summary
    )
    
    return response.dict()


@mcp.tool(name="opa.program_lookup", description="Ontario Health screening program information")
async def program_lookup_handler(
    program: str,
    patient_age: Optional[int] = None,
    risk_factors: Optional[List[str]] = None,
    info_needed: List[str] = None
) -> Dict[str, Any]:
    """
    Ontario Health screening program information lookup.
    
    Args:
        program: Screening program (breast, cervical, colorectal, lung, hpv)
        patient_age: Patient age for eligibility
        risk_factors: Patient risk factors
        info_needed: Information types to retrieve
    
    Returns:
        Program eligibility, intervals, procedures, and patient-specific info
    """
    logger.info(f"opa.program_lookup called for program: {program}")
    
    sql_client = get_sql_client()
    
    if info_needed is None:
        info_needed = ["eligibility", "intervals"]
    
    # Get program information from database
    program_data = await sql_client.get_program_info(program)
    
    if not program_data:
        return {
            "error": f"No information found for {program} screening program",
            "program": program
        }
    
    # Parse program data into structured format
    eligibility = {}
    intervals = {}
    procedures = []
    followup = {}
    
    # Extract information from sections
    for section in program_data.get('sections', []):
        text = section.get('text', '').lower()
        heading = section.get('heading', '').lower()
        
        # Extract eligibility
        if 'eligibility' in info_needed and ('eligib' in heading or 'who' in heading):
            if 'age' in text:
                # Simple extraction - would be more sophisticated in production
                if '50' in text and '74' in text:
                    eligibility['age_range'] = '50-74'
                elif '21' in text and '69' in text:
                    eligibility['age_range'] = '21-69'
            
            if 'average risk' in text:
                eligibility['risk_level'] = 'average'
            elif 'high risk' in text:
                eligibility['risk_level'] = 'high'
        
        # Extract intervals
        if 'intervals' in info_needed and ('interval' in heading or 'how often' in heading):
            if 'every 2 years' in text or 'biennial' in text:
                intervals['standard'] = 'Every 2 years'
            elif 'every 3 years' in text:
                intervals['standard'] = 'Every 3 years'
            elif 'annual' in text or 'every year' in text:
                intervals['high_risk'] = 'Annual'
        
        # Extract procedures
        if 'procedures' in info_needed and ('test' in heading or 'procedure' in heading):
            if 'mammograph' in text:
                procedures.append('Mammography')
            if 'colonoscop' in text:
                procedures.append('Colonoscopy')
            if 'fit' in text or 'fecal' in text:
                procedures.append('FIT (Fecal Immunochemical Test)')
            if 'pap' in text:
                procedures.append('Pap test')
            if 'hpv' in text:
                procedures.append('HPV testing')
        
        # Extract follow-up
        if 'followup' in info_needed and ('follow' in heading or 'result' in heading):
            if 'abnormal' in text:
                followup['abnormal'] = 'Referral for further assessment'
            if 'positive' in text:
                followup['positive'] = 'Diagnostic testing recommended'
    
    # Patient-specific recommendations
    patient_specific = None
    if patient_age:
        patient_specific = {}
        
        # Check eligibility based on age
        if program == 'breast' and 50 <= patient_age <= 74:
            patient_specific['eligible'] = True
            patient_specific['recommendation'] = 'Eligible for routine mammography screening'
        elif program == 'cervical' and 21 <= patient_age <= 69:
            patient_specific['eligible'] = True
            patient_specific['recommendation'] = 'Eligible for cervical screening'
        elif program == 'colorectal' and 50 <= patient_age <= 74:
            patient_specific['eligible'] = True
            patient_specific['recommendation'] = 'Eligible for colorectal screening'
        else:
            patient_specific['eligible'] = False
            patient_specific['recommendation'] = 'Outside standard screening age range'
        
        # Adjust for risk factors
        if risk_factors:
            if 'family_history' in risk_factors:
                patient_specific['risk_level'] = 'increased'
                patient_specific['recommendation'] += ' - Consider earlier/more frequent screening due to family history'
    
    # Create citations
    citations = []
    for doc_id, doc_info in program_data.get('documents', {}).items():
        citations.append(Citation(
            source=doc_info.get('title', ''),
            source_org='ontario_health',
            loc=f"{program.capitalize()} Screening Program",
            url=doc_info.get('url')
        ))
    
    # Get last updated date
    last_updated = None
    for doc_info in program_data.get('documents', {}).values():
        if doc_info.get('effective_date'):
            last_updated = doc_info['effective_date']
            break
    
    # Create response
    response = ProgramLookupResponse(
        program=program,
        eligibility=eligibility,
        intervals=intervals,
        procedures=procedures,
        followup=followup,
        patient_specific=patient_specific,
        citations=citations[:3],  # Limit citations
        last_updated=last_updated
    )
    
    return response.dict()


@mcp.tool(name="opa.ipac_guidance", description="PHO infection prevention and control guidance")
async def ipac_guidance_handler(
    setting: str,
    topic: str,
    pathogen: Optional[str] = None,
    include_checklists: bool = True
) -> Dict[str, Any]:
    """
    PHO infection prevention and control guidance.
    
    Args:
        setting: Healthcare setting (clinic, hospital, community, ltc)
        topic: IPAC topic (hand hygiene, PPE, sterilization, etc.)
        pathogen: Specific pathogen if applicable
        include_checklists: Include practical checklists
    
    Returns:
        IPAC guidelines, procedures, checklists, and resources
    """
    logger.info(f"opa.ipac_guidance called for {setting}/{topic}")
    
    sql_client = get_sql_client()
    vector_client = get_vector_client()
    
    # Build search query
    search_query = f"{setting} {topic}"
    if pathogen:
        search_query += f" {pathogen}"
    
    # Search for IPAC guidance (focus on PHO sources)
    sql_task = sql_client.search_sections(
        query=search_query,
        sources=['pho', 'ontario_health'],
        doc_types=['guideline', 'tool', 'policy'],
        limit=15
    )
    
    vector_task = vector_client.search_sections(
        query=search_query,
        sources=['pho'],
        n_results=10
    )
    
    sql_results, vector_results = await asyncio.gather(sql_task, vector_task)
    
    # Process results
    guidelines = []
    procedures = []
    checklists = []
    
    for result in sql_results:
        text = result.get('section_text', '')
        heading = result.get('section_heading', '')
        
        # Create highlight for key guidelines
        if any(kw in heading.lower() for kw in ['requirement', 'must', 'standard']):
            guidelines.append(Highlight(
                point=text[:300],
                citations=[Citation(
                    source=result.get('document_title', ''),
                    source_org='pho',
                    loc=heading,
                    url=result.get('source_url')
                )]
            ))
        
        # Extract procedures
        if any(kw in heading.lower() for kw in ['procedure', 'step', 'process']):
            procedures.append({
                'title': heading,
                'steps': text[:500],
                'source': result.get('document_title', '')
            })
        
        # Extract checklists
        if include_checklists and any(kw in heading.lower() for kw in ['checklist', 'list', 'requirements']):
            checklists.append({
                'title': heading,
                'items': text[:400],
                'source': result.get('document_title', '')
            })
    
    # Pathogen-specific guidance
    pathogen_specific = None
    if pathogen:
        pathogen_results = [r for r in sql_results if pathogen.lower() in r.get('section_text', '').lower()]
        if pathogen_results:
            pathogen_specific = {
                'pathogen': pathogen,
                'guidance': pathogen_results[0].get('section_text', '')[:500],
                'source': pathogen_results[0].get('document_title', '')
            }
    
    # Create citations
    citations = []
    seen_sources = set()
    for result in sql_results[:5]:
        source = result.get('document_title', '')
        if source and source not in seen_sources:
            seen_sources.add(source)
            citations.append(Citation(
                source=source,
                source_org='pho',
                loc='IPAC Guidance',
                url=result.get('source_url')
            ))
    
    # Additional resources
    resources = [
        {'title': 'PHO IPAC Best Practices', 'url': 'https://www.publichealthontario.ca/ipac'},
        {'title': 'Hand Hygiene Resources', 'url': 'https://www.publichealthontario.ca/hand-hygiene'}
    ]
    
    # Create response
    response = IPACGuidanceResponse(
        setting=setting,
        topic=topic,
        guidelines=guidelines[:5],  # Limit to top 5
        procedures=procedures[:3],  # Limit to 3
        checklists=checklists[:3],  # Limit to 3
        pathogen_specific=pathogen_specific,
        citations=citations,
        resources=resources
    )
    
    return response.dict()


@mcp.tool(name="opa.freshness_probe", description="Check for guidance updates on a topic")
async def freshness_probe_handler(
    topic: str,
    current_date: Optional[str] = None,
    sources: Optional[List[str]] = None,
    check_web: bool = True
) -> Dict[str, Any]:
    """
    Check for guidance updates on a topic.
    
    Args:
        topic: Topic to check for updates
        current_date: Reference date for checking
        sources: Specific sources to check
        check_web: Check web for recent updates
    
    Returns:
        Current guidance status, recent updates, and recommendations
    """
    logger.info(f"opa.freshness_probe called for topic: {topic}")
    
    sql_client = get_sql_client()
    
    # Check current guidance in corpus
    freshness_data = await sql_client.check_freshness(
        topic=topic,
        sources=sources
    )
    
    current_guidance = freshness_data.get('current_guidance')
    last_updated = freshness_data.get('last_updated')
    
    if not current_guidance:
        return FreshnessProbeResponse(
            topic=topic,
            current_guidance=Document(
                document_id='none',
                title='No guidance found',
                source_org='',
                document_type='',
                effective_date=None,
                topics=[],
                url=None,
                is_superseded=False
            ),
            last_updated='Unknown',
            updates_found=False,
            recent_updates=[],
            recommended_action='No guidance in corpus - search for new sources',
            web_sources_checked=[]
        ).dict()
    
    # Convert to Document
    current_doc = Document(
        document_id=current_guidance.get('document_id', ''),
        title=current_guidance.get('title', ''),
        source_org=current_guidance.get('source_org', ''),
        document_type=current_guidance.get('document_type', ''),
        effective_date=current_guidance.get('effective_date'),
        topics=[],
        url=current_guidance.get('source_url'),
        is_superseded=False
    )
    
    # Calculate age of guidance
    updates_found = False
    recent_updates = []
    recommended_action = "Corpus is current"
    
    if last_updated:
        try:
            last_date = datetime.fromisoformat(last_updated.replace('Z', ''))
            days_old = (datetime.now() - last_date).days
            
            if days_old > 730:  # > 2 years
                recommended_action = "Guidance is over 2 years old - recommend checking for updates"
                updates_found = True
            elif days_old > 365:  # > 1 year
                recommended_action = "Guidance is over 1 year old - periodic review recommended"
            else:
                recommended_action = "Guidance is current (less than 1 year old)"
        except:
            pass
    
    # Mock web check (in production would actually search)
    web_sources_checked = []
    if check_web:
        web_sources_checked = [
            f"https://www.cpso.on.ca/search?q={topic}",
            f"https://www.ontariohealth.ca/search?q={topic}"
        ]
        
        # Simulate finding an update for old guidance
        if updates_found:
            recent_updates.append(Update(
                topic=topic,
                date=datetime.now().isoformat(),
                source="Web search (simulated)",
                summary="Newer guidance may be available - manual verification required",
                url=web_sources_checked[0]
            ))
    
    # Create response
    response = FreshnessProbeResponse(
        topic=topic,
        current_guidance=current_doc,
        last_updated=last_updated or 'Unknown',
        updates_found=updates_found,
        recent_updates=recent_updates,
        recommended_action=recommended_action,
        web_sources_checked=web_sources_checked
    )
    
    return response.dict()


@mcp.tool(name="opa.clinical_tools", description="CEP clinical decision support tools lookup")
async def clinical_tools_handler(
    condition: Optional[str] = None,
    tool_name: Optional[str] = None,
    category: Optional[str] = None,
    feature_type: Optional[str] = None,
    include_sections: bool = False
) -> Dict[str, Any]:
    """
    CEP clinical tools navigation and quick reference.
    Returns tool summaries with direct links to interactive features.
    
    Args:
        condition: Clinical condition (e.g., "dementia", "depression")
        tool_name: Specific tool name
        category: Tool category filter (mental_health, chronic_disease, etc.)
        feature_type: Type of clinical feature (algorithm, calculator, checklist)
        include_sections: Include section summaries
    
    Returns:
        Clinical tools with navigation links and key content
    """
    logger.info(f"opa.clinical_tools called - condition: {condition}, category: {category}")
    
    sql_client = get_sql_client()
    
    # Build query for clinical tools
    query_parts = []
    params = []
    
    query_parts.append("""
        SELECT DISTINCT
            d.document_id,
            d.title,
            d.source_url,
            d.effective_date as last_updated,
            d.metadata_json,
            s.section_text as overview_text
        FROM opa_documents d
        LEFT JOIN opa_sections s ON d.document_id = s.document_id 
            AND s.chunk_type = 'parent' 
            AND s.section_heading LIKE '%Overview%'
        WHERE d.source_org = 'cep' 
            AND d.document_type = 'clinical_tool'
    """)
    
    # Add filters
    if condition:
        query_parts.append("AND (LOWER(d.title) LIKE ? OR LOWER(d.metadata_json) LIKE ?)")
        params.extend([f"%{condition.lower()}%", f"%{condition.lower()}%"])
    
    if tool_name:
        query_parts.append("AND LOWER(d.title) LIKE ?")
        params.append(f"%{tool_name.lower()}%")
    
    if category:
        query_parts.append("AND LOWER(d.metadata_json) LIKE ?")
        params.append(f"%{category.lower()}%")
    
    if feature_type:
        query_parts.append("AND LOWER(d.metadata_json) LIKE ?")
        params.append(f"%has_{feature_type.lower()}%true%")
    
    query = " ".join(query_parts)
    
    # Execute query
    conn = sql_client.db.connect()
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    # Format results
    tools = []
    for row in results:
        doc_id, title, url, last_updated, metadata_json, overview_text = row
        
        # Parse metadata
        try:
            metadata = json.loads(metadata_json) if metadata_json else {}
        except:
            metadata = {}
        
        tool_data = {
            'tool_id': doc_id,
            'name': title,
            'url': url,
            'last_updated': last_updated,
            'category': metadata.get('category', 'general'),
            'summary': overview_text[:500] if overview_text else metadata.get('meta_description', ''),
            'key_features': {}
        }
        
        # Extract features
        features = metadata.get('features', {})
        if features.get('has_algorithm'):
            tool_data['key_features']['assessment_algorithm'] = {
                'available': True,
                'url': f"{url}#assessment"
            }
        
        if features.get('has_calculator'):
            tool_data['key_features']['calculator'] = {
                'available': True,
                'url': f"{url}#calculator"
            }
        
        if features.get('has_checklist'):
            tool_data['key_features']['checklist'] = {
                'available': True,
                'url': f"{url}#checklist"
            }
        
        # Add assessment tools if available
        if metadata.get('has_assessment_tools'):
            tool_data['key_features']['screening_tools'] = ['Available - see tool page']
        
        # Add sections if requested
        if include_sections:
            section_query = """
                SELECT section_heading, section_text
                FROM opa_sections
                WHERE document_id = ? AND chunk_type = 'child'
                LIMIT 5
            """
            cursor.execute(section_query, (doc_id,))
            sections = cursor.fetchall()
            
            tool_data['sections'] = []
            for heading, text in sections:
                tool_data['sections'].append({
                    'title': heading,
                    'summary': text[:200] + '...' if len(text) > 200 else text,
                    'url': f"{url}#{heading.lower().replace(' ', '-')}"
                })
        
        # Add quick links
        tool_data['quick_links'] = {
            'full_tool': url,
            'pdf_version': None  # CEP tools typically don't have PDFs
        }
        
        tools.append(tool_data)
    
    conn.close()
    
    # Create response
    response = {
        'tools': tools,
        'total_tools': len(tools),
        'query_interpretation': f"Searching CEP clinical tools"
    }
    
    if condition:
        response['query_interpretation'] += f" for condition: {condition}"
    elif category:
        response['query_interpretation'] += f" in category: {category}"
    elif feature_type:
        response['query_interpretation'] += f" with feature: {feature_type}"
    
    return response


if __name__ == "__main__":
    # For testing, run the server directly
    import uvicorn
    
    # Initialize clients on startup
    logger.info("Dr. OPA MCP server starting...")
    get_sql_client()
    get_vector_client()
    logger.info("Dr. OPA MCP server ready")
    
    # Run server
    uvicorn.run(mcp, host="127.0.0.1", port=8001)