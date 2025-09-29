"""Unit tests for configuration management."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest
import yaml

from src.config.settings import Settings


class TestSettings:
    """Test configuration settings."""
    
    def test_default_settings_initialization(self):
        """Test that settings initialize with defaults."""
        settings = Settings()
        
        assert settings.primary_model == "claude-3-opus-20240229"
        assert settings.max_tokens == 1500
        assert settings.temperature == 0.7
        assert settings.assistant_mode == "patient"
        assert settings.enable_web_fetch is True
        assert settings.enable_guardrails is True
    
    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(os.environ, {
            "PRIMARY_MODEL": "claude-3-haiku-20240307",
            "MAX_TOKENS": "2000",
            "TEMPERATURE": "0.5",
            "ASSISTANT_MODE": "physician"
        }):
            settings = Settings()
            
            assert settings.primary_model == "claude-3-haiku-20240307"
            assert settings.max_tokens == 2000
            assert settings.temperature == 0.5
            assert settings.assistant_mode == "physician"
    
    def test_load_prompts_from_yaml(self):
        """Test loading prompts from YAML file."""
        settings = Settings()
        prompts = settings.prompts
        
        assert "patient" in prompts
        assert "physician" in prompts
        assert "system_prompt" in prompts["patient"]
        assert "system_prompt" in prompts["physician"]
    
    def test_load_disclaimers_from_yaml(self):
        """Test loading disclaimers from YAML file."""
        settings = Settings()
        disclaimers = settings.disclaimers
        
        assert "patient" in disclaimers
        assert "physician" in disclaimers
        assert "emergency" in disclaimers
        assert "start" in disclaimers["patient"]
        assert "end" in disclaimers["patient"]
    
    def test_load_domains_from_yaml(self):
        """Test loading trusted domains from YAML file."""
        settings = Settings()
        domains = settings.domains
        
        assert "medical" in domains
        assert "government" in domains["medical"]
        assert "academic" in domains["medical"]
        assert "clinical" in domains["medical"]
        
        # Check some specific domains
        trusted = settings.trusted_domains
        assert "cdc.gov" in trusted
        assert "mayoclinic.org" in trusted
        assert "pubmed.ncbi.nlm.nih.gov" in trusted
    
    def test_system_prompt_selection(self):
        """Test that correct system prompt is selected based on mode."""
        # Test patient mode
        with patch.dict(os.environ, {"ASSISTANT_MODE": "patient"}):
            settings = Settings()
            prompt = settings.system_prompt
            assert "educational health information to patients" in prompt
            assert "NEVER provide medical diagnosis" in prompt
        
        # Test physician mode
        with patch.dict(os.environ, {"ASSISTANT_MODE": "physician"}):
            settings = Settings()
            prompt = settings.system_prompt
            assert "healthcare professionals" in prompt
            assert "evidence-based medical information" in prompt
    
    def test_disclaimer_selection(self):
        """Test disclaimer selection based on mode and position."""
        # Test patient mode with both disclaimers
        with patch.dict(os.environ, {
            "ASSISTANT_MODE": "patient",
            "DISCLAIMER_POSITION": "both"
        }):
            settings = Settings()
            assert "Medical Disclaimer" in settings.disclaimer_start
            assert "Remember" in settings.disclaimer_end
        
        # Test patient mode with start only
        with patch.dict(os.environ, {
            "ASSISTANT_MODE": "patient",
            "DISCLAIMER_POSITION": "start"
        }):
            settings = Settings()
            assert "Medical Disclaimer" in settings.disclaimer_start
            assert settings.disclaimer_end == ""
        
        # Test physician mode
        with patch.dict(os.environ, {"ASSISTANT_MODE": "physician"}):
            settings = Settings()
            assert settings.disclaimer_start == ""
            assert "Clinical Note" in settings.disclaimer_end
    
    def test_disclaimer_disabled(self):
        """Test that disclaimers can be disabled."""
        with patch.dict(os.environ, {"INCLUDE_DISCLAIMERS": "false"}):
            settings = Settings()
            assert settings.disclaimer_start == ""
            assert settings.disclaimer_end == ""
    
    def test_forbidden_phrases_default(self):
        """Test default forbidden phrases are loaded."""
        settings = Settings()
        
        assert "you have" in settings.forbidden_phrases
        assert "diagnosis is" in settings.forbidden_phrases
        assert "prescribe" in settings.forbidden_phrases
        assert len(settings.forbidden_phrases) > 10
    
    def test_get_domains_by_category(self):
        """Test getting domains by specific category."""
        settings = Settings()
        
        gov_domains = settings.get_domains_by_category("government")
        assert "cdc.gov" in gov_domains
        assert "nih.gov" in gov_domains
        
        academic_domains = settings.get_domains_by_category("academic")
        assert "pubmed.ncbi.nlm.nih.gov" in academic_domains
        assert "cochrane.org" in academic_domains
    
    def test_emergency_resources(self):
        """Test emergency resources are loaded."""
        settings = Settings()
        
        emergency = settings.emergency_resources
        assert "911" in emergency
        assert "Poison Control" in emergency
        
        mental_health = settings.mental_health_resources
        assert "988" in mental_health
        assert "Crisis Text Line" in mental_health
        
        redirect = settings.emergency_redirect
        assert "medical emergency" in redirect.lower()
    
    def test_validate_api_key(self):
        """Test API key validation."""
        # Test with no API key
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            settings = Settings()
            assert settings.validate_api_key() is False
        
        # Test with API key
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            settings = Settings()
            assert settings.validate_api_key() is True
    
    def test_get_log_level(self):
        """Test log level conversion."""
        import logging
        
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            settings = Settings()
            assert settings.get_log_level() == logging.DEBUG
        
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            settings = Settings()
            assert settings.get_log_level() == logging.ERROR
    
    def test_invalid_assistant_mode_raises_error(self):
        """Test that invalid assistant mode raises error."""
        with patch.dict(os.environ, {"ASSISTANT_MODE": "invalid"}):
            with pytest.raises(ValueError, match="assistant_mode must be one of"):
                Settings()
    
    def test_invalid_disclaimer_position_raises_error(self):
        """Test that invalid disclaimer position raises error."""
        with patch.dict(os.environ, {"DISCLAIMER_POSITION": "invalid"}):
            with pytest.raises(ValueError, match="disclaimer_position must be one of"):
                Settings()