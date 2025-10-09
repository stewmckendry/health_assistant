"""
Streaming FastAPI endpoint for Dr. OPA Agent.
Provides /api/agents/dr-opa/stream endpoint for real-time responses.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import json
import asyncio
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Import agent module - we'll instantiate inline
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Don't import the agent class directly to avoid dependency issues
# We'll use subprocess to call the agent
from src.utils.logging import get_logger

logger = get_logger(__name__)


class StreamingDrOPARequest(BaseModel):
    """Request model for streaming Dr. OPA queries."""
    query: str = Field(description="The query to process")
    sessionId: Optional[str] = Field(None, description="Session ID for tracking")
    messageHistory: Optional[List[Dict[str, str]]] = Field(None, description="Previous messages")
    stream: bool = Field(default=True, description="Enable streaming")


async def process_dr_opa_stream(request: StreamingDrOPARequest):
    """
    Process a Dr. OPA query with streaming updates.
    
    Yields Server-Sent Events (SSE) with progress updates.
    
    Args:
        request: StreamingDrOPARequest with query data
        
    Yields:
        SSE formatted strings with progress updates
    """
    assessment_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    try:
        logger.info(
            f"Dr. OPA streaming request received",
            extra={
                "assessment_id": assessment_id,
                "query": request.query[:100],
                "session_id": request.sessionId
            }
        )
        
        # Initialize agent
        agent = DrOPAAgent()

        # Use the agent's native streaming method
        async for event in agent.query_stream(
            user_input=request.query,
            session_id=request.sessionId,
            user_id=None
        ):
            event_type = event.get('type')

            if event_type == 'text':
                # Stream text delta
                yield f"data: {json.dumps({'type': 'text', 'data': {'delta': event['content']}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            elif event_type == 'tool_call':
                # Stream tool call
                tool_data = event['content']
                yield f"data: {json.dumps({'type': 'tool_call_start', 'data': tool_data, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            elif event_type == 'citation':
                # Stream citation
                citation = event['content']
                citation_event = {
                    "type": "citation",
                    "data": {
                        "id": citation.get("id", f"citation_{uuid.uuid4().hex[:8]}"),
                        "title": citation.get("title", ""),
                        "source": citation.get("source", ""),
                        "url": citation.get("url", ""),
                        "domain": citation.get("domain", ""),
                        "isTrusted": citation.get("is_trusted", True),
                        "accessDate": citation.get("access_date", datetime.utcnow().isoformat())
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(citation_event)}\n\n"

            elif event_type == 'complete':
                # Send final completion event
                done_event = {
                    "type": "done",
                    "data": {
                        "messageId": f"msg_{uuid.uuid4().hex[:8]}",
                        "citationIds": [c.get("id") for c in event.get('citations', [])],
                        "traceId": event.get('metadata', {}).get('trace_id')
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(done_event)}\n\n"

            elif event_type == 'error':
                # Stream error
                error_event = {
                    "type": "error",
                    "data": {"error": event['content']},
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(error_event)}\n\n"
            
    except Exception as e:
        logger.error(f"Dr. OPA streaming error: {e}")
        error_event = {
            "type": "error",
            "data": {"error": str(e)},
            "timestamp": datetime.utcnow().isoformat()
        }
        yield f"data: {json.dumps(error_event)}\n\n"


def register_dr_opa_streaming_endpoint(app):
    """
    Register the streaming Dr. OPA endpoint with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    @app.post("/api/agents/dr-opa/stream")
    async def dr_opa_stream(request: StreamingDrOPARequest):
        """
        Dr. OPA Streaming Endpoint
        
        Provides Ontario practice guidance with real-time streaming updates.
        Returns Server-Sent Events (SSE) with response progress.
        
        This endpoint:
        - Shows MCP tool calls in progress
        - Streams response text as it's generated
        - Provides citations from trusted Ontario sources
        - Returns structured guidance for clinical practice
        """
        return StreamingResponse(
            process_dr_opa_stream(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )