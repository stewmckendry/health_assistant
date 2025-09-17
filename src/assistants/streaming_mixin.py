"""Streaming support mixin for assistants."""

import json
from typing import Dict, Any, List, Optional, AsyncIterator, Iterator
from time import perf_counter
from langfuse import observe, get_client
import logging

class StreamingMixin:
    """Mixin to add streaming support to assistant classes."""
    
    @observe(name="llm_call_stream", as_type="generation", capture_input=True)
    def query_stream(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_logger: Optional[Any] = None,
        message_history: Optional[List[Dict[str, str]]] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream a query response from the Anthropic API.
        
        Yields:
            Dict events with keys:
            - type: "start", "text", "tool_use", "citation", "error", "complete"
            - content: The content for this event
            - metadata: Additional metadata (timing, tool names, etc.)
        """
        try:
            # Build request components
            messages = self._build_messages(query, message_history)
            tools = self._build_tools()
            
            # Track timing
            start_time = perf_counter()
            first_token_time = None
            
            # Track accumulated content
            accumulated_text = ""
            citations = []
            tool_calls = []
            
            # Prepare API call kwargs
            api_kwargs = {
                "model": self.model,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "system": self.config.system_prompt,
                "messages": messages
            }
            
            # Add tools if configured
            if tools:
                api_kwargs["tools"] = tools
                api_kwargs["extra_headers"] = {
                    "anthropic-beta": "web-search-2025-03-05,web-fetch-2025-09-10"
                }
            
            # Yield start event
            yield {
                "type": "start",
                "content": None,
                "metadata": {
                    "session_id": session_id,
                    "user_id": user_id,
                    "model": self.model,
                    "timestamp": perf_counter() - start_time
                }
            }
            
            # Start streaming
            with self.client.messages.stream(**api_kwargs) as stream:
                for event in stream:
                    current_time = perf_counter() - start_time
                    
                    if event.type == "content_block_start":
                        block_type = getattr(event.content_block, 'type', None)
                        
                        # Handle tool use
                        if block_type == "server_tool_use":
                            tool_name = getattr(event.content_block, 'name', 'unknown')
                            tool_input = getattr(event.content_block, 'input', {})
                            
                            tool_calls.append({
                                "name": tool_name,
                                "input": tool_input,
                                "timestamp": current_time
                            })
                            
                            yield {
                                "type": "tool_use",
                                "content": {
                                    "name": tool_name,
                                    "input": tool_input
                                },
                                "metadata": {
                                    "timestamp": current_time
                                }
                            }
                    
                    elif event.type == "content_block_delta":
                        # Stream text as it arrives
                        if hasattr(event.delta, 'text'):
                            text_chunk = event.delta.text
                            
                            if first_token_time is None:
                                first_token_time = current_time
                            
                            accumulated_text += text_chunk
                            
                            yield {
                                "type": "text",
                                "content": text_chunk,
                                "metadata": {
                                    "timestamp": current_time,
                                    "total_length": len(accumulated_text),
                                    "is_first_token": first_token_time == current_time
                                }
                            }
                
                # Get final message for citations and usage
                final_message = stream.get_final_message()
                
                # Extract citations from final message
                for block in final_message.content:
                    if hasattr(block, 'citations') and block.citations:
                        for citation in block.citations:
                            citation_dict = {
                                "url": getattr(citation, 'url', ''),
                                "title": getattr(citation, 'title', 'Source')
                            }
                            if citation_dict['url'] and citation_dict not in citations:
                                citations.append(citation_dict)
                                
                                yield {
                                    "type": "citation",
                                    "content": citation_dict,
                                    "metadata": {
                                        "timestamp": perf_counter() - start_time,
                                        "total_citations": len(citations)
                                    }
                                }
                
                # Update Langfuse with final details
                langfuse = get_client()
                if langfuse and hasattr(self, 'config'):
                    try:
                        langfuse.update_current_observation(
                            model=self.model,
                            input=messages,
                            output=accumulated_text,
                            metadata={
                                "session_id": session_id,
                                "user_id": user_id,
                                "streaming": True,
                                "system_prompt": self.config.system_prompt[:200] if hasattr(self, 'config') else None,
                                "tools_enabled": tools is not None,
                                "trusted_domains_count": len(self.trusted_domains) if hasattr(self, 'trusted_domains') and tools else 0,
                                "time_to_first_token": first_token_time,
                                "total_time": perf_counter() - start_time,
                                "citations_count": len(citations),
                                "tool_calls_count": len(tool_calls),
                                "tool_calls": [
                                    {"name": tc.get("name"), "timestamp": tc.get("timestamp")}
                                    for tc in tool_calls
                                ] if tool_calls else []
                            },
                            usage={
                                "input_tokens": final_message.usage.input_tokens,
                                "output_tokens": final_message.usage.output_tokens,
                                "total_tokens": final_message.usage.input_tokens + final_message.usage.output_tokens
                            }
                        )
                    except Exception as e:
                        logging.debug(f"Failed to update Langfuse: {e}")
                
                # Yield complete event with final stats
                yield {
                    "type": "complete",
                    "content": {
                        "total_text": accumulated_text,
                        "citations": citations,
                        "tool_calls": tool_calls
                    },
                    "metadata": {
                        "total_time": perf_counter() - start_time,
                        "time_to_first_token": first_token_time,
                        "usage": {
                            "input_tokens": final_message.usage.input_tokens,
                            "output_tokens": final_message.usage.output_tokens,
                            "total_tokens": final_message.usage.input_tokens + final_message.usage.output_tokens
                        },
                        "citations_count": len(citations),
                        "tool_calls_count": len(tool_calls),
                        "session_id": session_id,
                        "user_id": user_id
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Streaming query failed: {e}", exc_info=True)
            yield {
                "type": "error",
                "content": str(e),
                "metadata": {
                    "timestamp": perf_counter() - start_time if 'start_time' in locals() else 0
                }
            }