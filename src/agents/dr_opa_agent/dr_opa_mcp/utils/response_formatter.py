"""
Response formatter for standardizing MCP tool responses.
Ensures all tools return citations in a consistent format.
"""

from typing import Dict, Any, List, Set
import logging

logger = logging.getLogger(__name__)


def extract_citations_from_response(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract all unique citations from a response.
    Handles different response structures from various MCP tools.
    """
    citations = []
    seen_citations: Set[str] = set()  # Track unique citations by key
    
    def add_citation(cite_data: Dict[str, Any]):
        """Add a citation if not already seen."""
        # Create unique key for deduplication
        key = f"{cite_data.get('source', '')}_{cite_data.get('source_org', '')}_{cite_data.get('loc', '')}"
        if key not in seen_citations and key != "__":
            seen_citations.add(key)
            citations.append(cite_data)
    
    # Extract from direct citations field
    if 'citations' in response_data:
        for cite in response_data['citations']:
            if isinstance(cite, dict):
                add_citation(Citation(**cite))
    
    # Extract from highlights (used in SearchSectionsResponse)
    if 'highlights' in response_data:
        for highlight in response_data['highlights']:
            if isinstance(highlight, dict) and 'citations' in highlight:
                for cite in highlight['citations']:
                    if isinstance(cite, dict):
                        add_citation(Citation(**cite))
    
    # Extract from expectations (used in PolicyCheckResponse)
    if 'expectations' in response_data:
        for expectation in response_data['expectations']:
            if isinstance(expectation, dict) and 'citations' in expectation:
                for cite in expectation['citations']:
                    if isinstance(cite, dict):
                        add_citation(Citation(**cite))
    
    # Extract from advice (used in PolicyCheckResponse)
    if 'advice' in response_data:
        for advice_item in response_data['advice']:
            if isinstance(advice_item, dict) and 'citations' in advice_item:
                for cite in advice_item['citations']:
                    if isinstance(cite, dict):
                        add_citation(Citation(**cite))
    
    # Extract from sections metadata (used in SearchSectionsResponse)
    if 'sections' in response_data:
        for section in response_data['sections']:
            if isinstance(section, dict) and 'metadata' in section:
                metadata = section['metadata']
                if 'url' in metadata and metadata['url']:
                    cite_dict = {
                        'source': section.get('heading', 'Document Section'),
                        'source_org': metadata.get('source_org', 'unknown'),
                        'loc': f"Section {section.get('section_id', '')}",
                        'url': metadata['url']
                    }
                    add_citation(cite_dict)
    
    # Extract from documents (used in multiple responses)
    if 'documents' in response_data:
        for doc in response_data['documents']:
            if isinstance(doc, dict) and 'url' in doc and doc['url']:
                cite_dict = {
                    'source': doc.get('title', 'Document'),
                    'source_org': doc.get('source_org', 'unknown'),
                    'loc': f"Document ID: {doc.get('document_id', '')}",
                    'url': doc['url']
                }
                add_citation(cite_dict)
    
    # Extract from policies (used in PolicyCheckResponse)
    if 'policies' in response_data:
        for policy in response_data['policies']:
            if isinstance(policy, dict) and 'url' in policy and policy['url']:
                cite_dict = {
                    'source': policy.get('title', 'Policy'),
                    'source_org': policy.get('source_org', 'cpso'),
                    'loc': "Policy Document",
                    'url': policy['url']
                }
                add_citation(cite_dict)
    
    # Extract from updates (used in FreshnessProbeResponse)
    if 'updates' in response_data:
        for update in response_data['updates']:
            if isinstance(update, dict) and 'url' in update and update['url']:
                cite = Citation(
                    source=update.get('topic', 'Update'),
                    source_org=update.get('source', 'unknown'),
                    loc=f"Updated: {update.get('date', '')}",
                    url=update['url']
                )
                add_citation(cite)
    
    return citations


def standardize_mcp_response(response_data: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
    """
    Standardize MCP tool response to include top-level citations.
    
    Args:
        response_data: Raw response from MCP tool
        tool_name: Name of the MCP tool that generated the response
    
    Returns:
        Standardized response with top-level 'citations' field
    """
    # Extract all citations from the response
    citations = extract_citations_from_response(response_data)
    
    # Add citations as a top-level field if not already present
    if 'citations' not in response_data:
        response_data['citations'] = citations
    else:
        # Merge with existing citations if any
        existing = response_data['citations']
        if isinstance(existing, list):
            # Deduplicate
            existing_keys = {f"{c.get('source', '')}_{c.get('source_org', '')}_{c.get('loc', '')}" 
                           for c in existing if isinstance(c, dict)}
            for cite in citations:
                key = f"{cite.get('source', '')}_{cite.get('source_org', '')}_{cite.get('loc', '')}"
                if key not in existing_keys:
                    existing.append(cite)
        else:
            response_data['citations'] = citations
    
    # Add metadata about the tool
    response_data['_tool_name'] = tool_name
    response_data['_citation_count'] = len(response_data.get('citations', []))
    
    logger.info(f"Standardized response from {tool_name}: {response_data['_citation_count']} citations extracted")
    
    return response_data