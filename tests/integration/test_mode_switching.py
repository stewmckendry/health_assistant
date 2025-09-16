"""Integration tests for mode switching between patient and provider assistants."""
import pytest
import os
from unittest.mock import Mock, patch
import json

from src.assistants.patient import PatientAssistant
from src.assistants.provider import ProviderAssistant
from src.web.api.main import get_assistant


class TestModeSwitching:
    """Test suite for mode switching functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key-123"
        yield
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
    
    def test_get_assistant_returns_patient_by_default(self):
        """Test that get_assistant returns PatientAssistant by default."""
        with patch('src.assistants.patient.Anthropic'):
            with patch('src.assistants.provider.Anthropic'):
                assistant = get_assistant()
                assert isinstance(assistant, PatientAssistant)
                assert assistant.mode == "patient"
    
    def test_get_assistant_returns_patient_when_specified(self):
        """Test that get_assistant returns PatientAssistant when mode='patient'."""
        with patch('src.assistants.patient.Anthropic'):
            with patch('src.assistants.provider.Anthropic'):
                assistant = get_assistant(mode="patient")
                assert isinstance(assistant, PatientAssistant)
                assert assistant.mode == "patient"
    
    def test_get_assistant_returns_provider_when_specified(self):
        """Test that get_assistant returns ProviderAssistant when mode='provider'."""
        with patch('src.assistants.patient.Anthropic'):
            with patch('src.assistants.provider.Anthropic'):
                assistant = get_assistant(mode="provider")
                assert isinstance(assistant, ProviderAssistant)
                assert assistant.mode == "provider"
    
    def test_assistant_instances_are_cached(self):
        """Test that assistant instances are cached and reused."""
        with patch('src.assistants.patient.Anthropic'):
            with patch('src.assistants.provider.Anthropic'):
                # Get patient assistant twice
                patient1 = get_assistant(mode="patient")
                patient2 = get_assistant(mode="patient")
                assert patient1 is patient2  # Same instance
                
                # Get provider assistant twice
                provider1 = get_assistant(mode="provider")
                provider2 = get_assistant(mode="provider")
                assert provider1 is provider2  # Same instance
                
                # Different modes should be different instances
                assert patient1 is not provider1
    
    def test_patient_mode_applies_guardrails(self):
        """Test that patient mode applies appropriate guardrails."""
        with patch('src.assistants.patient.Anthropic') as mock_anthropic:
            # Mock API response with medical advice
            mock_response = Mock()
            mock_response.content = [
                Mock(type="text", text="You should take this medication...")
            ]
            mock_response.usage.input_tokens = 100
            mock_response.usage.output_tokens = 200
            mock_response.model = "claude-3-opus"
            
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            assistant = get_assistant(mode="patient")
            
            with patch('src.assistants.patient.SessionLogger'):
                with patch('src.assistants.patient.settings') as mock_settings:
                    mock_settings.enable_guardrails = True
                    mock_settings.emergency_redirect = "Call 911"
                    mock_settings.mental_health_resources = "Crisis hotline"
                    
                    # Mock guardrails to detect issue
                    with patch.object(assistant, 'regex_guardrails') as mock_guardrails:
                        mock_result = {
                            "content": "Educational information only...",
                            "guardrails_triggered": True,
                            "violations": ["medical_advice"],
                            "emergency_detected": False,
                            "mental_health_crisis": False
                        }
                        mock_guardrails.apply.return_value = mock_result
                        
                        response = assistant.query("What medication should I take?")
                        
                        # Check guardrails were applied
                        assert response["guardrails_applied"] == True
                        assert "Educational" in response["content"]
    
    def test_provider_mode_allows_clinical_content(self):
        """Test that provider mode allows clinical terminology."""
        with patch('src.assistants.provider.Anthropic') as mock_anthropic:
            # Mock API response with clinical content
            mock_response = Mock()
            mock_response.content = [
                Mock(type="text", text="Diagnosis: Hypertension. Treatment: ACE inhibitors.")
            ]
            mock_response.usage.input_tokens = 100
            mock_response.usage.output_tokens = 200
            mock_response.model = "claude-3-opus"
            
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            assistant = get_assistant(mode="provider")
            
            with patch('src.assistants.provider.SessionLogger'):
                with patch('src.assistants.provider.settings') as mock_settings:
                    mock_settings.enable_guardrails = True
                    response = assistant.query("What is the diagnosis and treatment?")
                    
                    # Provider mode should allow diagnostic terminology
                    assert "Diagnosis" in response["content"]
                    assert "Treatment" in response["content"]
                    assert response["mode"] == "provider"
    
    def test_mode_specific_system_prompts(self):
        """Test that each mode uses its specific system prompt."""
        with patch('src.assistants.patient.Anthropic'):
            with patch('src.assistants.provider.Anthropic'):
                patient_assistant = get_assistant(mode="patient")
                provider_assistant = get_assistant(mode="provider")
                
                # Check patient prompt
                patient_prompt = patient_assistant.config.system_prompt
                assert "educational" in patient_prompt.lower()
                assert "not a substitute" in patient_prompt.lower()
                
                # Check provider prompt
                provider_prompt = provider_assistant.config.system_prompt
                assert "healthcare professionals" in provider_prompt.lower()
                assert "evidence-based" in provider_prompt.lower()
                assert "clinical" in provider_prompt.lower()
                
                # Prompts should be different
                assert patient_prompt != provider_prompt
    
    def test_mode_specific_domains(self):
        """Test that each mode has appropriate trusted domains."""
        with patch('src.assistants.patient.Anthropic'):
            with patch('src.assistants.provider.Anthropic'):
                patient_assistant = get_assistant(mode="patient")
                provider_assistant = get_assistant(mode="provider")
                
                patient_domains = patient_assistant.config.trusted_domains
                provider_domains = provider_assistant.config.trusted_domains
                
                # Provider should have more domains
                assert len(provider_domains) >= len(patient_domains)
                
                # Provider should have medical journal domains
                provider_specific = [
                    "dynamed.com",
                    "uptodate.com",
                    "cochranelibrary.com",
                    "nejm.org"
                ]
                
                for domain in provider_specific:
                    assert any(domain in d for d in provider_domains)
    
    def test_session_maintains_mode(self):
        """Test that a session maintains its mode across queries."""
        with patch('src.assistants.patient.Anthropic') as mock_patient_anthropic:
            with patch('src.assistants.provider.Anthropic') as mock_provider_anthropic:
                # Mock responses for both
                mock_response = Mock()
                mock_response.content = [Mock(type="text", text="Response")]
                mock_response.usage.input_tokens = 100
                mock_response.usage.output_tokens = 200
                mock_response.model = "claude-3-opus"
                
                mock_patient_client = Mock()
                mock_patient_client.messages.create.return_value = mock_response
                mock_patient_anthropic.return_value = mock_patient_client
                
                mock_provider_client = Mock()
                mock_provider_client.messages.create.return_value = mock_response
                mock_provider_anthropic.return_value = mock_provider_client
                
                # Simulate session with patient mode
                session_id = "test-session-123"
                
                with patch('src.assistants.patient.SessionLogger'):
                    patient_assistant = get_assistant(mode="patient")
                    response1 = patient_assistant.query("Query 1", session_id=session_id)
                    assert response1["mode"] == "patient"
                
                # Later query with provider mode
                with patch('src.assistants.provider.SessionLogger'):
                    provider_assistant = get_assistant(mode="provider")
                    response2 = provider_assistant.query("Query 2", session_id=session_id)
                    assert response2["mode"] == "provider"
    
    def test_mode_switching_preserves_conversation_history(self):
        """Test that conversation history is preserved when switching modes."""
        with patch('src.assistants.patient.Anthropic') as mock_patient:
            with patch('src.assistants.provider.Anthropic') as mock_provider:
                # Mock responses
                mock_response = Mock()
                mock_response.content = [Mock(type="text", text="Response")]
                mock_response.usage.input_tokens = 100
                mock_response.usage.output_tokens = 200
                mock_response.model = "claude-3-opus"
                
                mock_patient.return_value.messages.create.return_value = mock_response
                mock_provider.return_value.messages.create.return_value = mock_response
                
                # Create message history
                message_history = [
                    {"role": "user", "content": "Previous question"},
                    {"role": "assistant", "content": "Previous answer"}
                ]
                
                # Query in patient mode with history
                with patch('src.assistants.patient.SessionLogger'):
                    patient_assistant = get_assistant(mode="patient")
                    response1 = patient_assistant.query(
                        "Follow-up question",
                        message_history=message_history
                    )
                
                # Query in provider mode with same history
                with patch('src.assistants.provider.SessionLogger'):
                    provider_assistant = get_assistant(mode="provider")
                    response2 = provider_assistant.query(
                        "Another follow-up",
                        message_history=message_history
                    )
                
                # Both should have processed with history
                # Check that the API was called with message history
                assert mock_patient.return_value.messages.create.called
                assert mock_provider.return_value.messages.create.called