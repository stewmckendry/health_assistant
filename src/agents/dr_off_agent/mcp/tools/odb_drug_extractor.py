"""
Drug name extraction from natural language queries using LLM.
"""

import re
import logging
from typing import Optional, Tuple
import openai
import os

logger = logging.getLogger(__name__)


class DrugExtractor:
    """Extract drug names from natural language queries using LLM."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("No OpenAI API key provided, LLM extraction disabled")
    
    def extract_drug_info(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract drug name and condition from natural language query.
        
        Args:
            query: Natural language query
            
        Returns:
            Tuple of (drug_name, condition) or (None, None) if extraction fails
        """
        # First try simple patterns for common cases
        drug_name = self._try_simple_extraction(query)
        if drug_name:
            return drug_name, None
        
        # If simple extraction fails and query looks like natural language, use LLM
        if self._is_natural_language(query):
            return self._llm_extraction(query)
        
        # Fall back to treating entire query as drug name
        return query.strip(), None
    
    def _try_simple_extraction(self, query: str) -> Optional[str]:
        """Try to extract drug name using simple patterns."""
        # Common patterns
        patterns = [
            r"(?:is\s+)?(\w+)\s+covered",  # "Is Ozempic covered"
            r"(?:can\s+i\s+prescribe\s+)?(\w+)",  # "Can I prescribe Jardiance"
            r"(?:what\s+about\s+)?(\w+)\s+for",  # "What about metformin for"
            r"(?:does\s+)?(\w+)\s+require",  # "Does Januvia require"
        ]
        
        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                drug = match.group(1)
                # Capitalize first letter for drug names
                return drug.capitalize()
        
        return None
    
    def _is_natural_language(self, query: str) -> bool:
        """Check if query appears to be natural language."""
        # Check for question words or phrases
        nl_indicators = [
            'is ', 'can ', 'does ', 'what', 'covered', 'prescribe',
            'for ', 'require', 'need', 'patient', '?'
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in nl_indicators)
    
    def _llm_extraction(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """Use LLM to extract drug name and condition from query."""
        if not self.client:
            logger.warning("LLM extraction requested but no API key available")
            return None, None
        
        try:
            # Use a fast, cheap model for extraction
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """Extract the drug name and medical condition from the query.
                        Return ONLY a JSON object with 'drug' and 'condition' keys.
                        If no drug is mentioned, set drug to null.
                        If no condition is mentioned, set condition to null.
                        Examples:
                        - "Is Ozempic covered for type 2 diabetes?" -> {"drug": "Ozempic", "condition": "type 2 diabetes"}
                        - "Can I prescribe Jardiance?" -> {"drug": "Jardiance", "condition": null}
                        - "What's the cheapest statin?" -> {"drug": "statin", "condition": null}
                        """
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                temperature=0,
                max_tokens=100
            )
            
            # Parse the response
            import json
            result = response.choices[0].message.content
            parsed = json.loads(result)
            
            drug = parsed.get('drug')
            condition = parsed.get('condition')
            
            logger.info(f"LLM extracted: drug='{drug}', condition='{condition}' from query='{query}'")
            return drug, condition
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return None, None


# Singleton instance
_extractor = None

def get_drug_extractor(api_key: Optional[str] = None) -> DrugExtractor:
    """Get or create singleton drug extractor."""
    global _extractor
    if _extractor is None:
        _extractor = DrugExtractor(api_key)
    return _extractor