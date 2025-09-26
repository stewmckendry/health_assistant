"""
Agent 97 Streaming Endpoint for FastAPI
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.assistants.patient import PatientAssistant


class Agent97StreamRequest(BaseModel):
    sessionId: str
    query: str
    stream: bool = True


def register_agent_97_endpoint(app: FastAPI):
    """Register Agent 97 endpoints with the FastAPI app"""
    
    @app.post("/agents/agent-97/stream")
    async def stream_agent_97_response(request: Agent97StreamRequest):
        """
        Stream responses from Agent 97
        """
        try:
            async def generate() -> AsyncGenerator[str, None]:
                # Initialize the assistant
                assistant = PatientAssistant()
                
                # Send initial event
                yield f"data: {json.dumps({'type': 'response_start', 'data': {}})}\n\n"
                
                # Process the query with streaming
                try:
                    # Use the streaming method from PatientAssistant
                    citations_sent = []
                    
                    for chunk in assistant.query_stream(request.query, session_id=request.sessionId):
                        if chunk['type'] == 'tool_use':
                            # Forward tool call events
                            tool_event = {
                                'type': 'tool_call_start',
                                'data': {
                                    'id': chunk.get('id', f'tool_{uuid.uuid4().hex[:8]}'),
                                    'name': chunk.get('content', {}).get('name', 'web_search'),
                                    'arguments': chunk.get('content', {}).get('arguments', {}),
                                    'status': 'executing'
                                }
                            }
                            yield f"data: {json.dumps(tool_event)}\n\n"
                        
                        elif chunk['type'] == 'text':
                            # Stream text content directly from the assistant
                            text_event = {
                                'type': 'text',
                                'data': {
                                    'delta': chunk.get('content', '')
                                }
                            }
                            yield f"data: {json.dumps(text_event)}\n\n"
                        
                        elif chunk['type'] == 'citation':
                            # Forward citation events
                            citation = chunk.get('content', {})
                            if citation and citation.get('url') not in citations_sent:
                                citations_sent.append(citation.get('url'))
                                citation_event = {
                                    'type': 'citation',
                                    'data': {
                                        'id': f'citation_{uuid.uuid4().hex[:8]}',
                                        'title': citation.get('title', 'Medical Source'),
                                        'source': citation.get('source', ''),
                                        'url': citation.get('url', ''),
                                        'domain': citation.get('url', '').replace('https://', '').replace('http://', '').split('/')[0] if citation.get('url') else '',
                                        'isTrusted': True
                                    }
                                }
                                yield f"data: {json.dumps(citation_event)}\n\n"
                    
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
    
    @app.post("/agents/agent-97/query")
    async def query_agent_97(request: Agent97StreamRequest):
        """
        Non-streaming query endpoint for Agent 97
        """
        try:
            assistant = PatientAssistant()
            response = assistant.query(request.query)
            
            return {
                "response": response,
                "tool_calls": [],
                "tools_used": [],
                "sessionId": request.sessionId
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))