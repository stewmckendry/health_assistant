"""
OHIP Schedule of Benefits dual-path retrieval tool.
Always runs SQL and vector search in parallel, merges results.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.request import ScheduleGetRequest
from ..models.response import (
    ScheduleGetResponse,
    ScheduleItem,
    Citation,
    Conflict
)
from ..retrieval import SQLClient, VectorClient
from ..utils import ConfidenceScorer, ConflictDetector

logger = logging.getLogger(__name__)


class ScheduleTool:
    """
    OHIP Schedule retrieval tool with dual-path execution.
    Always runs SQL and vector queries in parallel.
    """
    
    def __init__(
        self,
        sql_client: Optional[SQLClient] = None,
        vector_client: Optional[VectorClient] = None
    ):
        """
        Initialize schedule tool with retrieval clients.
        
        Args:
            sql_client: SQL client instance (creates default if None)
            vector_client: Vector client instance (creates default if None)
        """
        self.sql_client = sql_client or SQLClient(db_path="data/ohip.db", timeout_ms=500)
        self.vector_client = vector_client or VectorClient(persist_directory="data/dr_off_agent/processed/dr_off/chroma", timeout_ms=1000)
        self.confidence_scorer = ConfidenceScorer()
        self.conflict_detector = ConflictDetector()
        
        logger.info("Schedule tool initialized with dual-path retrieval")
    
    async def execute(self, request: ScheduleGetRequest) -> ScheduleGetResponse:
        """
        Execute schedule query with dual-path retrieval.
        
        Args:
            request: ScheduleGetRequest with query parameters
            
        Returns:
            ScheduleGetResponse with merged SQL + vector results
        """
        start_time = datetime.now()
        
        # Always run SQL and vector in parallel
        sql_task = self._sql_query(request)
        vector_task = self._vector_search(request)
        
        sql_result, vector_result = await asyncio.gather(
            sql_task,
            vector_task,
            return_exceptions=True
        )
        
        # Track which sources succeeded
        provenance = []
        if not isinstance(sql_result, Exception):
            provenance.append("sql")
        else:
            logger.warning(f"SQL query failed: {sql_result}")
            sql_result = []
            
        if not isinstance(vector_result, Exception):
            provenance.append("vector")
        else:
            logger.warning(f"Vector search failed: {vector_result}")
            vector_result = []
        
        # Merge results
        items, citations, conflicts = await self._merge_results(
            sql_result if not isinstance(sql_result, Exception) else [],
            vector_result if not isinstance(vector_result, Exception) else [],
            request
        )
        
        # Calculate confidence
        sql_hits = len(sql_result) if not isinstance(sql_result, Exception) and "sql" in provenance else 0
        vector_hits = len(vector_result) if not isinstance(vector_result, Exception) and "vector" in provenance else 0
        
        confidence = self.confidence_scorer.calculate(
            sql_hits=sql_hits,
            vector_matches=vector_hits,
            has_conflict=len(conflicts) > 0
        )
        
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"Schedule query completed in {elapsed_ms:.1f}ms: {len(items)} items, confidence={confidence:.2f}")
        
        return ScheduleGetResponse(
            provenance=provenance,
            confidence=confidence,
            items=items,
            citations=citations,
            conflicts=conflicts
        )
    
    async def _sql_query(self, request: ScheduleGetRequest) -> List[Dict[str, Any]]:
        """
        Execute SQL query for OHIP fee codes.
        
        Args:
            request: Schedule request parameters
            
        Returns:
            List of SQL results
        """
        try:
            # If specific codes are requested, prioritize those over text search
            # This avoids the AND condition that would exclude valid codes
            if request.codes:
                results = await self.sql_client.query_schedule_fees(
                    codes=request.codes,
                    search_text=None,  # Don't use text search when codes are specified
                    limit=request.top_k * 2  # Get extra for merging
                )
            else:
                # Use text search when no specific codes requested
                results = await self.sql_client.query_schedule_fees(
                    codes=None,
                    search_text=request.q,
                    limit=request.top_k * 2  # Get extra for merging
                )
            
            logger.debug(f"SQL query returned {len(results)} fee codes")
            return results
            
        except asyncio.TimeoutError:
            logger.warning("SQL query timed out")
            raise
        except Exception as e:
            logger.error(f"SQL query error: {e}")
            raise
    
    async def _vector_search(self, request: ScheduleGetRequest) -> List[Dict[str, Any]]:
        """
        Execute vector search for OHIP context.
        
        Args:
            request: Schedule request parameters
            
        Returns:
            List of vector search results
        """
        try:
            # Build search query combining text and codes
            search_query = request.q
            if request.codes:
                search_query = f"{request.q} {' '.join(request.codes)}"
            
            # Search OHIP chunks
            results = await self.vector_client.search_schedule(
                query=search_query,
                codes=request.codes,
                n_results=request.top_k
            )
            
            logger.debug(f"Vector search returned {len(results)} chunks")
            return results
            
        except asyncio.TimeoutError:
            logger.warning("Vector search timed out")
            raise
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            raise
    
    async def _merge_results(
        self,
        sql_results: List[Dict[str, Any]],
        vector_results: List[Dict[str, Any]],
        request: ScheduleGetRequest
    ) -> tuple[List[ScheduleItem], List[Citation], List[Conflict]]:
        """
        Merge SQL and vector results intelligently.
        
        Args:
            sql_results: Results from SQL query
            vector_results: Results from vector search
            request: Original request for context
            
        Returns:
            Tuple of (items, citations, conflicts)
        """
        items = []
        citations = []
        conflicts = []
        seen_codes = set()
        
        # Process SQL results first (structured data)
        for sql_item in sql_results:
            code = sql_item.get("code")
            if code and code not in seen_codes:
                seen_codes.add(code)
                
                # Create schedule item from SQL data
                item = ScheduleItem(
                    code=code,
                    description=sql_item.get("description", ""),
                    fee=sql_item.get("amount"),
                    requirements=sql_item.get("requirements"),
                    limits=None,  # Will be enriched from vector
                    page_num=sql_item.get("page_number")
                )
                
                # Check if vector has additional context for this code
                vector_context = self._find_vector_context(code, vector_results)
                if vector_context:
                    # Enrich with vector information
                    item = self._enrich_with_vector(item, vector_context)
                    
                    # Check for conflicts
                    item_conflicts = self.conflict_detector.detect_schedule_conflicts(
                        sql_item, vector_context
                    )
                    conflicts.extend(item_conflicts)
                
                if self._should_include_item(item, request):
                    items.append(item)
        
        # Add citations from vector results
        for vector_item in vector_results:
            metadata = vector_item.get("metadata", {})
            
            # Create citation
            citation = Citation(
                source=metadata.get("source", "schedule.pdf"),
                loc=metadata.get("section", ""),
                page=metadata.get("page")
            )
            
            # Avoid duplicate citations
            if not any(c.source == citation.source and c.loc == citation.loc 
                      for c in citations):
                citations.append(citation)
        
        # Process vector-only context (codes not in SQL)
        for vector_item in vector_results:
            text = vector_item.get("text", "")
            
            # Extract any fee codes mentioned
            mentioned_codes = self._extract_codes_from_text(text)
            
            for code in mentioned_codes:
                if code not in seen_codes:
                    # Create item from vector context only
                    item = self._create_item_from_vector(code, vector_item)
                    if item and self._should_include_item(item, request):
                        items.append(item)
                        seen_codes.add(code)
        
        # Sort items by code
        items.sort(key=lambda x: x.code)
        
        # Limit to requested top_k
        items = items[:request.top_k]
        
        return items, citations, conflicts
    
    def _find_vector_context(
        self,
        code: str,
        vector_results: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find vector result that mentions a specific code."""
        for result in vector_results:
            text = result.get("text", "")
            metadata = result.get("metadata", {})
            
            # Check if code is mentioned in text or metadata
            if code in text or code in metadata.get("fee_codes_list", []):
                return result
        
        return None
    
    def _enrich_with_vector(
        self,
        item: ScheduleItem,
        vector_context: Dict[str, Any]
    ) -> ScheduleItem:
        """Enrich schedule item with vector context."""
        text = vector_context.get("text", "")
        
        # Extract additional requirements or documentation needs
        if "documentation" in text.lower() or "require" in text.lower():
            if not item.requirements:
                item.requirements = self._extract_requirements(text, item.code)
            elif self._extract_requirements(text, item.code):
                # Append if different
                vector_req = self._extract_requirements(text, item.code)
                if vector_req and vector_req not in item.requirements:
                    item.requirements = f"{item.requirements}. {vector_req}"
        
        # Extract limits
        if "limit" in text.lower() or "maximum" in text.lower():
            item.limits = self._extract_limits(text, item.code)
        
        return item
    
    def _extract_requirements(self, text: str, code: str) -> Optional[str]:
        """Extract requirements from vector text."""
        # Look for requirements related to the specific code
        lines = text.split(".")
        for line in lines:
            if code in line and ("require" in line.lower() or "documentation" in line.lower()):
                return line.strip()
        return None
    
    def _extract_limits(self, text: str, code: str) -> Optional[str]:
        """Extract service limits from vector text."""
        lines = text.split(".")
        for line in lines:
            if code in line and ("limit" in line.lower() or "maximum" in line.lower()):
                return line.strip()
        return None
    
    def _extract_codes_from_text(self, text: str) -> List[str]:
        """Extract fee codes from text using pattern matching."""
        import re
        
        # Common OHIP fee code patterns
        patterns = [
            r'\b[A-Z]\d{3}\b',  # A123, C124, etc.
            r'\bGP\d{2}\b',     # GP21, GP22, etc.
            r'\b[A-Z]{2}\d{2}\b' # SP01, etc.
        ]
        
        codes = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            codes.extend(matches)
        
        return list(set(codes))  # Remove duplicates
    
    def _create_item_from_vector(
        self,
        code: str,
        vector_item: Dict[str, Any]
    ) -> Optional[ScheduleItem]:
        """Create schedule item from vector context alone."""
        text = vector_item.get("text", "")
        metadata = vector_item.get("metadata", {})
        
        # Try to extract description from text
        description = None
        for line in text.split("."):
            if code in line:
                description = line.strip()[:200]  # Limit length
                break
        
        if not description:
            return None
        
        return ScheduleItem(
            code=code,
            description=description,
            fee=None,  # No fee data from vector
            requirements=self._extract_requirements(text, code),
            limits=self._extract_limits(text, code),
            page_num=metadata.get("page")
        )
    
    def _should_include_item(
        self,
        item: ScheduleItem,
        request: ScheduleGetRequest
    ) -> bool:
        """Determine if item should be included based on request filters."""
        # If specific codes requested, only include those
        if request.codes:
            return item.code in request.codes
        
        # Otherwise include all relevant items
        return True


async def schedule_get(
    request: Dict[str, Any],
    sql_client: Optional[SQLClient] = None,
    vector_client: Optional[VectorClient] = None
) -> Dict[str, Any]:
    """
    MCP tool entry point for schedule.get.
    
    Args:
        request: Raw request dictionary
        sql_client: Optional SQL client (for testing)
        vector_client: Optional vector client (for testing)
        
    Returns:
        Response dictionary
    """
    # Parse request
    parsed_request = ScheduleGetRequest(**request)
    
    # Create tool instance
    tool = ScheduleTool(sql_client=sql_client, vector_client=vector_client)
    
    # Execute query
    response = await tool.execute(parsed_request)
    
    # Return as dictionary
    return response.model_dump()