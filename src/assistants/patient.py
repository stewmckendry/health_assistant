"""Patient-focused medical education assistant."""
import time
from typing import Dict, Any, Optional

from langfuse import get_client, observe
from src.assistants.base import BaseAssistant, AssistantConfig
from src.utils.guardrails import (
    ResponseGuardrails,
    detect_emergency_content,
    detect_mental_health_crisis,
    apply_disclaimers
)
from src.utils.llm_guardrails import LLMGuardrails
from src.utils.logging import get_logger, log_decision
from src.utils.session_logging import SessionLogger
from src.config.settings import settings


logger = get_logger(__name__)

# Initialize Langfuse client
if settings.langfuse_enabled:
    try:
        langfuse = get_client()
        logger.info("Langfuse client initialized for observability")
    except Exception as e:
        logger.warning(f"Failed to initialize Langfuse: {e}")
        langfuse = None
else:
    langfuse = None


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
    
    @observe(name="patient_query", capture_input=True, capture_output=True)
    def query(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        message_history: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Process a patient query with appropriate guardrails and disclaimers.
        This overrides the base class query method to add patient-specific safety checks.
        
        Args:
            query: Patient's question or concern
            session_id: Session identifier for logging
            user_id: User identifier for tracking
        
        Returns:
            Response dictionary with educational content and metadata
        """
        # Track processing time
        start_time = time.time()
        
        # Initialize session logger
        session_logger = SessionLogger(session_id or "default")
        
        # Log original query
        session_logger.log_original_query(query, self.mode)
        
        # Update Langfuse trace with metadata
        if langfuse and settings.langfuse_enabled:
            try:
                langfuse.update_current_trace(
                    input={"query": query, "mode": self.mode},
                    metadata={
                        "session_id": session_id or "default",
                        "user_id": user_id or "anon",
                        "guardrail_mode": self.guardrail_mode,
                        "assistant_mode": self.mode
                    },
                    session_id=session_id,
                    user_id=user_id,
                    tags=["patient_assistant", f"guardrail_{self.guardrail_mode}"]
                )
                # Add session/user tags for filtering
                if session_id:
                    langfuse.update_current_trace(tags=[f"session:{session_id[:8]}"])
                if user_id:
                    langfuse.update_current_trace(tags=[f"user:{user_id}"])
            except Exception as e:
                logger.debug(f"Failed to update Langfuse trace: {e}")
        
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
            
            # Log input guardrail check
            session_logger.log_input_guardrail(input_check, self.guardrail_mode)
            
            if input_check["requires_intervention"]:
                logger.warning(
                    f"{input_check['intervention_type']} detected in query",
                    extra={"session_id": session_id, "explanation": input_check["explanation"]}
                )
                
                # Return appropriate response based on intervention type
                if input_check["intervention_type"] == "emergency":
                    response = {
                        "content": settings.emergency_redirect,
                        "emergency_detected": True,
                        "guardrails_applied": True,
                        "session_id": session_id,
                        "mode": self.mode
                    }
                    # Log final response
                    session_logger.log_final_response(response, time.time() - start_time)
                    return response
                elif input_check["intervention_type"] == "mental_health_crisis":
                    response = {
                        "content": settings.mental_health_resources,
                        "mental_health_crisis": True,
                        "guardrails_applied": True,
                        "session_id": session_id,
                        "mode": self.mode
                    }
                    # Log final response
                    session_logger.log_final_response(response, time.time() - start_time)
                    return response
        
        # Fallback to regex if not using LLM or for regex mode
        elif self.guardrail_mode == "regex":
            # Check for emergency content in the query BEFORE sending to API
            input_check = {
                "requires_intervention": False,
                "intervention_type": "none",
                "explanation": "",
                "should_block": False
            }
            
            if detect_emergency_content(query):
                input_check["requires_intervention"] = True
                input_check["intervention_type"] = "emergency"
                input_check["explanation"] = "Emergency keywords detected"
                input_check["should_block"] = True
            elif detect_mental_health_crisis(query):
                input_check["requires_intervention"] = True
                input_check["intervention_type"] = "mental_health_crisis"
                input_check["explanation"] = "Crisis keywords detected"
                input_check["should_block"] = True
            
            # Log input guardrail check
            session_logger.log_input_guardrail(input_check, self.guardrail_mode)
            
            if input_check["requires_intervention"]:
                logger.warning(
                    f"{input_check['intervention_type']} detected in query",
                    extra={"session_id": session_id}
                )
                
                log_decision(
                    logger,
                    decision_type=f"{input_check['intervention_type']}_redirect",
                    decision=f"Redirecting due to {input_check['intervention_type']}",
                    reason=input_check["explanation"],
                    session_id=session_id
                )
                
                if input_check["intervention_type"] == "emergency":
                    response = {
                        "content": settings.emergency_redirect,
                        "emergency_detected": True,
                        "guardrails_applied": True,
                        "session_id": session_id,
                        "mode": self.mode
                    }
                else:
                    response = {
                        "content": settings.mental_health_resources,
                        "mental_health_crisis": True,
                        "guardrails_applied": True,
                        "session_id": session_id,
                        "mode": self.mode
                    }
                
                # Log final response
                session_logger.log_final_response(response, time.time() - start_time)
                return response
        
        try:
            # Call the parent class query method which makes the actual Anthropic API call
            # This is where the request goes to Claude (in base.py line 206)
            api_response = super().query(query, session_id, user_id, session_logger, message_history)
            
            # Apply output guardrails based on mode
            original_response = api_response["content"]
            
            if settings.enable_guardrails:
                if self.guardrail_mode in ["llm", "hybrid"]:
                    # Use LLM guardrails for output checking
                    output_check = self.llm_guardrails.check_output(
                        api_response["content"],
                        api_response.get("citations", []),
                        session_id,
                        api_response.get("tool_calls", [])
                    )
                    
                    # Log output guardrail check
                    session_logger.log_output_guardrail(
                        output_check,
                        self.guardrail_mode,
                        original_response,
                        output_check["modified_response"]
                    )
                    
                    # Update response based on LLM guardrail results
                    api_response["content"] = output_check["modified_response"]
                    api_response["guardrails_applied"] = not output_check["passes_guardrails"]
                    api_response["violations"] = output_check.get("violations", [])
                    api_response["web_search_performed"] = output_check.get("web_search_performed", False)
                    api_response["has_trusted_citations"] = output_check.get("has_trusted_citations", False)
                    
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
                    
                    # Log output guardrail check
                    output_check = {
                        "passes_guardrails": not guardrails_result["guardrails_triggered"],
                        "violations": guardrails_result.get("violations", []),
                        "explanation": "Regex pattern matching",
                        "suggested_action": "modify" if guardrails_result["guardrails_triggered"] else "pass",
                        "web_search_performed": len(api_response.get("tool_calls", [])) > 0,
                        "has_trusted_citations": len(api_response.get("citations", [])) > 0
                    }
                    session_logger.log_output_guardrail(
                        output_check,
                        self.guardrail_mode,
                        original_response,
                        guardrails_result["content"]
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
            
            # Add trace ID from current context (we're inside @observe)
            if langfuse and settings.langfuse_enabled:
                try:
                    trace_id = langfuse.get_current_trace_id()
                    if trace_id:
                        api_response["trace_id"] = trace_id
                except Exception as e:
                    logger.debug(f"Failed to get trace ID: {e}")
                    api_response["trace_id"] = None
            else:
                api_response["trace_id"] = None
            
            # Log final response
            processing_time = time.time() - start_time
            session_logger.log_final_response(api_response, processing_time)
            
            # Log successful response
            logger.info(
                "Patient query completed",
                extra={
                    "session_id": session_id,
                    "response_length": len(api_response["content"]),
                    "guardrails_applied": api_response.get("guardrails_applied", False),
                    "citations_count": len(api_response.get("citations", [])),
                    "processing_time": processing_time
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
            error_response = {
                "content": (
                    "I apologize, but I'm unable to process your request at the moment. "
                    "Please try again or consult with a healthcare provider directly. "
                    "If this is a medical emergency, please call 911 immediately."
                ),
                "error": True,
                "session_id": session_id,
                "mode": self.mode
            }
            
            # Log final response even for errors
            session_logger.log_final_response(error_response, time.time() - start_time)
            
            return error_response