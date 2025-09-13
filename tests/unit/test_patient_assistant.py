"""Unit tests for patient assistant."""
import os
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.assistants.patient import PatientAssistant
from src.assistants.base import BaseAssistant


class TestPatientAssistant:
    """Test patient assistant functionality."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for patient mode."""
        settings = Mock()
        settings.assistant_mode = "patient"
        settings.system_prompt = "You are a medical education assistant."
        settings.primary_model = "claude-3-opus-20240229"
        settings.enable_guardrails = True
        settings.enable_web_fetch = True
        settings.trusted_domains = ["mayoclinic.org", "cdc.gov"]
        settings.disclaimer_start = "⚠️ Educational purposes only"
        settings.disclaimer_end = "💡 Consult a healthcare provider"
        settings.emergency_redirect = "🚨 Call 911 immediately"
        settings.mental_health_resources = "Mental health support: Call 988"
        return settings
    
    def test_patient_assistant_initialization(self):
        """Test patient assistant initializes with correct settings."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('src.assistants.patient.settings') as mock_settings:
                mock_settings.assistant_mode = "patient"
                mock_settings.system_prompt = "Patient education prompt"
                mock_settings.primary_model = "claude-3-opus-20240229"
                mock_settings.trusted_domains = ["cdc.gov"]
                
                assistant = PatientAssistant()
                
                assert assistant.mode == "patient"
                assert assistant.config.system_prompt == "Patient education prompt"
                assert assistant.config.model == "claude-3-opus-20240229"
    
    def test_patient_assistant_uses_patient_system_prompt(self):
        """Test that patient assistant uses the patient-specific system prompt."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('src.assistants.patient.settings') as mock_settings:
                mock_settings.assistant_mode = "patient"
                mock_settings.system_prompt = (
                    "You are a helpful medical information assistant designed to provide "
                    "educational health information to patients."
                )
                mock_settings.primary_model = "claude-3-opus-20240229"
                mock_settings.trusted_domains = ["cdc.gov"]
                
                assistant = PatientAssistant()
                messages = assistant._build_messages("What is diabetes?")
                
                assert len(messages) == 1
                assert messages[0]["role"] == "user"
                assert messages[0]["content"] == "What is diabetes?"
                # System prompt is now handled separately, check config
                assert "educational health information to patients" in assistant.config.system_prompt
    
    @patch('src.assistants.patient.ResponseGuardrails')
    def test_patient_assistant_applies_guardrails(self, mock_guardrails_class):
        """Test that patient assistant applies guardrails to responses."""
        mock_guardrails = Mock()
        mock_guardrails_class.return_value = mock_guardrails
        mock_guardrails.apply.return_value = {
            "content": "Safe educational content about diabetes.",
            "guardrails_triggered": True,
            "violations": ["you have"],
            "emergency_detected": False,
            "mental_health_crisis": False
        }
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('src.assistants.patient.settings') as mock_settings:
                mock_settings.assistant_mode = "patient"
                mock_settings.enable_guardrails = True
                mock_settings.system_prompt = "Patient prompt"
                mock_settings.primary_model = "claude-3-opus-20240229"
                mock_settings.trusted_domains = ["cdc.gov"]
                
                with patch.object(BaseAssistant, 'query') as mock_api:
                    mock_api.return_value = {
                        "content": "You have diabetes symptoms.",
                        "model": "claude-3-opus-20240229",
                        "usage": {"input_tokens": 10, "output_tokens": 20},
                        "citations": []
                    }
                    
                    assistant = PatientAssistant()
                    result = assistant.query("What are my symptoms?", session_id="test-123")
                    
                    # Verify guardrails were applied
                    mock_guardrails.apply.assert_called_once()
                    assert result["content"] == "Safe educational content about diabetes."
                    assert result["guardrails_applied"] is True
    
    def test_patient_assistant_handles_emergency_query(self):
        """Test that emergency queries trigger emergency response."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('src.assistants.patient.settings') as mock_settings:
                mock_settings.assistant_mode = "patient"
                mock_settings.enable_guardrails = True
                mock_settings.emergency_redirect = "🚨 Call 911 immediately"
                mock_settings.system_prompt = "Patient prompt"
                mock_settings.primary_model = "claude-3-opus-20240229"
                mock_settings.trusted_domains = ["cdc.gov"]
                
                with patch('src.assistants.patient.detect_emergency_content') as mock_detect:
                    mock_detect.return_value = True
                    
                    assistant = PatientAssistant()
                    result = assistant.query("I'm having severe chest pain", session_id="test-123")
                    
                    assert "🚨" in result["content"]
                    assert "911" in result["content"]
                    assert result.get("emergency_detected") is True
    
    def test_patient_assistant_handles_mental_health_crisis(self):
        """Test that mental health crisis queries trigger appropriate response."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('src.assistants.patient.settings') as mock_settings:
                mock_settings.assistant_mode = "patient"
                mock_settings.enable_guardrails = True
                mock_settings.mental_health_resources = "Mental health support: Call 988"
                mock_settings.system_prompt = "Patient prompt"
                mock_settings.primary_model = "claude-3-opus-20240229"
                mock_settings.trusted_domains = ["cdc.gov"]
                
                with patch('src.assistants.patient.detect_mental_health_crisis') as mock_detect:
                    mock_detect.return_value = True
                    
                    assistant = PatientAssistant()
                    result = assistant.query("I want to hurt myself", session_id="test-123")
                    
                    assert "988" in result["content"]
                    assert result.get("mental_health_crisis") is True
    
    def test_patient_assistant_includes_disclaimers(self):
        """Test that patient responses include appropriate disclaimers."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('src.assistants.patient.settings') as mock_settings:
                mock_settings.assistant_mode = "patient"
                mock_settings.enable_guardrails = False  # Disable to test base response
                mock_settings.disclaimer_start = "⚠️ Educational purposes only"
                mock_settings.disclaimer_end = "💡 Consult a healthcare provider"
                mock_settings.system_prompt = "Patient prompt"
                mock_settings.primary_model = "claude-3-opus-20240229"
                mock_settings.trusted_domains = ["cdc.gov"]
                
                with patch.object(BaseAssistant, 'query') as mock_api:
                    mock_api.return_value = {
                        "content": "Information about diabetes.",
                        "model": "claude-3-opus-20240229",
                        "usage": {"input_tokens": 10, "output_tokens": 20},
                        "citations": []
                    }
                    
                    assistant = PatientAssistant()
                    result = assistant.query("What is diabetes?", session_id="test-123")
                    
                    # When guardrails are disabled, disclaimers are added manually
                    # The actual disclaimer content comes from YAML files
                    assert "educational purposes only" in result["content"].lower()
                    assert "consult" in result["content"].lower() and "healthcare provider" in result["content"].lower()
    
    def test_patient_assistant_logs_queries(self):
        """Test that patient assistant logs all queries and responses."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('src.assistants.patient.settings') as mock_settings:
                mock_settings.assistant_mode = "patient"
                mock_settings.enable_guardrails = False
                mock_settings.disclaimer_start = ""
                mock_settings.disclaimer_end = ""
                mock_settings.system_prompt = "Patient prompt"
                mock_settings.primary_model = "claude-3-opus-20240229"
                mock_settings.trusted_domains = ["cdc.gov"]
                
                with patch('src.assistants.patient.logger') as mock_logger:
                    with patch.object(BaseAssistant, 'query') as mock_api:
                        mock_api.return_value = {
                            "content": "Medical information.",
                            "model": "claude-3-opus-20240229",
                            "usage": {"input_tokens": 10, "output_tokens": 20},
                            "citations": []
                        }
                        
                        assistant = PatientAssistant()
                        assistant.query("Test query", session_id="test-123")
                        
                        # Check that query was logged
                        assert mock_logger.info.called
                        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                        assert any("Patient query received" in call for call in log_calls)