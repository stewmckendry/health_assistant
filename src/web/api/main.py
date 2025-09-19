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
import logging

# Load environment variables FIRST, before any other imports
from dotenv import load_dotenv
# Go up to the actual project root (health_assistant_triage)
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Debug: Print environment variables
import os
print(f"Loading .env from: {env_path}")
print(f"LANGFUSE_PUBLIC_KEY: {os.getenv('LANGFUSE_PUBLIC_KEY', 'NOT SET')[:20]}..." if os.getenv('LANGFUSE_PUBLIC_KEY') else "LANGFUSE_PUBLIC_KEY: NOT SET")
print(f"LANGFUSE_SECRET_KEY: {'SET' if os.getenv('LANGFUSE_SECRET_KEY') else 'NOT SET'}")
print(f"LANGFUSE_HOST: {os.getenv('LANGFUSE_HOST', 'NOT SET')}")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Now import FastAPI and other modules
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import json
import asyncio

# Add src directory to path to import modules
sys.path.insert(0, str(project_root / "src"))

from assistants.patient import PatientAssistant
from assistants.provider import ProviderAssistant
from utils.session_logging import SessionLogger
from langfuse import Langfuse

# Import triage endpoints
from src.web.api.triage_endpoint import register_triage_endpoint
from src.web.api.triage_streaming_endpoint import register_streaming_endpoint

# Initialize FastAPI app
app = FastAPI(
    title="Health Assistant API",
    description="API for AI-powered medical education platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",  # Next.js dev server on alternate port
        "https://health-assistant.vercel.app",  # Production Vercel URL
        "https://health-assistant-*.vercel.app",  # Allow health-assistant deployments
        "https://health-assistant-stewart-mckendrys-projects.vercel.app",  # Project-specific URL
        "https://health-assistant-*-stewart-mckendrys-projects.vercel.app",  # Branch deployments
        "https://*.vercel.app"  # Allow Vercel preview deployments
    ],
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
    
    # Log which mode is being requested
    logger.info(f"get_assistant called with mode: '{mode}'")
    
    if mode == "provider":
        if provider_assistant is None:
            provider_assistant = ProviderAssistant()
        logger.info("Returning ProviderAssistant instance")
        return provider_assistant
    else:
        # Default to patient mode
        if patient_assistant is None:
            patient_assistant = PatientAssistant()
        logger.info("Returning PatientAssistant instance")
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
# Session settings store
session_settings: Dict[str, Dict[str, Any]] = {}

# Register triage endpoints
register_triage_endpoint(app)
register_streaming_endpoint(app)


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


class SessionSettingsRequest(BaseModel):
    # Safety Settings
    enable_input_guardrails: Optional[bool] = True
    enable_output_guardrails: Optional[bool] = False
    guardrail_mode: Optional[str] = "llm"
    
    # Performance Settings
    enable_streaming: Optional[bool] = True
    max_web_searches: Optional[int] = 1
    max_web_fetches: Optional[int] = 2
    response_timeout: Optional[int] = 30
    
    # Content Settings
    enable_trusted_domains: Optional[bool] = True
    custom_trusted_domains: Optional[List[str]] = []
    blocked_domains: Optional[List[str]] = []
    include_citations: Optional[str] = "always"
    response_detail_level: Optional[str] = "standard"
    show_confidence_scores: Optional[bool] = False
    
    # Model Settings
    model: Optional[str] = "claude-3-5-sonnet-20241022"
    temperature: Optional[float] = 0.3
    max_tokens: Optional[int] = 1000
    
    # Display Settings
    show_tool_calls: Optional[bool] = False
    show_response_timing: Optional[bool] = False
    markdown_rendering: Optional[bool] = True


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
        # Get session settings or use defaults
        settings_dict = session_settings.get(request.sessionId, {})
        
        # Determine if we should use streaming
        use_streaming = settings_dict.get('enable_streaming', True)
        output_guardrails = settings_dict.get('enable_output_guardrails', False)
        
        # If output guardrails are enabled, can't use streaming
        if output_guardrails:
            use_streaming = False
        
        # Note: We don't redirect to streaming here anymore
        # The /chat endpoint should always use non-streaming for proper Langfuse traces
        # Users should explicitly call /chat/stream if they want streaming
        
        # Get services - use mode from request
        assistant = get_assistant(request.mode)
        # Pass session settings to assistant
        if hasattr(assistant, 'session_settings'):
            assistant.session_settings = settings_dict
            assistant.enable_input_guardrails = settings_dict.get('enable_input_guardrails', True)
            assistant.enable_output_guardrails = settings_dict.get('enable_output_guardrails', False)
        
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


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Process a chat request with streaming response using Server-Sent Events.
    """
    async def event_generator():
        try:
            # Get session settings
            settings_dict = session_settings.get(request.sessionId, {})
            
            # Log the incoming request mode
            logger.info(f"chat_stream received request with mode: '{request.mode}' for session: {request.sessionId}")
            
            # Get services - use mode from request
            assistant = get_assistant(request.mode)
            # Pass session settings to assistant
            if hasattr(assistant, 'session_settings'):
                assistant.session_settings = settings_dict
                assistant.enable_input_guardrails = settings_dict.get('enable_input_guardrails', True)
                assistant.enable_output_guardrails = settings_dict.get('enable_output_guardrails', False)
            
            # Retrieve conversation history for this session
            message_history = []
            if request.sessionId in sessions:
                # Convert session messages to Anthropic format (only content, not metadata)
                for msg in sessions[request.sessionId]["messages"]:
                    message_history.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Variables to accumulate response data
            accumulated_text = ""
            citations = []
            tool_calls = []
            trace_id = None  # Will be set from assistant's response
            
            # Stream the response
            for event in assistant.query_stream(
                query=request.query,
                session_id=request.sessionId,
                user_id=request.userId,
                message_history=message_history
            ):
                print(f"DEBUG: Received event type: {event.get('type')}, metadata: {event.get('metadata', {})}")
                # Convert event to SSE format
                if event["type"] == "start":
                    # Don't set trace_id here - it's not available until complete event
                    # Send initial event with metadata
                    sse_data = {
                        "type": "start",
                        "sessionId": request.sessionId,
                        "traceId": None,  # Will be set in complete event
                        "mode": request.mode
                    }
                    yield f"data: {json.dumps(sse_data)}\n\n"
                
                elif event["type"] == "text":
                    # Stream text chunks
                    accumulated_text += event["content"]
                    sse_data = {
                        "type": "text",
                        "content": event["content"],
                        "metadata": event.get("metadata", {})
                    }
                    yield f"data: {json.dumps(sse_data)}\n\n"
                
                elif event["type"] == "tool_use":
                    # Send tool use events
                    tool_calls.append(event["content"])
                    sse_data = {
                        "type": "tool_use",
                        "content": event["content"]
                    }
                    yield f"data: {json.dumps(sse_data)}\n\n"
                
                elif event["type"] == "citation":
                    # Send citation events
                    citations.append(event["content"])
                    sse_data = {
                        "type": "citation",
                        "content": event["content"]
                    }
                    yield f"data: {json.dumps(sse_data)}\n\n"
                
                elif event["type"] == "complete":
                    # Extract the actual Langfuse trace ID from the complete event
                    # The patient assistant includes this in the metadata after creating the trace
                    complete_metadata = event.get("metadata", {})
                    actual_trace_id = complete_metadata.get("trace_id")
                    print(f"DEBUG: Complete event metadata: {complete_metadata}")
                    print(f"DEBUG: Extracted trace_id: {actual_trace_id}")
                    if actual_trace_id:
                        trace_id = actual_trace_id
                    # Don't use a fallback UUID - if we don't have a real trace ID,
                    # we won't show feedback buttons (better than logging to wrong trace)
                    
                    # Send final event with all data
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
                            "mode": request.mode
                        },
                        {
                            "role": "assistant",
                            "content": accumulated_text,
                            "timestamp": datetime.now().isoformat(),
                            "citations": citations,
                            "mode": request.mode
                        }
                    ])
                    
                    sse_data = {
                        "type": "complete",
                        "content": accumulated_text,
                        "citations": citations,
                        "toolCalls": tool_calls,
                        "metadata": event.get("metadata", {}),
                        "traceId": trace_id  # Will be None if no real trace ID
                    }
                    yield f"data: {json.dumps(sse_data)}\n\n"
                
                elif event["type"] == "error":
                    # Send error event
                    sse_data = {
                        "type": "error",
                        "error": event["content"]
                    }
                    yield f"data: {json.dumps(sse_data)}\n\n"
                
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)
            
        except Exception as e:
            # Send error event
            sse_data = {
                "type": "error",
                "error": str(e)
            }
            yield f"data: {json.dumps(sse_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )


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


@app.get("/settings/trusted-domains")
async def get_trusted_domains():
    """
    Get the default list of trusted medical domains from configuration.
    """
    from src.config.settings import settings
    return {
        "trusted_domains": settings.trusted_domains,
        "count": len(settings.trusted_domains)
    }


@app.get("/sessions/{session_id}/settings")
async def get_session_settings(session_id: str):
    """
    Get settings for a specific session.
    """
    settings_dict = session_settings.get(session_id, {})
    # Also include default trusted domains for reference
    from src.config.settings import settings
    return {
        "sessionId": session_id,
        "settings": settings_dict,
        "default_trusted_domains": settings.trusted_domains
    }


@app.put("/sessions/{session_id}/settings")
async def update_session_settings(session_id: str, request: SessionSettingsRequest):
    """
    Update settings for a specific session.
    """
    # Convert request to dict and store
    settings_dict = request.dict(exclude_unset=True)
    session_settings[session_id] = settings_dict
    
    return {
        "sessionId": session_id,
        "settings": settings_dict,
        "success": True
    }


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