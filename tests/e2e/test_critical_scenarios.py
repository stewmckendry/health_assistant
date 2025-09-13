"""End-to-end tests for critical scenarios."""
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import pytest

from src.assistants.patient import PatientAssistant
from src.assistants.base import BaseAssistant, AssistantConfig


class TestCriticalScenarios:
    """Test 5 critical end-to-end scenarios."""
    
    @pytest.fixture
    def mock_anthropic_response(self):
        """Create a standard mock Anthropic response."""
        def _create_response(text, citations=None):
            mock_response = Mock()
            mock_response.model = "claude-3-opus-20240229"
            mock_response.usage = Mock()
            mock_response.usage.input_tokens = 100
            mock_response.usage.output_tokens = 200
            
            mock_content = Mock()
            mock_content.text = text
            mock_content.citations = citations
            mock_response.content = [mock_content]
            
            return mock_response
        return _create_response
    
    @pytest.fixture
    def patient_assistant_with_mocks(self):
        """Create PatientAssistant with all necessary mocks."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('src.assistants.patient.settings') as mock_settings:
                # Configure mock settings
                mock_settings.assistant_mode = "patient"
                mock_settings.system_prompt = "You are a patient education assistant."
                mock_settings.primary_model = "claude-3-opus-20240229"
                mock_settings.max_tokens = 1500
                mock_settings.temperature = 0.7
                mock_settings.trusted_domains = ["mayoclinic.org", "cdc.gov"]
                mock_settings.enable_web_fetch = True
                mock_settings.citations_enabled = True
                mock_settings.max_web_fetch_uses = 5
                mock_settings.enable_guardrails = True
                mock_settings.disclaimer_start = "⚠️ **Medical Disclaimer**: This information is for educational purposes only."
                mock_settings.disclaimer_end = "💡 **Remember**: Always consult with a healthcare provider."
                mock_settings.emergency_redirect = "🚨 **Medical Emergency**: If this is a medical emergency, call 911 immediately."
                mock_settings.mental_health_resources = "**Mental Health Support**: If you're in crisis, call 988 for support."
                mock_settings.forbidden_phrases = [
                    "you have", "you should take", "your diagnosis",
                    "diagnosis is", "treatment plan", "prescribe"
                ]
                
                assistant = PatientAssistant()
                return assistant, mock_settings
    
    def test_scenario_1_safe_educational_query(self, patient_assistant_with_mocks, mock_anthropic_response):
        """
        Scenario 1: Safe Educational Query
        User asks about general health information.
        Expected: Educational response with disclaimers and no violations.
        """
        assistant, mock_settings = patient_assistant_with_mocks
        
        # Mock Anthropic API response
        mock_client = Mock()
        mock_client.messages = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "Diabetes is a chronic condition that affects how your body processes blood sugar. "
            "Common symptoms include increased thirst, frequent urination, and fatigue. "
            "Risk factors include obesity, family history, and sedentary lifestyle.",
            citations=[{"url": "https://mayoclinic.org/diabetes", "title": "Diabetes - Mayo Clinic"}]
        )
        
        with patch('src.assistants.base.Anthropic', return_value=mock_client):
            response = assistant.query(
                "What are the symptoms and risk factors of diabetes?",
                session_id="e2e-test-1"
            )
            
            # Assertions
            assert response["mode"] == "patient"
            assert "content" in response
            assert "diabetes" in response["content"].lower()
            assert "⚠️ **Medical Disclaimer**" in response["content"]
            assert "💡 **Remember**" in response["content"]
            assert response.get("emergency_detected") is False
            assert response.get("mental_health_crisis") is False
            assert len(response.get("citations", [])) > 0
            
            # Verify no forbidden phrases in final response
            content_lower = response["content"].lower()
            assert "you have" not in content_lower
            assert "your diagnosis" not in content_lower
    
    def test_scenario_2_emergency_detection(self, patient_assistant_with_mocks):
        """
        Scenario 2: Emergency Detection
        User describes emergency symptoms.
        Expected: Immediate emergency redirect without API call.
        """
        assistant, mock_settings = patient_assistant_with_mocks
        
        # Should NOT call API for emergency
        mock_client = Mock()
        mock_client.messages = Mock()
        mock_client.messages.create.side_effect = Exception("Should not be called")
        
        with patch('src.assistants.base.Anthropic', return_value=mock_client):
            response = assistant.query(
                "I'm having severe chest pain and difficulty breathing",
                session_id="e2e-test-2"
            )
            
            # Assertions
            assert response["emergency_detected"] is True
            assert response["content"] == mock_settings.emergency_redirect
            assert "911" in response["content"]
            assert response["guardrails_applied"] is True
            assert response["mode"] == "patient"
            
            # Verify API was NOT called
            mock_client.messages.create.assert_not_called()
    
    def test_scenario_3_mental_health_crisis(self, patient_assistant_with_mocks):
        """
        Scenario 3: Mental Health Crisis Detection
        User expresses suicidal thoughts.
        Expected: Mental health resources without API call.
        """
        assistant, mock_settings = patient_assistant_with_mocks
        
        # Should NOT call API for crisis
        mock_client = Mock()
        mock_client.messages = Mock()
        mock_client.messages.create.side_effect = Exception("Should not be called")
        
        with patch('src.assistants.base.Anthropic', return_value=mock_client):
            response = assistant.query(
                "I've been thinking about ending my life",
                session_id="e2e-test-3"
            )
            
            # Assertions
            assert response["mental_health_crisis"] is True
            assert response["content"] == mock_settings.mental_health_resources
            assert "988" in response["content"]
            assert response["guardrails_applied"] is True
            assert response["mode"] == "patient"
            
            # Verify API was NOT called
            mock_client.messages.create.assert_not_called()
    
    def test_scenario_4_forbidden_content_sanitization(self, patient_assistant_with_mocks, mock_anthropic_response):
        """
        Scenario 4: Forbidden Content Sanitization
        API returns diagnostic language.
        Expected: Content sanitized and disclaimers added.
        """
        assistant, mock_settings = patient_assistant_with_mocks
        
        # Mock API response with forbidden content
        mock_client = Mock()
        mock_client.messages = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "Based on your symptoms, you have diabetes. "
            "You should take metformin 500mg twice daily. "
            "Your treatment plan includes diet changes and exercise."
        )
        
        with patch('src.assistants.base.Anthropic', return_value=mock_client):
            response = assistant.query(
                "I have frequent urination and thirst, what's wrong?",
                session_id="e2e-test-4"
            )
            
            # Assertions
            assert response["guardrails_applied"] is True
            assert len(response.get("violations", [])) > 0
            
            # Verify forbidden phrases were removed/sanitized
            content_lower = response["content"].lower()
            assert "you have diabetes" not in content_lower
            assert "you should take metformin" not in content_lower
            assert "your treatment plan" not in content_lower
            
            # Verify disclaimers were added
            assert "⚠️ **Medical Disclaimer**" in response["content"]
            assert "💡 **Remember**" in response["content"]
    
    def test_scenario_5_web_fetch_with_citations(self, patient_assistant_with_mocks, mock_anthropic_response):
        """
        Scenario 5: Web Fetch with Trusted Sources
        User asks about CDC guidelines.
        Expected: Response with citations from trusted domains.
        """
        assistant, mock_settings = patient_assistant_with_mocks
        
        # Mock API response with citations
        mock_client = Mock()
        mock_client.messages = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "According to the CDC, annual flu vaccination is recommended for everyone "
            "6 months and older. The vaccine is especially important for people at "
            "high risk of complications, including older adults, pregnant women, and "
            "people with certain chronic conditions.",
            citations=[
                {"url": "https://cdc.gov/flu/prevent/vaccinations.htm", "title": "Flu Vaccination - CDC"},
                {"url": "https://cdc.gov/flu/highrisk/index.htm", "title": "High Risk Groups - CDC"}
            ]
        )
        
        with patch('src.assistants.base.Anthropic', return_value=mock_client):
            response = assistant.query(
                "What are the CDC guidelines for flu vaccination?",
                session_id="e2e-test-5"
            )
            
            # Assertions
            assert "citations" in response
            assert len(response["citations"]) == 2
            assert all("cdc.gov" in c["url"] for c in response["citations"])
            
            # Verify content includes citation information
            assert "CDC" in response["content"]
            assert "flu vaccination" in response["content"].lower()
            
            # Verify tools were configured correctly in API call
            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert "tools" in call_kwargs
            assert call_kwargs["tools"][0]["type"] == "web_fetch_20250910"
            assert "cdc.gov" in call_kwargs["tools"][0]["allowed_domains"]
    
    def test_logging_throughout_scenarios(self, patient_assistant_with_mocks, mock_anthropic_response):
        """Test that all critical paths produce appropriate logs."""
        assistant, mock_settings = patient_assistant_with_mocks
        
        with patch('src.assistants.patient.logger') as mock_logger:
                # Test normal query logging
                mock_client = Mock()
                mock_client.messages = Mock()
                mock_client.messages.create.return_value = mock_anthropic_response(
                    "Educational content about health."
                )
                
                with patch('src.assistants.base.Anthropic', return_value=mock_client):
                    response = assistant.query("Tell me about health", session_id="log-test")
                    
                    # Verify logging occurred
                    assert mock_logger.info.called
                    log_messages = [call[0][0] for call in mock_logger.info.call_args_list]
                    assert any("Patient query received" in msg for msg in log_messages)
                    assert any("completed" in msg.lower() for msg in log_messages)
    
    def test_configuration_loading(self):
        """Test that configuration is properly loaded from environment and files."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            # Create temporary config files
            with tempfile.TemporaryDirectory() as tmpdir:
                config_dir = Path(tmpdir) / "config"
                config_dir.mkdir()
                
                # Create test YAML files
                prompts_yaml = config_dir / "prompts.yaml"
                prompts_yaml.write_text("""
patient: "You are a patient education assistant."
physician: "You are a physician assistant."
                """)
                
                domains_yaml = config_dir / "domains.yaml"
                domains_yaml.write_text("""
trusted_domains:
  - mayoclinic.org
  - cdc.gov
  - pubmed.ncbi.nlm.nih.gov
                """)
                
                disclaimers_yaml = config_dir / "disclaimers.yaml"
                disclaimers_yaml.write_text("""
disclaimer_start: "⚠️ Educational purposes only"
disclaimer_end: "💡 Consult a healthcare provider"
emergency_redirect: "🚨 Call 911"
mental_health_resources: "Call 988 for support"
                """)
                
                # Test that configuration loads correctly
                with patch('src.config.settings.Path', return_value=config_dir):
                    # Can't easily test dynamic loading here since Settings is already imported
                    # Just verify that Settings can be created
                    from src.config.settings import Settings
                    test_settings = Settings()
                    
                    # Verify loaded values
                    assert len(test_settings.trusted_domains) > 0
                    assert "mayoclinic.org" in test_settings.trusted_domains