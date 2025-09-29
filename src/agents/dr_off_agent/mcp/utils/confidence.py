"""
Confidence scoring system for Dr. OFF responses.
Combines evidence from SQL and vector sources.
"""

from typing import List, Dict, Any


class ConfidenceScorer:
    """Calculate confidence scores based on evidence sources."""
    
    # Base confidence scores
    SQL_BASE = 0.9  # High confidence for structured data
    VECTOR_BASE = 0.6  # Moderate confidence for semantic search only
    
    # Modifiers
    VECTOR_CORROBORATION_BONUS = 0.03  # Per matching vector passage
    CONFLICT_PENALTY = 0.1  # When SQL and vector disagree
    MULTIPLE_SQL_HITS_BONUS = 0.02  # Per additional SQL record
    
    # Caps
    MAX_CONFIDENCE = 0.99
    MIN_CONFIDENCE = 0.3
    
    @classmethod
    def calculate(
        cls,
        sql_hits: int = 0,
        vector_matches: int = 0,
        has_conflict: bool = False,
        additional_factors: Dict[str, float] = None
    ) -> float:
        """
        Calculate confidence score based on evidence.
        
        Args:
            sql_hits: Number of SQL records found
            vector_matches: Number of relevant vector passages
            has_conflict: Whether there's conflict between sources
            additional_factors: Custom factors to add/subtract
        
        Returns:
            Confidence score between 0 and 1
        """
        # Start with base confidence
        if sql_hits > 0:
            confidence = cls.SQL_BASE
            # Add bonus for multiple SQL hits
            if sql_hits > 1:
                confidence += min((sql_hits - 1) * cls.MULTIPLE_SQL_HITS_BONUS, 0.06)
        else:
            confidence = cls.VECTOR_BASE
        
        # Add vector corroboration
        if vector_matches > 0:
            vector_bonus = min(vector_matches * cls.VECTOR_CORROBORATION_BONUS, 0.15)
            confidence += vector_bonus
        
        # Apply conflict penalty
        if has_conflict:
            confidence -= cls.CONFLICT_PENALTY
        
        # Apply additional factors if provided
        if additional_factors:
            for factor, value in additional_factors.items():
                confidence += value
        
        # Cap the confidence
        return max(cls.MIN_CONFIDENCE, min(confidence, cls.MAX_CONFIDENCE))
    
    @classmethod
    def get_confidence_level(cls, score: float) -> str:
        """
        Get human-readable confidence level.
        
        Args:
            score: Confidence score (0-1)
        
        Returns:
            Confidence level description
        """
        if score >= 0.9:
            return "Very High"
        elif score >= 0.8:
            return "High"
        elif score >= 0.7:
            return "Moderate"
        elif score >= 0.6:
            return "Low"
        else:
            return "Very Low"
    
    @classmethod
    def explain_score(
        cls,
        sql_hits: int = 0,
        vector_matches: int = 0,
        has_conflict: bool = False
    ) -> str:
        """
        Generate explanation for confidence score.
        
        Args:
            sql_hits: Number of SQL records found
            vector_matches: Number of relevant vector passages
            has_conflict: Whether there's conflict between sources
        
        Returns:
            Human-readable explanation
        """
        explanations = []
        
        if sql_hits > 0:
            explanations.append(f"Found {sql_hits} matching record(s) in structured data")
        
        if vector_matches > 0:
            explanations.append(f"Corroborated by {vector_matches} document passage(s)")
        
        if has_conflict:
            explanations.append("Some conflict detected between sources")
        
        if not sql_hits and not vector_matches:
            explanations.append("Limited evidence available")
        
        return "; ".join(explanations)


class ConfidenceAggregator:
    """Aggregate confidence scores from multiple tools."""
    
    @staticmethod
    def aggregate(scores: List[float], weights: List[float] = None) -> float:
        """
        Aggregate multiple confidence scores.
        
        Args:
            scores: List of confidence scores
            weights: Optional weights for each score
        
        Returns:
            Aggregated confidence score
        """
        if not scores:
            return 0.5  # Default neutral confidence
        
        if weights:
            if len(weights) != len(scores):
                raise ValueError("Weights must match number of scores")
            
            weighted_sum = sum(s * w for s, w in zip(scores, weights))
            total_weight = sum(weights)
            return weighted_sum / total_weight if total_weight > 0 else 0.5
        else:
            # Simple average if no weights provided
            return sum(scores) / len(scores)
    
    @staticmethod
    def combine_tool_confidences(tool_results: Dict[str, Dict[str, Any]]) -> float:
        """
        Combine confidence scores from multiple tool results.
        
        Args:
            tool_results: Dictionary of tool names to their results
        
        Returns:
            Combined confidence score
        """
        scores = []
        weights = []
        
        # Define tool importance weights
        tool_weights = {
            "schedule.get": 1.0,
            "adp.get": 1.0,
            "odb.get": 1.0
        }
        
        for tool_name, result in tool_results.items():
            if "confidence" in result:
                scores.append(result["confidence"])
                weights.append(tool_weights.get(tool_name, 0.8))
        
        if not scores:
            return 0.5
        
        return ConfidenceAggregator.aggregate(scores, weights)