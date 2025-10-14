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

from src.ai_agents.agent_97.openai_agent import create_agent_97


class Agent97StreamRequest(BaseModel):
    sessionId: str
    query: str
    userId: str = None  # Add user ID for Langfuse tracing
    stream: bool = True
    reasoningEffort: str = "auto"  # "auto", "low", "medium", "high", or "off"


def register_agent_97_endpoint(app: FastAPI):
    """Register Agent 97 endpoints with the FastAPI app"""

    @app.post("/agents/agent-97/stream")
    async def stream_agent_97_response(request: Agent97StreamRequest):
        """
        Stream responses from Agent 97 using OpenAI Agent wrapper
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Agent 97 endpoint called - session: {request.sessionId}, query: {request.query[:50] if request.query else 'None'}...")

        try:
            async def generate() -> AsyncGenerator[str, None]:
                logger = logging.getLogger(__name__)
                logger.info(f"Creating Agent 97 for session {request.sessionId}")

                # Create the Agent 97 instance with reasoning effort
                agent = await create_agent_97(reasoning_effort=request.reasoningEffort)

                logger.info(f"Agent 97 created successfully, type: {type(agent)}")

                # Send initial event
                yield f"data: {json.dumps({'type': 'response_start', 'data': {}})}\n\n"

                try:
                    # Use real streaming from the agent with session and user_id
                    citations_sent = []
                    tool_ids = {}  # Track tool call IDs
                    trace_id = None  # Will be set from complete event

                    async for event in agent.query_stream(request.query, session_id=request.sessionId, user_id=request.userId):
                        if event['type'] == 'progress':
                            # Stream progress update
                            progress_event = {
                                "type": "progress",
                                "message": event.get('message', ''),
                                "event_type": event.get('event_type', ''),
                                "agent_name": event.get('agent_name', ''),
                                "tool_name": event.get('tool_name'),
                                "details": event.get('details'),
                                "timestamp": event.get('timestamp', '')
                            }
                            logger.info(f"📤 SENDING PROGRESS: {progress_event['message']}")
                            yield f"data: {json.dumps(progress_event)}\n\n"

                        elif event['type'] == 'text':
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
                                        'title': citation.get('title', 'Medical Source'),
                                        'source': citation.get('source', ''),
                                        'url': citation.get('url', ''),
                                        'domain': citation.get('domain', ''),
                                        'isTrusted': citation.get('is_trusted', True),
                                        'sourceType': citation.get('source_type', 'clinical_evidence')
                                    }
                                }
                                logger.info(f"📚 SENDING CITATION: {citation.get('title', 'Unknown')} - {citation.get('url', 'No URL')}")
                                yield f"data: {json.dumps(citation_event)}\n\n"

                        elif event['type'] == 'complete':
                            # Extract trace_id (at root level for Agent 97)
                            trace_id = event.get('trace_id')

                            # Mark all tool calls as completed
                            for tool_call in event.get('tool_calls', []):
                                # Agent 97 uses 'tool' key, not 'name'
                                tool_name = tool_call.get('tool', tool_call.get('name', 'mcp_tool'))
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

    @app.post("/agents/agent-97/query")
    async def query_agent_97(request: Agent97StreamRequest):
        """
        Non-streaming query endpoint for Agent 97
        """
        try:
            # Create the Agent 97 instance with reasoning effort
            agent = await create_agent_97(reasoning_effort=request.reasoningEffort)

            # Process query with session
            result = await agent.query(request.query, session_id=request.sessionId, user_id=request.userId)

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
                        'sourceType': cite.get('source_type', 'clinical_evidence')
                    }
                    for cite in result.get('citations', [])
                ],
                "toolCalls": [
                    {
                        'name': tc.get('tool', tc.get('name')),
                        'arguments': tc.get('arguments', {}),
                        'status': 'completed'
                    }
                    for tc in result.get('tool_calls', [])
                ],
                "confidence": result.get('confidence', 0.9)
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/agents/agent-97/health")
    async def agent_97_health_check():
        """
        Health check endpoint for Agent 97
        """
        try:
            # Try to create agent to verify it works
            agent = await create_agent_97()
            return {
                "status": "healthy",
                "agent": "Agent 97",
                "version": "2.0.0",
                "mcp_server": "agent-97-clinician-search",
                "tools": ["clinician_search", "clinician_search_get_domains", "clinician_search_health_check"],
                "model": "gpt-5-mini"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
