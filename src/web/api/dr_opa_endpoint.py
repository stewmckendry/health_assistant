"""
Dr. OPA Streaming Endpoint for FastAPI
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agents.dr_opa_agent.openai_agent import create_dr_opa_agent


class DrOPAStreamRequest(BaseModel):
    sessionId: str
    query: str
    stream: bool = True


def register_dr_opa_endpoint(app: FastAPI):
    """Register Dr. OPA endpoints with the FastAPI app"""
    
    @app.post("/agents/dr-opa/stream")
    async def stream_dr_opa_response(request: DrOPAStreamRequest):
        """
        Stream responses from Dr. OPA Agent using OpenAI Agent wrapper
        """
        try:
            async def generate() -> AsyncGenerator[str, None]:
                # Create the Dr. OPA agent instance
                agent = await create_dr_opa_agent()
                
                # Send initial event
                yield f"data: {json.dumps({'type': 'response_start', 'data': {}})}\n\n"
                
                try:
                    # Check if agent has streaming method
                    if hasattr(agent, 'query_stream'):
                        # Use real streaming from the agent
                        citations_sent = []
                        
                        async for event in agent.query_stream(request.query):
                            if event['type'] == 'text':
                                # Stream text deltas
                                text_event = {
                                    'type': 'text',
                                    'data': {
                                        'delta': event['content']
                                    }
                                }
                                yield f"data: {json.dumps(text_event)}\n\n"
                            
                            elif event['type'] == 'tool_call':
                                # Send tool call event
                                tool_event = {
                                    'type': 'tool_call_start',
                                    'data': {
                                        'id': f'tool_{uuid.uuid4().hex[:8]}',
                                        'name': event['content'].get('name', 'mcp_tool'),
                                        'arguments': event['content'].get('arguments', {}),
                                        'status': 'executing'
                                    }
                                }
                                yield f"data: {json.dumps(tool_event)}\n\n"
                            
                            elif event['type'] == 'citation':
                                # Send citation event (deduplicated)
                                citation = event['content']
                                if citation.get('url') and citation['url'] not in citations_sent:
                                    citations_sent.append(citation['url'])
                                    citation_event = {
                                        'type': 'citation',
                                        'data': {
                                            'id': citation.get('id', f'citation_{uuid.uuid4().hex[:8]}'),
                                            'title': citation.get('title', 'Source'),
                                            'source': citation.get('source', ''),
                                            'url': citation.get('url', ''),
                                            'domain': citation.get('domain', ''),
                                            'isTrusted': citation.get('is_trusted', True)
                                        }
                                    }
                                    yield f"data: {json.dumps(citation_event)}\n\n"
                            
                            elif event['type'] == 'complete':
                                # Mark all tool calls as completed
                                for tool_call in event.get('tool_calls', []):
                                    tool_complete_event = {
                                        'type': 'tool_call_complete',
                                        'data': {
                                            'id': f'tool_{uuid.uuid4().hex[:8]}',
                                            'name': tool_call.get('name', 'mcp_tool'),
                                            'status': 'completed'
                                        }
                                    }
                                    yield f"data: {json.dumps(tool_complete_event)}\n\n"
                            
                            elif event['type'] == 'error':
                                # Send error event
                                yield f"data: {json.dumps({'type': 'error', 'data': {'error': event['content']}})}\n\n"
                    
                    else:
                        # Fallback to non-streaming query
                        result = await agent.query(request.query)
                        
                        # Convert OpenAI Agent response to streaming format
                        if isinstance(result, dict):
                            # Stream the response content
                            response_text = result.get('response', '')
                            tool_calls = result.get('tool_calls', [])
                            citations = result.get('citations', [])
                            
                            # Send tool call events first
                            for tool_call in tool_calls:
                                tool_event = {
                                    'type': 'tool_call_start',
                                    'data': {
                                        'id': f'tool_{uuid.uuid4().hex[:8]}',
                                        'name': tool_call.get('name', 'mcp_tool'),
                                        'arguments': tool_call.get('arguments', {}),
                                        'status': 'completed'
                                    }
                                }
                                yield f"data: {json.dumps(tool_event)}\n\n"
                            
                            # Send citations
                            citations_sent = []
                            for citation in citations:
                                if citation.get('url') and citation['url'] not in citations_sent:
                                    citations_sent.append(citation['url'])
                                    citation_event = {
                                        'type': 'citation',
                                        'data': {
                                            'id': citation.get('id', f'citation_{uuid.uuid4().hex[:8]}'),
                                            'title': citation.get('title', 'Source'),
                                            'source': citation.get('source', ''),
                                            'url': citation.get('url', ''),
                                            'domain': citation.get('domain', ''),
                                            'isTrusted': citation.get('is_trusted', True)
                                        }
                                    }
                                    yield f"data: {json.dumps(citation_event)}\n\n"
                            
                            # Stream text content in chunks (simulate streaming)
                            words = response_text.split(' ')
                            for i, word in enumerate(words):
                                # Send individual word chunks
                                word_with_space = word + (' ' if i < len(words) - 1 else '')
                                text_event = {
                                    'type': 'text',
                                    'data': {
                                        'delta': word_with_space
                                    }
                                }
                                yield f"data: {json.dumps(text_event)}\n\n"
                                await asyncio.sleep(0.03)  # Small delay for natural streaming
                        else:
                            # Fallback for string response
                            text_event = {
                                'type': 'text',
                                'data': {
                                    'delta': str(result)
                                }
                            }
                            yield f"data: {json.dumps(text_event)}\n\n"
                    
                    # Send completion event
                    yield f"data: {json.dumps({'type': 'response_done', 'data': {'message_id': str(uuid.uuid4())}})}\n\n"
                    
                except Exception as e:
                    # Send error event
                    yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}})}\n\n"
                
                # End stream
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/agents/dr-opa/query")
    async def query_dr_opa(request: DrOPAStreamRequest):
        """
        Non-streaming query endpoint for Dr. OPA
        """
        try:
            agent = await create_dr_opa_agent()
            response = await agent.query(request.query)
            
            return {
                "response": response.get('response', str(response)) if isinstance(response, dict) else str(response),
                "tool_calls": response.get('tool_calls', []) if isinstance(response, dict) else [],
                "tools_used": response.get('tools_used', []) if isinstance(response, dict) else [],
                "citations": response.get('citations', []) if isinstance(response, dict) else [],
                "sessionId": request.sessionId
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))