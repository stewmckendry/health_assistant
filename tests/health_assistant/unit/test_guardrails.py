"""Unit tests for guardrails module."""
import pytest
from unittest.mock import Mock, patch

from src.utils.guardrails import (
    ResponseGuardrails,
    check_forbidden_phrases,
    detect_emergency_content,
    detect_mental_health_crisis,
    apply_disclaimers,
    sanitize_response
)


class TestResponseGuardrails:
    """Test response guardrails functionality."""
    
    @pytest.fixture
    def guardrails(self):
        """Create a guardrails instance."""
        return ResponseGuardrails()
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.forbidden_phrases = [
            "you have",
            "you should take",
            "your diagnosis",
            "diagnosis is",
            "treatment plan",
            "prescribe",
            "medication dosage"
        ]
        settings.enable_guardrails = True
        settings.assistant_mode = "patient"
        settings.disclaimer_start = "⚠️ **Medical Disclaimer**: Educational purposes only."
        settings.disclaimer_end = "💡 **Remember**: Consult a healthcare provider."
        settings.disclaimer_position = "both"
        settings.emergency_redirect = "🚨 **Medical Emergency**: Call 911 immediately."
        settings.mental_health_resources = "**Mental Health Support**: Call 988 for crisis support."
        return settings
    
    def test_check_forbidden_phrases_detects_diagnosis(self, guardrails):
        """Test detection of diagnostic language."""
        response = "Based on your symptoms, you have the flu."
        violations = check_forbidden_phrases(response)
        
        assert len(violations) > 0
        assert "you have" in violations
    
    def test_check_forbidden_phrases_detects_treatment(self, guardrails):
        """Test detection of treatment recommendations."""
        response = "You should take ibuprofen for the pain."
        violations = check_forbidden_phrases(response)
        
        assert len(violations) > 0
        assert "you should take" in violations
    
    def test_check_forbidden_phrases_clean_response(self, guardrails):
        """Test that clean responses pass without violations."""
        response = "Common symptoms of the flu include fever, fatigue, and body aches."
        violations = check_forbidden_phrases(response)
        
        assert len(violations) == 0
    
    def test_detect_emergency_content(self, guardrails):
        """Test detection of emergency situations."""
        # Test chest pain
        assert detect_emergency_content("I have severe chest pain") is True
        assert detect_emergency_content("experiencing crushing chest pressure") is True
        
        # Test breathing issues
        assert detect_emergency_content("I can't breathe") is True
        assert detect_emergency_content("having trouble breathing") is True
        
        # Test stroke symptoms
        assert detect_emergency_content("sudden numbness on one side") is True
        assert detect_emergency_content("face is drooping") is True
        
        # Test non-emergency
        assert detect_emergency_content("I have a mild headache") is False
        assert detect_emergency_content("feeling tired lately") is False
    
    def test_detect_mental_health_crisis(self, guardrails):
        """Test detection of mental health crisis situations."""
        # Test suicidal ideation
        assert detect_mental_health_crisis("I want to end my life") is True
        assert detect_mental_health_crisis("thinking about suicide") is True
        assert detect_mental_health_crisis("I want to hurt myself") is True
        
        # Test harm to others
        assert detect_mental_health_crisis("I want to hurt someone") is True
        
        # Test non-crisis
        assert detect_mental_health_crisis("feeling sad sometimes") is False
        assert detect_mental_health_crisis("stressed about work") is False
    
    def test_guardrails_apply_method(self, guardrails, mock_settings):
        """Test the main apply method of guardrails."""
        with patch('src.utils.guardrails.settings', mock_settings):
            # Test with forbidden phrases
            response = "You have diabetes and should take metformin."
            result = guardrails.apply(response, session_id="test-123")
            
            assert "you have" not in result["content"].lower() or "diagnosis" not in result["content"].lower()
            assert result["guardrails_triggered"] is True
            assert len(result["violations"]) > 0
            assert "⚠️ **Medical Disclaimer**" in result["content"]
    
    def test_guardrails_emergency_redirect(self, guardrails, mock_settings):
        """Test emergency content triggers redirect."""
        with patch('src.utils.guardrails.settings', mock_settings):
            response = "I'm having severe chest pain and can't breathe."
            result = guardrails.apply(response, session_id="test-123")
            
            assert "🚨 **Medical Emergency**" in result["content"]
            assert "Call 911" in result["content"]
            assert result["emergency_detected"] is True
    
    def test_guardrails_mental_health_redirect(self, guardrails, mock_settings):
        """Test mental health crisis triggers resources."""
        with patch('src.utils.guardrails.settings', mock_settings):
            response = "I've been thinking about ending my life."
            result = guardrails.apply(response, session_id="test-123")
            
            # Mental health resources should replace the dangerous content
            assert result["content"] == mock_settings.mental_health_resources
            assert result["mental_health_crisis"] is True
    
    def test_guardrails_disabled(self, guardrails, mock_settings):
        """Test that guardrails can be disabled."""
        mock_settings.enable_guardrails = False
        
        with patch('src.utils.guardrails.settings', mock_settings):
            response = "You have diabetes."
            result = guardrails.apply(response, session_id="test-123")
            
            # Original response should be unchanged when guardrails disabled
            assert result["content"] == response
            assert result["guardrails_triggered"] is False
    
    def test_sanitize_response_removes_forbidden_phrases(self):
        """Test response sanitization removes forbidden phrases."""
        response = "Based on your symptoms, you have the flu. You should take rest."
        sanitized = sanitize_response(response)
        
        assert "you have" not in sanitized.lower()
        assert "you should take" not in sanitized.lower()
        assert "symptoms" in sanitized.lower()  # Safe content remains
    
    def test_sanitize_response_preserves_safe_content(self):
        """Test that safe content is preserved during sanitization."""
        response = "The flu is a respiratory illness caused by influenza viruses."
        sanitized = sanitize_response(response)
        
        assert sanitized == response  # No changes to safe content
    
    def test_apply_disclaimers_patient_mode(self):
        """Test disclaimer application in patient mode."""
        with patch('src.utils.guardrails.settings') as mock_settings:
            mock_settings.assistant_mode = "patient"
            mock_settings.disclaimer_start = "⚠️ Disclaimer start"
            mock_settings.disclaimer_end = "💡 Disclaimer end"
            mock_settings.disclaimer_position = "both"
            
            response = "Medical information content."
            result = apply_disclaimers(response)
            
            assert result.startswith("⚠️ Disclaimer start")
            assert result.endswith("💡 Disclaimer end")
            assert "Medical information content" in result
    
    def test_apply_disclaimers_physician_mode(self):
        """Test disclaimer application in physician mode."""
        with patch('src.utils.guardrails.settings') as mock_settings:
            mock_settings.assistant_mode = "physician"
            mock_settings.disclaimer_start = ""
            mock_settings.disclaimer_end = "📋 Clinical note"
            mock_settings.disclaimer_position = "end"
            
            response = "Clinical information."
            result = apply_disclaimers(response)
            
            assert not result.startswith("⚠️")
            assert result.endswith("📋 Clinical note")
    
    def test_guardrails_logging(self, guardrails, mock_settings):
        """Test that guardrails violations are logged."""
        with patch('src.utils.guardrails.settings', mock_settings):
            with patch('src.utils.guardrails.log_guardrail_trigger') as mock_log:
                response = "You have diabetes."
                guardrails.apply(response, session_id="test-123")
                
                mock_log.assert_called()
                call_kwargs = mock_log.call_args[1]
                assert call_kwargs["session_id"] == "test-123"
                assert "violations" in call_kwargs or "rule" in call_kwargs