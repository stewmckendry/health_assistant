"""
Source passages retrieval tool for "show source" functionality.
Directly fetches document chunks by their IDs.
"""
import logging
from typing import Dict, Any, List, Optional

from ..models.request import SourcePassagesRequest
from ..models.response import SourcePassagesResponse, SourcePassage
from ..retrieval import VectorClient

logger = logging.getLogger(__name__)


class SourceTool:
    """
    Source passages retrieval tool.
    Fetches exact text chunks used in decisions for transparency.
    """
    
    def __init__(self, vector_client: Optional[VectorClient] = None):
        """
        Initialize source tool with vector client.
        
        Args:
            vector_client: Vector client instance (creates default if None)
        """
        self.vector_client = vector_client or VectorClient(
            persist_directory="data/dr_off_agent/processed/dr_off/chroma",
            timeout_ms=1000
        )
        logger.info("Source passages tool initialized")
    
    async def execute(
        self,
        request: SourcePassagesRequest
    ) -> SourcePassagesResponse:
        """
        Retrieve source passages by their chunk IDs.
        
        Args:
            request: SourcePassagesRequest with chunk IDs
            
        Returns:
            SourcePassagesResponse with retrieved passages
        """
        passages = []
        
        # Group chunk IDs by collection (inferred from ID patterns or metadata)
        collections_map = self._group_chunks_by_collection(request.chunk_ids)
        
        for collection, chunk_ids in collections_map.items():
            try:
                # Retrieve chunks from the collection
                results = await self.vector_client.get_passages_by_ids(
                    chunk_ids=chunk_ids,
                    collection=collection
                )
                
                # Convert to SourcePassage format
                if results:  # Only process if we got results
                    for result in results:
                        passage = SourcePassage(
                            chunk_id=result.get('id', ''),
                            text=result.get('text', ''),
                            source=result.get('metadata', {}).get('source', collection),
                            page=result.get('metadata', {}).get('page'),
                            section=result.get('metadata', {}).get('section'),
                            highlights=self._highlight_terms(
                                result.get('text', ''),
                                request.highlight_terms
                            ) if request.highlight_terms else None
                        )
                        passages.append(passage)
                elif chunk_ids:  # If no results but chunks requested, add placeholder
                    for chunk_id in chunk_ids[:2]:  # Limit to 2 placeholders
                        passage = SourcePassage(
                            chunk_id=chunk_id,
                            text=f"[Passage {chunk_id} from {collection} not available - collection not initialized]",
                            source=collection,
                            page=None,
                            section=None,
                            highlights=[]
                        )
                        passages.append(passage)
                    
            except Exception as e:
                logger.error(f"Error retrieving chunks from {collection}: {e}")
                # Continue with other collections
        
        logger.info(f"Retrieved {len(passages)} passages from {len(collections_map)} collections")
        
        return SourcePassagesResponse(
            passages=passages,
            total_chunks=len(passages)
        )
    
    def _group_chunks_by_collection(
        self,
        chunk_ids: List[str]
    ) -> Dict[str, List[str]]:
        """
        Group chunk IDs by their collection.
        
        Args:
            chunk_ids: List of chunk IDs to group
            
        Returns:
            Dict mapping collection name to list of chunk IDs
        """
        # Default collections based on ID patterns or prefixes
        collections = {
            'ohip_chunks': [],
            'adp_v1': [],
            'odb_documents': []
        }
        
        for chunk_id in chunk_ids:
            # Try to infer collection from chunk ID pattern
            # This is a simplified heuristic - production would use metadata
            if 'ohip' in chunk_id.lower() or 'schedule' in chunk_id.lower():
                collections['ohip_chunks'].append(chunk_id)
            elif 'adp' in chunk_id.lower() or 'device' in chunk_id.lower():
                collections['adp_v1'].append(chunk_id)
            elif 'odb' in chunk_id.lower() or 'drug' in chunk_id.lower():
                collections['odb_documents'].append(chunk_id)
            else:
                # Default to OHIP if unclear
                collections['ohip_chunks'].append(chunk_id)
        
        # Remove empty collections
        return {k: v for k, v in collections.items() if v}
    
    def _highlight_terms(
        self,
        text: str,
        terms: List[str]
    ) -> List[str]:
        """
        Find and highlight terms in the text.
        
        Args:
            text: Text to search in
            terms: Terms to highlight
            
        Returns:
            List of text snippets containing the terms
        """
        highlights = []
        text_lower = text.lower()
        
        for term in terms:
            term_lower = term.lower()
            
            # Find all occurrences
            start = 0
            while True:
                pos = text_lower.find(term_lower, start)
                if pos == -1:
                    break
                
                # Extract context around the term (50 chars before and after)
                context_start = max(0, pos - 50)
                context_end = min(len(text), pos + len(term) + 50)
                
                # Find word boundaries
                while context_start > 0 and text[context_start] not in ' \n\t':
                    context_start -= 1
                while context_end < len(text) and text[context_end] not in ' \n\t':
                    context_end += 1
                
                snippet = text[context_start:context_end].strip()
                
                # Mark the term with ** for emphasis
                highlighted = snippet.replace(
                    text[pos:pos+len(term)],
                    f"**{text[pos:pos+len(term)]}**"
                )
                
                if highlighted not in highlights:
                    highlights.append(highlighted)
                
                start = pos + 1
        
        return highlights[:5]  # Limit to 5 highlights per passage


async def source_passages(
    request: Dict[str, Any],
    vector_client: Optional[VectorClient] = None
) -> Dict[str, Any]:
    """
    MCP tool entry point for source.passages.
    
    Args:
        request: Raw request dictionary with chunk_ids
        vector_client: Optional vector client (for testing)
        
    Returns:
        Response dictionary with passages
    """
    # Parse request
    parsed_request = SourcePassagesRequest(**request)
    
    # Create tool instance
    tool = SourceTool(vector_client=vector_client)
    
    # Execute retrieval
    response = await tool.execute(parsed_request)
    
    # Return as dictionary
    return response.model_dump()