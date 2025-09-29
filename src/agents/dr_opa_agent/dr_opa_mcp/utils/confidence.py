"""
Confidence scoring system for Dr. OPA responses.
Combines evidence from SQL and vector sources for practice guidance.
"""

from typing import List, Dict, Any


def calculate_confidence(
    sql_hits: int = 0,
    vector_matches: int = 0,
    has_conflict: bool = False,
    source_recency: float = 1.0,
    source_authority: float = 1.0
) -> float:
    """
    Calculate confidence score for OPA guidance responses.
    
    Args:
        sql_hits: Number of SQL records found
        vector_matches: Number of relevant vector passages
        has_conflict: Whether there's conflict between sources
        source_recency: Recency factor (0-1, 1 = very recent)
        source_authority: Authority factor (0-1, 1 = CPSO/Ontario Health)
    
    Returns:
        Confidence score between 0 and 1
    """
    # Base confidence scores
    SQL_BASE = 0.85  # High confidence for structured data
    VECTOR_BASE = 0.6  # Moderate confidence for semantic search only
    
    # Modifiers
    VECTOR_CORROBORATION_BONUS = 0.03  # Per matching vector passage
    CONFLICT_PENALTY = 0.15  # When sources disagree (higher penalty for practice guidance)
    MULTIPLE_SQL_HITS_BONUS = 0.02  # Per additional SQL record
    
    # Start with base confidence
    if sql_hits > 0:
        confidence = SQL_BASE
        # Add bonus for multiple SQL hits
        if sql_hits > 1:
            confidence += min((sql_hits - 1) * MULTIPLE_SQL_HITS_BONUS, 0.06)
    else:
        confidence = VECTOR_BASE
    
    # Add vector corroboration
    if vector_matches > 0:
        vector_bonus = min(vector_matches * VECTOR_CORROBORATION_BONUS, 0.15)
        confidence += vector_bonus
    
    # Apply conflict penalty
    if has_conflict:
        confidence -= CONFLICT_PENALTY
    
    # Apply source factors
    confidence *= source_recency * source_authority
    
    # Cap the confidence
    return max(0.3, min(confidence, 0.99))


class OPAConfidenceScorer:
    """Calculate confidence scores for OPA practice guidance."""
    
    # Source authority weights
    SOURCE_WEIGHTS = {
        "cpso": 1.0,        # Highest authority for Ontario practice
        "ontario_health": 0.95,  # Official screening guidelines
        "pho": 0.9,         # Public Health Ontario
        "cep": 0.85,        # Centre for Effective Practice
        "moh": 0.85,        # Ministry of Health
        "other": 0.7
    }
    
    # Document type weights
    DOC_TYPE_WEIGHTS = {
        "policy": 1.0,      # Mandatory expectations
        "standard": 0.95,   # Quality standards
        "guideline": 0.9,   # Clinical guidelines
        "advice": 0.85,     # Advice to profession
        "tool": 0.8,        # Clinical tools
        "statement": 0.75   # Position statements
    }
    
    @classmethod
    def calculate(
        cls,
        sql_hits: int = 0,
        vector_matches: int = 0,
        sources: List[str] = None,
        doc_types: List[str] = None,
        has_conflict: bool = False,
        recency_days: int = None
    ) -> float:
        """
        Calculate confidence score based on OPA-specific factors.
        
        Args:
            sql_hits: Number of SQL records found
            vector_matches: Number of relevant vector passages
            sources: Source organizations involved
            doc_types: Document types involved
            has_conflict: Whether there's conflict between sources
            recency_days: Days since last update (None if unknown)
        
        Returns:
            Confidence score between 0 and 1
        """
        # Get source authority
        source_authority = 1.0
        if sources:
            weights = [cls.SOURCE_WEIGHTS.get(s, cls.SOURCE_WEIGHTS["other"]) for s in sources]
            source_authority = max(weights)  # Use highest authority source
        
        # Get document type weight
        doc_weight = 1.0
        if doc_types:
            weights = [cls.DOC_TYPE_WEIGHTS.get(t, 0.7) for t in doc_types]
            doc_weight = max(weights)
        
        # Calculate recency factor
        recency_factor = 1.0
        if recency_days is not None:
            if recency_days < 90:
                recency_factor = 1.0
            elif recency_days < 365:
                recency_factor = 0.95
            elif recency_days < 730:
                recency_factor = 0.85
            else:
                recency_factor = 0.75
        
        # Combine factors
        authority_factor = (source_authority + doc_weight) / 2
        
        return calculate_confidence(
            sql_hits=sql_hits,
            vector_matches=vector_matches,
            has_conflict=has_conflict,
            source_recency=recency_factor,
            source_authority=authority_factor
        )
    
    @classmethod
    def get_confidence_level(cls, score: float) -> str:
        """
        Get human-readable confidence level for practice guidance.
        
        Args:
            score: Confidence score (0-1)
        
        Returns:
            Confidence level description
        """
        if score >= 0.9:
            return "Very High - Official policy/guideline"
        elif score >= 0.8:
            return "High - Authoritative guidance"
        elif score >= 0.7:
            return "Moderate - Well-supported advice"
        elif score >= 0.6:
            return "Fair - Some evidence available"
        else:
            return "Low - Limited or dated guidance"
    
    @classmethod
    def explain_score(
        cls,
        sql_hits: int = 0,
        vector_matches: int = 0,
        sources: List[str] = None,
        has_conflict: bool = False,
        recency_days: int = None
    ) -> str:
        """
        Generate explanation for confidence score.
        
        Args:
            sql_hits: Number of SQL records found
            vector_matches: Number of relevant vector passages  
            sources: Source organizations
            has_conflict: Whether there's conflict
            recency_days: Days since update
        
        Returns:
            Human-readable explanation
        """
        explanations = []
        
        if sql_hits > 0:
            explanations.append(f"Found {sql_hits} matching document(s)")
        
        if vector_matches > 0:
            explanations.append(f"Supported by {vector_matches} relevant passage(s)")
        
        if sources:
            source_str = ", ".join(sources)
            explanations.append(f"From: {source_str}")
        
        if recency_days is not None:
            if recency_days < 90:
                explanations.append("Very recent guidance")
            elif recency_days < 365:
                explanations.append("Current guidance")
            elif recency_days < 730:
                explanations.append("Guidance may need review")
            else:
                explanations.append("Older guidance - check for updates")
        
        if has_conflict:
            explanations.append("Note: Some conflicting information found")
        
        return "; ".join(explanations)