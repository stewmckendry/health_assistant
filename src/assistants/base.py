"""Base assistant class for interacting with Anthropic API."""
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

from anthropic import Anthropic
from anthropic.types import Message

from src.utils.logging import get_logger, log_api_call


@dataclass
class AssistantConfig:
    """Configuration for the assistant."""
    model: str = "claude-3-opus-20240229"
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
            List of message dictionaries
        """
        messages = [
            {"role": "system", "content": self.config.system_prompt},
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
                "type": "web_fetch_20250910",
                "name": "web_fetch",
                "allowed_domains": self.trusted_domains,
                "max_uses": self.config.max_web_fetch_uses,
                "citations": self.config.citations_enabled
            }
        ]
        return tools
    
    def _extract_citations(self, response: Message) -> List[Dict[str, str]]:
        """
        Extract citations from the API response.
        
        Args:
            response: Anthropic API response
        
        Returns:
            List of citation dictionaries
        """
        citations = []
        for content_block in response.content:
            if hasattr(content_block, 'citations') and content_block.citations:
                for citation in content_block.citations:
                    citations.append({
                        "url": citation.get("url", ""),
                        "title": citation.get("title", "")
                    })
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
    
    def query(
        self,
        query: str,
        session_id: Optional[str] = None
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
                "messages": messages
            }
            
            # Add tools if configured
            if tools:
                api_kwargs["tools"] = tools
                api_kwargs["extra_headers"] = {"web-fetch-2025-09-10": "true"}
            
            # Make API call
            response = self.client.messages.create(**api_kwargs)
            
            # Extract content from response
            content = ""
            for content_block in response.content:
                if hasattr(content_block, 'text'):
                    content += content_block.text
            
            # Extract citations if available
            citations = self._extract_citations(response) if self.config.citations_enabled else []
            
            # Format response with citations
            if citations:
                content = self._format_response_with_citations(content, citations)
            
            # Log successful response
            self.logger.info(
                "Query completed successfully",
                extra={
                    "session_id": session_id,
                    "model": response.model,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "citations_count": len(citations)
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