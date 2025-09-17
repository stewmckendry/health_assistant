"""LLM-based guardrails for input and output safety checks."""
import json
import logging
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
from langfuse import get_client, observe
import yaml
from pathlib import Path

from src.config.settings import settings
from src.utils.logging import get_logger
from src.utils.guardrails import (
    detect_emergency_content,
    detect_mental_health_crisis,
    check_forbidden_phrases,
    EMERGENCY_KEYWORDS,
    MENTAL_HEALTH_CRISIS_KEYWORDS
)

logger = get_logger(__name__)

# Initialize Langfuse client
if settings.langfuse_enabled:
    try:
        langfuse = get_client()
    except Exception:
        langfuse = None
else:
    langfuse = None


class LLMGuardrails:
    """LLM-based guardrails for enhanced safety checking."""
    
    def __init__(self, mode: str = "llm", model: str = "claude-3-5-haiku-latest"):
        """
        Initialize LLM guardrails.
        
        Args:
            mode: "llm" for LLM-based, "regex" for pattern matching, "hybrid" for both
            model: Model to use for guardrail checks (faster/cheaper model recommended)
        """
        self.mode = mode
        self.model = model
        self.client = None
        
        if mode in ["llm", "hybrid"]:
            self.client = Anthropic(api_key=settings.anthropic_api_key)
            
        # Load guardrail prompts
        self.prompts = self._load_guardrail_prompts()
        
        logger.info(f"Initialized LLM guardrails in {mode} mode with model {model}")
    
    def _load_guardrail_prompts(self) -> Dict[str, Any]:
        """Load guardrail prompts from YAML file."""
        prompts_file = Path(__file__).parent.parent / "config" / "guardrail_prompts.yaml"
        
        if not prompts_file.exists():
            logger.warning(f"Guardrail prompts file not found: {prompts_file}")
            return {}
            
        with open(prompts_file, 'r') as f:
            return yaml.safe_load(f)
    
    def check_input(self, query: str, session_id: Optional[str] = None, create_span: bool = True) -> Dict[str, Any]:
        """
        Check user input for emergencies or crises before main LLM call.
        
        The create_span parameter controls whether to create a Langfuse span.
        Set to False when calling from streaming mode to avoid creating separate traces.
        
        Args:
            query: User's input query
            session_id: Optional session ID for logging
            create_span: Whether to create a Langfuse span (default: True)
            
        Returns:
            Dictionary with:
                - requires_intervention: bool
                - intervention_type: str ("emergency", "mental_health_crisis", "none")
                - explanation: str
                - should_block: bool
        """
        # Conditionally create span based on parameter
        if create_span:
            return self._check_input_with_span(query, session_id)
        else:
            return self._check_input_internal(query, session_id)
    
    @observe(name="input_guardrail_check", capture_input=True, capture_output=True)
    def _check_input_with_span(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Check input with Langfuse span creation (for non-streaming)."""
        return self._check_input_internal(query, session_id)
    
    def _check_input_internal(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Internal input checking logic without span creation."""
        result = {
            "requires_intervention": False,
            "intervention_type": "none",
            "explanation": "",
            "should_block": False
        }
        
        # Step 1: Try LLM-based check if enabled
        if self.mode in ["llm", "hybrid"]:
            try:
                llm_result = self._check_input_with_llm(query)
                result.update(llm_result)
                
                if result["requires_intervention"]:
                    logger.warning(
                        "LLM input guardrail triggered",
                        extra={
                            "session_id": session_id,
                            "intervention_type": result["intervention_type"],
                            "explanation": result["explanation"]
                        }
                    )
                    result["should_block"] = True
                    return result
                    
            except Exception as e:
                logger.error(f"LLM input check failed, falling back to regex: {str(e)}")
                # Fall through to regex check
        
        # Step 2: Regex fallback if in hybrid/regex mode or if LLM failed
        if self.mode in ["regex", "hybrid"]:
            if detect_emergency_content(query):
                result["requires_intervention"] = True
                result["intervention_type"] = "emergency"
                result["explanation"] = "Emergency keywords detected in query"
                result["should_block"] = True
                
            elif detect_mental_health_crisis(query):
                result["requires_intervention"] = True
                result["intervention_type"] = "mental_health_crisis"
                result["explanation"] = "Mental health crisis keywords detected"
                result["should_block"] = True
                
            if result["requires_intervention"]:
                logger.warning(
                    "Regex input guardrail triggered",
                    extra={
                        "session_id": session_id,
                        "intervention_type": result["intervention_type"]
                    }
                )
        
        return result
    
    def _check_input_with_llm(self, query: str) -> Dict[str, Any]:
        """Use LLM to check if input describes an emergency."""
        if not self.client or "input_guardrail" not in self.prompts:
            raise ValueError("LLM client or prompts not initialized")
        
        prompt = self.prompts["emergency_classifier"]["prompt_template"].format(query=query)
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=200,
            temperature=0,
            system=self.prompts["input_guardrail"]["system_prompt"],
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract response text
        response_text = ""
        for block in response.content:
            if hasattr(block, 'text') and block.text:
                response_text += str(block.text)
        
        try:
            # Parse JSON response
            result = json.loads(response_text)
            return {
                "requires_intervention": result.get("requires_intervention", False),
                "intervention_type": result.get("intervention_type", "none"),
                "explanation": result.get("explanation", "")
            }
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response_text}")
            raise
    
    @observe(name="output_guardrail_check", capture_input=True, capture_output=True)
    def check_output(
        self, 
        response: str, 
        citations: List[Dict[str, str]] = None,
        session_id: Optional[str] = None,
        tool_calls: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check assistant output for quality and safety after main LLM call.
        
        Args:
            response: Assistant's response text
            citations: List of citations included
            session_id: Optional session ID for logging
            tool_calls: List of tool calls made during the response
            
        Returns:
            Dictionary with:
                - passes_guardrails: bool
                - violations: list of violation types
                - explanation: str
                - suggested_action: str
                - modified_response: str (if modifications needed)
        """
        result = {
            "passes_guardrails": True,
            "violations": [],
            "explanation": "",
            "suggested_action": "pass",
            "modified_response": response,
            "web_search_performed": False,
            "has_trusted_citations": False
        }
        
        # Step 1: Check for web fetch tool usage and trusted sources
        web_search_performed = self._check_web_search_performed(tool_calls)
        has_trusted_citations = self._check_trusted_citations(citations)
        
        result["web_search_performed"] = web_search_performed
        result["has_trusted_citations"] = has_trusted_citations
        
        # If response contains medical information but lacks trusted sources, flag it
        if self._contains_medical_info(response) and not has_trusted_citations:
            result["passes_guardrails"] = False
            result["violations"].append("NO_TRUSTED_SOURCES")
            result["explanation"] = "Medical information provided without citations from trusted sources"
            result["suggested_action"] = "require_sources"
            
            logger.warning(
                "No trusted sources found in medical response",
                extra={
                    "session_id": session_id,
                    "web_search_performed": web_search_performed,
                    "citations_count": len(citations) if citations else 0
                }
            )
            
            # Add a warning to the response
            result["modified_response"] = (
                "⚠️ **Note**: The following information needs to be verified with trusted medical sources.\n\n" 
                + response +
                "\n\n⚠️ **Important**: Please consult verified medical sources or healthcare providers for accurate information."
            )
        
        # Step 2: Try LLM-based check if enabled
        if self.mode in ["llm", "hybrid"]:
            try:
                llm_result = self._check_output_with_llm(response, citations)
                result.update(llm_result)
                
                if not result["passes_guardrails"]:
                    logger.warning(
                        "LLM output guardrail triggered",
                        extra={
                            "session_id": session_id,
                            "violations": result["violations"],
                            "explanation": result["explanation"]
                        }
                    )
                    
                    # Apply suggested action
                    result["modified_response"] = self._apply_suggested_action(
                        response, 
                        result["suggested_action"],
                        result["violations"]
                    )
                    
                    # If LLM says block, we block
                    if result["suggested_action"] == "block_response":
                        return result
                        
            except Exception as e:
                logger.error(f"LLM output check failed, falling back to regex: {str(e)}")
                # Fall through to regex check
        
        # Step 2: Regex fallback if in hybrid/regex mode or if LLM failed
        if self.mode in ["regex", "hybrid"]:
            violations = check_forbidden_phrases(response)
            
            if violations:
                result["passes_guardrails"] = False
                result["violations"].extend(violations)
                result["explanation"] = f"Forbidden phrases detected: {', '.join(violations)}"
                result["suggested_action"] = "remove_diagnosis"
                
                logger.warning(
                    "Regex output guardrail triggered",
                    extra={
                        "session_id": session_id,
                        "violations": violations
                    }
                )
                
                # Apply basic cleaning
                modified = response
                for phrase in violations:
                    modified = modified.replace(phrase, "[medical assessment needed]")
                result["modified_response"] = modified
        
        return result
    
    def _check_output_with_llm(
        self, 
        response: str, 
        citations: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Use LLM to check if output meets quality standards."""
        if not self.client or "output_guardrail" not in self.prompts:
            raise ValueError("LLM client or prompts not initialized")
        
        # Format citations for review
        citations_text = "None"
        if citations:
            citations_text = ", ".join([c.get("url", "") for c in citations])
        
        prompt = self.prompts["quality_reviewer"]["prompt_template"].format(
            response=response,
            citations=citations_text
        )
        
        response_obj = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            temperature=0,
            system=self.prompts["output_guardrail"]["system_prompt"],
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract response text
        response_text = ""
        for block in response_obj.content:
            if hasattr(block, 'text') and block.text:
                response_text += str(block.text)
        
        # First try to extract just the JSON part
        import re
        json_text = response_text.strip()
        
        # Look for JSON object pattern and extract just that part
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_text)
        if json_match:
            json_text = json_match.group()
        
        try:
            # Parse JSON response
            result = json.loads(json_text)
            return {
                "passes_guardrails": result.get("passes_guardrails", True),
                "violations": result.get("violations", []),
                "explanation": result.get("explanation", ""),
                "suggested_action": result.get("suggested_action", "pass"),
                "specific_fixes": result.get("specific_fixes", [])
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {response_text[:500]}")
            
            # Try to repair common JSON issues
            try:
                # Fix common issues like unquoted values
                json_str = re.sub(r':\s*([a-zA-Z_]\w*)\s*([,}])', r': "\1"\2', json_text)
                # Remove trailing commas
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                
                # Try parsing again
                result = json.loads(json_str)
                logger.info("Successfully repaired JSON response")
                return {
                    "passes_guardrails": result.get("passes_guardrails", True),
                    "violations": result.get("violations", []),
                    "explanation": result.get("explanation", ""),
                    "suggested_action": result.get("suggested_action", "pass"),
                    "specific_fixes": result.get("specific_fixes", [])
                }
            except Exception as repair_error:
                logger.debug(f"JSON repair failed: {repair_error}")
            
            # If repair fails, raise original error
            raise e
    
    def _apply_suggested_action(
        self, 
        response: str, 
        action: str,
        violations: List[str]
    ) -> str:
        """Apply the suggested action to modify the response."""
        
        if action == "block_response":
            return (
                "I apologize, but I cannot provide that information as it may contain "
                "medical advice that should only come from a healthcare provider. "
                "Please consult with a medical professional for personalized guidance."
            )
        
        elif action == "add_disclaimer" and "MISSING_DISCLAIMER" in violations:
            if not response.startswith("⚠️"):
                response = (
                    "⚠️ **Medical Disclaimer**: This information is for educational purposes only "
                    "and is not a substitute for professional medical advice.\n\n" + response
                )
            if not response.endswith("professional."):
                response += (
                    "\n\n💡 **Remember**: Please consult with a healthcare provider "
                    "for personalized medical advice."
                )
        
        elif action == "remove_diagnosis" and "DIAGNOSIS" in violations:
            # Remove diagnostic language
            replacements = {
                "you have": "this may indicate",
                "you are": "this could be",
                "your condition": "this condition",
                "your symptoms": "these symptoms",
                "diagnosis is": "possibility includes"
            }
            
            for old, new in replacements.items():
                response = response.replace(old, new)
        
        return response
    
    def _check_web_search_performed(self, tool_calls: List[Dict[str, Any]] = None) -> bool:
        """
        Check if web search/fetch tools were called.
        
        Args:
            tool_calls: List of tool calls made during response
            
        Returns:
            True if web search or fetch was performed
        """
        if not tool_calls:
            return False
        
        web_tools = ["web_search", "web_fetch", "server_tool_use"]
        for call in tool_calls:
            if any(tool in str(call).lower() for tool in web_tools):
                return True
        
        return False
    
    def _check_trusted_citations(self, citations: List[Dict[str, str]] = None) -> bool:
        """
        Check if citations are from trusted medical domains.
        
        Args:
            citations: List of citation dictionaries with 'url' field
            
        Returns:
            True if at least one citation is from a trusted domain
        """
        if not citations:
            return False
        
        # Get trusted domains from settings
        trusted = settings.trusted_domains if hasattr(settings, 'trusted_domains') else []
        
        # Add common trusted medical domains as fallback
        trusted_patterns = [
            "mayoclinic.org", "mayo.edu",
            "cdc.gov", "nih.gov", 
            "clevelandclinic.org",
            "pubmed.ncbi.nlm.nih.gov",
            "who.int",
            "hopkinsmedicine.org",
            "webmd.com",
            "healthline.com",
            ".gov",  # Government sites
            ".edu"   # Educational institutions
        ]
        
        # Check each citation
        for citation in citations:
            url = citation.get("url", "").lower()
            if url:
                # Check against trusted domains list
                for domain in trusted:
                    if domain.lower() in url:
                        return True
                
                # Check against trusted patterns
                for pattern in trusted_patterns:
                    if pattern in url:
                        return True
        
        return False
    
    def _contains_medical_info(self, response: str) -> bool:
        """
        Check if response contains medical information that requires sources.
        
        Args:
            response: Response text to check
            
        Returns:
            True if response contains medical information
        """
        # Medical keywords that indicate medical information
        medical_keywords = [
            "symptom", "diagnosis", "treatment", "medication", "disease",
            "condition", "disorder", "syndrome", "infection", "virus",
            "bacteria", "cancer", "diabetes", "heart", "blood pressure",
            "cholesterol", "fever", "pain", "nausea", "fatigue",
            "medical", "clinical", "therapy", "surgery", "doctor",
            "physician", "healthcare", "hospital", "emergency"
        ]
        
        response_lower = response.lower()
        
        # Check if any medical keywords are present
        for keyword in medical_keywords:
            if keyword in response_lower:
                return True
        
        return False