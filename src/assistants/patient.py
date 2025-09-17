"""Patient-focused medical education assistant."""
import time
from typing import Dict, Any, Optional, List
from contextlib import nullcontext

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
    
    def __init__(self, guardrail_mode: str = "hybrid", session_settings: Optional[Dict] = None):
        """
        Initialize patient assistant with patient-specific configuration.
        
        Args:
            guardrail_mode: "llm", "regex", or "hybrid" for guardrail checking
            session_settings: Optional session-specific settings to override defaults
        """
        # Store session settings
        self.session_settings = session_settings or {}
        
        # Extract settings with defaults (handle both dict and SessionSettings object)
        if hasattr(self.session_settings, 'enable_input_guardrails'):
            # It's a SessionSettings object
            self.enable_input_guardrails = self.session_settings.enable_input_guardrails
            self.enable_output_guardrails = self.session_settings.enable_output_guardrails
            if hasattr(self.session_settings, 'guardrail_mode') and self.session_settings.guardrail_mode:
                guardrail_mode = self.session_settings.guardrail_mode
        else:
            # It's a dictionary
            self.enable_input_guardrails = self.session_settings.get('enable_input_guardrails', True)
            self.enable_output_guardrails = self.session_settings.get('enable_output_guardrails', False)
            if 'guardrail_mode' in self.session_settings:
                guardrail_mode = self.session_settings['guardrail_mode']
        
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
                # Build complete tag list
                all_tags = ["patient_assistant", f"guardrail_{self.guardrail_mode}", "mode:patient"]
                if session_id:
                    all_tags.append(f"session:{session_id[:8]}")
                if user_id:
                    all_tags.append(f"user:{user_id}")
                
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
                    tags=all_tags
                )
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
        
        # Use LLM guardrails for input checking if configured AND enabled
        if self.enable_input_guardrails and self.guardrail_mode in ["llm", "hybrid"]:
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
        elif self.enable_input_guardrails and self.guardrail_mode == "regex":
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
            
            if self.enable_output_guardrails and settings.enable_guardrails:
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
    
    def query_stream(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_logger: Optional[Any] = None,
        message_history: Optional[List[Dict[str, str]]] = None
    ):
        """
        Stream a patient query response with appropriate guardrails.
        This overrides the base method to add patient-specific safety checks.
        
        Due to Langfuse limitations with generators, we collect streaming data
        and send a complete trace after streaming completes.
        """
        from typing import Iterator
        import time
        
        # Track timing
        start_time = time.time()
        
        # Initialize session logger if not provided
        if not session_logger:
            from src.utils.session_logging import SessionLogger
            session_logger = SessionLogger(session_id or "default")
        
        # Log original query
        session_logger.log_original_query(query, self.mode)
        
        # Initialize trace data collection
        trace_data = {
            "start_time": start_time,
            "query": query,
            "session_id": session_id,
            "user_id": user_id,
            "mode": self.mode,
            "guardrail_mode": self.guardrail_mode,
            "input_guardrail_result": None,
            "full_response": "",
            "citations": [],
            "tool_calls": [],
            "time_to_first_token": None,
            "streaming_complete": False,
            "error": None
        }
        
        # Use LLM guardrails for input checking if configured AND enabled
        if self.enable_input_guardrails and self.guardrail_mode in ["llm", "hybrid"]:
            # Input guardrail check
            # Note: Pass create_span=False in streaming context to avoid separate trace
            guardrail_span = None
            input_check = self.llm_guardrails.check_input(query, session_id, create_span=False)
            trace_data["input_guardrail_result"] = input_check
            
            # Log input guardrail check
            session_logger.log_input_guardrail(input_check, self.guardrail_mode)
            
            if input_check["requires_intervention"]:
                logger.warning(
                    f"{input_check['intervention_type']} detected in query",
                    extra={"session_id": session_id, "explanation": input_check["explanation"]}
                )
                
                # Return appropriate response based on intervention type
                if input_check["intervention_type"] == "emergency":
                    # Yield emergency response events
                    yield {
                        "type": "text",
                        "content": settings.emergency_redirect,
                        "metadata": {"emergency_detected": True}
                    }
                    yield {
                        "type": "complete",
                        "content": {"total_text": settings.emergency_redirect},
                        "metadata": {"emergency_detected": True}
                    }
                    return
                elif input_check["intervention_type"] == "mental_health_crisis":
                    # Yield mental health response events
                    yield {
                        "type": "text", 
                        "content": settings.mental_health_resources,
                        "metadata": {"mental_health_crisis": True}
                    }
                    yield {
                        "type": "complete",
                        "content": {"total_text": settings.mental_health_resources},
                        "metadata": {"mental_health_crisis": True}
                    }
                    return
        
        # Fallback to regex if not using LLM or for regex mode
        elif self.enable_input_guardrails and self.guardrail_mode == "regex":
            # Check for emergency content in the query BEFORE sending to API
            if self.guardrails.is_emergency_query(query):
                logger.warning("Emergency content detected in query", extra={"session_id": session_id})
                
                yield {
                    "type": "text",
                    "content": settings.emergency_redirect,
                    "metadata": {"emergency_detected": True}
                }
                yield {
                    "type": "complete",
                    "content": {"total_text": settings.emergency_redirect},
                    "metadata": {"emergency_detected": True}
                }
                return
        
        # Define a wrapper generator to collect data during streaming
        def stream_and_collect():
            """Generator that streams responses and collects data for post-stream logging."""
            # Track if this is the first token for timing
            first_token_received = False
            
            # Call the parent class streaming method
            generator = BaseAssistant.query_stream(
                self, query, session_id, user_id, session_logger, message_history
            )
            
            try:
                # Yield all events from the generator while collecting data
                for event in generator:
                    # Track time to first token
                    if not first_token_received and event.get("type") == "text":
                        trace_data["time_to_first_token"] = time.time() - start_time
                        first_token_received = True
                    
                    # Accumulate data for trace
                    if event.get("type") == "text":
                        trace_data["full_response"] += event.get("content", "")
                    elif event.get("type") == "citation":
                        trace_data["citations"].append(event.get("content"))
                    elif event.get("type") == "tool_use":
                        trace_data["tool_calls"].append(event.get("content"))
                    elif event.get("type") == "complete":
                        # Don't yield the BaseAssistant's complete event
                        # We'll yield our own with the trace_id below
                        continue
                    
                    yield event
                
                # Mark streaming as complete
                trace_data["streaming_complete"] = True
                trace_data["duration"] = time.time() - start_time
                
                # Get the trace ID before logging (we need to create the span first)
                trace_id_to_return = None
                logger.info(f"Langfuse enabled: {settings.langfuse_enabled}, langfuse module: {langfuse is not None}")
                if langfuse and settings.langfuse_enabled:
                    try:
                        # Create the trace now to get the ID
                        from langfuse import Langfuse
                        lf_client = Langfuse()
                        root_span = lf_client.start_span(
                            name="patient_query_streaming",
                            input={"query": trace_data["query"], "mode": trace_data["mode"]}
                        )
                        trace_id_to_return = root_span.trace_id
                        trace_data["trace_id"] = trace_id_to_return
                        # Store the span to end it later
                        trace_data["_root_span"] = root_span
                        trace_data["_lf_client"] = lf_client
                        logger.info(f"Created Langfuse trace with ID: {trace_id_to_return}")
                    except Exception as e:
                        logger.error(f"Failed to create trace: {e}", exc_info=True)
                
                # Yield final complete event with trace ID
                yield {
                    "type": "complete",
                    "content": {"total_text": trace_data["full_response"]},
                    "metadata": {
                        "citations": trace_data["citations"],
                        "tool_calls": trace_data["tool_calls"],
                        "trace_id": trace_id_to_return
                    }
                }
                
            except Exception as e:
                trace_data["error"] = str(e)
                trace_data["duration"] = time.time() - start_time
                logger.error(f"Error during streaming: {e}")
                raise
            finally:
                # Send complete trace to Langfuse after streaming
                self._log_streaming_trace(trace_data)
        
        # Return the generator
        for event in stream_and_collect():
            yield event
    
    def _log_streaming_trace(self, trace_data: Dict[str, Any]):
        """Log the complete streaming trace to Langfuse after streaming completes."""
        if not langfuse or not settings.langfuse_enabled:
            return
        
        try:
            import datetime
            from langfuse import Langfuse
            
            # Check if we already created the span (for trace ID)
            if "_root_span" in trace_data and "_lf_client" in trace_data:
                root_span = trace_data["_root_span"]
                lf_client = trace_data["_lf_client"]
            else:
                # Create a new Langfuse client instance for direct trace creation
                # This ensures we have full control over trace creation
                lf_client = Langfuse()
                
                # Calculate timestamps
                start_time = datetime.datetime.fromtimestamp(trace_data["start_time"])
                end_time = datetime.datetime.fromtimestamp(trace_data["start_time"] + trace_data.get("duration", 0))
                
                # Create a root span (which creates a new trace when no context exists)
                # This is the correct way to create a manual trace in Langfuse v3
                root_span = lf_client.start_span(
                    name="patient_query_streaming",
                    input={"query": trace_data["query"], "mode": trace_data["mode"]}
                )
            
            # Update the span with metadata
            root_span.update(
                metadata={
                    "session_id": trace_data["session_id"] or "default",
                    "user_id": trace_data["user_id"] or "anon",
                    "guardrail_mode": trace_data["guardrail_mode"],
                    "assistant_mode": trace_data["mode"],
                    "streaming": True,
                    "duration_seconds": trace_data.get("duration", 0),
                    "time_to_first_token": trace_data.get("time_to_first_token")
                }
            )
            
            # Update trace-level attributes
            root_span.update_trace(
                name="patient_query_streaming",
                session_id=trace_data["session_id"],
                user_id=trace_data["user_id"],
                tags=["patient_assistant", f"guardrail_{trace_data['guardrail_mode']}", "mode:patient", "streaming"],
                input={"query": trace_data["query"], "mode": trace_data["mode"]},
                output={
                    "response": trace_data["full_response"],  # Full response, no truncation
                    "response_length": len(trace_data["full_response"]),
                    "citations": trace_data["citations"],  # Include actual citations
                    "tool_calls": trace_data["tool_calls"],  # Include actual tool calls
                    "citations_count": len(trace_data["citations"]),
                    "tool_calls_count": len(trace_data["tool_calls"]),
                    "streaming_complete": trace_data["streaming_complete"],
                    "error": trace_data["error"]
                }
            )
            
            # Add input guardrail check as a child span if it was performed
            if trace_data.get("input_guardrail_result"):
                guardrail_span = root_span.start_span(
                    name="input_guardrail_check",
                    input={"query": trace_data["query"]},
                    output=trace_data["input_guardrail_result"]
                )
                guardrail_span.end()  # Manually end the span
            
            # Add LLM generation as a generation
            if trace_data["full_response"] or trace_data["tool_calls"]:
                gen = root_span.start_generation(
                    name="llm_stream",
                    model=self.config.model,
                    input={"messages": [{"role": "user", "content": trace_data["query"]}]},
                    output=trace_data["full_response"],
                    usage_details={
                        "output": len(trace_data["full_response"].split()),
                        "total": len(trace_data["query"].split()) + len(trace_data["full_response"].split())
                    },
                    metadata={
                        "citations": trace_data["citations"],
                        "tool_calls": trace_data["tool_calls"],
                        "time_to_first_token": trace_data.get("time_to_first_token")
                    }
                )
                gen.end()  # Manually end the generation
            
            # End the root span (important!)
            root_span.end()
            
            # Flush to ensure the trace is sent
            lf_client.flush()
            
            logger.info(
                "Streaming trace logged to Langfuse",
                extra={
                    "session_id": trace_data["session_id"],
                    "duration": trace_data.get("duration", 0),
                    "response_length": len(trace_data["full_response"])
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to log streaming trace to Langfuse: {e}")