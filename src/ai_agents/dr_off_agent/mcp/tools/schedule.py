"""
OHIP Schedule of Benefits retrieval tool with intelligent routing.
Uses query classification to determine optimal search strategy.

Now includes OHIPQueryProcessor for flexible natural language understanding.
"""

import asyncio
import logging
import os
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.request import StandardToolRequest
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
from .ohip_query_processor import OHIPQueryProcessor

logger = logging.getLogger(__name__)

# Feature flag for new query processor - unified toggle
def _should_use_query_processor():
    """Check if query processor should be enabled (global or tool-specific override)."""
    # Check tool-specific override first
    tool_specific = os.getenv("SCHEDULE_QUERY_PROCESSOR")
    if tool_specific is not None:
        return tool_specific.lower() in ["true", "1", "yes"]

    # Fall back to global setting
    global_setting = os.getenv("ENABLE_QUERY_PROCESSOR", "false")
    return global_setting.lower() in ["true", "1", "yes"]

USE_QUERY_PROCESSOR = _should_use_query_processor()


class ScheduleTool:
    """
    OHIP Schedule retrieval tool with intelligent search routing.
    Uses query classification to choose optimal search strategy.
    """
    
    def __init__(
        self,
        sql_client: Optional[SQLClient] = None,
        vector_client: Optional[VectorClient] = None,
        session_id: Optional[str] = None,
        use_query_processor: Optional[bool] = None
    ):
        """
        Initialize schedule tool with retrieval clients.

        Args:
            sql_client: SQL client instance (creates default if None)
            vector_client: Vector client instance (creates default if None)
            session_id: Session ID for logging
            use_query_processor: Whether to use new LLM-powered query processor (default: from env)
        """
        self.sql_client = sql_client or SQLClient(
            db_path="data/ohip.db",
            timeout_ms=500
        )
        self.vector_client = vector_client or VectorClient(
            persist_directory=None,  # Will use environment-appropriate default
            timeout_ms=5000
        )

        # Initialize legacy components
        self.query_classifier = QueryClassifier()
        self.confidence_scorer = ConfidenceScorer()
        self.conflict_detector = ConflictDetector()
        self.llm_reranker = LLMReranker()

        # Setup logging
        session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.search_logger = SearchLogger(session_id)

        # Initialize query processor if enabled
        self.use_query_processor = use_query_processor if use_query_processor is not None else USE_QUERY_PROCESSOR
        if self.use_query_processor:
            try:
                self.query_processor = OHIPQueryProcessor(
                    sql_client=self.sql_client,
                    vector_client=self.vector_client
                )
                logger.info("Schedule tool initialized with LLM-powered query processor")
            except Exception as e:
                logger.warning(f"Failed to initialize query processor: {e}. Falling back to legacy mode.")
                self.use_query_processor = False
                self.query_processor = None
        else:
            self.query_processor = None
            logger.info("Schedule tool initialized with intelligent routing (legacy mode)")
    
    async def execute(self, request: Dict[str, Any]) -> ScheduleGetResponse:
        """
        Execute schedule query with intelligent routing.

        Routes to enhanced query processor if enabled, otherwise uses legacy path.

        Args:
            request: Request dictionary with query parameters

        Returns:
            ScheduleGetResponse with results based on optimal search strategy
        """
        # Start operation logging
        operation_id = self.search_logger.start_operation(
            tool="schedule.get",
            query=request.get("q"),
            request_data=request
        )

        try:
            # Route to query processor if enabled and this is a natural language query
            if self.use_query_processor and 'q' in request and request.get("q"):
                logger.info("Using enhanced query processor for natural language understanding")
                return await self._execute_with_query_processor(request)

            # Legacy path: Classify query to determine strategy
            strategy, reason = self.query_classifier.classify(
                query=request.get("q"),
                tool="schedule.get",
                codes=request.get("codes")
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
    
    async def _execute_sql_only(self, request: Dict[str, Any]) -> ScheduleGetResponse:
        """
        Execute SQL-only search for structured queries.
        Used for direct code lookups.
        """
        start_time = datetime.now()

        # Build SQL query for codes
        codes = request.get("codes")
        query = request.get("q", "")
        if codes:
            sql_results = await self._sql_code_lookup(codes)
        else:
            # Single code in query
            sql_results = await self._sql_code_lookup([query.strip()])

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        self.search_logger.log_sql_search(
            query=f"Code lookup: {codes or query}",
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
    
    async def _execute_vector_with_rerank(self, request: Dict[str, Any]) -> ScheduleGetResponse:
        """
        Execute vector search with LLM reranking.
        Used for natural language queries.
        """
        start_time = datetime.now()

        query = request.get("q", "")
        top_k = request.get("top_k", 10)

        # Step 1: Vector search with wider net
        vector_results = await self._vector_semantic_search(
            query=query,
            top_k=50  # Get more candidates for reranking
        )

        vector_duration = (datetime.now() - start_time).total_seconds() * 1000

        self.search_logger.log_vector_search(
            query=query,
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
            query=query,
            documents=documents,
            top_k=top_k,
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
    
    async def _execute_hybrid_smart(self, request: Dict[str, Any]) -> ScheduleGetResponse:
        """
        Execute intelligent hybrid search.
        Combines SQL for structured data with vector for context.
        """
        query = request.get("q", "")

        # Run both in parallel
        sql_task = self._sql_structured_search(request)
        vector_task = self._vector_semantic_search(query, top_k=30)
        
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
            query=query,
            results_count=len(sql_results) if sql_results else 0,
            duration_ms=0  # Would need timing
        )
        self.search_logger.log_vector_search(
            query=query,
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
                query=query,
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
    
    async def _execute_sql_primary(self, request: Dict[str, Any]) -> ScheduleGetResponse:
        """
        Execute SQL-primary search with vector fallback.
        """
        top_k = request.get("top_k", 10)

        # Try SQL first
        sql_results = await self._sql_structured_search(request)

        if sql_results and len(sql_results) >= top_k // 2:
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

    # ========================================================================
    # NEW: Query Processor Execution Path
    # ========================================================================

    async def _execute_with_query_processor(self, request: Dict[str, Any]) -> ScheduleGetResponse:
        """
        Execute query using LLM-powered query processor.

        This path provides flexible natural language understanding for complex
        billing queries like:
        - "Can I bill C124 as MRP after 3 days?"
        - "ER consultation as internist"
        - "house call codes for elderly patient"

        Args:
            request: Request dictionary with query

        Returns:
            ScheduleGetResponse with enriched results
        """
        query = request.get("q", "")
        top_k = request.get("top_k", 10)

        try:
            # Step 1: Understand query intent
            intent = await self.query_processor.understand_query(query)
            logger.info(f"Query intent: type={intent.query_type}, codes={intent.billing_codes}, terms={intent.clinical_terms}")

            # Step 2: Retrieve data
            retrieval = await self.query_processor.retrieve(intent)
            logger.info(f"Retrieved: {len(retrieval.sql_results)} SQL, {len(retrieval.vector_results)} vector")

            # Step 3: Enrich with LLM
            enriched = await self.query_processor.enrich_with_llm(intent, retrieval)

            # Step 4: Convert to ScheduleGetResponse format
            response = await self._format_enhanced_response(enriched, top_k)

            return response

        except Exception as e:
            logger.error(f"Query processor error: {e}. Falling back to legacy path.")
            # Fallback to legacy vector search
            return await self._execute_vector_with_rerank(request)

    async def _format_enhanced_response(
        self,
        enriched_result,
        top_k: int
    ) -> ScheduleGetResponse:
        """
        Convert enriched query processor result to ScheduleGetResponse.

        Args:
            enriched_result: EnrichedBillingResult from query processor
            top_k: Maximum number of items to return

        Returns:
            ScheduleGetResponse in standard format
        """
        items = []
        provenance = []

        # Build items from SQL results
        for sql_result in enriched_result.retrieval.sql_results[:top_k]:
            item = self._sql_to_item(sql_result)
            if item:
                items.append(item)
                if "sql" not in provenance:
                    provenance.append("sql")

        # Add vector results if we don't have enough
        if len(items) < top_k:
            from ..utils import Document
            for vec_result in enriched_result.retrieval.vector_results[:top_k - len(items)]:
                doc = Document(
                    text=vec_result.get('text', ''),
                    metadata=vec_result.get('metadata', {}),
                    score=vec_result.get('score')
                )
                item = self._vector_to_item(doc)
                if item and not self._is_duplicate(item, items):
                    items.append(item)
                    if "vector" not in provenance:
                        provenance.append("vector")

        # Add LLM enrichment to provenance
        if enriched_result.eligibility or enriched_result.yes_no_answer:
            provenance.append("llm_enriched")

        # Build enhanced text explanation if available
        if enriched_result.billing_explanation and items:
            # Add explanation to first item's text
            items[0].text = f"{enriched_result.billing_explanation}\n\n{items[0].text}"

        # Generate citations
        citations = self._merge_citations(
            enriched_result.retrieval.sql_results[:5],
            [{'metadata': r.get('metadata', {}), 'text': r.get('text', '')}
             for r in enriched_result.retrieval.vector_results[:5]]
        )

        # Calculate confidence
        confidence = 0.85 if enriched_result.eligibility or enriched_result.yes_no_answer else 0.75
        if enriched_result.yes_no_answer:
            confidence = enriched_result.yes_no_answer.confidence

        return ScheduleGetResponse(
            provenance=provenance,
            confidence=confidence,
            items=items[:top_k],
            citations=citations,
            conflicts=[]
        )

    def _merge_citations(
        self,
        sql_results: List[Dict[str, Any]],
        vector_results  # Can be List[Dict] or List[Document]
    ) -> List[Citation]:
        """
        Merge citations from both SQL and vector results.

        Args:
            sql_results: SQL query results
            vector_results: Vector search results (with metadata) - can be dicts or Document objects

        Returns:
            List of citations
        """
        citations = []

        # Add SQL citations
        for result in sql_results[:3]:
            code = result.get('code', '')
            page = result.get('page_num')
            page_text = f", page {page}" if page else ""
            citations.append(Citation(
                source="OHIP Schedule of Benefits (March 2025)",
                loc=f"Fee code {code}{page_text}",
                page=page,
                url="https://www.ontario.ca/files/2025-03/moh-schedule-benefit-2024-03-04.pdf"
            ))

        # Add vector citations - handle both dict and Document objects
        for result in vector_results[:3]:
            # Handle Document objects or dicts
            if isinstance(result, Document):
                metadata = result.metadata or {}
            else:
                metadata = result.get('metadata', {})

            section = metadata.get('section', '')
            page = metadata.get('page_num')
            loc_parts = []
            if section:
                loc_parts.append(f"Section {section}")
            if page:
                loc_parts.append(f"page {page}")
            loc = ", ".join(loc_parts) if loc_parts else "General Reference"

            citations.append(Citation(
                source="OHIP Schedule of Benefits (March 2025)",
                loc=loc,
                page=page,
                url="https://www.ontario.ca/files/2025-03/moh-schedule-benefit-2024-03-04.pdf"
            ))

        return citations

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
    
    async def _sql_structured_search(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """SQL search for structured queries"""
        try:
            # Build query based on request
            query_text = request.get("q", "").lower()
            top_k = request.get("top_k", 10)

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
            params = (search_pattern, search_pattern.upper(), top_k * 2)
            
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
        request: Dict[str, Any]
    ) -> List[ScheduleItem]:
        """Intelligently merge SQL and vector results"""
        items = []
        top_k = request.get("top_k", 10)

        # Add SQL results first (usually more precise for codes)
        for result in sql_results[:top_k // 2]:
            item = self._sql_to_item(result)
            if item:
                items.append(item)

        # Add vector results (reranked)
        for doc in vector_results[:top_k // 2]:
            item = self._vector_to_item(doc)
            if item and not self._is_duplicate(item, items):
                items.append(item)

        return items[:top_k]
    
    def _sql_to_item(self, result: Dict[str, Any]) -> Optional[ScheduleItem]:
        """Convert SQL result to ScheduleItem using Option A minimal schema"""
        if not result:
            return None

        code = result.get('code', '')
        description = result.get('description', '')
        requirements = result.get('requirements')
        limits = result.get('limits')

        # Build combined text field
        text_parts = []
        if description:
            text_parts.append(description)
        if requirements:
            text_parts.append(f"Requirements: {requirements}")
        if limits:
            text_parts.append(f"Limits: {limits}")

        text = '\n'.join(text_parts) if text_parts else description or ''

        # Build metadata with all domain-specific fields
        metadata = {
            'code': code,
            'description': description,
            'fee': result.get('fee'),
            'requirements': requirements,
            'limits': limits,
            'page_num': result.get('page_num')
        }

        # Remove None values from metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return ScheduleItem(
            id=code,
            text=text,
            relevance_score=1.0,  # SQL exact match gets perfect score
            source='ohip_schedule:sql',
            metadata=metadata
        )
    
    def _vector_to_item(self, doc: Document) -> Optional[ScheduleItem]:
        """Convert vector result Document to ScheduleItem using Option A minimal schema"""
        if not doc:
            return None

        # Extract from metadata and text
        doc_metadata = doc.metadata or {}

        # Get fee code from metadata first, then try to parse from text
        code = doc_metadata.get('fee_code', '')
        if not code:
            import re
            code_match = re.search(r'([A-Z]\d{3,4})', doc.text)
            code = code_match.group(1) if code_match else ''

        # Build enriched text with all relevant information
        text_parts = [doc.text[:500]]  # Include more of the original text

        # Add specialty and category context if available
        if doc_metadata.get('specialty'):
            text_parts.append(f"Specialty: {doc_metadata.get('specialty')}")
        if doc_metadata.get('category'):
            text_parts.append(f"Category: {doc_metadata.get('category')}")

        # Extract billing conditions if flagged
        requirements = None
        if doc_metadata.get('has_conditions') == 'true':
            # Try to extract from text
            if 'Billing Conditions:' in doc.text:
                requirements = doc.text.split('Billing Conditions:')[1].split('\n')[0].strip()
                text_parts.append(f"Requirements: {requirements}")

        # Add limits if available
        if doc_metadata.get('limits'):
            text_parts.append(f"Limits: {doc_metadata.get('limits')}")

        combined_text = '\n'.join(text_parts)

        # Build metadata dict with all domain-specific fields
        item_metadata = {
            'code': code,
            'description': doc.text[:200],  # Store original description
            'fee': doc_metadata.get('fee_amount'),
            'requirements': requirements,
            'limits': doc_metadata.get('limits'),
            'page_num': doc_metadata.get('page_num'),
            'specialty': doc_metadata.get('specialty'),
            'category': doc_metadata.get('category'),
            'has_conditions': doc_metadata.get('has_conditions')
        }

        # Remove None values from metadata
        item_metadata = {k: v for k, v in item_metadata.items() if v is not None}

        # Get relevance score from document or use default
        relevance_score = doc.relevance_score if doc.relevance_score is not None else (doc.score / 10.0 if doc.score else 0.8)
        relevance_score = min(max(relevance_score, 0.0), 1.0)  # Clamp to 0-1

        return ScheduleItem(
            id=code or f"vec_{hash(doc.text[:50]) % 1000000}",  # Fallback ID if no code
            text=combined_text,
            relevance_score=relevance_score,
            source='ohip_schedule:vector',
            metadata=item_metadata
        )
    
    def _is_duplicate(self, item: ScheduleItem, items: List[ScheduleItem]) -> bool:
        """Check if item is duplicate based on ID or code in metadata"""
        for existing in items:
            # Check by ID first
            if existing.id == item.id:
                return True
            # Also check by code in metadata
            existing_code = existing.metadata.get('code')
            item_code = item.metadata.get('code')
            if existing_code and item_code and existing_code == item_code:
                return True
        return False
    
    def _generate_sql_citations(self, items: List[ScheduleItem]) -> List[Citation]:
        """Generate citations for SQL results using Option A schema"""
        citations = []
        for item in items:
            code = item.metadata.get('code')
            if code:
                # Generate specific PDF citation with page number and section_path
                page_num = item.metadata.get('page_num')
                page_text = f", page {page_num}" if page_num else ""
                section_path = item.metadata.get('section_path', '')
                citations.append(Citation(
                    source="OHIP Schedule of Benefits (March 2025)",
                    loc=f"Fee code {code}{page_text}",
                    section_path=section_path,
                    page=page_num,
                    url="https://www.ontario.ca/files/2025-03/moh-schedule-benefit-2024-03-04.pdf"
                ))
        return citations[:5]  # Limit citations
    
    def _generate_vector_citations(self, docs: List[Document]) -> List[Citation]:
        """Generate citations for vector results"""
        citations = []
        for doc in docs[:5]:  # Limit to top 5
            metadata = doc.metadata or {}
            # Generate specific PDF citation with section and page
            section = metadata.get('section', '')
            page = metadata.get('page_num')
            section_path = metadata.get('section_path', '')
            loc_parts = []
            if section:
                loc_parts.append(f"Section {section}")
            if page:
                loc_parts.append(f"page {page}")
            loc = ", ".join(loc_parts) if loc_parts else "General Reference"

            citations.append(Citation(
                source="OHIP Schedule of Benefits (March 2025)",
                loc=loc,
                section_path=section_path,
                page=page,
                url="https://www.ontario.ca/files/2025-03/moh-schedule-benefit-2024-03-04.pdf"
            ))
        return citations


# Export for use in server
async def schedule_get(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for schedule.get tool.

    Args:
        request: Standardized request dict with query, k, filters

    Returns:
        Response dictionary with schedule items
    """
    # Extract from standardized format
    query = request.get("query", "")
    k = request.get("k", 10)
    filters = request.get("filters", {})

    # Build internal request format
    internal_request = {
        "q": query,
        "codes": filters.get("codes"),
        "include": filters.get("include", ["codes", "fee", "limits", "documentation"]),
        "top_k": k
    }

    # Create tool instance (could cache this)
    tool = ScheduleTool()

    # Execute
    response = await tool.execute(internal_request)

    # Return as dict
    return response.dict()