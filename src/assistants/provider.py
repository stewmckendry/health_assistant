"""Provider-focused medical information assistant for healthcare professionals."""
import time
from typing import Dict, Any, Optional

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