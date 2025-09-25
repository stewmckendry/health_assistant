"""
Query classifier for intelligent search strategy routing.
Determines optimal search approach based on query characteristics.
"""

import re
import logging
from enum import Enum
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class SearchStrategy(Enum):
    """Search strategy options for query processing"""
    SQL_ONLY = "sql_only"  # Structured data only
    VECTOR_ONLY = "vector_only"  # Semantic search only
    VECTOR_WITH_RERANK = "vector_with_rerank"  # Semantic + LLM reranking
    SQL_PRIMARY = "sql_primary"  # SQL first, vector fallback
    HYBRID_SMART = "hybrid_smart"  # Both with intelligent merge


class QueryClassifier:
    """
    Classifies queries to determine optimal search strategy.
    Routes to SQL for structured data, Vector for natural language.
    """
    
    # OHIP fee code patterns
    OHIP_CODE_PATTERNS = [
        r'^[A-Z]\d{3,4}$',  # A123, A1234
        r'^[A-Z]\d{3,4}[A-Z]?$',  # A123B
        r'^[GKLPQRXZ]\d{3,4}$',  # Special sections
    ]
    
    # DIN patterns (8-digit drug identification numbers)
    DIN_PATTERN = r'^\d{8}$'
    
    # Structured query indicators
    STRUCTURED_OPERATORS = ['>', '<', '>=', '<=', '=', 'BETWEEN', 'IN']
    
    # Natural language indicators
    NATURAL_LANGUAGE_INDICATORS = [
        'how', 'what', 'when', 'where', 'why', 'which',
        'can i', 'should i', 'is it', 'are there',
        'requirements', 'guidelines', 'documentation',
        'billing', 'coverage', 'eligibility'
    ]
    
    def __init__(self):
        """Initialize query classifier with compiled patterns"""
        self.ohip_patterns = [re.compile(p, re.IGNORECASE) for p in self.OHIP_CODE_PATTERNS]
        self.din_pattern = re.compile(self.DIN_PATTERN)
        
    def classify(self, query: str, tool: str, codes: Optional[List[str]] = None) -> Tuple[SearchStrategy, str]:
        """
        Classify query to determine search strategy.
        
        Args:
            query: The search query string
            tool: The tool being used (schedule.get, odb.get, etc.)
            codes: Optional list of specific codes to lookup
            
        Returns:
            Tuple of (SearchStrategy, reason for classification)
        """
        # Normalize query for analysis
        query_lower = query.lower().strip() if query else ""
        
        # Priority 1: Direct code lookups
        if codes and len(codes) > 0:
            logger.debug(f"Classified as SQL_ONLY: Direct code lookup for {codes}")
            return SearchStrategy.SQL_ONLY, "Direct code list provided"
            
        # Priority 2: Check for OHIP codes
        if self._is_ohip_code(query):
            logger.debug(f"Classified as SQL_ONLY: OHIP code pattern detected: {query}")
            return SearchStrategy.SQL_ONLY, "OHIP fee code pattern"
            
        # Priority 3: Check for DIN
        if self._is_din(query):
            logger.debug(f"Classified as SQL_ONLY: DIN pattern detected: {query}")
            return SearchStrategy.SQL_ONLY, "DIN (Drug Identification Number)"
            
        # Priority 4: Check for structured operators
        if self._has_structured_operators(query):
            logger.debug(f"Classified as SQL_PRIMARY: Structured operators detected")
            return SearchStrategy.SQL_PRIMARY, "Contains structured query operators"
            
        # Tool-specific classification
        if tool == "schedule.get":
            return self._classify_schedule_query(query_lower)
        elif tool == "odb.get":
            return self._classify_odb_query(query_lower)
        elif tool == "adp.get":
            return self._classify_adp_query(query_lower)
        elif tool == "coverage.answer":
            # Coverage tool always uses vector with reranking for NL queries
            return SearchStrategy.VECTOR_WITH_RERANK, "Coverage orchestrator - natural language"
            
        # Default: Natural language with reranking
        if self._is_natural_language(query_lower):
            logger.debug(f"Classified as VECTOR_WITH_RERANK: Natural language detected")
            return SearchStrategy.VECTOR_WITH_RERANK, "Natural language query"
            
        # Fallback
        logger.debug(f"Classified as VECTOR_WITH_RERANK: Default fallback")
        return SearchStrategy.VECTOR_WITH_RERANK, "Default strategy"
        
    def _is_ohip_code(self, query: str) -> bool:
        """Check if query matches OHIP code pattern"""
        query = query.strip()
        for pattern in self.ohip_patterns:
            if pattern.match(query):
                return True
        
        # Check for multiple codes separated by comma or space
        tokens = re.split(r'[,\s]+', query)
        if len(tokens) <= 5:  # Reasonable limit for code list
            all_codes = all(
                any(p.match(t) for p in self.ohip_patterns)
                for t in tokens if t
            )
            if all_codes and len(tokens) > 0:
                return True
                
        return False
        
    def _is_din(self, query: str) -> bool:
        """Check if query is a DIN"""
        return bool(self.din_pattern.match(query.strip()))
        
    def _has_structured_operators(self, query: str) -> bool:
        """Check for SQL-like operators"""
        query_upper = query.upper()
        # Use word boundaries to avoid false positives (e.g., "billing" containing "IN")
        import re
        for op in self.STRUCTURED_OPERATORS:
            if re.search(r'\b' + re.escape(op) + r'\b', query_upper):
                return True
        return False
        
    def _is_natural_language(self, query: str) -> bool:
        """Check if query appears to be natural language"""
        # Check for question words or phrases
        for indicator in self.NATURAL_LANGUAGE_INDICATORS:
            if indicator in query:
                return True
                
        # Check for sentence-like structure (multiple words)
        word_count = len(query.split())
        if word_count >= 3:
            return True
            
        return False
        
    def _classify_schedule_query(self, query: str) -> Tuple[SearchStrategy, str]:
        """Classify schedule.get specific queries"""
        
        # Keywords suggesting code lookup
        code_keywords = ['code', 'fee code', 'billing code', 'ohip code']
        if any(kw in query for kw in code_keywords) and len(query.split()) <= 4:
            return SearchStrategy.SQL_PRIMARY, "Code lookup keywords"
            
        # Natural language about billing scenarios - use hybrid for better coverage
        billing_scenarios = [
            'discharge', 'admission', 'consultation', 'virtual',
            'house call', 'after hours', 'weekend', 'emergency'
        ]
        if any(scenario in query for scenario in billing_scenarios):
            return SearchStrategy.HYBRID_SMART, "Billing scenario - needs both SQL descriptions and vector context"
            
        return SearchStrategy.VECTOR_WITH_RERANK, "Schedule natural language query"
        
    def _classify_odb_query(self, query: str) -> Tuple[SearchStrategy, str]:
        """Classify odb.get specific queries"""
        
        # Drug names often need both vector (for variations) and SQL (for data)
        if len(query.split()) <= 2 and not self._is_natural_language(query):
            # Single drug name - use hybrid to find variations
            return SearchStrategy.HYBRID_SMART, "Drug name lookup"
            
        # Questions about coverage need vector search
        coverage_keywords = ['covered', 'coverage', 'formulary', 'alternatives', 'generic']
        if any(kw in query for kw in coverage_keywords):
            return SearchStrategy.VECTOR_WITH_RERANK, "Coverage question"
            
        return SearchStrategy.HYBRID_SMART, "Drug query - needs both sources"
        
    def _classify_adp_query(self, query: str) -> Tuple[SearchStrategy, str]:
        """Classify adp.get specific queries"""
        
        # Device categories need vector for semantic matching
        device_terms = [
            'wheelchair', 'walker', 'scooter', 'mobility',
            'hearing aid', 'prosthetic', 'orthotic', 'cpap'
        ]
        if any(term in query for term in device_terms):
            return SearchStrategy.VECTOR_WITH_RERANK, "Device description query"
            
        # Funding questions might need SQL for percentages
        if 'funding' in query or 'percent' in query or '%' in query:
            return SearchStrategy.HYBRID_SMART, "Funding percentage query"
            
        return SearchStrategy.VECTOR_WITH_RERANK, "ADP natural language query"
        
    def explain_classification(self, strategy: SearchStrategy, reason: str) -> str:
        """
        Provide human-readable explanation of classification.
        
        Args:
            strategy: The chosen search strategy
            reason: Brief reason for classification
            
        Returns:
            Detailed explanation string
        """
        explanations = {
            SearchStrategy.SQL_ONLY: 
                f"Using SQL database only for structured lookup: {reason}",
            SearchStrategy.VECTOR_ONLY: 
                f"Using vector search only for semantic matching: {reason}",
            SearchStrategy.VECTOR_WITH_RERANK: 
                f"Using vector search with LLM reranking for natural language: {reason}",
            SearchStrategy.SQL_PRIMARY: 
                f"Using SQL first with vector fallback: {reason}",
            SearchStrategy.HYBRID_SMART: 
                f"Using both SQL and vector with intelligent merging: {reason}"
        }
        
        return explanations.get(strategy, f"Strategy {strategy.value}: {reason}")