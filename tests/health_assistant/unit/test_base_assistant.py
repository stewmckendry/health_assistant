"""Unit tests for base assistant class."""
import os
from unittest.mock import Mock, patch, MagicMock
import pytest
from anthropic import Anthropic
from anthropic.types import Message, MessageParam, Usage

from src.assistants.base import BaseAssistant, AssistantConfig


class TestBaseAssistant:
    """Test base assistant functionality."""
    
    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client."""
        mock_client = Mock(spec=Anthropic)
        mock_client.messages = Mock()
        mock_client.messages.create = Mock()
        return mock_client
    
    @pytest.fixture
    def assistant_config(self):
        """Create a basic assistant configuration."""
        return AssistantConfig(
            model="claude-3-opus-20240229",
            max_tokens=1500,
            temperature=0.7,
            system_prompt="You are a helpful assistant.",
            trusted_domains=["mayoclinic.org", "cdc.gov", "pubmed.ncbi.nlm.nih.gov"],
            enable_web_fetch=True,
            citations_enabled=True
        )
    
    def test_assistant_initialization(self, assistant_config):
        """Test that assistant initializes with correct configuration."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            assistant = BaseAssistant(config=assistant_config)
            
            assert assistant.config == assistant_config
            assert assistant.model == "claude-3-opus-20240229"
            assert assistant.trusted_domains == ["mayoclinic.org", "cdc.gov", "pubmed.ncbi.nlm.nih.gov"]
            assert assistant.enable_web_fetch is True
    
    def test_assistant_requires_api_key(self, assistant_config):
        """Test that assistant raises error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                BaseAssistant(config=assistant_config)
    
    def test_build_messages(self, assistant_config):
        """Test message building (system prompt handled separately)."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            assistant = BaseAssistant(config=assistant_config)
            
            messages = assistant._build_messages("What is diabetes?")
            
            # System prompt is now a separate parameter, not in messages
            assert len(messages) == 1
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == "What is diabetes?"
            # System prompt is stored in config
            assert assistant.config.system_prompt == "You are a helpful assistant."
    
    def test_build_tools_with_web_fetch(self, assistant_config):
        """Test that web_fetch tool is configured correctly."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            assistant = BaseAssistant(config=assistant_config)
            
            tools = assistant._build_tools()
            
            assert len(tools) == 1
            assert tools[0]["type"] == "web_fetch_20250910"
            assert tools[0]["name"] == "web_fetch"
            assert tools[0]["allowed_domains"] == ["mayoclinic.org", "cdc.gov", "pubmed.ncbi.nlm.nih.gov"]
            assert tools[0]["max_uses"] == 5
            assert tools[0]["citations"] == {"enabled": True}
    
    def test_build_tools_without_web_fetch(self, assistant_config):
        """Test that no tools are returned when web_fetch is disabled."""
        assistant_config.enable_web_fetch = False
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            assistant = BaseAssistant(config=assistant_config)
            
            tools = assistant._build_tools()
            
            assert tools is None
    
    @patch('src.assistants.base.Anthropic')
    def test_query_calls_anthropic_api(self, mock_anthropic_class, assistant_config):
        """Test that query method calls Anthropic API correctly."""
        # Setup mock
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock(spec=Message)
        mock_content = Mock(text="Diabetes is a chronic condition...")
        mock_content.citations = None  # No citations in this test
        mock_response.content = [mock_content]
        mock_response.usage = Mock(spec=Usage, input_tokens=50, output_tokens=100)
        mock_response.model = "claude-3-opus-20240229"
        mock_client.messages.create.return_value = mock_response
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            assistant = BaseAssistant(config=assistant_config)
            response = assistant.query("What is diabetes?", session_id="test-123")
        
        # Verify API was called correctly
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        
        assert call_kwargs["model"] == "claude-3-opus-20240229"
        assert call_kwargs["max_tokens"] == 1500
        assert call_kwargs["temperature"] == 0.7
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["tools"] is not None
        assert call_kwargs["extra_headers"]["web-fetch-2025-09-10"] == "true"
        
        # Verify response
        assert response["content"] == "Diabetes is a chronic condition..."
        assert response["model"] == "claude-3-opus-20240229"
        assert response["usage"]["input_tokens"] == 50
        assert response["usage"]["output_tokens"] == 100
        assert response["session_id"] == "test-123"
    
    @patch('src.assistants.base.Anthropic')
    def test_query_logs_api_call(self, mock_anthropic_class, assistant_config):
        """Test that query method logs API calls."""
        # Setup mock
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock(spec=Message)
        mock_content = Mock(text="Response text")
        mock_content.citations = None  # No citations in this test
        mock_response.content = [mock_content]
        mock_response.usage = Mock(spec=Usage, input_tokens=50, output_tokens=100)
        mock_response.model = "claude-3-opus-20240229"
        mock_client.messages.create.return_value = mock_response
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('src.assistants.base.log_api_call') as mock_log_api:
                assistant = BaseAssistant(config=assistant_config)
                assistant.query("Test query", session_id="test-123")
                
                mock_log_api.assert_called_once()
                
                # log_api_call is called with (logger, service, endpoint, **kwargs)
                # Get the positional and keyword arguments
                args, kwargs = mock_log_api.call_args
                
                # First arg is the logger
                assert args[0] == assistant.logger
                # All other args are keyword args
                assert kwargs["service"] == "anthropic"
                assert kwargs["endpoint"] == "messages"
                assert kwargs["model"] == "claude-3-opus-20240229"
                assert kwargs["session_id"] == "test-123"
                assert "tokens" in kwargs
    
    @patch('src.assistants.base.Anthropic')
    def test_query_handles_api_error(self, mock_anthropic_class, assistant_config):
        """Test that query method handles API errors gracefully."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            assistant = BaseAssistant(config=assistant_config)
            
            with pytest.raises(Exception, match="API Error"):
                assistant.query("Test query")
    
    def test_extract_citations_from_response(self, assistant_config):
        """Test extraction of citations from API response."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            assistant = BaseAssistant(config=assistant_config)
            
            # Mock response with citations
            mock_response = Mock()
            mock_response.content = [
                Mock(text="Diabetes affects millions.", citations=[
                    {"url": "https://mayoclinic.org/diabetes", "title": "Diabetes Overview"}
                ])
            ]
            
            citations = assistant._extract_citations(mock_response)
            
            assert len(citations) == 1
            assert citations[0]["url"] == "https://mayoclinic.org/diabetes"
            assert citations[0]["title"] == "Diabetes Overview"
    
    def test_format_response_with_citations(self, assistant_config):
        """Test that response is formatted with citations."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            assistant = BaseAssistant(config=assistant_config)
            
            content = "Diabetes is a chronic condition."
            citations = [
                {"url": "https://mayoclinic.org/diabetes", "title": "Diabetes Overview"},
                {"url": "https://cdc.gov/diabetes", "title": "CDC Diabetes Info"}
            ]
            
            formatted = assistant._format_response_with_citations(content, citations)
            
            assert "Diabetes is a chronic condition." in formatted
            assert "\n\n**Sources:**\n" in formatted
            assert "1. [Diabetes Overview](https://mayoclinic.org/diabetes)" in formatted
            assert "2. [CDC Diabetes Info](https://cdc.gov/diabetes)" in formatted