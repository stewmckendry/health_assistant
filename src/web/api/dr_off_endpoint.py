"""
Dr. OFF Streaming Endpoint for FastAPI
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agents.dr_off_agent.openai_agent import create_dr_off_agent


class DrOffStreamRequest(BaseModel):
    sessionId: str
    query: str
    stream: bool = True
    userId: str = None  # Add user ID for Langfuse tracing


def register_dr_off_endpoint(app: FastAPI):
    """Register Dr. OFF endpoints with the FastAPI app"""
    
    @app.post("/agents/dr-off/stream")
    async def stream_dr_off_response(request: DrOffStreamRequest):
        """
        Stream responses from Dr. OFF Agent using OpenAI Agent wrapper
        """
        try:
            async def generate() -> AsyncGenerator[str, None]:
                # Create the Dr. OFF agent instance
                agent = await create_dr_off_agent()
                
                # Send initial event
                yield f"data: {json.dumps({'type': 'response_start', 'data': {}})}\n\n"
                
                try:
                    # Check if agent has streaming method
                    if hasattr(agent, 'query_stream'):
                        # Use real streaming from the agent with session and user_id
                        citations_sent = []
                        tool_ids = {}  # Track tool call IDs
                        trace_id = None  # Will be set from complete event
                        
                        async for event in agent.query_stream(request.query, session_id=request.sessionId, user_id=request.userId):
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
                                tool_id = f'tool_{uuid.uuid4().hex[:8]}'
                                tool_name = event['content'].get('name', 'mcp_tool')
                                tool_ids[tool_name] = tool_id
                                
                                tool_event = {
                                    'type': 'tool_call_start',
                                    'data': {
                                        'id': tool_id,
                                        'name': tool_name,
                                        'arguments': event['content'].get('arguments', {}),
                                        'status': 'executing'
                                    }
                                }
                                yield f"data: {json.dumps(tool_event)}\n\n"
                            
                            elif event['type'] == 'citation':
                                # Send citation event (deduplicated)
                                citation = event['content']
                                citation_key = f"{citation.get('url', '')}_{citation.get('title', '')}"
                                if citation_key not in citations_sent:
                                    citations_sent.append(citation_key)
                                    citation_event = {
                                        'type': 'citation',
                                        'data': {
                                            'id': citation.get('id', f'citation_{uuid.uuid4().hex[:8]}'),
                                            'title': citation.get('title', 'Source'),
                                            'source': citation.get('source', ''),
                                            'url': citation.get('url', ''),
                                            'domain': citation.get('domain', ''),
                                            'isTrusted': citation.get('is_trusted', True),
                                            'sourceType': citation.get('source_type', 'policy')
                                        }
                                    }
                                    yield f"data: {json.dumps(citation_event)}\n\n"
                            
                            elif event['type'] == 'complete':
                                # Extract trace_id from metadata if available
                                metadata = event.get('metadata', {})
                                trace_id = metadata.get('trace_id')
                                
                                # Mark all tool calls as completed
                                for tool_call in event.get('tool_calls', []):
                                    tool_name = tool_call.get('name', 'mcp_tool')
                                    tool_id = tool_ids.get(tool_name, f'tool_{uuid.uuid4().hex[:8]}')
                                    tool_complete_event = {
                                        'type': 'tool_call_complete',
                                        'data': {
                                            'id': tool_id,
                                            'name': tool_name,
                                            'status': 'completed'
                                        }
                                    }
                                    yield f"data: {json.dumps(tool_complete_event)}\n\n"
                            
                            elif event['type'] == 'error':
                                # Send error event
                                error_event = {
                                    'type': 'error',
                                    'data': {
                                        'message': event['content']
                                    }
                                }
                                yield f"data: {json.dumps(error_event)}\n\n"
                    else:
                        # Fallback to non-streaming query with session and user_id
                        result = await agent.query(request.query, session_id=request.sessionId, user_id=request.userId)
                        
                        # Extract trace_id from result
                        trace_id = result.get('trace_id')
                        
                        # Send citations first
                        for citation in result.get('citations', []):
                            citation_event = {
                                'type': 'citation',
                                'data': {
                                    'id': citation.get('id', f'citation_{uuid.uuid4().hex[:8]}'),
                                    'title': citation.get('title', 'Source'),
                                    'source': citation.get('source', ''),
                                    'url': citation.get('url', ''),
                                    'domain': citation.get('domain', ''),
                                    'isTrusted': citation.get('is_trusted', True),
                                    'sourceType': citation.get('source_type', 'policy')
                                }
                            }
                            yield f"data: {json.dumps(citation_event)}\n\n"
                        
                        # Send tool calls
                        for tool_call in result.get('tool_calls', []):
                            tool_id = f'tool_{uuid.uuid4().hex[:8]}'
                            # Send start event
                            tool_start_event = {
                                'type': 'tool_call_start',
                                'data': {
                                    'id': tool_id,
                                    'name': tool_call.get('name', 'mcp_tool'),
                                    'arguments': tool_call.get('arguments', {}),
                                    'status': 'executing'
                                }
                            }
                            yield f"data: {json.dumps(tool_start_event)}\n\n"
                            
                            # Send complete event
                            await asyncio.sleep(0.1)  # Small delay for visual effect
                            tool_complete_event = {
                                'type': 'tool_call_complete',
                                'data': {
                                    'id': tool_id,
                                    'name': tool_call.get('name', 'mcp_tool'),
                                    'status': 'completed'
                                }
                            }
                            yield f"data: {json.dumps(tool_complete_event)}\n\n"
                        
                        # Send response text
                        response_text = result.get('response', '')
                        text_event = {
                            'type': 'text',
                            'data': {
                                'delta': response_text
                            }
                        }
                        yield f"data: {json.dumps(text_event)}\n\n"
                
                except Exception as e:
                    # Send error event
                    error_event = {
                        'type': 'error',
                        'data': {
                            'message': str(e)
                        }
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                
                # Send completion event with trace_id for feedback
                complete_event = {
                    'type': 'response_done',
                    'data': {
                        'sessionId': request.sessionId,
                        'traceId': trace_id  # Include trace_id for feedback functionality
                    }
                }
                yield f"data: {json.dumps(complete_event)}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable Nginx buffering
                }
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/agents/dr-off/query")
    async def query_dr_off(request: DrOffStreamRequest):
        """
        Non-streaming query endpoint for Dr. OFF Agent
        """
        try:
            # Create the Dr. OFF agent instance
            agent = await create_dr_off_agent()
            
            # Process query with session
            result = await agent.query(request.query, session_id=request.sessionId)
            
            # Format response for frontend
            return {
                "sessionId": request.sessionId,
                "response": result.get('response', ''),
                "citations": [
                    {
                        'id': cite.get('id'),
                        'title': cite.get('title'),
                        'source': cite.get('source'),
                        'url': cite.get('url'),
                        'domain': cite.get('domain'),
                        'isTrusted': cite.get('is_trusted', True),
                        'sourceType': cite.get('source_type', 'policy')
                    }
                    for cite in result.get('citations', [])
                ],
                "toolCalls": [
                    {
                        'name': tc.get('name'),
                        'arguments': tc.get('arguments'),
                        'status': 'completed'
                    }
                    for tc in result.get('tool_calls', [])
                ],
                "confidence": result.get('confidence', 0.8)
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/agents/dr-off/health")
    async def dr_off_health_check():
        """
        Health check endpoint for Dr. OFF Agent
        """
        try:
            # Try to create agent to verify it works
            agent = await create_dr_off_agent()
            return {
                "status": "healthy",
                "agent": "Dr. OFF",
                "version": "1.0.0",
                "mcp_server": "dr-off-server",
                "tools": ["schedule_get", "odb_get", "adp_get"]
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }