"""
Simple streaming proxy for agent endpoints.
Provides streaming responses without complex dependencies.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import json
import asyncio
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class StreamingAgentRequest(BaseModel):
    """Request model for streaming agent queries."""
    query: str = Field(description="The query to process")
    sessionId: Optional[str] = Field(None, description="Session ID for tracking")
    messageHistory: Optional[List[Dict[str, str]]] = Field(None, description="Previous messages")
    stream: bool = Field(default=True, description="Enable streaming")


async def simulate_agent_stream(agent_id: str, request: StreamingAgentRequest):
    """
    Simulate agent streaming response with realistic data.
    This is a placeholder that will be replaced with real agent calls.
    """
    assessment_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    try:
        # Send initial tool call event
        tool_name = "opa_search_sections" if agent_id == "dr-opa" else "agent_97_query"
        tool_event = {
            "type": "tool_call_start",
            "data": {
                "id": f"tool_{uuid.uuid4().hex[:8]}",
                "name": tool_name,
                "arguments": {"query": request.query[:100]},
                "status": "executing",
                "startTime": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        yield f"data: {json.dumps(tool_event)}\n\n"
        await asyncio.sleep(0.5)
        
        # Send tool completion
        tool_complete = {
            "type": "tool_call_end",
            "data": {
                **tool_event["data"],
                "status": "completed",
                "endTime": datetime.utcnow().isoformat(),
                "result": "Retrieved relevant information"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        yield f"data: {json.dumps(tool_complete)}\n\n"
        
        # Generate sample response based on agent
        if agent_id == "dr-opa":
            response_text = (
                f"Based on Ontario practice guidance for your query '{request.query[:50]}...', "
                "I can provide the following information from CPSO policies and Ontario Health programs. "
                "According to current regulatory requirements, practitioners should follow established "
                "protocols as outlined in the relevant policy documents. Please verify specific requirements "
                "with official sources and use clinical judgment."
            )
            citation = {
                "title": "CPSO Virtual Care Policy",
                "source": "College of Physicians and Surgeons of Ontario",
                "url": "https://www.cpso.on.ca/",
                "domain": "cpso.on.ca"
            }
        else:  # agent-97
            response_text = (
                f"Regarding your health education question about '{request.query[:50]}...', "
                "I can provide educational information from trusted medical sources. "
                "This information is drawn from reputable medical organizations and is intended "
                "for educational purposes only. Always consult with your healthcare provider "
                "for personalized medical advice."
            )
            citation = {
                "title": "Health Information",
                "source": "Mayo Clinic",
                "url": "https://www.mayoclinic.org/",
                "domain": "mayoclinic.org"
            }
        
        # Stream text response
        words = response_text.split()
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
            await asyncio.sleep(0.03)
        
        # Send citation
        citation_event = {
            "type": "citation",
            "data": {
                "id": f"citation_{uuid.uuid4().hex[:8]}",
                "title": citation["title"],
                "source": citation["source"],
                "url": citation["url"],
                "domain": citation["domain"],
                "isTrusted": True,
                "accessDate": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        yield f"data: {json.dumps(citation_event)}\n\n"
        
        # Send completion
        done_event = {
            "type": "done",
            "data": {
                "messageId": f"msg_{uuid.uuid4().hex[:8]}",
                "citationIds": [citation_event["data"]["id"]]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        yield f"data: {json.dumps(done_event)}\n\n"
        
    except Exception as e:
        logger.error(f"Agent streaming error: {e}")
        error_event = {
            "type": "error",
            "data": {"error": str(e)},
            "timestamp": datetime.utcnow().isoformat()
        }
        yield f"data: {json.dumps(error_event)}\n\n"


def register_agent_streaming_endpoints(app):
    """
    Register streaming endpoints for Dr. OPA and Agent 97.
    
    Args:
        app: FastAPI application instance
    """
    @app.post("/api/agents/dr-opa/stream")
    async def dr_opa_stream(request: StreamingAgentRequest):
        """Dr. OPA Streaming Endpoint"""
        return StreamingResponse(
            simulate_agent_stream("dr-opa", request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
    
    @app.post("/api/agents/agent-97/stream")
    async def agent_97_stream(request: StreamingAgentRequest):
        """Agent 97 Streaming Endpoint"""
        return StreamingResponse(
            simulate_agent_stream("agent-97", request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )