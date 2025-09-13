"""Integration tests for Anthropic API interactions."""
import os
import pytest
from unittest.mock import patch, Mock, MagicMock
from anthropic import Anthropic
from anthropic.types import Message, Usage, ContentBlock

from src.assistants.base import BaseAssistant, AssistantConfig
from src.assistants.patient import PatientAssistant


class TestAnthropicIntegration:
    """Test actual Anthropic API integration."""
    
    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client."""
        mock_client = Mock(spec=Anthropic)
        mock_client.messages = Mock()
        
        # Create mock response
        mock_response = Mock(spec=Message)
        mock_response.model = "claude-3-opus-20240229"
        mock_response.usage = Mock(spec=Usage)
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 200
        
        # Create mock content block
        mock_content = Mock(spec=ContentBlock)
        mock_content.text = "Diabetes is a chronic condition that affects blood sugar regulation."
        mock_content.citations = None
        mock_response.content = [mock_content]
        
        mock_client.messages.create.return_value = mock_response
        
        return mock_client
    
    @pytest.fixture
    def mock_anthropic_with_citations(self):
        """Create a mock Anthropic client with web_fetch citations."""
        mock_client = Mock(spec=Anthropic)
        mock_client.messages = Mock()
        
        # Create mock response with citations
        mock_response = Mock(spec=Message)
        mock_response.model = "claude-3-opus-20240229"
        mock_response.usage = Mock(spec=Usage)
        mock_response.usage.input_tokens = 150
        mock_response.usage.output_tokens = 300
        
        # Create mock content with citations
        mock_content = Mock(spec=ContentBlock)
        mock_content.text = "According to the CDC, flu vaccines are recommended annually."
        mock_content.citations = [
            {"url": "https://cdc.gov/flu/prevent", "title": "Flu Prevention - CDC"}
        ]
        mock_response.content = [mock_content]
        
        mock_client.messages.create.return_value = mock_response
        
        return mock_client
    
    def test_base_assistant_api_call(self, mock_anthropic_client):
        """Test that BaseAssistant makes correct API call."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('src.assistants.base.Anthropic', return_value=mock_anthropic_client):
                config = AssistantConfig(
                    model="claude-3-opus-20240229",
                    max_tokens=1500,
                    temperature=0.7,
                    system_prompt="You are a medical education assistant.",
                    enable_web_fetch=False
                )
                
                assistant = BaseAssistant(config)
                response = assistant.query("What is diabetes?")
                
                # Verify API was called correctly
                mock_anthropic_client.messages.create.assert_called_once()
                
                # Check the call arguments
                call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
                assert call_kwargs["model"] == "claude-3-opus-20240229"
                assert call_kwargs["max_tokens"] == 1500
                assert call_kwargs["temperature"] == 0.7
                assert len(call_kwargs["messages"]) == 2
                
                # Check response format
                assert "content" in response
                assert "model" in response
                assert "usage" in response
                assert response["usage"]["input_tokens"] == 100
                assert response["usage"]["output_tokens"] == 200
    
    def test_base_assistant_with_web_fetch(self, mock_anthropic_with_citations):
        """Test BaseAssistant with web_fetch tool enabled."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('src.assistants.base.Anthropic', return_value=mock_anthropic_with_citations):
                config = AssistantConfig(
                    model="claude-3-opus-20240229",
                    system_prompt="You are a medical assistant.",
                    trusted_domains=["cdc.gov", "mayoclinic.org"],
                    enable_web_fetch=True,
                    citations_enabled=True,
                    max_web_fetch_uses=5
                )
                
                assistant = BaseAssistant(config)
                response = assistant.query("What are CDC flu guidelines?")
                
                # Verify API was called with tools
                call_kwargs = mock_anthropic_with_citations.messages.create.call_args.kwargs
                assert "tools" in call_kwargs
                assert len(call_kwargs["tools"]) == 1
                assert call_kwargs["tools"][0]["type"] == "web_fetch_20250910"
                assert call_kwargs["tools"][0]["allowed_domains"] == ["cdc.gov", "mayoclinic.org"]
                assert "extra_headers" in call_kwargs
                assert call_kwargs["extra_headers"]["web-fetch-2025-09-10"] == "true"
                
                # Check citations in response
                assert "citations" in response
                assert len(response["citations"]) == 1
                assert response["citations"][0]["url"] == "https://cdc.gov/flu/prevent"
    
    def test_patient_assistant_api_integration(self, mock_anthropic_client):
        """Test PatientAssistant integration with Anthropic API."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('src.assistants.base.Anthropic', return_value=mock_anthropic_client):
                with patch('src.assistants.patient.settings') as mock_settings:
                    mock_settings.assistant_mode = "patient"
                    mock_settings.system_prompt = "You are a patient education assistant."
                    mock_settings.primary_model = "claude-3-opus-20240229"
                    mock_settings.max_tokens = 1500
                    mock_settings.temperature = 0.7
                    mock_settings.trusted_domains = ["mayoclinic.org"]
                    mock_settings.enable_web_fetch = False
                    mock_settings.citations_enabled = False
                    mock_settings.max_web_fetch_uses = 5
                    mock_settings.enable_guardrails = False
                    mock_settings.disclaimer_start = "⚠️ Educational purposes only"
                    mock_settings.disclaimer_end = "💡 Consult a healthcare provider"
                    
                    assistant = PatientAssistant()
                    response = assistant.query("What is diabetes?", session_id="test-123")
                    
                    # Verify API was called
                    mock_anthropic_client.messages.create.assert_called_once()
                    
                    # Check response includes patient mode
                    assert response["mode"] == "patient"
                    assert "content" in response
                    assert "educational purposes only" in response["content"].lower()
    
    def test_api_error_handling(self):
        """Test handling of API errors."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            mock_client = Mock(spec=Anthropic)
            mock_client.messages = Mock()
            mock_client.messages.create.side_effect = Exception("API rate limit exceeded")
            
            with patch('src.assistants.base.Anthropic', return_value=mock_client):
                config = AssistantConfig()
                assistant = BaseAssistant(config)
                
                with pytest.raises(Exception) as exc_info:
                    assistant.query("Test query")
                
                assert "API rate limit exceeded" in str(exc_info.value)
    
    def test_patient_assistant_error_recovery(self):
        """Test that PatientAssistant provides safe error messages."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            mock_client = Mock(spec=Anthropic)
            mock_client.messages = Mock()
            mock_client.messages.create.side_effect = Exception("Network error")
            
            with patch('src.assistants.base.Anthropic', return_value=mock_client):
                with patch('src.assistants.patient.settings') as mock_settings:
                    mock_settings.assistant_mode = "patient"
                    mock_settings.system_prompt = "Patient assistant"
                    mock_settings.primary_model = "claude-3-opus-20240229"
                    mock_settings.max_tokens = 1500
                    mock_settings.temperature = 0.7
                    mock_settings.trusted_domains = []
                    mock_settings.enable_web_fetch = False
                    mock_settings.citations_enabled = False
                    mock_settings.max_web_fetch_uses = 5
                    mock_settings.enable_guardrails = False
                    
                    assistant = PatientAssistant()
                    response = assistant.query("Test query", session_id="test-123")
                    
                    # Should return safe error message
                    assert response["error"] is True
                    assert "unable to process" in response["content"]
                    assert "911" in response["content"]
                    assert response["mode"] == "patient"
    
    def test_message_building(self):
        """Test correct message structure for API."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            config = AssistantConfig(
                system_prompt="You are a helpful medical assistant."
            )
            
            with patch('src.assistants.base.Anthropic'):
                assistant = BaseAssistant(config)
                messages = assistant._build_messages("What is hypertension?")
                
                assert len(messages) == 2
                assert messages[0]["role"] == "system"
                assert messages[0]["content"] == "You are a helpful medical assistant."
                assert messages[1]["role"] == "user"
                assert messages[1]["content"] == "What is hypertension?"
    
    def test_tools_configuration(self):
        """Test web_fetch tools configuration."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            config = AssistantConfig(
                trusted_domains=["pubmed.ncbi.nlm.nih.gov", "who.int"],
                enable_web_fetch=True,
                citations_enabled=True,
                max_web_fetch_uses=10
            )
            
            with patch('src.assistants.base.Anthropic'):
                assistant = BaseAssistant(config)
                tools = assistant._build_tools()
                
                assert tools is not None
                assert len(tools) == 1
                assert tools[0]["type"] == "web_fetch_20250910"
                assert tools[0]["name"] == "web_fetch"
                assert tools[0]["allowed_domains"] == ["pubmed.ncbi.nlm.nih.gov", "who.int"]
                assert tools[0]["max_uses"] == 10
                assert tools[0]["citations"] is True
    
    def test_tools_disabled(self):
        """Test that tools are not included when disabled."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            config = AssistantConfig(
                enable_web_fetch=False
            )
            
            with patch('src.assistants.base.Anthropic'):
                assistant = BaseAssistant(config)
                tools = assistant._build_tools()
                
                assert tools is None
    
    @pytest.mark.parametrize("model,expected", [
        ("claude-3-opus-20240229", "claude-3-opus-20240229"),
        ("claude-3-sonnet-20240229", "claude-3-sonnet-20240229"),
        ("claude-3-haiku-20240307", "claude-3-haiku-20240307"),
    ])
    def test_different_models(self, model, expected, mock_anthropic_client):
        """Test using different Claude models."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            mock_anthropic_client.messages.create.return_value.model = expected
            
            with patch('src.assistants.base.Anthropic', return_value=mock_anthropic_client):
                config = AssistantConfig(model=model)
                assistant = BaseAssistant(config)
                response = assistant.query("Test query")
                
                call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
                assert call_kwargs["model"] == model
                assert response["model"] == expected