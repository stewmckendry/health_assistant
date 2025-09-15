"""Base assistant class for interacting with Anthropic API."""
import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
from time import perf_counter

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


# Helper functions for tool tracking
SENSITIVE_KEYS = {"authorization", "api_key", "cookie", "token", "password", "secret"}

def _sanitize_input(d: dict, limit: int = 2000) -> dict:
    """Sanitize and truncate tool input for logging."""
    if not isinstance(d, dict):
        return {}
    out = {}
    for k, v in d.items():
        if k.lower() in SENSITIVE_KEYS:
            out[k] = "[redacted]"
        elif isinstance(v, str) and len(v) > limit:
            out[k] = v[:limit] + f"... [truncated {len(v)-limit} chars]"
        else:
            out[k] = v
    return out

def _summ(o, limit: int = 4000) -> str:
    """Summarize tool output for logging."""
    if o is None:
        return ""
    try:
        s = o if isinstance(o, str) else json.dumps(o, ensure_ascii=False)
    except Exception:
        s = str(o)
    return s if len(s) <= limit else s[:limit] + f"... [truncated {len(s)-limit} chars]"

def _tool_meta(name: str, args: dict = None, result=None, tool_id=None, **extras):
    """Create metadata for tool observations."""
    meta = {"tool_name": name}
    if tool_id:
        meta["tool_id"] = tool_id
    
    if name == "web_search" and args:
        meta.update({
            "query": args.get("query"),
            "domains": args.get("domains"),
            "top_k": args.get("top_k"),
        })
        if isinstance(result, dict):
            meta["num_results"] = (len(result.get("results", []))
                                  if isinstance(result.get("results"), list) else None)
        elif isinstance(result, list):
            meta["num_results"] = len(result)
    elif name == "web_fetch":
        if args:
            meta["url"] = args.get("url")
        if isinstance(result, dict):
            meta.update({
                "status": result.get("status"),
                "bytes": (len(result.get("body", "")) if isinstance(result.get("body"), str) else None),
                "title": result.get("title"),
                "cache": result.get("cache"),
            })
        elif isinstance(result, list):
            meta["fetch_count"] = len(result)
    
    meta.update({k: v for k, v in extras.items() if v is not None})
    return meta


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
        user_id: Optional[str] = None,
        session_logger: Optional[Any] = None  # SessionLogger instance
    ) -> Dict[str, Any]:
        """
        Send a query to the Anthropic API.
        
        Args:
            query: User query
            session_id: Optional session identifier for logging
            user_id: Optional user identifier for tracking
        
        Returns:
            Response dictionary with content, model, usage, session_id, and user_id
        
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
            
            # Update Langfuse with session metadata before the API call
            if langfuse and settings.langfuse_enabled:
                try:
                    langfuse.update_current_observation(
                        metadata={
                            "session_id": session_id,
                            "user_id": user_id
                        }
                    )
                    # Also add tags for easy filtering
                    if session_id:
                        langfuse.update_current_trace(
                            session_id=session_id,
                            tags=[f"session:{session_id[:8]}"]  # Use first 8 chars for tag
                        )
                    if user_id:
                        langfuse.update_current_trace(
                            user_id=user_id,
                            tags=[f"user:{user_id}"]
                        )
                except Exception as e:
                    self.logger.debug(f"Failed to update observation metadata: {e}")
            
            # Make API call
            response = self.client.messages.create(**api_kwargs)
            
            # Process response and create tool spans as blocks arrive
            content_text = ""
            citations = []
            tool_calls = []
            
            # Track live tool spans by id
            tool_span_by_id = {}  # { tool_use_id: {"span": Span, "t0": float, "name": str, "args": dict} }
            
            # Track if web tools were used (server-side tools)
            web_search_span = None
            web_fetch_spans = []
            
            # Check if web_search was used by looking for multiple citations (heuristic)
            # or by checking if the query would trigger a web search
            has_web_search = False
            
            # PASS 1: Walk blocks; open spans for tool_use immediately
            self.logger.info(f"Response has {len(response.content)} blocks")
            for i, block in enumerate(response.content or []):
                block_type = getattr(block, "type", None)
                # Log ALL attributes of the block for debugging
                block_attrs = [attr for attr in dir(block) if not attr.startswith('_')]
                self.logger.info(f"Block {i}: type={block_type}, attrs={block_attrs[:10]}")  # First 10 attrs
                
                if block_type:
                    self.logger.info(f"Block {i} detail: type={block_type}, has_text={hasattr(block, 'text')}, has_citations={hasattr(block, 'citations')}")
                
                # Accumulate assistant text
                if block_type == "text" and getattr(block, "text", None):
                    content_text += str(block.text)
                    
                    # Collect citations from text blocks (Anthropic citations live on text)
                    if hasattr(block, "citations") and block.citations:
                        self.logger.info(f"Found {len(block.citations)} citations in text block")
                        
                        for c in block.citations:
                            url = getattr(c, "url", None) 
                            title = getattr(c, "title", None)
                            cit = {"url": url, "title": title}
                            if any(cit.values()):
                                citations.append(cit)
                
                # SERVER TOOL USE: Handle web_search and web_fetch (server-side tools)
                if getattr(block, "type", None) == "server_tool_use":
                    tool_name = getattr(block, "name", "unknown")
                    tool_args = getattr(block, "input", {}) or {}
                    tool_id = getattr(block, "id", None)
                    
                    self.logger.info(f"Found server_tool_use block: name='{tool_name}', id={tool_id}, args={tool_args}")
                    
                    # Create span for ANY server tool (not just web_search/web_fetch)
                    if langfuse and settings.langfuse_enabled:
                        try:
                            # Start span and enter context to get the actual span object
                            span_context = langfuse.start_as_current_span(
                                name=f"tool:{tool_name}"
                            )
                            span = span_context.__enter__()  # Get the actual span object
                            
                            # Different input format for each tool
                            if tool_name == "web_search":
                                span_input = {"query": tool_args.get("query", "")}
                                span_metadata = {
                                    "session_id": session_id,
                                    "user_id": user_id,
                                    "tool_name": "web_search",
                                    "query": tool_args.get("query", "")
                                }
                            else:  # web_fetch
                                span_input = {"url": tool_args.get("url", ""), "prompt": tool_args.get("prompt", "")}
                                span_metadata = {
                                    "session_id": session_id,
                                    "user_id": user_id,
                                    "tool_name": "web_fetch",
                                    "url": tool_args.get("url", ""),
                                    "prompt": tool_args.get("prompt", "")
                                }
                            
                            span.update(
                                input=span_input,
                                metadata=span_metadata
                            )
                            
                            if tool_name == "web_search":
                                has_web_search = True
                            
                            self.logger.info(f"Created {tool_name} span with id: {tool_id}")
                            
                            # Store for later update - use tool_id as key
                            span_key = tool_id or tool_name
                            tool_span_by_id[span_key] = {
                                "span": span,
                                "span_context": span_context,  # Store context for proper cleanup
                                "t0": perf_counter(), 
                                "name": tool_name, 
                                "args": tool_args
                            }
                        except Exception as e:
                            self.logger.error(f"Failed to create {tool_name} span: {e}")
                    
                    # Keep record for response
                    tool_calls.append({"type": "server_tool_use", "name": tool_name, "input": tool_args})
                
                # CLIENT TOOL USE: Handle traditional tool_use blocks
                elif getattr(block, "type", None) == "tool_use":
                    tool_name = getattr(block, "name", "unknown")
                    tool_args = getattr(block, "input", {}) or {}
                    tool_id = getattr(block, "id", None)
                    
                    self.logger.info(f"Found tool_use block: {tool_name}, type: {block.type}, id: {tool_id}")
                    
                    if langfuse and settings.langfuse_enabled:
                        try:
                            span_context = langfuse.start_as_current_span(
                                name=f"tool:{tool_name}"
                            )
                            span = span_context.__enter__()  # Get the actual span object
                            
                            span.update(
                                input=_sanitize_input(tool_args),
                                metadata={
                                    "session_id": session_id,
                                    "user_id": getattr(self, "user_id", None),
                                    "tool_id": tool_id,
                                    "tool_name": tool_name
                                }
                            )
                            
                            self.logger.info(f"Created tool span for {tool_name}")
                            
                            tool_span_by_id[tool_id or f"{tool_name}:{len(tool_span_by_id)}"] = {
                                "span": span,
                                "span_context": span_context,
                                "t0": perf_counter(),
                                "name": tool_name,
                                "args": tool_args
                            }
                        except Exception as e:
                            self.logger.error(f"Failed to create tool span for {tool_name}: {e}", exc_info=True)
                    
                    # Keep a compact record for the response payload
                    tool_calls.append({"type": "tool_use", "name": tool_name, "input": tool_args, "id": tool_id})
                
                # TOOL RESULT blocks - check multiple possible block types
                # Claude may use different block types for tool results
                possible_result_types = ["tool_result", "web_search_tool_result", "web_fetch_tool_result", "server_tool_result"]
                if getattr(block, "type", None) in possible_result_types:
                    block_type = getattr(block, "type", None)
                    self.logger.info(f"Found {block_type} block")
                    result_payload = getattr(block, "result", None) or getattr(block, "content", None)
                    tool_use_id = getattr(block, "tool_use_id", None) or getattr(block, "id", None)
                    tool_name = getattr(block, "name", None)
                    
                    # Log detailed result info for debugging
                    self.logger.info(f"Result block: type={block_type}, tool_use_id={tool_use_id}, name={tool_name}, has_result={result_payload is not None}")
                    if result_payload:
                        self.logger.info(f"Result type: {type(result_payload)}, has_len={hasattr(result_payload, '__len__')}")
                    
                    # Find the corresponding span by tool_use_id or tool name
                    span_key = tool_use_id
                    if not span_key:
                        # Fallback - try to find by matching tool name
                        if tool_name:
                            # Look for a span with matching name
                            for key, info in tool_span_by_id.items():
                                if info.get("name") == tool_name:
                                    span_key = key
                                    break
                    
                    if span_key in tool_span_by_id:
                        info = tool_span_by_id[span_key]
                        try:
                            # Format output based on tool type
                            if block_type == "web_search_tool_result":
                                result_count = 0
                                search_results = []
                                
                                # Extract search results if available
                                if result_payload:
                                    if hasattr(result_payload, "__len__"):
                                        result_count = len(result_payload)
                                    
                                    # Try to extract result details (titles, URLs, snippets)
                                    try:
                                        if hasattr(result_payload, '__iter__'):
                                            for i, result in enumerate(result_payload[:10], 1):  # Limit to first 10
                                                # Try different attribute names for URL and title
                                                url = getattr(result, "url", getattr(result, "link", None))
                                                title = getattr(result, "title", getattr(result, "name", None))
                                                snippet = getattr(result, "snippet", getattr(result, "description", ""))
                                                
                                                if url or title:
                                                    # Truncate snippet to 100 chars
                                                    if snippet and len(snippet) > 100:
                                                        snippet = snippet[:97] + "..."
                                                    
                                                    result_str = f"{i}. "
                                                    if title:
                                                        result_str += f"{title[:60]} "
                                                    if url:
                                                        result_str += f"({url[:50]})"
                                                    if snippet:
                                                        result_str += f" - {snippet}"
                                                    
                                                    search_results.append(result_str)
                                    except Exception as e:
                                        self.logger.debug(f"Could not extract search result details: {e}")
                                
                                # Create output text with results list
                                output_text = f"Found {result_count} search results"
                                if search_results:
                                    output_text += ":\n" + "\n".join(search_results)
                                
                                extra_metadata = {"result_count": result_count}
                                
                            else:  # web_fetch_tool_result
                                # Extract content info from web_fetch result
                                content_length = 0
                                content_preview = ""
                                
                                if result_payload:
                                    # Try to get content string
                                    content_str = ""
                                    if hasattr(result_payload, "content"):
                                        content_str = str(result_payload.content)
                                    elif hasattr(result_payload, "text"):
                                        content_str = str(result_payload.text)
                                    elif isinstance(result_payload, str):
                                        content_str = result_payload
                                    
                                    content_length = len(content_str)
                                    
                                    # Get first 500 chars as preview
                                    if content_str:
                                        content_preview = content_str[:500]
                                        if len(content_str) > 500:
                                            content_preview += "..."
                                
                                output_text = f"Fetched {content_length} characters"
                                if content_preview:
                                    output_text += f":\n{content_preview}"
                                
                                extra_metadata = {"content_length": content_length}
                            
                            # Update span with results
                            info["span"].update(
                                output=output_text,
                                metadata={
                                    "session_id": session_id,
                                    "tool_name": info["name"],
                                    "duration_ms": round((perf_counter() - info["t0"]) * 1000, 1),
                                    **extra_metadata
                                }
                            )
                            info["span"].end()
                            # Properly exit the context manager
                            if "span_context" in info:
                                info["span_context"].__exit__(None, None, None)
                            tool_span_by_id.pop(span_key, None)
                            self.logger.info(f"Closed {info['name']} span: {output_text}")
                        except Exception as e:
                            self.logger.error(f"Failed to update {info['name']} span: {e}")
                
                # Handle traditional tool results
                elif getattr(block, "type", None) == "tool_result":
                    result_payload = getattr(block, "result", None)
                    span_key = getattr(block, "tool_use_id", None) or getattr(block, "id", None)
                    info = tool_span_by_id.get(span_key)
                    if info and info.get("span"):
                        try:
                            info["span"].update(
                                output=_summ(result_payload) or f"{info['name']} completed",
                                metadata=_tool_meta(
                                    info["name"], 
                                    info["args"], 
                                    result_payload, 
                                    tool_id=span_key,
                                    duration_ms=round((perf_counter() - info["t0"]) * 1000, 1)
                                )
                            )
                            info["span"].end()
                            # Properly exit the context manager
                            if "span_context" in info:
                                info["span_context"].__exit__(None, None, None)
                            tool_span_by_id.pop(span_key, None)
                        except Exception as e:
                            self.logger.debug(f"Failed to update tool span: {e}")
            
            # PASS 2: Close any spans that didn't get an explicit tool_result
            for key, info in list(tool_span_by_id.items()):
                if info and info.get("span"):
                    try:
                        info["span"].update(
                            output=f"{info['name']} executed",
                            metadata=_tool_meta(
                                info["name"], 
                                info["args"], 
                                result=None, 
                                tool_id=key,
                                duration_ms=round((perf_counter() - info["t0"]) * 1000, 1)
                            )
                        )
                        info["span"].end()
                        # Properly exit the context manager
                        if "span_context" in info:
                            info["span_context"].__exit__(None, None, None)
                    except Exception as e:
                        self.logger.debug(f"Failed to close tool span: {e}")
            
            # Process tool calls for web_fetch details from citations
            # Claude's web_fetch results appear as citations in text blocks
            if citations:
                for i, citation in enumerate(citations[:5]):  # Limit to first 5
                    url = citation.get("url")
                    title = citation.get("title", "content")
                    
                    # Add to tool_calls for tracking
                    tool_calls.append({
                        "type": "web_fetch",
                        "name": "web_fetch",
                        "input": {"url": url},
                        "result": f"Fetched: {title}",
                        "id": f"fetch_{i}"
                    })
                    
                    # Create a web_fetch span for each citation
                    if langfuse and settings.langfuse_enabled and url:
                        try:
                            span_context = langfuse.start_as_current_span(
                                name="tool:web_fetch"
                            )
                            span = span_context.__enter__()
                            
                            span.update(
                                input={"url": url},
                                output=f"Fetched: {title}",
                                metadata={
                                    "session_id": session_id,
                                    "user_id": user_id,
                                    "tool_name": "web_fetch",
                                    "url": url,
                                    "title": title,
                                    "citation_index": i
                                }
                            )
                            span.end()
                            span_context.__exit__(None, None, None)
                            
                            self.logger.info(f"Created web_fetch span for citation {i}: {url}")
                        except Exception as e:
                            self.logger.error(f"Failed to create web_fetch span for citation: {e}")
            
            # Extract additional citations if needed (beyond what we already collected)
            all_citations = self._extract_citations(response) if self.config.citations_enabled else citations
            
            # Format response with citations
            if all_citations:
                content_text = self._format_response_with_citations(content_text, all_citations)
            
            # Update Langfuse generation with complete details
            if langfuse and settings.langfuse_enabled:
                try:
                    langfuse.update_current_observation(
                        model=self.model,
                        input=messages,
                        output=content_text,
                        metadata={
                            "session_id": session_id,
                            "user_id": user_id,
                            "system_prompt": self.config.system_prompt[:200],  # First 200 chars
                            "tools_enabled": tools is not None,
                            "trusted_domains_count": len(self.trusted_domains) if tools else 0,
                            "tool_calls_count": len(tool_calls),
                            "citations_count": len(all_citations),
                            "tool_calls": [
                                {"name": tc.get("name"), "type": tc.get("type"), "id": tc.get("id")}
                                for tc in tool_calls
                            ] if tool_calls else []
                        },
                        usage={
                            "input_tokens": response.usage.input_tokens,
                            "output_tokens": response.usage.output_tokens,
                            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                        }
                    )
                except Exception as e:
                    self.logger.debug(f"Failed to update Langfuse observation: {e}")
            
            # Log API response if session logger provided
            if session_logger:
                session_logger.log_api_response(
                    response_text=content_text,
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
                if all_citations:
                    session_logger.log_citations(all_citations)
            
            # Log successful response
            self.logger.info(
                "Query completed successfully",
                extra={
                    "session_id": session_id,
                    "model": response.model,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "citations_count": len(all_citations),
                    "tool_calls_count": len(tool_calls)
                }
            )
            
            return {
                "content": content_text,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                "citations": all_citations,
                "tool_calls": tool_calls,
                "session_id": session_id,
                "user_id": user_id
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