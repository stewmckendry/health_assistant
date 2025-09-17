"""Provider-focused medical information assistant for healthcare professionals."""
import time
from typing import Dict, Any, Optional, List

from langfuse import get_client, observe
from src.assistants.base import BaseAssistant, AssistantConfig
from src.utils.guardrails import ResponseGuardrails, apply_disclaimers
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


class ProviderAssistant(BaseAssistant):
    """Assistant specialized for healthcare provider support and clinical information."""
    
    def __init__(self, guardrail_mode: str = "hybrid"):
        """
        Initialize provider assistant with provider-specific configuration.
        
        Args:
            guardrail_mode: "llm", "regex", or "hybrid" for guardrail checking
        """
        # Load provider-specific prompt from config
        # Since settings loads from prompts.yaml, we need to use the provider prompt
        import yaml
        from pathlib import Path
        
        prompts_file = Path(__file__).parent.parent / "config" / "prompts.yaml"
        with open(prompts_file) as f:
            prompts = yaml.safe_load(f)
        provider_prompt = prompts["provider"]["system_prompt"]
        
        # Load extended domains for providers (includes medical journals)
        domains_file = Path(__file__).parent.parent / "config" / "domains.yaml"
        with open(domains_file) as f:
            domains_config = yaml.safe_load(f)
        
        # Combine standard domains with provider-specific domains
        provider_domains = domains_config.get("trusted_domains", [])
        if "provider_domains" in domains_config:
            provider_domains.extend(domains_config["provider_domains"])
        
        # Remove duplicates while preserving order
        seen = set()
        provider_domains = [d for d in provider_domains if not (d in seen or seen.add(d))]
        
        # Create provider-specific configuration
        config = AssistantConfig(
            model=settings.primary_model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            system_prompt=provider_prompt,  # Use provider-specific prompt
            trusted_domains=provider_domains,  # Extended domains for providers
            enable_web_fetch=settings.enable_web_fetch,
            citations_enabled=settings.citations_enabled,
            max_web_fetch_uses=settings.max_web_fetch_uses
        )
        
        super().__init__(config)
        
        self.mode = "provider"
        self.guardrail_mode = guardrail_mode
        
        # Initialize appropriate guardrails (relaxed for providers)
        if guardrail_mode in ["llm", "hybrid"]:
            self.llm_guardrails = LLMGuardrails(mode=guardrail_mode)
        
        self.regex_guardrails = ResponseGuardrails()  # Keep for compatibility
        
        logger.info(
            "ProviderAssistant initialized",
            extra={
                "mode": self.mode,
                "model": self.config.model,
                "guardrails_enabled": settings.enable_guardrails,
                "guardrail_mode": guardrail_mode,
                "trusted_domains_count": len(provider_domains)
            }
        )
    
    @observe(name="provider_query", capture_input=True, capture_output=True)
    def query(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        message_history: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Process a provider query with appropriate professional context.
        Provides evidence-based information suitable for healthcare professionals.
        
        Args:
            query: Healthcare provider's clinical question
            session_id: Session identifier for logging
            user_id: User identifier for tracking
            message_history: Optional conversation history for multi-turn support
        
        Returns:
            Response dictionary with clinical information and metadata
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
                all_tags = ["provider_assistant", f"guardrail_{self.guardrail_mode}", "mode:provider"]
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
            "Provider query received",
            extra={
                "session_id": session_id,
                "query_length": len(query),
                "mode": self.mode
            }
        )
        
        # For providers, we apply relaxed guardrails
        # No emergency redirects needed as providers can handle clinical emergencies
        # But we still check for inappropriate requests (non-medical, etc.)
        
        if self.guardrail_mode in ["llm", "hybrid"] and settings.enable_guardrails:
            # Modified input checking for providers - more permissive
            # Providers can ask about diagnoses, treatments, medications, etc.
            pass  # Skip input guardrails for providers
        
        try:
            # Call the parent class query method which makes the actual Anthropic API call
            api_response = super().query(query, session_id, user_id, session_logger, message_history)
            
            # For providers, we apply minimal guardrails on output
            # Mainly to ensure professional disclaimers are included
            original_response = api_response["content"]
            
            if settings.enable_guardrails:
                # Add professional use disclaimer if not already present
                disclaimer_phrases = [
                    "clinical judgment",
                    "professional judgment",
                    "evidence-based",
                    "professional use"
                ]
                
                has_disclaimer = any(phrase.lower() in original_response.lower() for phrase in disclaimer_phrases)
                
                if not has_disclaimer:
                    # Add subtle professional disclaimer at the end
                    provider_disclaimer = "\n\n*This information is provided for professional use and should be applied with clinical judgment in the context of individual patient care.*"
                    api_response["content"] = original_response + provider_disclaimer
                    api_response["guardrails_applied"] = True
                else:
                    api_response["guardrails_applied"] = False
                
                # Log output guardrail check (minimal for providers)
                output_check = {
                    "passes_guardrails": True,  # Providers generally pass
                    "violations": [],
                    "explanation": "Provider mode - minimal guardrails",
                    "suggested_action": "pass",
                    "web_search_performed": len(api_response.get("tool_calls", [])) > 0,
                    "has_trusted_citations": len(api_response.get("citations", [])) > 0
                }
                session_logger.log_output_guardrail(
                    output_check,
                    self.guardrail_mode,
                    original_response,
                    api_response["content"]
                )
            else:
                api_response["guardrails_applied"] = False
            
            # Add provider mode indicator
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
                "Provider query completed",
                extra={
                    "session_id": session_id,
                    "response_length": len(api_response["content"]),
                    "guardrails_applied": api_response.get("guardrails_applied", False),
                    "citations_count": len(api_response.get("citations", [])),
                    "tool_calls_count": len(api_response.get("tool_calls", [])),
                    "processing_time": processing_time
                }
            )
            
            return api_response
            
        except Exception as e:
            logger.error(
                f"Error processing provider query: {str(e)}",
                extra={
                    "session_id": session_id,
                    "error": str(e),
                    "mode": self.mode
                }
            )
            
            # Return a professional error message for providers
            error_response = {
                "content": (
                    "An error occurred while processing your request. "
                    "Please verify your query and try again. "
                    "If the issue persists, contact system support."
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
        Stream a provider query response with appropriate professional context.
        Collects streaming data and logs complete trace after stream completes.
        """
        import time
        from langfuse import Langfuse
        
        # Initialize session logger if not provided
        if not session_logger:
            session_logger = SessionLogger(session_id or "default")
        
        # Log original query
        session_logger.log_original_query(query, self.mode)
        
        # Track streaming start time
        stream_start_time = time.time()
        
        # Initialize trace data collection
        trace_data = {
            "query": query,
            "mode": self.mode,
            "session_id": session_id,
            "user_id": user_id,
            "guardrail_mode": self.guardrail_mode,
            "start_time": stream_start_time,
            "ttft": None,
            "full_response": "",
            "citations": [],
            "tool_calls": [],
            "input_guardrail_result": None  # Providers don't have input guardrails
        }
        
        # Note: Provider mode doesn't apply input guardrails
        # Providers can handle all medical queries including emergencies
        
        # Call the parent class streaming method
        generator = super().query_stream(
            query, session_id, user_id, session_logger, message_history
        )
        
        # Track if we've received first token
        first_token_received = False
        
        # Yield all events from the generator and collect data
        for event in generator:
            # Track time to first token
            if not first_token_received and event.get("type") == "text":
                trace_data["ttft"] = time.time() - stream_start_time
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
        
        # Calculate total duration
        trace_data["duration"] = time.time() - stream_start_time
        
        # Get the trace ID before logging (we need to create the span first)
        trace_id_to_return = None
        logger.info(f"Langfuse enabled: {settings.langfuse_enabled}, langfuse module: {langfuse is not None}")
        if langfuse and settings.langfuse_enabled:
            try:
                # Create the trace now to get the ID
                from langfuse import Langfuse
                lf_client = Langfuse()
                root_span = lf_client.start_span(
                    name="provider_query_streaming",
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
        
        # Yield our own complete event with trace ID
        yield {
            "type": "complete",
            "content": {"total_text": trace_data["full_response"]},
            "metadata": {
                "citations": trace_data["citations"],
                "tool_calls": trace_data["tool_calls"],
                "trace_id": trace_id_to_return
            }
        }
        
        # Log the complete trace to Langfuse after streaming completes
        if langfuse and settings.langfuse_enabled:
            try:
                self._log_streaming_trace(trace_data)
            except Exception as e:
                logger.error(f"Failed to log streaming trace: {e}")
    
    def _log_streaming_trace(self, trace_data: Dict[str, Any]):
        """Log the complete streaming trace to Langfuse after streaming completes."""
        from langfuse import Langfuse
        
        # Check if we already created the span (for trace ID)
        if "_root_span" in trace_data and "_lf_client" in trace_data:
            root_span = trace_data["_root_span"]
            lf_client = trace_data["_lf_client"]
        else:
            # Create a new Langfuse client instance for direct trace creation
            lf_client = Langfuse()
            
            # Create a root span (which creates a new trace when no context exists)
            root_span = lf_client.start_span(
                name="provider_query_streaming",
                input={"query": trace_data["query"], "mode": trace_data["mode"]}
            )
        
        try:
            # Update the span with metadata
            root_span.update(
                metadata={
                    "session_id": trace_data.get("session_id", "default"),
                    "user_id": trace_data.get("user_id", "anon"),
                    "guardrail_mode": trace_data["guardrail_mode"],
                    "assistant_mode": trace_data["mode"],
                    "streaming": True,
                    "ttft": trace_data.get("ttft"),
                    "duration": trace_data.get("duration")
                }
            )
            
            # Update trace-level attributes
            root_span.update_trace(
                name="provider_query_streaming",
                session_id=trace_data.get("session_id"),
                user_id=trace_data.get("user_id"),
                tags=["provider_assistant", f"guardrail_{trace_data['guardrail_mode']}", "mode:provider", "streaming"],
                input={"query": trace_data["query"], "mode": trace_data["mode"]},
                output={
                    "response": trace_data["full_response"],
                    "citations": trace_data["citations"],
                    "tool_calls": trace_data["tool_calls"],
                    "response_length": len(trace_data["full_response"]),
                    "citations_count": len(trace_data["citations"]),
                    "tool_calls_count": len(trace_data["tool_calls"]),
                    "ttft": trace_data.get("ttft"),
                    "duration": trace_data.get("duration")
                }
            )
            
            # Add LLM generation child span
            llm_span = root_span.start_span(
                name="llm_stream",
                metadata={
                    "model": self.config.model,
                    "ttft": trace_data.get("ttft"),
                    "duration": trace_data.get("duration")
                },
                input={"messages": [{"role": "user", "content": trace_data["query"]}]},
                output=trace_data["full_response"]
            )
            llm_span.end()
            
            # End the root span
            root_span.end()
            
            # Store the trace ID for reference
            if hasattr(root_span, 'trace_id'):
                trace_data["trace_id"] = root_span.trace_id
            
            logger.info(
                "Provider streaming trace logged successfully",
                extra={
                    "trace_id": trace_data.get("trace_id"),
                    "ttft": trace_data.get("ttft"),
                    "duration": trace_data.get("duration"),
                    "response_length": len(trace_data["full_response"])
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to create Langfuse streaming trace: {e}")