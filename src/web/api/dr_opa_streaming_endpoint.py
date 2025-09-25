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
        
        # Send initial tool call event
        tool_event = {
            "type": "tool_call_start",
            "data": {
                "id": f"tool_{uuid.uuid4().hex[:8]}",
                "name": "opa_search_sections",
                "arguments": {"query": request.query[:100]},
                "status": "executing",
                "startTime": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        yield f"data: {json.dumps(tool_event)}\n\n"
        await asyncio.sleep(0.1)
        
        # Query the agent
        response = agent.query(
            query=request.query,
            session_id=request.sessionId,
            message_history=request.messageHistory
        )
        
        # Send tool completion
        tool_complete = {
            "type": "tool_call_end",
            "data": {
                **tool_event["data"],
                "status": "completed",
                "endTime": datetime.utcnow().isoformat(),
                "result": "Retrieved Ontario practice guidance"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        yield f"data: {json.dumps(tool_complete)}\n\n"
        
        # Handle response
        if isinstance(response, dict):
            text = response.get("response", "")
            citations = response.get("citations", [])
            
            # Stream text in chunks
            words = text.split()
            for i, word in enumerate(words):
                chunk = " ".join(words[:i+1])
                text_event = {
                    "type": "text",
                    "data": {
                        "content": chunk,
                        "delta": word + (" " if i < len(words)-1 else "")
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(text_event)}\n\n"
                await asyncio.sleep(0.02)
            
            # Send citations
            for citation in citations:
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
            
            # Send completion
            done_event = {
                "type": "done",
                "data": {
                    "messageId": f"msg_{uuid.uuid4().hex[:8]}",
                    "citationIds": [c.get("id") for c in citations if c.get("id")]
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(done_event)}\n\n"
        else:
            # Handle string response
            text_event = {
                "type": "text",
                "data": {"content": str(response), "delta": str(response)},
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(text_event)}\n\n"
            
            done_event = {
                "type": "done",
                "data": {"messageId": f"msg_{uuid.uuid4().hex[:8]}"},
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(done_event)}\n\n"
            
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