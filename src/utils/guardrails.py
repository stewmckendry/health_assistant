"""Guardrails for response safety and compliance."""
import re
from typing import List, Dict, Any, Optional
from src.utils.logging import get_logger, log_guardrail_trigger
from src.config.settings import settings


logger = get_logger(__name__)


# Emergency keywords that require immediate medical attention
EMERGENCY_KEYWORDS = [
    "chest pain", "chest pressure", "crushing chest",
    "can't breathe", "cannot breathe", "trouble breathing", "difficulty breathing",
    "severe pain", "severe headache", "worst headache",
    "stroke", "drooping", "arm weakness", "speech difficulty",
    "numbness one side", "sudden numbness", "sudden confusion",
    "unconscious", "unresponsive", "seizure",
    "severe bleeding", "heavy bleeding",
    "overdose", "poisoning",
    "severe allergic", "anaphylaxis",
    "heart attack", "cardiac arrest"
]

# Mental health crisis keywords
MENTAL_HEALTH_CRISIS_KEYWORDS = [
    "suicide", "suicidal", "kill myself", "end my life", "ending my life", 
    "want to die", "hurt myself", "self-harm", "cutting myself",
    "hurt someone", "kill someone", "harm others",
    "hopeless", "no reason to live", "better off dead"
]


def check_forbidden_phrases(response: str) -> List[str]:
    """
    Check response for forbidden diagnostic/treatment phrases.
    
    Args:
        response: The response text to check
    
    Returns:
        List of violated forbidden phrases
    """
    violations = []
    response_lower = response.lower()
    
    for phrase in settings.forbidden_phrases:
        if phrase.lower() in response_lower:
            violations.append(phrase)
    
    return violations


def detect_emergency_content(text: str) -> bool:
    """
    Detect if the content describes a medical emergency.
    
    Args:
        text: Text to check for emergency content
    
    Returns:
        True if emergency content detected
    """
    text_lower = text.lower()
    
    # Check if this is educational content about complications/risks
    # These phrases indicate discussion of risks, not actual emergencies
    educational_context = [
        "complications", "risk of", "may lead to", "can lead to", 
        "symptoms include", "symptoms of", "signs of", "information about",
        "educational", "if not managed", "if untreated", "long-term",
        "over time", "potential for", "increase risk"
    ]
    
    for keyword in EMERGENCY_KEYWORDS:
        if keyword in text_lower:
            # Check context around the keyword
            keyword_index = text_lower.find(keyword)
            context_start = max(0, keyword_index - 100)
            context_end = min(len(text_lower), keyword_index + 100)
            context = text_lower[context_start:context_end]
            
            # Skip if in educational context
            if any(edu_phrase in context for edu_phrase in educational_context):
                logger.debug(
                    f"Skipping emergency keyword '{keyword}' in educational context",
                    extra={"keyword": keyword, "context": context[:50]}
                )
                continue
            
            # Check if user is describing their current symptoms
            current_symptom_phrases = ["i have", "i'm having", "i am having", "i feel", "my chest", "my head"]
            if any(phrase in context for phrase in current_symptom_phrases):
                logger.warning(
                    "Emergency content detected",
                    extra={"keyword": keyword, "text_snippet": text[:100]}
                )
                return True
    
    return False


def detect_mental_health_crisis(text: str) -> bool:
    """
    Detect if the content indicates a mental health crisis.
    
    Args:
        text: Text to check for crisis content
    
    Returns:
        True if mental health crisis detected
    """
    text_lower = text.lower()
    
    for keyword in MENTAL_HEALTH_CRISIS_KEYWORDS:
        if keyword in text_lower:
            logger.warning(
                "Mental health crisis detected",
                extra={"keyword": keyword, "text_snippet": text[:100]}
            )
            return True
    
    return False


def sanitize_response(response: str) -> str:
    """
    Remove or replace forbidden phrases from response.
    
    Args:
        response: Response to sanitize
    
    Returns:
        Sanitized response
    """
    sanitized = response
    
    # Replace diagnostic language
    replacements = {
        r"\byou have\b": "symptoms may indicate",
        r"\byour diagnosis\b": "this condition",
        r"\bdiagnosis is\b": "this appears to be related to",
        r"\byou should take\b": "patients typically benefit from",
        r"\byour condition\b": "this condition",
        r"\byour illness\b": "this illness",
        r"\byou are suffering from\b": "these symptoms are associated with",
        r"\byou need to\b": "it may be beneficial to",
        r"\bprescribe\b": "healthcare providers may consider",
        r"\bmedication dosage\b": "typical dosing",
        r"\btreatment plan\b": "management approach",
        r"\bstop taking\b": "discuss with your doctor about"
    }
    
    for pattern, replacement in replacements.items():
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized


def apply_disclaimers(response: str) -> str:
    """
    Add appropriate disclaimers to response.
    Checks for existing disclaimers to prevent duplication.
    
    Args:
        response: Response content
    
    Returns:
        Response with disclaimers
    """
    result = response
    
    # Add start disclaimer if configured and not already present
    if settings.disclaimer_start:
        # Check if disclaimer already exists at the start
        if not result.startswith(settings.disclaimer_start) and "⚠️ **Medical Disclaimer**" not in result[:200]:
            result = settings.disclaimer_start + "\n" + result
    
    # Add end disclaimer if configured and not already present
    if settings.disclaimer_end:
        # Check if disclaimer already exists at the end
        if not result.endswith(settings.disclaimer_end) and "💡 **Remember**" not in result[-200:]:
            result = result + "\n" + settings.disclaimer_end
    
    return result


class ResponseGuardrails:
    """Main guardrails class for processing responses."""
    
    def __init__(self):
        """Initialize guardrails."""
        self.logger = get_logger(__name__)
    
    def apply(
        self,
        response: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply all guardrails to a response.
        
        Args:
            response: Original response from the model
            session_id: Session identifier for logging
        
        Returns:
            Dictionary with processed content and metadata
        """
        result = {
            "original_response": response,
            "content": response,
            "guardrails_triggered": False,
            "violations": [],
            "emergency_detected": False,
            "mental_health_crisis": False,
            "session_id": session_id
        }
        
        # Check if guardrails are enabled
        if not settings.enable_guardrails:
            self.logger.info(
                "Guardrails disabled, returning original response",
                extra={"session_id": session_id}
            )
            return result
        
        # Check for emergency content in user query or response
        if detect_emergency_content(response):
            result["emergency_detected"] = True
            result["content"] = settings.emergency_redirect
            result["guardrails_triggered"] = True
            
            log_guardrail_trigger(
                self.logger,
                rule="emergency_redirect",
                original_response=response,
                modified_response=result["content"],
                session_id=session_id
            )
            return result
        
        # Check for mental health crisis
        if detect_mental_health_crisis(response):
            result["mental_health_crisis"] = True
            # Don't include the original response if it contains crisis content
            result["content"] = settings.mental_health_resources
            result["guardrails_triggered"] = True
            
            log_guardrail_trigger(
                self.logger,
                rule="mental_health_resources",
                original_response=response,
                modified_response=result["content"],
                session_id=session_id
            )
            return result  # Return early for mental health crisis
        
        # Check for forbidden phrases
        violations = check_forbidden_phrases(response)
        if violations:
            result["violations"] = violations
            result["guardrails_triggered"] = True
            
            # Sanitize the response
            sanitized = sanitize_response(response)
            result["content"] = sanitized
            
            log_guardrail_trigger(
                self.logger,
                rule="forbidden_phrases",
                original_response=response,
                modified_response=sanitized,
                session_id=session_id,
                violations=violations
            )
        
        # Note: Disclaimers are now applied in patient.py after all guardrail processing
        # This prevents duplicate disclaimers from different processing paths
        
        # Log summary
        if result["guardrails_triggered"]:
            self.logger.info(
                "Guardrails applied to response",
                extra={
                    "session_id": session_id,
                    "violations_count": len(result["violations"]),
                    "emergency": result["emergency_detected"],
                    "mental_health": result["mental_health_crisis"]
                }
            )
        
        return result