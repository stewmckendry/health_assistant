"""Patient-focused medical education assistant."""
from typing import Dict, Any, Optional

from src.assistants.base import BaseAssistant, AssistantConfig
from src.utils.guardrails import (
    ResponseGuardrails,
    detect_emergency_content,
    detect_mental_health_crisis,
    apply_disclaimers
)
from src.utils.llm_guardrails import LLMGuardrails
from src.utils.logging import get_logger, log_decision
from src.config.settings import settings


logger = get_logger(__name__)


class PatientAssistant(BaseAssistant):
    """Assistant specialized for patient education and information."""
    
    def __init__(self, guardrail_mode: str = "hybrid"):
        """
        Initialize patient assistant with patient-specific configuration.
        
        Args:
            guardrail_mode: "llm", "regex", or "hybrid" for guardrail checking
        """
        # Ensure we're in patient mode
        if settings.assistant_mode != "patient":
            logger.warning(
                f"PatientAssistant created but mode is {settings.assistant_mode}, forcing to patient mode"
            )
        
        # Create patient-specific configuration
        config = AssistantConfig(
            model=settings.primary_model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            system_prompt=settings.system_prompt,  # Will use patient prompt from settings
            trusted_domains=settings.trusted_domains,
            enable_web_fetch=settings.enable_web_fetch,
            citations_enabled=settings.citations_enabled,
            max_web_fetch_uses=settings.max_web_fetch_uses
        )
        
        super().__init__(config)
        
        self.mode = "patient"
        self.guardrail_mode = guardrail_mode
        
        # Initialize appropriate guardrails
        if guardrail_mode in ["llm", "hybrid"]:
            self.llm_guardrails = LLMGuardrails(mode=guardrail_mode)
        
        self.regex_guardrails = ResponseGuardrails()  # Keep for compatibility
        
        logger.info(
            "PatientAssistant initialized",
            extra={
                "mode": self.mode,
                "model": self.config.model,
                "guardrails_enabled": settings.enable_guardrails,
                "guardrail_mode": guardrail_mode
            }
        )
    
    def query(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a patient query with appropriate guardrails and disclaimers.
        This overrides the base class query method to add patient-specific safety checks.
        
        Args:
            query: Patient's question or concern
            session_id: Session identifier for logging
        
        Returns:
            Response dictionary with educational content and metadata
        """
        logger.info(
            "Patient query received",
            extra={
                "session_id": session_id,
                "query_length": len(query),
                "mode": self.mode
            }
        )
        
        # Use LLM guardrails for input checking if configured
        if self.guardrail_mode in ["llm", "hybrid"]:
            input_check = self.llm_guardrails.check_input(query, session_id)
            
            if input_check["requires_intervention"]:
                logger.warning(
                    f"{input_check['intervention_type']} detected in query",
                    extra={"session_id": session_id, "explanation": input_check["explanation"]}
                )
                
                # Return appropriate response based on intervention type
                if input_check["intervention_type"] == "emergency":
                    return {
                        "content": settings.emergency_redirect,
                        "emergency_detected": True,
                        "guardrails_applied": True,
                        "session_id": session_id,
                        "mode": self.mode
                    }
                elif input_check["intervention_type"] == "mental_health_crisis":
                    return {
                        "content": settings.mental_health_resources,
                        "mental_health_crisis": True,
                        "guardrails_applied": True,
                        "session_id": session_id,
                        "mode": self.mode
                    }
        
        # Fallback to regex if not using LLM or for regex mode
        elif self.guardrail_mode == "regex":
            # Check for emergency content in the query BEFORE sending to API
            if detect_emergency_content(query):
                logger.warning(
                    "Emergency content detected in query",
                    extra={"session_id": session_id}
                )
                
                log_decision(
                    logger,
                    decision_type="emergency_redirect",
                    decision="Redirecting to emergency services",
                    reason="Emergency keywords detected in query",
                    session_id=session_id
                )
                
                return {
                    "content": settings.emergency_redirect,
                    "emergency_detected": True,
                    "guardrails_applied": True,
                    "session_id": session_id,
                    "mode": self.mode
                }
            
            # Check for mental health crisis in the query BEFORE sending to API
            if detect_mental_health_crisis(query):
                logger.warning(
                    "Mental health crisis detected in query",
                    extra={"session_id": session_id}
                )
                
                log_decision(
                    logger,
                    decision_type="mental_health_redirect",
                    decision="Providing mental health resources",
                    reason="Crisis keywords detected in query",
                    session_id=session_id
                )
                
                return {
                    "content": settings.mental_health_resources,
                    "mental_health_crisis": True,
                    "guardrails_applied": True,
                    "session_id": session_id,
                    "mode": self.mode
                }
        
        try:
            # Call the parent class query method which makes the actual Anthropic API call
            # This is where the request goes to Claude (in base.py line 206)
            api_response = super().query(query, session_id)
            
            # Apply output guardrails based on mode
            if settings.enable_guardrails:
                if self.guardrail_mode in ["llm", "hybrid"]:
                    # Use LLM guardrails for output checking
                    output_check = self.llm_guardrails.check_output(
                        api_response["content"],
                        api_response.get("citations", []),
                        session_id,
                        api_response.get("tool_calls", [])
                    )
                    
                    # Update response based on LLM guardrail results
                    api_response["content"] = output_check["modified_response"]
                    api_response["guardrails_applied"] = not output_check["passes_guardrails"]
                    api_response["violations"] = output_check.get("violations", [])
                    
                    if not output_check["passes_guardrails"]:
                        logger.info(
                            "LLM guardrails applied to response",
                            extra={
                                "session_id": session_id,
                                "violations": output_check["violations"],
                                "action": output_check["suggested_action"]
                            }
                        )
                
                elif self.guardrail_mode == "regex":
                    # Use regex guardrails
                    guardrails_result = self.regex_guardrails.apply(
                        api_response["content"],
                        session_id=session_id
                    )
                    
                    # Update response with guardrails result
                    api_response["content"] = guardrails_result["content"]
                    api_response["guardrails_applied"] = guardrails_result["guardrails_triggered"]
                    api_response["violations"] = guardrails_result.get("violations", [])
                    api_response["emergency_detected"] = guardrails_result.get("emergency_detected", False)
                    api_response["mental_health_crisis"] = guardrails_result.get("mental_health_crisis", False)
                    
                    if guardrails_result["guardrails_triggered"]:
                        logger.info(
                            "Regex guardrails applied to response",
                            extra={
                                "session_id": session_id,
                                "violations_count": len(guardrails_result.get("violations", [])),
                                "emergency": guardrails_result.get("emergency_detected", False),
                                "crisis": guardrails_result.get("mental_health_crisis", False)
                            }
                        )
            else:
                # If guardrails are disabled, still apply disclaimers
                api_response["content"] = apply_disclaimers(api_response["content"])
                api_response["guardrails_applied"] = False
            
            # Add patient mode indicator
            api_response["mode"] = self.mode
            
            # Log successful response
            logger.info(
                "Patient query completed",
                extra={
                    "session_id": session_id,
                    "response_length": len(api_response["content"]),
                    "guardrails_applied": api_response.get("guardrails_applied", False),
                    "citations_count": len(api_response.get("citations", []))
                }
            )
            
            return api_response
            
        except Exception as e:
            logger.error(
                f"Error processing patient query: {str(e)}",
                extra={
                    "session_id": session_id,
                    "error": str(e),
                    "mode": self.mode
                }
            )
            
            # Return a safe error message for patients
            return {
                "content": (
                    "I apologize, but I'm unable to process your request at the moment. "
                    "Please try again or consult with a healthcare provider directly. "
                    "If this is a medical emergency, please call 911 immediately."
                ),
                "error": True,
                "session_id": session_id,
                "mode": self.mode
            }