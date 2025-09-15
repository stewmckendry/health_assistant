"""Base assistant class for interacting with Anthropic API."""
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

from anthropic import Anthropic
from anthropic.types import Message
from langfuse import get_client, observe

from src.utils.logging import get_logger, log_api_call
from src.config.settings import settings

# Initialize Langfuse client
if settings.langfuse_enabled:
    try:
        langfuse = get_client()
    except Exception:
        langfuse = None
else:
    langfuse = None


@dataclass
class AssistantConfig:
    """Configuration for the assistant."""
    model: str = "claude-3-5-haiku-latest"  # Updated to working model
    max_tokens: int = 1500
    temperature: float = 0.7
    system_prompt: str = "You are a helpful assistant."
    trusted_domains: List[str] = None
    enable_web_fetch: bool = True
    citations_enabled: bool = True
    max_web_fetch_uses: int = 5
    
    def __post_init__(self):
        if self.trusted_domains is None:
            self.trusted_domains = [
                "mayoclinic.org",
                "cdc.gov",
                "pubmed.ncbi.nlm.nih.gov",
                "who.int",
                "nih.gov",
                "medlineplus.gov",
                "webmd.com",
                "healthline.com"
            ]


class BaseAssistant:
    """Base assistant class for medical information queries."""
    
    def __init__(self, config: Optional[AssistantConfig] = None):
        """
        Initialize the assistant.
        
        Args:
            config: Assistant configuration
        
        Raises:
            ValueError: If ANTHROPIC_API_KEY is not set
        """
        self.config = config or AssistantConfig()
        self.logger = get_logger(__name__)
        
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
        
        self.client = Anthropic(api_key=api_key)
        
        # Extract commonly used config values
        self.model = self.config.model
        self.trusted_domains = self.config.trusted_domains
        self.enable_web_fetch = self.config.enable_web_fetch
        
        self.logger.info(
            "BaseAssistant initialized",
            extra={
                "model": self.model,
                "enable_web_fetch": self.enable_web_fetch,
                "trusted_domains_count": len(self.trusted_domains)
            }
        )
    
    def _build_messages(self, query: str) -> List[Dict[str, str]]:
        """
        Build messages for the API request.
        
        Args:
            query: User query
        
        Returns:
            List of message dictionaries (user messages only, system prompt handled separately)
        """
        messages = [
            {"role": "user", "content": query}
        ]
        return messages
    
    def _build_tools(self) -> Optional[List[Dict[str, Any]]]:
        """
        Build tools configuration for the API request.
        
        Returns:
            List of tool configurations or None if no tools enabled
        """
        if not self.enable_web_fetch:
            return None
        
        tools = [
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 3  # Use search to find URLs first
            },
            {
                "type": "web_fetch_20250910",
                "name": "web_fetch",
                "allowed_domains": self.trusted_domains,
                "max_uses": self.config.max_web_fetch_uses,
                "citations": {"enabled": self.config.citations_enabled}
            }
        ]
        return tools
    
    def _extract_citations(self, response: Message) -> List[Dict[str, str]]:
        """
        Extract citations from the API response.
        
        Args:
            response: Anthropic API response
        
        Returns:
            List of unique citation dictionaries
        """
        citations = []
        seen_urls = set()  # Track URLs to avoid duplicates
        duplicate_count = 0
        
        for content_block in response.content:
            if hasattr(content_block, 'citations') and content_block.citations:
                for citation in content_block.citations:
                    # Handle different citation formats
                    if isinstance(citation, dict):
                        url = citation.get("url", "")
                        title = citation.get("title", "")
                    elif hasattr(citation, 'url'):
                        # Handle object-based citations
                        url = getattr(citation, 'url', '')
                        title = getattr(citation, 'title', 'Source')
                    else:
                        continue
                    
                    # Only add if URL hasn't been seen before
                    if url:
                        if url not in seen_urls:
                            citations.append({
                                "url": url,
                                "title": title
                            })
                            seen_urls.add(url)
                        else:
                            duplicate_count += 1
        
        if duplicate_count > 0:
            self.logger.info(
                f"Removed {duplicate_count} duplicate citations",
                extra={"unique_citations": len(citations), "duplicates_removed": duplicate_count}
            )
                        
        return citations
    
    def _format_response_with_citations(
        self,
        content: str,
        citations: List[Dict[str, str]]
    ) -> str:
        """
        Format response content with citations.
        
        Args:
            content: Response content
            citations: List of citations
        
        Returns:
            Formatted response with citations
        """
        if not citations:
            return content
        
        formatted = content + "\n\n**Sources:**\n"
        for i, citation in enumerate(citations, 1):
            title = citation.get("title", "Source")
            url = citation.get("url", "")
            formatted += f"{i}. [{title}]({url})\n"
        
        return formatted
    
    @observe(name="llm_call", as_type="generation", capture_input=True, capture_output=True)
    def query(
        self,
        query: str,
        session_id: Optional[str] = None,
        session_logger: Optional[Any] = None  # SessionLogger instance
    ) -> Dict[str, Any]:
        """
        Send a query to the Anthropic API.
        
        Args:
            query: User query
            session_id: Optional session identifier for logging
        
        Returns:
            Response dictionary with content, model, usage, and session_id
        
        Raises:
            Exception: If API call fails
        """
        try:
            # Build request components
            messages = self._build_messages(query)
            tools = self._build_tools()
            
            # Log the API call
            log_api_call(
                self.logger,
                service="anthropic",
                endpoint="messages",
                model=self.model,
                tokens=len(query.split()),  # Approximate input tokens
                session_id=session_id
            )
            
            # Prepare API call kwargs
            api_kwargs = {
                "model": self.model,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "system": self.config.system_prompt,  # System prompt as parameter
                "messages": messages
            }
            
            # Add tools if configured
            if tools:
                api_kwargs["tools"] = tools
                # Include both web search and web fetch betas
                api_kwargs["extra_headers"] = {
                    "anthropic-beta": "web-search-2025-03-05,web-fetch-2025-09-10"
                }
            
            # Log API call if session logger provided
            if session_logger:
                session_logger.log_api_call(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    system_prompt=self.config.system_prompt
                )
            
            # Make API call
            response = self.client.messages.create(**api_kwargs)
            
            # Update Langfuse generation with model details
            if langfuse and settings.langfuse_enabled:
                try:
                    langfuse.update_current_observation(
                        model=self.model,
                        input=messages,
                        metadata={
                            "system_prompt": self.config.system_prompt[:200],  # First 200 chars
                            "tools_enabled": tools is not None,
                            "trusted_domains_count": len(self.trusted_domains) if tools else 0
                        },
                        usage={
                            "input_tokens": response.usage.input_tokens,
                            "output_tokens": response.usage.output_tokens,
                            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                        }
                    )
                except Exception as e:
                    self.logger.debug(f"Failed to update Langfuse observation: {e}")
            
            # Extract content and track tool calls
            content = ""
            tool_calls = []
            web_fetches_count = 0
            
            for content_block in response.content:
                if hasattr(content_block, 'text') and content_block.text is not None:
                    content += str(content_block.text)
                    
                    # Count web fetches by checking citations in text blocks
                    if hasattr(content_block, 'citations') and content_block.citations:
                        web_fetches_count += len(content_block.citations)
                
                # Track tool usage
                if hasattr(content_block, 'type'):
                    if content_block.type == 'server_tool_use':
                        tool_calls.append({
                            "type": "tool_use",
                            "name": getattr(content_block, 'name', 'unknown'),
                            "input": getattr(content_block, 'input', {})
                        })
                    elif content_block.type == 'web_search_tool_result':
                        tool_calls.append({
                            "type": "web_search_result",
                            "name": "web_search"
                        })
            
            # Add web_fetch summary if citations were found
            if web_fetches_count > 0:
                tool_calls.append({
                    "type": "web_fetch_summary",
                    "name": "web_fetch",
                    "fetch_count": web_fetches_count
                })
            
            # Extract citations if available
            citations = self._extract_citations(response) if self.config.citations_enabled else []
            
            # Format response with citations
            if citations:
                content = self._format_response_with_citations(content, citations)
            
            # Log API response if session logger provided
            if session_logger:
                session_logger.log_api_response(
                    response_text=content,
                    usage={
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens
                    },
                    tool_calls=tool_calls
                )
                
                # Log individual tool calls
                for tool_call in tool_calls:
                    session_logger.log_tool_call(
                        tool_name=tool_call.get("name", "unknown"),
                        tool_type=tool_call.get("type", "unknown"),
                        tool_input=tool_call
                    )
                
                # Log citations if any
                if citations:
                    session_logger.log_citations(citations)
            
            # Log successful response
            self.logger.info(
                "Query completed successfully",
                extra={
                    "session_id": session_id,
                    "model": response.model,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "citations_count": len(citations),
                    "tool_calls_count": len(tool_calls)
                }
            )
            
            return {
                "content": content,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                "citations": citations,
                "tool_calls": tool_calls,
                "session_id": session_id
            }
            
        except Exception as e:
            self.logger.error(
                f"API call failed: {str(e)}",
                extra={
                    "session_id": session_id,
                    "error": str(e)
                }
            )
            raise