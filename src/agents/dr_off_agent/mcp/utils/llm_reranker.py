"""
LLM-based document reranker for semantic relevance scoring.
Uses OpenAI API to score and rank search results.
"""

import asyncio
import json
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import openai
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Document with content and metadata"""
    text: str
    metadata: Dict[str, Any]
    score: Optional[float] = None  # Original search score
    relevance_score: Optional[float] = None  # LLM-assigned relevance


class LLMReranker:
    """
    Rerank search results using LLM for semantic relevance.
    Scores each document's relevance to the query.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        max_concurrent: int = 5
    ):
        """
        Initialize LLM reranker.
        
        Args:
            api_key: OpenAI API key (uses env var if not provided)
            model: Model to use for scoring
            temperature: Temperature for consistency (0 = deterministic)
            max_concurrent: Maximum concurrent API calls
        """
        # Initialize OpenAI client
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required for LLM reranking")
            
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_concurrent = max_concurrent
        
        logger.info(f"LLM Reranker initialized with model: {model}")
        
    async def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: Optional[int] = None,
        context: Optional[str] = None
    ) -> List[Document]:
        """
        Rerank documents by relevance to query.
        
        Args:
            query: Search query
            documents: List of documents to rerank
            top_k: Number of top documents to return (None = all)
            context: Additional context for scoring
            
        Returns:
            List of documents sorted by relevance score
        """
        if not documents:
            return []
            
        start_time = datetime.now()
        
        # Score documents in batches for efficiency
        scored_docs = await self._score_documents_batch(
            query, documents, context
        )
        
        # Sort by relevance score
        scored_docs.sort(key=lambda d: d.relevance_score or 0, reverse=True)
        
        # Apply top_k if specified
        if top_k and top_k < len(scored_docs):
            scored_docs = scored_docs[:top_k]
            
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"Reranked {len(documents)} to {len(scored_docs)} documents in {duration_ms:.2f}ms")
        
        return scored_docs
        
    async def _score_documents_batch(
        self,
        query: str,
        documents: List[Document],
        context: Optional[str]
    ) -> List[Document]:
        """
        Score documents in parallel batches.
        
        Args:
            query: Search query
            documents: Documents to score
            context: Additional context
            
        Returns:
            Documents with relevance scores
        """
        # Create scoring tasks
        tasks = []
        for i in range(0, len(documents), self.max_concurrent):
            batch = documents[i:i + self.max_concurrent]
            batch_tasks = [
                self._score_single_document(query, doc, context)
                for doc in batch
            ]
            tasks.extend(batch_tasks)
            
        # Execute scoring
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        scored_docs = []
        for doc, result in zip(documents, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to score document: {result}")
                doc.relevance_score = 0.0
            else:
                doc.relevance_score = result
            scored_docs.append(doc)
            
        return scored_docs
        
    async def _score_single_document(
        self,
        query: str,
        document: Document,
        context: Optional[str]
    ) -> float:
        """
        Score a single document's relevance.
        
        Args:
            query: Search query
            document: Document to score
            context: Additional context
            
        Returns:
            Relevance score (0-10)
        """
        # Build scoring prompt
        prompt = self._build_scoring_prompt(query, document, context)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=50
            )
            
            # Parse score from response
            score_text = response.choices[0].message.content.strip()
            score = self._parse_score(score_text)
            
            return score
            
        except Exception as e:
            logger.error(f"Error scoring document: {e}")
            return 0.0
            
    def _get_system_prompt(self) -> str:
        """Get system prompt for scoring"""
        return """You are a medical document relevance scorer for Ontario healthcare.
        
Your task is to score how relevant a document is to a search query on a scale of 0-10.

Consider:
1. Direct answer to the query (highest weight)
2. Topic relevance
3. Practical applicability
4. Currency/timeliness of information

Output ONLY a number between 0-10. No explanation needed.
- 10: Perfect direct answer
- 7-9: Highly relevant, addresses the query
- 4-6: Somewhat relevant, related topic
- 1-3: Marginally relevant
- 0: Not relevant"""

    def _build_scoring_prompt(
        self,
        query: str,
        document: Document,
        context: Optional[str]
    ) -> str:
        """
        Build prompt for scoring document.
        
        Args:
            query: Search query
            document: Document to score
            context: Additional context
            
        Returns:
            Scoring prompt
        """
        # Extract relevant metadata
        metadata = document.metadata or {}
        title = metadata.get('title', 'Unknown')
        source = metadata.get('source', 'Unknown')
        doc_type = metadata.get('document_type', 'Unknown')
        
        # Truncate document text if too long
        max_text_length = 1500
        doc_text = document.text
        if len(doc_text) > max_text_length:
            doc_text = doc_text[:max_text_length] + "..."
            
        prompt = f"""Score the relevance of this document to the query.

Query: {query}"""

        if context:
            prompt += f"\nContext: {context}"
            
        prompt += f"""

Document Info:
- Title: {title}
- Source: {source}
- Type: {doc_type}

Document Text:
{doc_text}

Relevance Score (0-10):"""
        
        return prompt
        
    def _parse_score(self, score_text: str) -> float:
        """
        Parse score from LLM response.
        
        Args:
            score_text: LLM response text
            
        Returns:
            Parsed score (0-10)
        """
        try:
            # Try to extract number from response
            import re
            match = re.search(r'(\d+\.?\d*)', score_text.strip())
            if match:
                score = float(match.group(1))
                # Ensure score is in valid range
                return min(max(score, 0.0), 10.0)
        except:
            pass
            
        logger.warning(f"Failed to parse score from: {score_text}")
        return 0.0
        
    async def rerank_with_explanation(
        self,
        query: str,
        documents: List[Document],
        top_k: Optional[int] = None
    ) -> List[Tuple[Document, str]]:
        """
        Rerank documents with explanations for scores.
        Useful for debugging and transparency.
        
        Args:
            query: Search query
            documents: Documents to rerank
            top_k: Number of top documents
            
        Returns:
            List of (document, explanation) tuples
        """
        if not documents:
            return []
            
        # Score with explanations
        results = []
        for doc in documents[:10]:  # Limit for efficiency
            score, explanation = await self._score_with_explanation(query, doc)
            doc.relevance_score = score
            results.append((doc, explanation))
            
        # Sort by score
        results.sort(key=lambda x: x[0].relevance_score or 0, reverse=True)
        
        if top_k:
            results = results[:top_k]
            
        return results
        
    async def _score_with_explanation(
        self,
        query: str,
        document: Document
    ) -> Tuple[float, str]:
        """
        Score document with explanation.
        
        Args:
            query: Search query
            document: Document to score
            
        Returns:
            Tuple of (score, explanation)
        """
        prompt = self._build_scoring_prompt(query, document, None)
        prompt += "\n\nProvide score and brief explanation in format: SCORE: X | REASON: explanation"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=100
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse score and explanation
            if "SCORE:" in response_text and "|" in response_text:
                parts = response_text.split("|")
                score_part = parts[0].replace("SCORE:", "").strip()
                reason_part = parts[1].replace("REASON:", "").strip() if len(parts) > 1 else ""
                
                score = self._parse_score(score_part)
                return score, reason_part
            else:
                score = self._parse_score(response_text)
                return score, "No explanation provided"
                
        except Exception as e:
            logger.error(f"Error scoring with explanation: {e}")
            return 0.0, f"Error: {str(e)}"