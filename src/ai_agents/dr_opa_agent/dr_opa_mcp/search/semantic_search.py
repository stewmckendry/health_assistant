"""
Semantic search implementation with Vector → Rerank → Filter algorithm.
Now supports hybrid (dense + BM25) retrieval with RRF fusion.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
import json
import openai
from openai import AsyncOpenAI
import os

if TYPE_CHECKING:
    from ..models.request import StandardToolRequest

# Optional imports for BM25 and cross-encoder (graceful fallback if not installed)
try:
    from ..retrieval.bm25_client import BM25Client
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("BM25Client not available - hybrid search disabled (whoosh not installed)")

try:
    from ..retrieval.rrf_fusion import RRFFusion
    RRF_AVAILABLE = True
except ImportError:
    RRF_AVAILABLE = False

try:
    from ..retrieval.cross_encoder_reranker import CrossEncoderReranker
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    if not BM25_AVAILABLE:
        logger.warning("CrossEncoderReranker not available - reranking disabled (torch/transformers not installed)")

logger = logging.getLogger(__name__)

class SemanticSearchEngine:
    """
    Implements the Vector → Rerank → Filter search algorithm.
    Now supports hybrid (dense + BM25) retrieval with RRF fusion.
    """

    def __init__(self, vector_client, openai_api_key: Optional[str] = None):
        """
        Initialize the semantic search engine.

        Args:
            vector_client: VectorClient instance for Chroma DB access
            openai_api_key: OpenAI API key for LLM reranking
        """
        self.vector_client = vector_client
        self.openai_client = AsyncOpenAI(
            api_key=openai_api_key or os.getenv('OPENAI_API_KEY')
        )

        # Initialize BM25 client for sparse retrieval (optional)
        if BM25_AVAILABLE:
            self.bm25_client = BM25Client()
            logger.info("BM25Client initialized")
        else:
            self.bm25_client = None
            logger.info("BM25Client not available - hybrid search will be disabled")

        # Initialize RRF fusion (optional)
        if RRF_AVAILABLE:
            self.rrf_fusion = RRFFusion(c=60.0)
        else:
            self.rrf_fusion = None

        # Initialize cross-encoder reranker (optional, lazy initialization)
        self.ce_reranker = None  # Lazy initialization to avoid loading model unnecessarily

        logger.info(f"SemanticSearchEngine initialized (BM25: {BM25_AVAILABLE}, CrossEncoder: {CROSS_ENCODER_AVAILABLE})")
    
    async def search(
        self,
        query: Optional[str] = None,
        sources: Optional[List[str]] = None,
        k: Optional[int] = None,
        use_reranking: bool = True,
        use_hybrid: bool = False,  # Disable hybrid mode (Issue #2 showed no improvement)
        use_ce_reranking: bool = False,  # NEW: Enable cross-encoder reranking (DISABLED - using LLM reranking)
        where_filter: Optional[Dict] = None,  # NEW: Custom ChromaDB where filter
        request: Optional['StandardToolRequest'] = None
    ) -> List[Dict[str, Any]]:
        """
        Main search method with hybrid (dense + BM25) support.

        Can be called either with individual parameters or with StandardToolRequest.

        Args:
            query: Natural language search query (or use request.query)
            sources: Filter by source organizations (or use request.filters['sources'])
            k: Number of final results to return (or use request.k)
            use_reranking: Whether to use LLM reranking
            use_hybrid: Whether to use hybrid (dense + BM25) retrieval with RRF fusion
            use_ce_reranking: Whether to use cross-encoder reranking (recommended for best MRR/nDCG)
            where_filter: Custom ChromaDB where filter dict (overrides sources filter)
            request: StandardToolRequest object (standardized interface)

        Returns:
            List of relevant documents with metadata
        """
        # Extract parameters from StandardToolRequest if provided
        if request is not None:
            query = request.query
            k = request.k
            filters = request.filters or {}
            sources = filters.get('sources', sources)

        # Set defaults if not provided
        if k is None:
            k = 10

        logger.info(f"=== SEMANTIC SEARCH START (hybrid={use_hybrid}) ===")
        logger.info(f"Query: {query}")
        logger.info(f"Filters: sources={sources}")

        if use_hybrid:
            # === HYBRID MODE: Dense + BM25 + RRF ===

            # Check if hybrid dependencies are available
            if not BM25_AVAILABLE or not RRF_AVAILABLE:
                logger.warning("Hybrid mode requested but dependencies not available - falling back to dense-only search")
                use_hybrid = False
            else:
                # Step 1: Parallel retrieval (dense + sparse)
                logger.info("Step 1: Hybrid Retrieval - Running dense + BM25 in parallel...")

                dense_task = self._vector_search(query=query, sources=sources, n_results=50, where_filter=where_filter)
                sparse_task = self.bm25_client.search(query=query, sources=sources, n_results=50)

                dense_results, sparse_results = await asyncio.gather(dense_task, sparse_task)

                logger.info(f"  Dense: {len(dense_results)} results, BM25: {len(sparse_results)} results")

                # Log top results from each retriever
                if dense_results:
                    top_dense = [f"{r.get('document_id', r.get('id', 'unknown'))} ({r.get('distance', r.get('similarity_score', 0)):.3f})" for r in dense_results[:3]]
                    logger.info(f"  Top 3 dense: {top_dense}")
                if sparse_results:
                    top_sparse = [f"{r.get('document_id', r.get('id', 'unknown'))} ({r.get('bm25_score', 0):.3f})" for r in sparse_results[:3]]
                    logger.info(f"  Top 3 sparse: {top_sparse}")

                # Step 2: RRF Fusion
                logger.info("Step 2: RRF Fusion - Merging dense + sparse rankings...")
                fused = self.rrf_fusion.fuse(dense_results, sparse_results, k=50)
                logger.info(f"  RRF fusion produced {len(fused)} unique documents")

                # Log provenance distribution
                provenance_counts = {}
                for doc in fused:
                    prov = doc.get('provenance', 'unknown')
                    provenance_counts[prov] = provenance_counts.get(prov, 0) + 1
                logger.info(f"  Provenance distribution: {provenance_counts}")

                # Log top fused results
                if fused:
                    top_fused = [f"{r.get('id', 'unknown')} (rrf={r.get('rrf_score', 0):.4f}, {r.get('provenance', '?')})" for r in fused[:5]]
                    logger.info(f"  Top 5 RRF: {top_fused}")

                candidates = fused

        if not use_hybrid:
            # === DENSE-ONLY MODE (backward compatibility) ===
            logger.info("Step 1: Vector Search (dense-only) - Retrieving candidates...")
            candidates = await self._vector_search(
                query=query,
                sources=sources,
                n_results=50,  # Get 5x more than needed for reranking
                where_filter=where_filter
            )
            logger.info(f"  Vector search returned {len(candidates)} candidates")

        if not candidates:
            logger.warning("No candidates found")
            return []

        # Step 3: Cross-Encoder Reranking (NEW - highest impact on MRR/nDCG)
        if use_ce_reranking and len(candidates) > 0:
            if not CROSS_ENCODER_AVAILABLE:
                logger.warning("Cross-encoder reranking requested but not available (torch/transformers not installed) - skipping")
            else:
                step_num = 3 if use_hybrid else 2
                logger.info(f"Step {step_num}: Cross-Encoder Reranking - Scoring relevance...")

                # Lazy initialize cross-encoder reranker
                if self.ce_reranker is None:
                    logger.info("Initializing cross-encoder reranker (first use)...")
                    self.ce_reranker = CrossEncoderReranker()

                # Log before reranking
                before_ids = [doc.get('document_id', doc.get('id', 'unknown')) for doc in candidates[:5]]
                logger.info(f"  Top 5 before CE reranking: {before_ids}")

                # Rerank with cross-encoder
                reranked = self.ce_reranker.rerank(
                    query=query,
                    documents=candidates,
                    top_k=min(20, len(candidates))  # Narrow to top 20
                )

                # Log after reranking
                after_ids = [doc.get('document_id', doc.get('id', 'unknown')) for doc in reranked[:5]]
                logger.info(f"  Top 5 after CE reranking: {after_ids}")
                logger.info(f"  Cross-encoder reranking narrowed to {len(reranked)} documents")

        # Step 3b: Optional LLM Reranking (legacy, can be used in addition to CE)
        elif use_reranking and len(candidates) > 0:
            step_num = 3 if use_hybrid else 2
            logger.info(f"Step {step_num}: LLM Reranking - Scoring relevance...")
            reranked = await self._llm_rerank(
                query=query,
                documents=candidates,
                k=min(20, len(candidates))  # Narrow to 20 or fewer
            )
            logger.info(f"  LLM reranking narrowed to {len(reranked)} documents")
        else:
            logger.info(f"Step {3 if use_hybrid else 2}: Skipping reranking (disabled or no candidates)")
            reranked = candidates[:20]

        # Step 4: Parent Context Enrichment
        # Enrich child chunks with parent context
        step_num = 4 if use_hybrid else 3
        logger.info(f"Step {step_num}: Parent Context Enrichment - Enriching child chunks...")
        enriched_results = await self._enrich_with_parent_context(reranked[:k])
        logger.info(f"  Enriched {len([r for r in enriched_results if r.get('has_parent_context')])} child chunks with parent context")

        # Return top K results
        final_results = enriched_results
        mode = "HYBRID" if use_hybrid else "DENSE"
        logger.info(f"=== {mode} SEARCH COMPLETE: Returning {len(final_results)} results ===")

        return final_results
    
    async def _vector_search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        n_results: int = 50,
        where_filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Step 1: Vector search across collections.

        Args:
            query: Search query
            sources: Source organizations to search
            n_results: Number of candidates to retrieve
            where_filter: Custom ChromaDB where filter (overrides sources filter)

        Returns:
            List of candidate documents with metadata
        """
        logger.debug(f"Vector search: query='{query[:50]}...', sources={sources}, n={n_results}, where_filter={where_filter is not None}")

        # Determine which collections to search
        collection_map = {
            'cpso': 'opa_cpso_corpus',
            'pho': 'opa_pho_corpus',
            'cep': 'opa_cep_corpus',
            'quality_standards': 'opa_quality_standards_corpus',
            'ontario_health_quality_standards': 'opa_quality_standards_corpus',  # Alias for compatibility
            'choosing_wisely': 'opa_choosing_wisely_corpus',
            'choosing_wisely_canada': 'opa_choosing_wisely_corpus'  # Alias for compatibility
        }
        
        if sources:
            collections_to_search = [collection_map[s] for s in sources if s in collection_map]
        else:
            collections_to_search = list(collection_map.values())
        
        logger.debug(f"Searching collections: {collections_to_search}")
        
        # Search across collections
        all_results = []
        for collection_name in collections_to_search:
            try:
                logger.debug(f"Searching {collection_name}...")
                results = await self.vector_client.search_collection(
                    collection_name=collection_name,
                    query=query,
                    n_results=n_results,
                    where=where_filter  # Pass where_filter as 'where' parameter
                )
                
                # Format results with consistent structure
                for i, doc_id in enumerate(results.get('ids', [[]])[0]):
                    result = {
                        'document_id': doc_id,
                        'text': results['documents'][0][i] if i < len(results.get('documents', [[]])[0]) else '',
                        'metadata': results['metadatas'][0][i] if i < len(results.get('metadatas', [[]])[0]) else {},
                        'distance': results['distances'][0][i] if i < len(results.get('distances', [[]])[0]) else 1.0,
                        'collection': collection_name
                    }
                    all_results.append(result)
                    
                logger.debug(f"Found {len(results.get('ids', [[]])[0])} results in {collection_name}")
                
            except Exception as e:
                logger.error(f"Error searching {collection_name}: {e}")
                continue
        
        # Sort by distance (lower is better)
        all_results.sort(key=lambda x: x.get('distance', 1.0))
        
        logger.debug(f"Total vector search results: {len(all_results)}")
        return all_results
    
    async def _llm_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Step 2: LLM-based reranking for improved relevance.
        
        Args:
            query: Original search query
            documents: Candidate documents from vector search
            k: Number of documents to keep after reranking
            
        Returns:
            Reranked list of documents
        """
        logger.debug(f"LLM reranking {len(documents)} documents")
        
        # Batch reranking for efficiency
        reranking_tasks = []
        for doc in documents[:30]:  # Limit to top 30 for cost
            task = self._score_document(query, doc)
            reranking_tasks.append(task)
        
        # Execute reranking in parallel
        scores = await asyncio.gather(*reranking_tasks)
        
        # Attach scores to documents
        for doc, score in zip(documents[:30], scores):
            doc['relevance_score'] = score
            logger.debug(f"Document {doc.get('metadata', {}).get('document_title', 'Unknown')[:30]}: score={score}")
        
        # Add minimal scores to remaining documents
        for doc in documents[30:]:
            doc['relevance_score'] = 0.0
        
        # Sort by relevance score
        documents.sort(key=lambda x: x.get('relevance_score', 0.0), reverse=True)
        
        logger.info(f"Top 3 reranked results: {[d.get('relevance_score', 0) for d in documents[:3]]}")
        
        return documents[:k]
    
    async def _score_document(self, query: str, document: Dict[str, Any]) -> float:
        """
        Score a single document's relevance to the query using LLM.
        
        Args:
            query: Search query
            document: Document to score
            
        Returns:
            Relevance score (0-10)
        """
        metadata = document.get('metadata', {})
        text_preview = document.get('text', '')[:500]
        
        prompt = f"""Score the relevance of this document to the query on a scale of 0-10.

Query: {query}

Document Title: {metadata.get('document_title', metadata.get('title', 'Unknown'))}
Document Type: {metadata.get('document_type', 'Unknown')}
Source: {metadata.get('source_org', 'Unknown')}
Section: {metadata.get('section_heading', 'N/A')}

Document Excerpt:
{text_preview}

Scoring Guidelines:
- 9-10: Directly answers the query
- 7-8: Highly relevant to the query topic
- 5-6: Related but not directly addressing the query
- 3-4: Tangentially related
- 0-2: Not relevant

Respond with ONLY a number between 0 and 10:"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Fast and cheap for reranking
                messages=[
                    {"role": "system", "content": "You are a relevance scoring system. Respond only with a number between 0 and 10."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=5,
                temperature=0.0
            )
            
            score_text = response.choices[0].message.content.strip()
            score = float(score_text)
            return min(max(score, 0.0), 10.0)  # Ensure within range
            
        except Exception as e:
            logger.error(f"Error scoring document: {e}")
            # Fallback to distance-based scoring
            distance = document.get('distance', 1.0)
            return max(0, 10 * (1 - distance))  # Convert distance to score
    
    async def _enrich_with_parent_context(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich child chunks with parent chunk context for better comprehension.

        For each child chunk in results, fetches the parent chunk and prepends
        its content to provide full context. This improves AI agent understanding
        of fragmented information.

        Args:
            results: List of search results (may include child chunks)

        Returns:
            Results with parent context added to child chunks
        """
        enriched_results = []

        for result in results:
            metadata = result.get('metadata', {})
            chunk_type = metadata.get('chunk_type', '')

            # Only enrich child chunks
            if chunk_type == 'child':
                parent_id = metadata.get('parent_id')
                collection = result.get('collection')

                if parent_id and collection:
                    try:
                        # Fetch parent chunk from the same collection
                        parent_results = await self.vector_client.get_by_id(
                            collection_name=collection,
                            ids=[parent_id]
                        )

                        if parent_results and parent_results.get('documents'):
                            parent_text = parent_results['documents'][0]
                            parent_metadata = parent_results.get('metadatas', [{}])[0]

                            # Prepend parent context to child text
                            # Format: [PARENT CONTEXT]\n\n[CHILD CONTENT]
                            enriched_text = f"[PARENT CONTEXT - {parent_metadata.get('section_title', 'Section')}]\n{parent_text}\n\n[DETAILED CONTENT]\n{result['text']}"

                            # Update result with enriched text
                            enriched_result = result.copy()
                            enriched_result['text'] = enriched_text
                            enriched_result['has_parent_context'] = True
                            enriched_result['parent_chunk_id'] = parent_id

                            logger.debug(f"Enriched child chunk {result.get('document_id')} with parent {parent_id}")
                            enriched_results.append(enriched_result)
                        else:
                            # Parent not found, return original
                            logger.warning(f"Parent chunk {parent_id} not found for child {result.get('document_id')}")
                            enriched_results.append(result)

                    except Exception as e:
                        logger.error(f"Error enriching child chunk with parent context: {e}")
                        enriched_results.append(result)
                else:
                    # Child chunk missing parent_id, return original
                    enriched_results.append(result)
            else:
                # Not a child chunk (parent or flat), return as-is
                enriched_results.append(result)

        return enriched_results

    def format_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format search results for API response with hierarchical citations.

        Args:
            results: Raw search results

        Returns:
            Formatted results with consistent structure and section_path for citations
        """
        formatted = []
        for result in results:
            metadata = result.get('metadata', {})

            formatted_result = {
                'document_id': result.get('document_id', ''),
                'document_title': metadata.get('document_title', metadata.get('title', '')),
                'source_org': metadata.get('source_org', ''),
                'document_type': metadata.get('document_type', ''),
                'section_heading': metadata.get('section_heading', ''),
                'section_path': metadata.get('section_path', ''),  # Hierarchical source path
                'section_title': metadata.get('section_title', ''),  # Current section title
                'text': result.get('text', ''),
                'relevance_score': result.get('relevance_score', 0.0),
                'distance': result.get('distance', 1.0),
                'policy_level': metadata.get('policy_level', ''),
                'effective_date': metadata.get('effective_date', ''),
                'source_url': metadata.get('source_url', ''),
                'topics': metadata.get('topics', '').split(',') if metadata.get('topics') else [],
                'chunk_type': metadata.get('chunk_type', 'unknown'),
                'has_parent_context': result.get('has_parent_context', False),  # Flag if child was enriched
                'parent_chunk_id': result.get('parent_chunk_id', '')  # Parent ID if child chunk
            }
            formatted.append(formatted_result)

        return formatted