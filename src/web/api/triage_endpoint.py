"""
FastAPI endpoint for the Emergency Triage Assistant.
Provides /api/agents/triage endpoint for triage assessments.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from fastapi import HTTPException
from pydantic import BaseModel, Field
import asyncio

from src.agents.clinical.orchestrator import run_triage_assessment, TriageDecision
from src.utils.logging import get_logger

logger = get_logger(__name__)


class VitalSigns(BaseModel):
    """Patient vital signs."""
    blood_pressure: Optional[str] = Field(None, description="Blood pressure (e.g., '120/80')")
    heart_rate: Optional[int] = Field(None, description="Heart rate in bpm")
    respiratory_rate: Optional[int] = Field(None, description="Respiratory rate per minute")
    temperature: Optional[float] = Field(None, description="Temperature in Celsius")
    oxygen_saturation: Optional[int] = Field(None, description="O2 saturation percentage")
    pain_scale: Optional[int] = Field(None, description="Pain scale 0-10", ge=0, le=10)


class TriageRequest(BaseModel):
    """Request model for triage assessment."""
    # Demographics
    age: int = Field(description="Patient age in years", ge=0, le=150)
    sex: Optional[str] = Field(None, description="Patient sex", pattern="^(Male|Female|Other)$")
    
    # Presentation
    chief_complaint: str = Field(description="Chief complaint or reason for visit")
    history: Optional[str] = Field(None, description="History of present illness")
    symptoms: Optional[List[str]] = Field(default_factory=list, description="List of current symptoms")
    
    # Clinical data
    vitals: Optional[VitalSigns] = Field(None, description="Vital signs")
    medical_history: Optional[List[str]] = Field(default_factory=list, description="Past medical history")
    medications: Optional[List[str]] = Field(default_factory=list, description="Current medications")
    allergies: Optional[List[str]] = Field(default_factory=list, description="Known allergies")
    
    # Metadata
    session_id: Optional[str] = Field(None, description="Session ID for tracking")
    user_id: Optional[str] = Field(None, description="User ID for tracking")


class TriageResponse(BaseModel):
    """Response model for triage assessment."""
    # Core triage decision
    ctas_level: int = Field(description="CTAS level (1-5)")
    urgency: str = Field(description="Urgency category")
    estimated_wait_time: str = Field(description="Estimated wait time")
    disposition: str = Field(description="Where patient should be directed")
    
    # Clinical details
    red_flags: List[str] = Field(description="Identified red flags")
    initial_actions: List[str] = Field(description="Immediate actions to take")
    recommended_tests: List[str] = Field(description="Recommended diagnostic tests")
    clinical_summary: str = Field(description="Clinical summary of assessment")
    
    # Metadata
    confidence: float = Field(description="Confidence in assessment", ge=0, le=1)
    assessment_id: str = Field(description="Unique assessment ID")
    timestamp: str = Field(description="Assessment timestamp")
    session_id: Optional[str] = Field(None, description="Session ID if provided")
    
    # Warnings
    warnings: List[str] = Field(default_factory=list, description="Important warnings or disclaimers")


async def process_triage_request(request: TriageRequest) -> TriageResponse:
    """
    Process a triage request using the orchestrator and specialist agents.
    
    Args:
        request: TriageRequest with patient data
        
    Returns:
        TriageResponse with assessment results
    """
    try:
        # Generate assessment ID
        assessment_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Log request
        logger.info(
            f"Triage request received",
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
            vitals_dict = {}
            if request.vitals.blood_pressure:
                vitals_dict["blood_pressure"] = request.vitals.blood_pressure
            if request.vitals.heart_rate is not None:
                vitals_dict["heart_rate"] = request.vitals.heart_rate
            if request.vitals.respiratory_rate is not None:
                vitals_dict["respiratory_rate"] = request.vitals.respiratory_rate
            if request.vitals.temperature is not None:
                vitals_dict["temperature"] = request.vitals.temperature
            if request.vitals.oxygen_saturation is not None:
                vitals_dict["oxygen_saturation"] = request.vitals.oxygen_saturation
            if request.vitals.pain_scale is not None:
                vitals_dict["pain_scale"] = request.vitals.pain_scale
            
            if vitals_dict:
                patient_data["vitals"] = vitals_dict
        
        # Run triage assessment
        decision = await run_triage_assessment(
            patient_data=patient_data,
            session_id=request.session_id or assessment_id,
            trace_id=assessment_id,
            langfuse_enabled=False  # Disable Langfuse for now
        )
        
        # Build response
        response = TriageResponse(
            ctas_level=decision.final_ctas_level,
            urgency=decision.urgency,
            estimated_wait_time=decision.estimated_wait_time,
            disposition=decision.disposition,
            red_flags=decision.red_flags_identified,
            initial_actions=decision.initial_actions,
            recommended_tests=decision.recommended_tests,
            clinical_summary=decision.clinical_summary,
            confidence=decision.confidence,
            assessment_id=assessment_id,
            timestamp=timestamp,
            session_id=request.session_id,
            warnings=[
                "This is a clinical decision support tool only - not a diagnosis.",
                "Always seek immediate medical attention for emergencies.",
                "Assessment should be verified by a qualified healthcare provider."
            ]
        )
        
        # Log successful assessment
        logger.info(
            f"Triage assessment completed",
            extra={
                "assessment_id": assessment_id,
                "ctas_level": response.ctas_level,
                "confidence": response.confidence,
                "red_flags_count": len(response.red_flags)
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(
            f"Triage assessment failed",
            extra={
                "error": str(e),
                "assessment_id": assessment_id if 'assessment_id' in locals() else None
            }
        )
        
        # Return safe error response
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Assessment failed",
                "message": "Unable to complete triage assessment. Please seek immediate medical attention if this is an emergency.",
                "assessment_id": assessment_id if 'assessment_id' in locals() else None
            }
        )


def register_triage_endpoint(app):
    """
    Register the triage endpoint with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    @app.post("/api/agents/triage", response_model=TriageResponse)
    async def triage_assessment(request: TriageRequest):
        """
        Emergency Triage Assessment Endpoint
        
        Performs a comprehensive triage assessment using the Canadian Triage and Acuity Scale (CTAS).
        
        This endpoint:
        - Evaluates patient acuity using CTAS levels 1-5
        - Identifies critical red flags requiring immediate attention
        - Recommends initial diagnostic workup
        - Provides structured triage decision support
        
        **Important**: This is a clinical decision support tool only, not a diagnosis.
        Always seek immediate medical attention for emergencies.
        """
        return await process_triage_request(request)