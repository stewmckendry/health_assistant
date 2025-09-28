"""
Clinical Intelligence Orchestrator Streaming Endpoint for FastAPI

Provides intelligent orchestration between Dr. OPA, Dr. OFF, and Agent 97
for comprehensive clinical guidance.
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator, Optional, List
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import logging

from src.agents.diagnostic_orchestrator.orchestrator_agent import create_diagnostic_orchestrator, DiagnosticOrchestrator

# Configure logging
logger = logging.getLogger(__name__)

# Cache orchestrator instance
_orchestrator_instance: Optional[DiagnosticOrchestrator] = None


class OrchestratorStreamRequest(BaseModel):
    """Request model for orchestrator queries."""
    sessionId: str
    query: str
    stream: bool = True
    userId: Optional[str] = None


class OrchestratorQueryRequest(BaseModel):
    """Request model for non-streaming orchestrator queries."""
    sessionId: str
    query: str
    userId: Optional[str] = None


async def get_orchestrator() -> DiagnosticOrchestrator:
    """Get or create the orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        logger.info("Creating new Clinical Intelligence Orchestrator instance...")
        _orchestrator_instance = await create_diagnostic_orchestrator()
        logger.info("Clinical Intelligence Orchestrator initialized")
    return _orchestrator_instance


def register_orchestrator_endpoint(app: FastAPI):
    """Register Clinical Intelligence Orchestrator endpoints with the FastAPI app."""
    
    @app.post("/agents/orchestrator/stream")
    async def stream_orchestrator_response(request: OrchestratorStreamRequest):
        """
        Stream responses from the Clinical Intelligence Orchestrator.
        
        The orchestrator intelligently routes queries to:
        - Dr. OPA for practice guidance and regulations
        - Dr. OFF for financing and coverage
        - Agent 97 for medical education
        """
        try:
            async def generate() -> AsyncGenerator[str, None]:
                # Get orchestrator instance
                orchestrator = await get_orchestrator()
                
                # Track event ID for this stream
                stream_id = str(uuid.uuid4())
                
                # Send initial event
                yield f"data: {json.dumps({'type': 'response_start', 'data': {'streamId': stream_id, 'orchestrator': 'Chief'}})}\n\n"
                
                try:
                    # Track citations to avoid duplicates
                    citations_sent = set()
                    
                    # Stream the orchestrated response
                    async for event in orchestrator.orchestrate_stream(
                        clinical_query=request.query,
                        session_id=request.sessionId,
                        user_id=request.userId
                    ):
                        if event['type'] == 'text':
                            # Stream text content
                            text_event = {
                                'type': 'text',
                                'data': {
                                    'delta': event['content']
                                }
                            }
                            yield f"data: {json.dumps(text_event)}\n\n"
                        
                        elif event['type'] == 'agent_consultation':
                            # Notify about agent being consulted
                            consultation_event = {
                                'type': 'agent_consultation',
                                'data': {
                                    'agent': event['content']['agent'],
                                    'status': event['content']['status'],
                                    'timestamp': datetime.now().isoformat()
                                }
                            }
                            yield f"data: {json.dumps(consultation_event)}\n\n"
                        
                        elif event['type'] == 'citation':
                            # Forward citations from agents
                            citation = event['content']
                            citation_key = f"{citation.get('url', '')}_{citation.get('title', '')}"
                            
                            if citation_key not in citations_sent:
                                citations_sent.add(citation_key)
                                citation_event = {
                                    'type': 'citation',
                                    'data': {
                                        'id': citation.get('id', f'citation_{uuid.uuid4().hex[:8]}'),
                                        'title': citation.get('title', 'Source'),
                                        'source': citation.get('source', ''),
                                        'url': citation.get('url', ''),
                                        'domain': citation.get('domain', ''),
                                        'isTrusted': citation.get('is_trusted', True),
                                        'sourceAgent': citation.get('source_agent', 'Unknown')
                                    }
                                }
                                yield f"data: {json.dumps(citation_event)}\n\n"
                        
                        elif event['type'] == 'complete':
                            # Send completion event with metadata including trace_id
                            complete_event = {
                                'type': 'response_done',
                                'data': {
                                    'message_id': str(uuid.uuid4()),
                                    'agents_consulted': event.get('agents_consulted', []),
                                    'orchestrator': event.get('orchestrator', 'Chief'),
                                    'traceId': event.get('trace_id'),  # Include traceId (camelCase for frontend)
                                    'timestamp': datetime.now().isoformat()
                                }
                            }
                            yield f"data: {json.dumps(complete_event)}\n\n"
                            break
                        
                        elif event['type'] == 'error':
                            # Send error event
                            error_event = {
                                'type': 'error',
                                'data': {
                                    'error': event['content'],
                                    'timestamp': datetime.now().isoformat()
                                }
                            }
                            yield f"data: {json.dumps(error_event)}\n\n"
                            break
                    
                except Exception as e:
                    logger.error(f"Error during orchestration streaming: {e}")
                    error_event = {
                        'type': 'error',
                        'data': {
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        }
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                
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
            logger.error(f"Error in orchestrator streaming endpoint: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/agents/orchestrator/query")
    async def query_orchestrator(request: OrchestratorQueryRequest):
        """
        Non-streaming query endpoint for the Clinical Intelligence Orchestrator.
        
        Returns a complete response with all agent consultations synthesized.
        """
        try:
            # Get orchestrator instance
            orchestrator = await get_orchestrator()
            
            # Process the query
            result = await orchestrator.orchestrate(
                clinical_query=request.query,
                session_id=request.sessionId,
                user_id=request.userId
            )
            
            # Format response for API including trace_id
            return {
                "response": result.get('response', ''),
                "agents_consulted": result.get('agents_consulted', []),
                "citations": result.get('citations', []),
                "confidence": result.get('confidence', 0.0),
                "orchestrator": result.get('orchestrator', 'Chief'),
                "trace_id": result.get('trace_id'),  # Include trace_id for feedback
                "model": result.get('model', 'gpt-4o'),
                "sessionId": request.sessionId,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in orchestrator query endpoint: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/agents/orchestrator/status")
    async def get_orchestrator_status():
        """
        Get the status of the Clinical Intelligence Orchestrator.
        
        Returns information about available agents and orchestrator health.
        """
        try:
            # Check if orchestrator is initialized
            is_initialized = _orchestrator_instance is not None
            
            status = {
                "orchestrator": "The Chief - Clinical Intelligence Orchestrator",
                "description": "Intelligent orchestration between Dr. OPA, Dr. OFF, and Agent 97",
                "status": "ready" if is_initialized else "not_initialized",
                "initialized": is_initialized,
                "available_agents": [
                    {
                        "name": "Dr. OPA",
                        "description": "Ontario Practice Advice - CPSO policies, clinical pathways",
                        "status": "available"
                    },
                    {
                        "name": "Dr. OFF",
                        "description": "Ontario Finance & Formulary - OHIP billing, ODB coverage",
                        "status": "available"
                    },
                    {
                        "name": "Agent 97",
                        "description": "Medical education from 97 trusted sources",
                        "status": "available"
                    }
                ],
                "capabilities": [
                    "Intelligent query routing to specialist agents",
                    "Multi-agent consultation and synthesis",
                    "Session-based conversation continuity",
                    "Real-time streaming responses",
                    "Citation aggregation and deduplication"
                ],
                "model": "gpt-4o",
                "timestamp": datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting orchestrator status: {e}")
            return {
                "orchestrator": "The Chief - Clinical Intelligence Orchestrator",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }