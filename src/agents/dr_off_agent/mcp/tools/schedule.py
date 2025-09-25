"""
OHIP Schedule of Benefits retrieval tool with intelligent routing.
Uses query classification to determine optimal search strategy.
"""

import asyncio
import logging
import uuid
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
from ..utils import (
    ConfidenceScorer,
    ConflictDetector,
    QueryClassifier,
    SearchStrategy,
    SearchLogger,
    LLMReranker,
    Document
)

logger = logging.getLogger(__name__)


class ScheduleTool:
    """
    OHIP Schedule retrieval tool with intelligent search routing.
    Uses query classification to choose optimal search strategy.
    """
    
    def __init__(
        self,
        sql_client: Optional[SQLClient] = None,
        vector_client: Optional[VectorClient] = None,
        session_id: Optional[str] = None
    ):
        """
        Initialize schedule tool with retrieval clients.
        
        Args:
            sql_client: SQL client instance (creates default if None)
            vector_client: Vector client instance (creates default if None)
            session_id: Session ID for logging
        """
        self.sql_client = sql_client or SQLClient(
            db_path="data/ohip.db",
            timeout_ms=500
        )
        self.vector_client = vector_client or VectorClient(
            persist_directory="data/dr_off_agent/processed/dr_off/chroma",
            timeout_ms=1000
        )
        
        # Initialize new components
        self.query_classifier = QueryClassifier()
        self.confidence_scorer = ConfidenceScorer()
        self.conflict_detector = ConflictDetector()
        self.llm_reranker = LLMReranker()
        
        # Setup logging
        session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.search_logger = SearchLogger(session_id)
        
        logger.info("Schedule tool initialized with intelligent routing")
    
    async def execute(self, request: ScheduleGetRequest) -> ScheduleGetResponse:
        """
        Execute schedule query with intelligent routing.
        
        Args:
            request: ScheduleGetRequest with query parameters
            
        Returns:
            ScheduleGetResponse with results based on optimal search strategy
        """
        # Start operation logging
        operation_id = self.search_logger.start_operation(
            tool="schedule.get",
            query=request.q,
            request_data=request.dict()
        )
        
        try:
            # Classify query to determine strategy
            strategy, reason = self.query_classifier.classify(
                query=request.q,
                tool="schedule.get",
                codes=request.codes
            )
            
            self.search_logger.log_classification(
                strategy=strategy.value,
                reason=reason
            )
            
            logger.info(f"Query classified as {strategy.value}: {reason}")
            
            # Execute based on strategy
            if strategy == SearchStrategy.SQL_ONLY:
                response = await self._execute_sql_only(request)
                
            elif strategy == SearchStrategy.VECTOR_WITH_RERANK:
                response = await self._execute_vector_with_rerank(request)
                
            elif strategy == SearchStrategy.HYBRID_SMART:
                response = await self._execute_hybrid_smart(request)
                
            else:  # SQL_PRIMARY or default
                response = await self._execute_sql_primary(request)
            
            # Log completion
            self.search_logger.complete_operation(
                final_count=len(response.items),
                confidence=response.confidence,
                success=True
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Schedule tool error: {e}")
            self.search_logger.log_error(e, context="schedule.execute")
            self.search_logger.complete_operation(
                final_count=0,
                success=False,
                error_message=str(e)
            )
            
            # Return empty response with error
            return ScheduleGetResponse(
                provenance=[],
                confidence=0.0,
                items=[],
                citations=[],
                conflicts=[]
            )
    
    async def _execute_sql_only(self, request: ScheduleGetRequest) -> ScheduleGetResponse:
        """
        Execute SQL-only search for structured queries.
        Used for direct code lookups.
        """
        start_time = datetime.now()
        
        # Build SQL query for codes
        if request.codes:
            sql_results = await self._sql_code_lookup(request.codes)
        else:
            # Single code in query
            sql_results = await self._sql_code_lookup([request.q.strip()])
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        self.search_logger.log_sql_search(
            query=f"Code lookup: {request.codes or request.q}",
            results_count=len(sql_results),
            duration_ms=duration_ms,
            table="ohip_fee_codes"
        )
        
        # Convert to response format
        items = [self._sql_to_item(result) for result in sql_results]
        
        return ScheduleGetResponse(
            provenance=["sql"],
            confidence=0.95 if items else 0.0,  # High confidence for direct lookups
            items=items,
            citations=self._generate_sql_citations(items),
            conflicts=[]
        )
    
    async def _execute_vector_with_rerank(self, request: ScheduleGetRequest) -> ScheduleGetResponse:
        """
        Execute vector search with LLM reranking.
        Used for natural language queries.
        """
        start_time = datetime.now()
        
        # Step 1: Vector search with wider net
        vector_results = await self._vector_semantic_search(
            query=request.q,
            top_k=50  # Get more candidates for reranking
        )
        
        vector_duration = (datetime.now() - start_time).total_seconds() * 1000
        
        self.search_logger.log_vector_search(
            query=request.q,
            results_count=len(vector_results),
            duration_ms=vector_duration,
            collection="ohip_documents",
            top_k=50
        )
        
        if not vector_results:
            return ScheduleGetResponse(
                provenance=["vector"],
                confidence=0.0,
                items=[],
                citations=[],
                conflicts=[]
            )
        
        # Step 2: Convert to Documents for reranking
        documents = [
            Document(
                text=result.get('text', ''),
                metadata=result.get('metadata', {}),
                score=result.get('score')
            )
            for result in vector_results
        ]
        
        # Step 3: Rerank with LLM
        rerank_start = datetime.now()
        reranked_docs = await self.llm_reranker.rerank(
            query=request.q,
            documents=documents,
            top_k=request.top_k,
            context="OHIP Schedule of Benefits billing codes and fees"
        )
        
        rerank_duration = (datetime.now() - rerank_start).total_seconds() * 1000
        
        self.search_logger.log_reranking(
            input_count=len(documents),
            output_count=len(reranked_docs),
            duration_ms=rerank_duration,
            model="gpt-4o-mini"
        )
        
        # Step 4: Convert to response items
        items = []
        for doc in reranked_docs:
            item = self._vector_to_item(doc)
            if item:
                items.append(item)
        
        # Calculate confidence based on reranking scores
        avg_score = sum(d.relevance_score or 0 for d in reranked_docs[:3]) / 3 if reranked_docs else 0
        confidence = min(avg_score / 10.0, 1.0)  # Normalize to 0-1
        
        return ScheduleGetResponse(
            provenance=["vector", "reranked"],
            confidence=confidence,
            items=items,
            citations=self._generate_vector_citations(reranked_docs),
            conflicts=[]
        )
    
    async def _execute_hybrid_smart(self, request: ScheduleGetRequest) -> ScheduleGetResponse:
        """
        Execute intelligent hybrid search.
        Combines SQL for structured data with vector for context.
        """
        # Run both in parallel
        sql_task = self._sql_structured_search(request)
        vector_task = self._vector_semantic_search(request.q, top_k=30)
        
        sql_results, vector_results = await asyncio.gather(
            sql_task,
            vector_task,
            return_exceptions=True
        )
        
        # Handle errors
        if isinstance(sql_results, Exception):
            logger.warning(f"SQL search failed: {sql_results}")
            sql_results = []
        if isinstance(vector_results, Exception):
            logger.warning(f"Vector search failed: {vector_results}")
            vector_results = []
        
        # Log both searches
        self.search_logger.log_sql_search(
            query=request.q,
            results_count=len(sql_results) if sql_results else 0,
            duration_ms=0  # Would need timing
        )
        self.search_logger.log_vector_search(
            query=request.q,
            results_count=len(vector_results) if vector_results else 0,
            duration_ms=0  # Would need timing
        )
        
        # Rerank vector results if we have them
        reranked_docs = []
        if vector_results:
            documents = [
                Document(text=r.get('text', ''), metadata=r.get('metadata', {}))
                for r in vector_results
            ]
            reranked_docs = await self.llm_reranker.rerank(
                query=request.q,
                documents=documents,
                top_k=10
            )
        
        # Intelligent merge
        merged_items = await self._smart_merge(
            sql_results=sql_results,
            vector_results=reranked_docs,
            request=request
        )
        
        self.search_logger.log_merge(
            sql_count=len(sql_results) if sql_results else 0,
            vector_count=len(reranked_docs),
            final_count=len(merged_items)
        )
        
        # Detect conflicts - TODO: Fix to handle lists properly
        conflicts = []  # Temporarily disabled due to signature mismatch
        
        return ScheduleGetResponse(
            provenance=["sql", "vector", "reranked"],
            confidence=self.confidence_scorer.calculate(
                sql_hits=len(sql_results) if sql_results else 0,
                vector_matches=len(reranked_docs)
            ),
            items=merged_items,
            citations=self._merge_citations(sql_results, reranked_docs),
            conflicts=conflicts
        )
    
    async def _execute_sql_primary(self, request: ScheduleGetRequest) -> ScheduleGetResponse:
        """
        Execute SQL-primary search with vector fallback.
        """
        # Try SQL first
        sql_results = await self._sql_structured_search(request)
        
        if sql_results and len(sql_results) >= request.top_k // 2:
            # SQL found sufficient results
            items = [self._sql_to_item(r) for r in sql_results]
            return ScheduleGetResponse(
                provenance=["sql"],
                confidence=0.8,
                items=items,
                citations=self._generate_sql_citations(items),
                conflicts=[]
            )
        
        # Fall back to vector search
        return await self._execute_vector_with_rerank(request)
    
    # Helper methods for actual database queries
    
    async def _sql_code_lookup(self, codes: List[str]) -> List[Dict[str, Any]]:
        """Direct SQL lookup for specific fee codes"""
        try:
            if not codes:
                return []
            
            # Build SQL query with placeholders for codes
            placeholders = ','.join(['?' for _ in codes])
            query = f"""
            SELECT 
                fee_code as code,
                description,
                amount as fee,
                requirements,
                notes as limits,
                null as page_num
            FROM ohip_fee_schedule
            WHERE fee_code IN ({placeholders})
            LIMIT 50
            """
            
            results = await self.sql_client.query(query, tuple(codes))
            return results
            
        except Exception as e:
            logger.error(f"SQL code lookup error: {e}")
            return []
    
    async def _sql_structured_search(self, request: ScheduleGetRequest) -> List[Dict[str, Any]]:
        """SQL search for structured queries"""
        try:
            # Build query based on request
            query_text = request.q.lower()
            
            # Search in descriptions and codes
            query = """
            SELECT 
                fee_code as code,
                description,
                amount as fee,
                requirements,
                notes as limits,
                null as page_num
            FROM ohip_fee_schedule
            WHERE 
                LOWER(description) LIKE ? 
                OR fee_code LIKE ?
            LIMIT ?
            """
            
            search_pattern = f"%{query_text}%"
            params = (search_pattern, search_pattern.upper(), request.top_k * 2)
            
            results = await self.sql_client.query(query, params)
            return results
            
        except Exception as e:
            logger.error(f"SQL structured search error: {e}")
            return []
    
    async def _vector_semantic_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Vector search for semantic queries"""
        try:
            # Search in OHIP documents collection using correct method signature
            results = await self.vector_client.search(
                query=query,
                collection="ohip_documents",
                n_results=top_k,
                where=None
            )
            
            # Results are already formatted by VectorClient.search()
            # They come as a list of dicts with 'text' and 'metadata' keys
            return results
            
        except Exception as e:
            logger.error(f"Vector semantic search error: {e}")
            return []
    
    async def _smart_merge(
        self,
        sql_results: List[Dict[str, Any]],
        vector_results: List[Document],
        request: ScheduleGetRequest
    ) -> List[ScheduleItem]:
        """Intelligently merge SQL and vector results"""
        items = []
        
        # Add SQL results first (usually more precise for codes)
        for result in sql_results[:request.top_k // 2]:
            item = self._sql_to_item(result)
            if item:
                items.append(item)
        
        # Add vector results (reranked)
        for doc in vector_results[:request.top_k // 2]:
            item = self._vector_to_item(doc)
            if item and not self._is_duplicate(item, items):
                items.append(item)
        
        return items[:request.top_k]
    
    def _sql_to_item(self, result: Dict[str, Any]) -> Optional[ScheduleItem]:
        """Convert SQL result to ScheduleItem"""
        if not result:
            return None
            
        return ScheduleItem(
            code=result.get('code', ''),
            description=result.get('description', ''),
            fee=result.get('fee'),
            requirements=result.get('requirements'),
            limits=result.get('limits'),
            page_num=result.get('page_num')
        )
    
    def _vector_to_item(self, doc: Document) -> Optional[ScheduleItem]:
        """Convert vector result Document to ScheduleItem"""
        if not doc:
            return None
            
        # Extract from metadata and text
        metadata = doc.metadata or {}
        
        # Try to parse code from text
        import re
        code_match = re.search(r'([A-Z]\d{3,4})', doc.text)
        code = code_match.group(1) if code_match else metadata.get('code', '')
        
        return ScheduleItem(
            code=code,
            description=doc.text[:200],  # First 200 chars
            fee=metadata.get('fee'),
            requirements=metadata.get('requirements'),
            limits=metadata.get('limits'),
            page_num=metadata.get('page_num')
        )
    
    def _is_duplicate(self, item: ScheduleItem, items: List[ScheduleItem]) -> bool:
        """Check if item is duplicate"""
        for existing in items:
            if existing.code and existing.code == item.code:
                return True
        return False
    
    def _generate_sql_citations(self, items: List[ScheduleItem]) -> List[Citation]:
        """Generate citations for SQL results"""
        citations = []
        for item in items:
            if item.code:
                citations.append(Citation(
                    source="OHIP Schedule of Benefits",
                    loc=f"Code {item.code}",
                    page=item.page_num
                ))
        return citations[:5]  # Limit citations
    
    def _generate_vector_citations(self, docs: List[Document]) -> List[Citation]:
        """Generate citations for vector results"""
        citations = []
        for doc in docs[:5]:  # Limit to top 5
            metadata = doc.metadata or {}
            citations.append(Citation(
                source=metadata.get('source', 'OHIP Schedule'),
                loc=metadata.get('section', ''),
                page=metadata.get('page_num')
            ))
        return citations
    
    def _merge_citations(
        self,
        sql_results: List[Dict[str, Any]],
        vector_docs: List[Document]
    ) -> List[Citation]:
        """Merge citations from both sources"""
        citations = []
        
        # Add SQL citations
        for result in sql_results[:3]:
            citations.append(Citation(
                source="OHIP Schedule (Database)",
                loc=result.get('code', ''),
                page=result.get('page_num')
            ))
        
        # Add vector citations
        for doc in vector_docs[:3]:
            metadata = doc.metadata or {}
            citations.append(Citation(
                source="OHIP Schedule (Document)",
                loc=metadata.get('section', ''),
                page=metadata.get('page_num')
            ))
        
        return citations


# Export for use in server
async def schedule_get(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for schedule.get tool.
    
    Args:
        request: Request dictionary with query parameters
        
    Returns:
        Response dictionary with schedule items
    """
    # Parse request
    req = ScheduleGetRequest(**request)
    
    # Create tool instance (could cache this)
    tool = ScheduleTool()
    
    # Execute
    response = await tool.execute(req)
    
    # Return as dict
    return response.dict()