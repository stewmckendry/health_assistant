"""
Chief Resident - Ontario Healthcare Coordinator Streaming Endpoint for FastAPI

Provides intelligent orchestration between Dr. OPA (Ontario regulations),
Dr. OFF (Ontario coverage), and Agent 97 (clinical evidence) for
comprehensive Ontario-specific clinical decision support.
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

import os

# Use HTTP version on Railway, regular version locally
if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("USE_HTTP_MCP"):
    from src.ai_agents.diagnostic_orchestrator.orchestrator_agent_http import create_orchestrator_http as create_diagnostic_orchestrator
    from src.ai_agents.diagnostic_orchestrator.orchestrator_agent_http import ClinicalIntelligenceOrchestratorHTTP as DiagnosticOrchestrator
else:
    from src.ai_agents.diagnostic_orchestrator.orchestrator_agent import create_diagnostic_orchestrator, DiagnosticOrchestrator

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
        logger.info("Creating new Chief Resident orchestrator instance...")
        _orchestrator_instance = await create_diagnostic_orchestrator()
        logger.info("Chief Resident orchestrator initialized")
    return _orchestrator_instance


def register_orchestrator_endpoint(app: FastAPI):
    """Register Chief Resident orchestrator endpoints with the FastAPI app."""

    @app.post("/agents/orchestrator/stream")
    async def stream_orchestrator_response(request: OrchestratorStreamRequest):
        """
        Stream responses from Chief Resident - Ontario Healthcare Coordinator.

        Chief Resident intelligently routes queries to:
        - Dr. OPA for Ontario regulations (CPSO, Ontario Health, PHO)
        - Dr. OFF for Ontario coverage (OHIP, ODB, ADP)
        - Agent 97 for clinical evidence from 97 trusted sources
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
                    # Track tool IDs for agent consultations
                    tool_ids = {}
                    
                    # Stream the orchestrated response
                    async for event in orchestrator.orchestrate_stream(
                        clinical_query=request.query,
                        session_id=request.sessionId,
                        user_id=request.userId
                    ):
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
                            yield f"data: {json.dumps(progress_event)}\n\n"

                        elif event['type'] == 'text':
                            # Stream text content
                            text_event = {
                                'type': 'text',
                                'data': {
                                    'delta': event['content']
                                }
                            }
                            yield f"data: {json.dumps(text_event)}\n\n"

                        elif event['type'] == 'agent_consultation':
                            # Safely extract content
                            content = event.get('content', {})
                            if isinstance(content, dict):
                                agent_name = content.get('agent', 'Unknown')
                                status = content.get('status', 'consulting')
                            else:
                                agent_name = 'Unknown'
                                status = 'consulting'
                            
                            # Send tool_call_start event for UI to show the agent being called
                            if status == 'consulting':
                                # Generate tool ID for this agent consultation
                                tool_id = f'tool_{uuid.uuid4().hex[:8]}'
                                tool_ids[agent_name] = tool_id
                                
                                tool_call_start_event = {
                                    'type': 'tool_call_start',
                                    'data': {
                                        'id': tool_id,
                                        'name': agent_name,  # Just the agent name (Dr. OPA, Dr. OFF, Agent 97)
                                        'arguments': {'query': request.query},
                                        'timestamp': datetime.now().isoformat()
                                    }
                                }
                                yield f"data: {json.dumps(tool_call_start_event)}\n\n"
                            
                            elif status == 'completed' and agent_name in tool_ids:
                                # Send tool_call_complete when agent finishes
                                tool_call_complete_event = {
                                    'type': 'tool_call_complete',
                                    'data': {
                                        'id': tool_ids[agent_name],
                                        'name': agent_name,
                                        'status': 'completed',
                                        'timestamp': datetime.now().isoformat()
                                    }
                                }
                                yield f"data: {json.dumps(tool_call_complete_event)}\n\n"
                        
                        elif event['type'] == 'citation':
                            # Forward citations from agents
                            citation = event.get('content', {})
                            if isinstance(citation, dict):
                                citation_key = f"{citation.get('url', '')}_{citation.get('title', '')}_{citation.get('source', '')}"
                                
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
                            # Send citations from the response (check for duplicates)
                            for cite in event.get('citations', []):
                                citation_key = None
                                citation_event = None
                                
                                if isinstance(cite, str):
                                    # String citation (URL or text)
                                    citation_key = f"{cite}_Ontario Health Resource_"
                                    
                                    if citation_key not in citations_sent:
                                        citations_sent.add(citation_key)
                                        citation_event = {
                                            'type': 'citation',
                                            'data': {
                                                'id': f'citation_{uuid.uuid4().hex[:8]}',
                                                'title': 'Ontario Health Resource',
                                                'source': cite if not cite.startswith('http') else 'Ontario Health',
                                                'url': cite if cite.startswith('http') else '',
                                                'domain': 'formulary.health.gov.on.ca' if 'formulary' in cite else 'ontario.ca',
                                                'isTrusted': True,
                                                'sourceAgent': 'Chief Orchestrator'
                                            }
                                        }
                                        yield f"data: {json.dumps(citation_event)}\n\n"
                                        
                                elif isinstance(cite, dict):
                                    # Dictionary citation with structured data
                                    citation_key = f"{cite.get('url', '')}_{cite.get('title', '')}_{cite.get('source', '')}"
                                    
                                    if citation_key not in citations_sent:
                                        citations_sent.add(citation_key)
                                        citation_event = {
                                            'type': 'citation',
                                            'data': {
                                                'id': cite.get('id', f'citation_{uuid.uuid4().hex[:8]}'),
                                                'title': cite.get('title', 'Source'),
                                                'source': cite.get('source', ''),
                                                'url': cite.get('url', ''),
                                                'domain': cite.get('domain', ''),
                                                'isTrusted': cite.get('is_trusted', True),
                                                'sourceAgent': cite.get('source_agent', 'Chief Orchestrator')
                                            }
                                        }
                                        yield f"data: {json.dumps(citation_event)}\n\n"
                            
                            # Send tool calls summary
                            for tc in event.get('tool_calls', []):
                                tool_summary_event = {
                                    'type': 'tool_summary',
                                    'data': {
                                        'agent': tc.get('agent', 'Unknown'),
                                        'tool': tc.get('tool', 'unknown'),
                                        'sub_tools': tc.get('sub_tools', [])
                                    }
                                }
                                yield f"data: {json.dumps(tool_summary_event)}\n\n"
                            
                            # Send completion event with metadata including trace_id
                            complete_event = {
                                'type': 'response_done',
                                'data': {
                                    'message_id': str(uuid.uuid4()),
                                    'agents_consulted': event.get('agents_consulted', []),
                                    'tool_calls': event.get('tool_calls', []),
                                    'citations_count': len(event.get('citations', [])),
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
        Non-streaming query endpoint for Chief Resident - Ontario Healthcare Coordinator.

        Returns a unified response synthesizing guidance from Ontario-specific sources.
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
        Get the status of Chief Resident - Ontario Healthcare Coordinator.

        Returns information about available Ontario healthcare agents and system health.
        """
        try:
            # Check if orchestrator is initialized
            is_initialized = _orchestrator_instance is not None

            status = {
                "orchestrator": "Chief Resident - Ontario Healthcare Coordinator",
                "description": "Coordinates Ontario-specific guidance from Dr. OPA (regulations), Dr. OFF (coverage), and Agent 97 (clinical evidence)",
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
                "orchestrator": "Chief Resident - Ontario Healthcare Coordinator",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }