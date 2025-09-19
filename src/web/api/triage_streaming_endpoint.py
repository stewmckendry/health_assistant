"""
Streaming FastAPI endpoint for the Emergency Triage Assistant.
Provides /api/agents/triage/stream endpoint for real-time progress updates.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import json
import asyncio
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agents.clinical.orchestrator_streaming import run_triage_assessment_streaming
from src.utils.logging import get_logger

logger = get_logger(__name__)


class StreamingTriageRequest(BaseModel):
    """Request model for streaming triage assessment."""
    # Demographics
    age: int = Field(description="Patient age in years", ge=0, le=150)
    sex: Optional[str] = Field(None, description="Patient sex", pattern="^(Male|Female|Other)$")
    
    # Presentation
    chief_complaint: str = Field(description="Chief complaint or reason for visit")
    history: Optional[str] = Field(None, description="History of present illness")
    symptoms: Optional[List[str]] = Field(default_factory=list, description="List of current symptoms")
    
    # Clinical data
    vitals: Optional[Dict[str, Any]] = Field(None, description="Vital signs")
    medical_history: Optional[List[str]] = Field(default_factory=list, description="Past medical history")
    medications: Optional[List[str]] = Field(default_factory=list, description="Current medications")
    allergies: Optional[List[str]] = Field(default_factory=list, description="Known allergies")
    
    # Metadata
    session_id: Optional[str] = Field(None, description="Session ID for tracking")
    user_id: Optional[str] = Field(None, description="User ID for tracking")


async def process_triage_stream(request: StreamingTriageRequest):
    """
    Process a triage request with streaming updates.
    
    Yields Server-Sent Events (SSE) with progress updates.
    
    Args:
        request: StreamingTriageRequest with patient data
        
    Yields:
        SSE formatted strings with progress updates
    """
    # Generate assessment ID
    assessment_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    try:
        # Log request
        logger.info(
            f"Streaming triage request received",
            extra={
                "assessment_id": assessment_id,
                "age": request.age,
                "chief_complaint": request.chief_complaint,
                "session_id": request.session_id
            }
        )
        
        # Convert request to format expected by orchestrator
        patient_data = {
            "age": request.age,
            "sex": request.sex or "Not specified",
            "chief_complaint": request.chief_complaint,
            "history": request.history or "",
            "symptoms": request.symptoms or [],
            "medical_history": request.medical_history or [],
            "medications": request.medications or [],
            "allergies": request.allergies or []
        }
        
        # Add vitals if provided
        if request.vitals:
            patient_data["vitals"] = request.vitals
        
        # Stream assessment updates
        async for update in run_triage_assessment_streaming(
            patient_data=patient_data,
            session_id=request.session_id or assessment_id,
            trace_id=assessment_id,
            langfuse_enabled=True  # Enable Langfuse tracing
        ):
            # Format as Server-Sent Event
            event_data = {
                "type": update.type,
                "agent": update.agent,
                "tool": update.tool,
                "message": update.message,
                "progress": update.progress,
                "timestamp": datetime.now().isoformat(),
                "trace_id": update.trace_id
            }
            
            # Include data field for all updates that have it (not just final)
            if update.data:
                event_data["data"] = update.data
            
            # Add additional metadata for final result
            if update.type == "final" and update.data:
                # Add metadata to final result
                update.data["assessment_id"] = assessment_id
                update.data["timestamp"] = timestamp
                update.data["session_id"] = request.session_id
                update.data["warnings"] = [
                    "This is a clinical decision support tool only - not a diagnosis.",
                    "Always seek immediate medical attention for emergencies.",
                    "Assessment should be verified by a qualified healthcare provider."
                ]
                event_data["result"] = update.data
                
                # Log successful assessment
                logger.info(
                    f"Streaming triage assessment completed",
                    extra={
                        "assessment_id": assessment_id,
                        "ctas_level": update.data.get("final_ctas_level"),
                        "confidence": update.data.get("confidence"),
                        "red_flags_count": len(update.data.get("red_flags_identified", []))
                    }
                )
            
            # Yield SSE formatted event
            yield f"data: {json.dumps(event_data)}\n\n"
            
            # Small delay to prevent overwhelming client
            await asyncio.sleep(0.01)
        
        # Send completion event
        yield f"data: {json.dumps({'type': 'complete', 'assessment_id': assessment_id})}\n\n"
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(
            f"Streaming triage assessment failed: {str(e)}\n{error_details}",
            extra={
                "error": str(e),
                "traceback": error_details,
                "assessment_id": assessment_id
            }
        )
        print(f"ERROR in process_triage_stream: {str(e)}")
        print(f"Traceback:\n{error_details}")
        
        # Send error event
        error_data = {
            "type": "error",
            "error": "Assessment failed",
            "message": "Unable to complete triage assessment. Please seek immediate medical attention if this is an emergency.",
            "assessment_id": assessment_id
        }
        yield f"data: {json.dumps(error_data)}\n\n"


def register_streaming_endpoint(app):
    """
    Register the streaming triage endpoint with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    @app.post("/api/agents/triage/stream")
    async def triage_assessment_stream(request: StreamingTriageRequest):
        """
        Emergency Triage Assessment Endpoint (Streaming)
        
        Performs a comprehensive triage assessment with real-time progress updates.
        Returns Server-Sent Events (SSE) with assessment progress and results.
        
        This endpoint:
        - Provides real-time updates as agents process the assessment
        - Shows which specialist agent is currently analyzing
        - Indicates when tools are being called
        - Returns the final CTAS assessment with all details
        
        **Important**: This is a clinical decision support tool only, not a diagnosis.
        Always seek immediate medical attention for emergencies.
        """
        return StreamingResponse(
            process_triage_stream(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Disable Nginx buffering
            }
        )