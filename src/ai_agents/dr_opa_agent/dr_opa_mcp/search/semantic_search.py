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

from ..retrieval.bm25_client import BM25Client
from ..retrieval.rrf_fusion import RRFFusion

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

        # Initialize BM25 client for sparse retrieval
        self.bm25_client = BM25Client()

        # Initialize RRF fusion
        self.rrf_fusion = RRFFusion(c=60.0)

        logger.info("SemanticSearchEngine initialized with hybrid (dense + BM25) support")
    
    async def search(
        self,
        query: Optional[str] = None,
        sources: Optional[List[str]] = None,
        document_types: Optional[List[str]] = None,
        policy_level: Optional[str] = None,
        after_date: Optional[str] = None,
        k: Optional[int] = None,
        use_reranking: bool = True,
        use_hybrid: bool = True,  # NEW: Enable hybrid mode
        request: Optional['StandardToolRequest'] = None
    ) -> List[Dict[str, Any]]:
        """
        Main search method with hybrid (dense + BM25) support.

        Can be called either with individual parameters or with StandardToolRequest.

        Args:
            query: Natural language search query (or use request.query)
            sources: Filter by source organizations (or use request.filters['sources'])
            document_types: Filter by document type (or use request.filters['doc_types'])
            policy_level: Filter by policy level (or use request.filters['policy_level'])
            after_date: Filter for documents after this date (or use request.filters['after_date'])
            k: Number of final results to return (or use request.k)
            use_reranking: Whether to use LLM reranking
            use_hybrid: Whether to use hybrid (dense + BM25) retrieval with RRF fusion
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
            document_types = filters.get('doc_types', document_types)
            policy_level = filters.get('policy_level', policy_level)
            after_date = filters.get('after_date', after_date)

        # Set defaults if not provided
        if k is None:
            k = 10

        logger.info(f"=== SEMANTIC SEARCH START (hybrid={use_hybrid}) ===")
        logger.info(f"Query: {query}")
        logger.info(f"Filters: sources={sources}, doc_types={document_types}, policy_level={policy_level}")

        if use_hybrid:
            # === HYBRID MODE: Dense + BM25 + RRF ===

            # Step 1: Parallel retrieval (dense + sparse)
            logger.info("Step 1: Hybrid Retrieval - Running dense + BM25 in parallel...")

            dense_task = self._vector_search(query=query, sources=sources, n_results=50)
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

        else:
            # === DENSE-ONLY MODE (backward compatibility) ===
            logger.info("Step 1: Vector Search (dense-only) - Retrieving candidates...")
            candidates = await self._vector_search(
                query=query,
                sources=sources,
                n_results=50  # Get 5x more than needed for reranking
            )
            logger.info(f"  Vector search returned {len(candidates)} candidates")

        if not candidates:
            logger.warning("No candidates found")
            return []

        # Step 3: Rerank (improve precision)
        if use_reranking and len(candidates) > 0:
            step_num = 3 if use_hybrid else 2
            logger.info(f"Step {step_num}: LLM Reranking - Scoring relevance...")
            reranked = await self._llm_rerank(
                query=query,
                documents=candidates,
                k=min(20, len(candidates))  # Narrow to 20 or fewer
            )
            logger.info(f"  Reranking narrowed to {len(reranked)} documents")
        else:
            logger.info(f"Step {3 if use_hybrid else 2}: Skipping reranking (disabled or no candidates)")
            reranked = candidates[:20]

        # Step 4: Filter (apply constraints)
        step_num = 4 if use_hybrid else 3
        logger.info(f"Step {step_num}: Metadata Filtering - Applying constraints...")
        filtered = self._apply_filters(
            documents=reranked,
            document_types=document_types,
            policy_level=policy_level,
            after_date=after_date
        )
        logger.info(f"  Filtering resulted in {len(filtered)} documents")

        # Return top K results
        final_results = filtered[:k]
        mode = "HYBRID" if use_hybrid else "DENSE"
        logger.info(f"=== {mode} SEARCH COMPLETE: Returning {len(final_results)} results ===")

        return final_results
    
    async def _vector_search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        n_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Step 1: Vector search across collections.
        
        Args:
            query: Search query
            sources: Source organizations to search
            n_results: Number of candidates to retrieve
            
        Returns:
            List of candidate documents with metadata
        """
        logger.debug(f"Vector search: query='{query[:50]}...', sources={sources}, n={n_results}")
        
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
                    n_results=n_results
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
    
    def _apply_filters(
        self,
        documents: List[Dict[str, Any]],
        document_types: Optional[List[str]] = None,
        policy_level: Optional[str] = None,
        after_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Step 3: Apply metadata filters to reranked documents.
        
        Args:
            documents: Reranked documents
            document_types: Filter by document type
            policy_level: Filter by policy level
            after_date: Filter by effective date
            
        Returns:
            Filtered list of documents
        """
        logger.debug(f"Applying filters: types={document_types}, level={policy_level}, after={after_date}")
        
        filtered = []
        for doc in documents:
            metadata = doc.get('metadata', {})
            
            # Check document type filter (handle both 'doc_type' and 'document_type' fields)
            if document_types:
                doc_type = metadata.get('doc_type') or metadata.get('document_type', '')
                if doc_type not in document_types:
                    logger.debug(f"Filtered out: wrong type ({doc_type} not in {document_types})")
                    continue
            
            # Check policy level filter
            if policy_level:
                doc_level = metadata.get('policy_level', '')
                if doc_level != policy_level:
                    logger.debug(f"Filtered out: wrong level ({doc_level} != {policy_level})")
                    continue
            
            # Check date filter
            if after_date:
                doc_date = metadata.get('effective_date', '')
                if doc_date and doc_date < after_date:
                    logger.debug(f"Filtered out: too old ({doc_date} < {after_date})")
                    continue
            
            filtered.append(doc)
        
        logger.debug(f"Filtering: {len(documents)} → {len(filtered)} documents")
        return filtered
    
    def format_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format search results for API response.
        
        Args:
            results: Raw search results
            
        Returns:
            Formatted results with consistent structure
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
                'text': result.get('text', ''),
                'relevance_score': result.get('relevance_score', 0.0),
                'distance': result.get('distance', 1.0),
                'policy_level': metadata.get('policy_level', ''),
                'effective_date': metadata.get('effective_date', ''),
                'source_url': metadata.get('source_url', ''),
                'topics': metadata.get('topics', '').split(',') if metadata.get('topics') else [],
                'chunk_type': metadata.get('chunk_type', 'unknown')
            }
            formatted.append(formatted_result)
        
        return formatted