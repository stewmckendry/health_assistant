"""
FastAPI server for the Health Assistant web application.
Provides API endpoints for chat, feedback, and session management.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

# Load environment variables FIRST, before any other imports
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Now import FastAPI and other modules
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add src directory to path to import modules
sys.path.insert(0, str(project_root))

from assistants.patient import PatientAssistant
from assistants.provider import ProviderAssistant
from utils.session_logging import SessionLogger
from langfuse import Langfuse

# Initialize FastAPI app
app = FastAPI(
    title="Health Assistant API",
    description="API for AI-powered medical education platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services - delay initialization to avoid import issues
patient_assistant = None
provider_assistant = None
langfuse = None

def get_assistant(mode: str = "patient"):
    """
    Get the appropriate assistant based on mode.
    
    Args:
        mode: Either "patient" or "provider"
    
    Returns:
        PatientAssistant or ProviderAssistant instance
    """
    global patient_assistant, provider_assistant
    
    if mode == "provider":
        if provider_assistant is None:
            provider_assistant = ProviderAssistant()
        return provider_assistant
    else:
        # Default to patient mode
        if patient_assistant is None:
            patient_assistant = PatientAssistant()
        return patient_assistant

def get_langfuse():
    global langfuse
    if langfuse is None:
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    return langfuse

# In-memory session store (for demo purposes)
sessions: Dict[str, Dict[str, Any]] = {}


# Request/Response models
class ChatRequest(BaseModel):
    query: str
    sessionId: str
    userId: Optional[str] = None
    mode: Optional[str] = "patient"  # New field for mode switching


class Citation(BaseModel):
    url: str
    title: str
    snippet: str


class ChatResponse(BaseModel):
    content: str
    citations: List[Citation]
    traceId: str
    sessionId: str
    guardrailTriggered: Optional[bool] = False
    toolCalls: Optional[List[Dict[str, Any]]] = None
    mode: Optional[str] = "patient"  # Include mode in response


class FeedbackRequest(BaseModel):
    traceId: str
    sessionId: str
    userId: Optional[str] = None
    rating: Optional[int] = None
    comment: Optional[str] = None
    thumbsUp: Optional[bool] = None


class SessionResponse(BaseModel):
    id: str
    userId: str
    createdAt: str
    messages: List[Dict[str, Any]]


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat request using the appropriate assistant based on mode.
    """
    try:
        # Get services - use mode from request
        assistant = get_assistant(request.mode)
        langfuse_client = get_langfuse()
        
        # Retrieve conversation history for this session
        message_history = []
        if request.sessionId in sessions:
            # Convert session messages to Anthropic format (only content, not metadata)
            for msg in sessions[request.sessionId]["messages"]:
                message_history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Process query with assistant (it has its own @observe decorator)
        response = assistant.query(
            query=request.query,
            session_id=request.sessionId,
            user_id=request.userId,
            message_history=message_history  # Pass conversation history
        )
        
        # Handle response - it might be a dict or an object
        if isinstance(response, dict):
            response_content = response.get('content', str(response))
            response_citations = response.get('citations', [])
            guardrail_triggered = response.get('guardrails_applied', False)  # Fixed key name
            tool_calls = response.get('tool_calls', None)
            response_mode = response.get('mode', 'patient')
            # Get trace_id from response (added by assistant)
            trace_id = response.get('trace_id')
        else:
            response_content = getattr(response, 'content', str(response))
            response_citations = getattr(response, 'citations', [])
            guardrail_triggered = getattr(response, 'guardrails_applied', False)
            tool_calls = getattr(response, 'tool_calls', None)
            response_mode = getattr(response, 'mode', 'patient')
            trace_id = getattr(response, 'trace_id', None)
        
        # Generate a fallback trace ID if we didn't get one
        if not trace_id:
            trace_id = str(uuid.uuid4())
        
        # Extract citations from response
        citations = []
        if response_citations:
            citations = [
                Citation(
                    url=c.get('url', ''),
                    title=c.get('title', ''),
                    snippet=c.get('snippet', '')
                )
                for c in response_citations
            ]
        
        # Store message in session
        if request.sessionId not in sessions:
            sessions[request.sessionId] = {
                "id": request.sessionId,
                "userId": request.userId or "anonymous",
                "createdAt": datetime.now().isoformat(),
                "messages": []
            }
        
        sessions[request.sessionId]["messages"].extend([
            {
                "role": "user",
                "content": request.query,
                "timestamp": datetime.now().isoformat(),
                "mode": request.mode  # Track mode per message
            },
            {
                "role": "assistant",
                "content": response_content,
                "timestamp": datetime.now().isoformat(),
                "citations": citations,
                "mode": response_mode  # Track mode in response
            }
        ])
        
        # Flush Langfuse
        langfuse_client.flush()
        
        return ChatResponse(
            content=response_content,
            citations=citations,
            traceId=trace_id,
            sessionId=request.sessionId,
            guardrailTriggered=guardrail_triggered,
            toolCalls=tool_calls,
            mode=response_mode  # Include mode in response
        )
        
    except Exception as e:
        # Log error to Langfuse
        if 'span' in locals():
            span.end(
                output={"error": str(e)},
                level="ERROR"
            )
            langfuse_client.flush()
        
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit user feedback for a specific interaction.
    """
    try:
        # Get Langfuse client
        langfuse_client = get_langfuse()
        
        # Submit feedback to Langfuse using create_score
        if request.rating is not None:
            langfuse_client.create_score(
                trace_id=request.traceId,
                name="user-rating",
                value=float(request.rating),
                comment=request.comment,
                data_type="NUMERIC"
            )
        
        if request.thumbsUp is not None:
            langfuse_client.create_score(
                trace_id=request.traceId,
                name="user-feedback",
                value=1.0 if request.thumbsUp else 0.0,
                comment=request.comment,
                data_type="BOOLEAN"
            )
        
        if request.comment and not request.rating and request.thumbsUp is None:
            langfuse_client.create_score(
                trace_id=request.traceId,
                name="user-comment",
                value="commented",
                comment=request.comment,
                data_type="CATEGORICAL"
            )
        
        # Flush Langfuse
        langfuse_client.flush()
        
        return {"success": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    Retrieve session information.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    return SessionResponse(
        id=session["id"],
        userId=session["userId"],
        createdAt=session["createdAt"],
        messages=session["messages"]
    )


@app.post("/sessions")
async def create_session(userId: Optional[str] = None):
    """
    Create a new session.
    """
    session_id = str(uuid.uuid4())
    user_id = userId or f"user_{uuid.uuid4()}"
    
    sessions[session_id] = {
        "id": session_id,
        "userId": user_id,
        "createdAt": datetime.now().isoformat(),
        "messages": []
    }
    
    return {
        "sessionId": session_id,
        "userId": user_id,
        "createdAt": sessions[session_id]["createdAt"]
    }


if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )