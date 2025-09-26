"""
Device and parameter extraction from natural language ADP queries using LLM.
Similar to odb_drug_extractor.py but for ADP devices and use cases.
"""

import re
import logging
from typing import Optional, Tuple, Dict, Any
import openai
import os

logger = logging.getLogger(__name__)


class ADPDeviceExtractor:
    """Extract device info and parameters from natural language ADP queries."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("No OpenAI API key provided, LLM extraction disabled")
    
    def extract_device_params(self, query: str) -> Dict[str, Any]:
        """
        Extract device parameters from natural language query.
        
        Args:
            query: Natural language query
            
        Returns:
            Dict with device info and parameters for SQL/vector queries
        """
        # First try simple patterns for common cases
        device_info = self._try_regex_extraction(query)
        if device_info["device_type"]:
            logger.info(f"Regex extracted device: {device_info}")
            # If we found device but no category, try LLM to get category
            if not device_info["device_category"] and self._is_natural_language(query):
                llm_result = self._llm_extraction(query)
                if llm_result and llm_result.get("device_category"):
                    device_info["device_category"] = llm_result["device_category"]
                    logger.info(f"LLM provided category: {llm_result['device_category']}")
            return device_info
        
        # If regex fails completely and query looks like natural language, use LLM
        if self._is_natural_language(query):
            llm_result = self._llm_extraction(query)
            if llm_result:
                logger.info(f"LLM extracted device: {llm_result}")
                return llm_result
        
        # Fallback: treat entire query as device search
        return {
            "device_type": query.strip(),
            "device_category": None,
            "use_case": {},
            "patient_income": None,
            "check_types": ["funding", "eligibility"]
        }
    
    def _try_regex_extraction(self, query: str) -> Dict[str, Any]:
        """Try to extract device info using regex patterns."""
        result = {
            "device_type": None,
            "device_category": None,
            "use_case": {},
            "patient_income": None,
            "check_types": []
        }
        
        # Common ADP query patterns
        patterns = [
            r"(?:can\s+i\s+get\s+funding\s+for\s+(?:a\s+)?)([\w\s]+?)(?:\s+for|\s+with|\?|$)",  # "Can I get funding for wheelchair"
            r"(?:is\s+(?:a\s+)?)([\w\s]+?)\s+covered",  # "Is wheelchair covered"
            r"(?:does\s+adp\s+cover\s+(?:a\s+)?)([\w\s]+?)(?:\s+for|\?|$)",  # "Does ADP cover scooter"
            r"(?:what\s+about\s+(?:a\s+)?)([\w\s]+?)\s+for",  # "What about walker for mobility"
            r"(?:funding\s+for\s+(?:a\s+)?)([\w\s]+?)(?:\s+for|\?|$)",  # "funding for power wheelchair"
        ]
        
        query_lower = query.lower().strip()
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                device = match.group(1).strip()
                result["device_type"] = self._normalize_device_name(device)
                result["device_category"] = self._infer_category(device)
                break
        
        # Extract use case indicators
        if "daily" in query_lower or "everyday" in query_lower:
            result["use_case"]["daily"] = True
        
        if "outdoor" in query_lower or "outside" in query_lower:
            result["use_case"]["location"] = "outdoor"
        elif "indoor" in query_lower or "inside" in query_lower or "home" in query_lower:
            result["use_case"]["location"] = "indoor"
        
        if "cannot transfer" in query_lower or "can't transfer" in query_lower:
            result["use_case"]["independent_transfer"] = False
        
        # Extract income if mentioned
        income_match = re.search(r"\$?([\d,]+)", query_lower)
        if income_match:
            try:
                result["patient_income"] = float(income_match.group(1).replace(",", ""))
            except ValueError:
                pass
        
        # Determine check types from query intent
        if "cep" in query_lower or "eligibility program" in query_lower:
            result["check_types"].append("cep")
        if "eligible" in query_lower or "qualify" in query_lower:
            result["check_types"].append("eligibility")
        if "funding" in query_lower or "covered" in query_lower or "cost" in query_lower:
            result["check_types"].append("funding")
        if "exclusion" in query_lower or "not covered" in query_lower:
            result["check_types"].append("exclusions")
        
        # Default check types if none detected
        if not result["check_types"]:
            result["check_types"] = ["funding", "eligibility"]
        
        return result
    
    def _normalize_device_name(self, device: str) -> str:
        """Normalize device names for better matching."""
        # Remove articles and common words
        device = re.sub(r"\b(a|an|the|my|for)\b", "", device).strip()
        
        # Common normalizations
        normalizations = {
            "wheel chair": "wheelchair",
            "power chair": "power wheelchair",
            "electric wheelchair": "power wheelchair",
            "mobility scooter": "scooter",
            "walking aid": "walker",
            "communication device": "communication aid",
            "speech device": "communication aid",
            "hearing aid": "hearing device",
        }
        
        device_lower = device.lower()
        for old, new in normalizations.items():
            if old in device_lower:
                return new
        
        return device
    
    def _infer_category(self, device: str) -> Optional[str]:
        """Infer device category from device name."""
        device_lower = device.lower()
        
        # Mobility devices
        if any(word in device_lower for word in ["wheelchair", "walker", "scooter", "crutch", "cane", "mobility"]):
            return "mobility"
        
        # Communication aids  
        if any(word in device_lower for word in ["communication", "speech", "voice", "aac", "talking"]):
            return "comm_aids"
        
        # Vision aids
        if any(word in device_lower for word in ["magnifier", "reading", "vision", "sight", "cctv"]):
            return "visual_aids"
        
        # Hearing aids
        if any(word in device_lower for word in ["hearing", "ear", "audio", "sound"]):
            return "hearing_devices"
        
        # Respiratory devices (CPAP, BiPAP, ventilators)
        if any(word in device_lower for word in ["cpap", "bipap", "ventilator", "oxygen", "breathing", "respiratory"]):
            return "respiratory"
        
        # Insulin pumps
        if "insulin" in device_lower and "pump" in device_lower:
            return "insulin_pump"
        
        # Glucose monitoring
        if any(word in device_lower for word in ["glucose", "blood sugar", "glucometer"]):
            return "glucose_monitoring"
        
        # Prosthetics
        if any(word in device_lower for word in ["prosthetic", "prosthesis", "limb", "artificial"]):
            return "prosthesis"
        
        # Positioning/seating
        if any(word in device_lower for word in ["cushion", "seating", "position", "support"]):
            return "mobility"  # These are usually mobility-related
        
        return None
    
    def _is_natural_language(self, query: str) -> bool:
        """Check if query appears to be natural language."""
        nl_indicators = [
            'can ', 'is ', 'does ', 'what', 'covered', 'funding',
            'for ', 'get ', 'qualify', 'eligible', 'patient', '?',
            'adp', 'cover', 'my ', 'income'
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in nl_indicators)
    
    def _llm_extraction(self, query: str) -> Optional[Dict[str, Any]]:
        """Use LLM to extract device parameters from complex queries."""
        if not self.client:
            logger.warning("LLM extraction requested but no API key available")
            return None
        
        try:
            # Use a fast, cheap model for extraction
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """Extract ADP device parameters from the query.
                        Return ONLY a JSON object with these keys:
                        - "device_type": specific device name (e.g., "wheelchair", "walker")
                        - "device_category": category ("mobility", "communication", "vision", "hearing", "positioning")  
                        - "use_case": object with "daily", "location", "independent_transfer" if mentioned
                        - "patient_income": number if income amount mentioned
                        - "check_types": array from ["funding", "eligibility", "exclusions", "cep"]
                        
                        Set to null if not mentioned. Examples:
                        - "Can I get funding for a power wheelchair?" -> {"device_type": "power wheelchair", "device_category": "mobility", "use_case": {}, "patient_income": null, "check_types": ["funding"]}
                        - "Is my patient with $20000 income eligible for a walker?" -> {"device_type": "walker", "device_category": "mobility", "use_case": {}, "patient_income": 20000, "check_types": ["eligibility"]}
                        """
                    },
                    {
                        "role": "user", 
                        "content": query
                    }
                ],
                temperature=0,
                max_tokens=200
            )
            
            # Parse the response
            import json
            result = response.choices[0].message.content
            parsed = json.loads(result)
            
            # Validate required fields
            required_fields = ["device_type", "device_category", "use_case", "patient_income", "check_types"]
            for field in required_fields:
                if field not in parsed:
                    parsed[field] = None if field != "check_types" else []
            
            # Ensure check_types is a list with defaults
            if not parsed["check_types"]:
                parsed["check_types"] = ["funding", "eligibility"]
            
            logger.info(f"LLM extracted from '{query}': {parsed}")
            return parsed
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return None


# Singleton instance
_extractor = None

def get_device_extractor(api_key: Optional[str] = None) -> ADPDeviceExtractor:
    """Get or create singleton device extractor."""
    global _extractor
    if _extractor is None:
        _extractor = ADPDeviceExtractor(api_key)
    return _extractor