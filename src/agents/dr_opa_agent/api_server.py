"""
FastAPI server for Dr. OPA Agent
Provides HTTP endpoints for web app integration
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, AsyncGenerator
import asyncio
import json
import logging
from datetime import datetime
import uuid

from src.agents.dr_opa_agent.openai_agent import DrOPAAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dr. OPA Agent API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent
agent = DrOPAAgent()

class QueryRequest(BaseModel):
    sessionId: str
    query: str
    stream: bool = True
    messageHistory: Optional[List[Dict[str, str]]] = None

class HealthResponse(BaseModel):
    status: str
    agent: str
    version: str
    timestamp: str

@app.get("/health")
async def health_check() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        agent="dr-opa",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )

@app.post("/agents/dr-opa/stream")
async def stream_query(request: QueryRequest):
    """Stream agent responses with SSE"""
    
    async def generate_events() -> AsyncGenerator[str, None]:
        try:
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
                    "result": "Retrieved relevant guidance"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(tool_complete)}\n\n"
            
            # Stream text response
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
                    await asyncio.sleep(0.02)  # Small delay for realistic streaming
                
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
                # Fallback for string response
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
            logger.error(f"Error in stream: {e}")
            error_event = {
                "type": "error",
                "data": {"error": str(e)},
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.post("/agents/dr-opa/chat")
async def chat_query(request: QueryRequest):
    """Non-streaming chat endpoint"""
    try:
        response = agent.query(
            query=request.query,
            session_id=request.sessionId,
            message_history=request.messageHistory
        )
        
        if isinstance(response, dict):
            return response
        else:
            return {
                "response": str(response),
                "citations": [],
                "tool_calls": []
            }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")