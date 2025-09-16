"""Unit tests for ProviderAssistant."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from pathlib import Path
import yaml

from src.assistants.provider import ProviderAssistant
from src.assistants.base import AssistantConfig


class TestProviderAssistant:
    """Test suite for ProviderAssistant functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        # Set required environment variable
        os.environ["ANTHROPIC_API_KEY"] = "test-key-123"
        yield
        # Clean up
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
    
    def test_provider_assistant_initialization(self):
        """Test that ProviderAssistant initializes with correct configuration."""
        with patch('src.assistants.base.Anthropic'):
            assistant = ProviderAssistant()
            
            # Check mode is set correctly
            assert assistant.mode == "provider"
            
            # Check system prompt includes provider-specific content
            assert "healthcare professionals" in assistant.config.system_prompt
            assert "evidence-based" in assistant.config.system_prompt.lower()
            assert "clinical" in assistant.config.system_prompt.lower()
    
    def test_provider_assistant_loads_extended_domains(self):
        """Test that ProviderAssistant loads provider-specific domains."""
        with patch('src.assistants.base.Anthropic'):
            assistant = ProviderAssistant()
            
            # Check that trusted domains include medical journals
            domains = assistant.config.trusted_domains
            
            # Should include standard domains
            assert any("mayoclinic.org" in d for d in domains)
            assert any("cdc.gov" in d for d in domains)
            
            # Should include provider-specific domains
            assert any("dynamed.com" in d for d in domains)
            assert any("uptodate.com" in d for d in domains)
            assert any("pubmed.ncbi.nlm.nih.gov" in d for d in domains)
    
    def test_provider_query_includes_mode(self):
        """Test that provider queries include mode in response."""
        with patch('src.assistants.base.Anthropic') as mock_anthropic:
            # Mock the API response
            mock_response = Mock()
            mock_response.content = [
                Mock(type="text", text="Clinical guidelines suggest...")
            ]
            mock_response.usage.input_tokens = 100
            mock_response.usage.output_tokens = 200
            mock_response.model = "claude-3-opus"
            
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            assistant = ProviderAssistant()
            
            # Mock session logger
            with patch('src.assistants.provider.SessionLogger'):
                response = assistant.query("What are treatment guidelines for hypertension?")
            
            # Check response includes provider mode
            assert response["mode"] == "provider"
            assert "Clinical guidelines" in response["content"]
    
    def test_provider_guardrails_are_relaxed(self):
        """Test that provider mode has relaxed guardrails."""
        with patch('src.assistants.base.Anthropic') as mock_anthropic:
            # Mock the API response with diagnostic content
            mock_response = Mock()
            mock_response.content = [
                Mock(type="text", text="Differential diagnosis includes...")
            ]
            mock_response.usage.input_tokens = 100
            mock_response.usage.output_tokens = 200
            mock_response.model = "claude-3-opus"
            
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            assistant = ProviderAssistant(guardrail_mode="regex")
            
            # Mock session logger
            with patch('src.assistants.provider.SessionLogger'):
                response = assistant.query("What is the differential diagnosis for chest pain?")
            
            # Provider mode should allow diagnostic terminology
            assert "diagnosis" in response["content"].lower()
            # Should have minimal guardrails applied
            assert response.get("guardrails_applied", False) == True  # Only for disclaimer
    
    def test_provider_professional_disclaimer(self):
        """Test that provider responses include professional disclaimer."""
        with patch('src.assistants.base.Anthropic') as mock_anthropic:
            # Mock the API response without disclaimer
            mock_response = Mock()
            mock_response.content = [
                Mock(type="text", text="Treatment options include beta blockers.")
            ]
            mock_response.usage.input_tokens = 100
            mock_response.usage.output_tokens = 200
            mock_response.model = "claude-3-opus"
            
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            assistant = ProviderAssistant()
            
            # Mock session logger
            with patch('src.assistants.provider.SessionLogger'):
                response = assistant.query("What medications for hypertension?")
            
            # Should add professional disclaimer
            assert "clinical judgment" in response["content"].lower() or \
                   "professional use" in response["content"].lower()
    
    def test_provider_handles_technical_queries(self):
        """Test that provider can handle technical medical queries."""
        with patch('src.assistants.base.Anthropic') as mock_anthropic:
            # Mock the API response with technical content
            mock_response = Mock()
            mock_response.content = [
                Mock(type="text", text="The NNT for statins in primary prevention is approximately 104.")
            ]
            mock_response.usage.input_tokens = 100
            mock_response.usage.output_tokens = 200
            mock_response.model = "claude-3-opus"
            
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            assistant = ProviderAssistant()
            
            # Mock session logger
            with patch('src.assistants.provider.SessionLogger'):
                response = assistant.query("What is the NNT for statins in primary prevention?")
            
            # Should handle technical content
            assert "NNT" in response["content"]
            assert "104" in response["content"]
    
    def test_provider_mode_logging(self):
        """Test that provider mode is properly logged."""
        with patch('src.assistants.base.Anthropic') as mock_anthropic:
            # Mock the API response
            mock_response = Mock()
            mock_response.content = [Mock(type="text", text="Clinical response")]
            mock_response.usage.input_tokens = 100
            mock_response.usage.output_tokens = 200
            mock_response.model = "claude-3-opus"
            
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            assistant = ProviderAssistant()
            
            # Mock session logger and check it receives correct mode
            with patch('src.assistants.provider.SessionLogger') as mock_logger:
                mock_logger_instance = Mock()
                mock_logger.return_value = mock_logger_instance
                
                response = assistant.query("Test query", session_id="test-session")
                
                # Verify logger was called with provider mode
                mock_logger_instance.log_original_query.assert_called_once_with(
                    "Test query", "provider"
                )
    
    def test_provider_langfuse_tags(self):
        """Test that provider mode adds correct Langfuse tags."""
        with patch('src.assistants.base.Anthropic') as mock_anthropic:
            with patch('src.assistants.provider.langfuse') as mock_langfuse:
                # Mock the API response
                mock_response = Mock()
                mock_response.content = [Mock(type="text", text="Clinical response")]
                mock_response.usage.input_tokens = 100
                mock_response.usage.output_tokens = 200
                mock_response.model = "claude-3-opus"
                
                mock_client = Mock()
                mock_client.messages.create.return_value = mock_response
                mock_anthropic.return_value = mock_client
                
                # Set up Langfuse mock
                mock_langfuse.update_current_trace = Mock()
                
                assistant = ProviderAssistant()
                
                # Mock session logger
                with patch('src.assistants.provider.SessionLogger'):
                    with patch('src.assistants.provider.settings') as mock_settings:
                        mock_settings.langfuse_enabled = True
                        response = assistant.query("Test query", session_id="test-session")
                
                # Check that Langfuse was called with provider tags
                calls = mock_langfuse.update_current_trace.call_args_list
                # Should have a call with mode:provider tag
                assert any("mode:provider" in str(call) for call in calls)
    
    def test_provider_error_handling(self):
        """Test that provider assistant handles errors appropriately."""
        with patch('src.assistants.base.Anthropic') as mock_anthropic:
            # Mock client to raise an exception
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("API Error")
            mock_anthropic.return_value = mock_client
            
            assistant = ProviderAssistant()
            
            # Mock session logger
            with patch('src.assistants.provider.SessionLogger'):
                response = assistant.query("Test query")
            
            # Should return professional error message
            assert response["error"] == True
            assert "error occurred" in response["content"].lower()
            assert response["mode"] == "provider"