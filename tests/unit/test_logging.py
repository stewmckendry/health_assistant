"""Unit tests for logging configuration."""
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import logging

from src.utils.logging import (
    get_logger,
    setup_logging,
    log_api_call,
    log_decision,
    log_guardrail_trigger
)


class TestLoggingConfiguration:
    """Test logging configuration and setup."""
    
    def test_setup_logging_creates_log_directory(self):
        """Test that setup_logging creates the log directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"
            setup_logging(log_dir=str(log_dir))
            assert log_dir.exists()
            assert log_dir.is_dir()
    
    def test_setup_logging_configures_file_handler(self):
        """Test that setup_logging configures a rotating file handler."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "logs" / "health_assistant.log"
            setup_logging(log_dir=str(Path(temp_dir) / "logs"))
            
            # Log a message and check it's written to file
            logger = get_logger("test")
            logger.info("Test message")
            
            assert log_file.exists()
            with open(log_file, 'r') as f:
                content = f.read()
                assert "Test message" in content
    
    def test_get_logger_returns_configured_logger(self):
        """Test that get_logger returns a properly configured logger."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"
        assert logger.level <= logging.INFO
    
    def test_log_format_includes_required_fields(self):
        """Test that log messages include timestamp, level, component, and message."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "logs" / "health_assistant.log"
            setup_logging(log_dir=str(Path(temp_dir) / "logs"))
            
            logger = get_logger("test.component")
            logger.info("Test message", extra={"session_id": "test-123"})
            
            with open(log_file, 'r') as f:
                log_line = f.readline()
                log_data = json.loads(log_line)
                
                assert "timestamp" in log_data
                assert log_data["level"] == "INFO"
                assert log_data["name"] == "test.component"
                assert log_data["message"] == "Test message"
                assert log_data["session_id"] == "test-123"


class TestLoggingHelpers:
    """Test logging helper functions."""
    
    def test_log_api_call(self):
        """Test that log_api_call logs API call details."""
        logger = MagicMock()
        
        log_api_call(
            logger,
            service="anthropic",
            endpoint="messages",
            model="claude-3-opus",
            tokens=100,
            session_id="test-123"
        )
        
        logger.info.assert_called_once()
        call_args = logger.info.call_args
        assert "Calling Anthropic API" in call_args[0][0]
        extra = call_args[1]["extra"]
        assert extra["service"] == "anthropic"
        assert extra["endpoint"] == "messages"
        assert extra["model"] == "claude-3-opus"
        assert extra["tokens"] == 100
        assert extra["session_id"] == "test-123"
    
    def test_log_decision(self):
        """Test that log_decision logs decision details."""
        logger = MagicMock()
        
        log_decision(
            logger,
            decision_type="source_selection",
            decision="Selected Mayo Clinic",
            reason="Most authoritative for symptom information",
            session_id="test-123"
        )
        
        logger.info.assert_called_once()
        call_args = logger.info.call_args
        assert "Decision made" in call_args[0][0]
        extra = call_args[1]["extra"]
        assert extra["decision_type"] == "source_selection"
        assert extra["decision"] == "Selected Mayo Clinic"
        assert extra["reason"] == "Most authoritative for symptom information"
    
    def test_log_guardrail_trigger(self):
        """Test that log_guardrail_trigger logs at warning level."""
        logger = MagicMock()
        
        log_guardrail_trigger(
            logger,
            rule="no_diagnosis",
            original_response="You have the flu",
            modified_response="Common cold symptoms include...",
            session_id="test-123"
        )
        
        logger.warning.assert_called_once()
        call_args = logger.warning.call_args
        assert "Guardrail triggered" in call_args[0][0]
        extra = call_args[1]["extra"]
        assert extra["rule"] == "no_diagnosis"
        assert extra["original_response"] == "You have the flu"
        assert extra["modified_response"] == "Common cold symptoms include..."
    
    def test_rotating_file_handler(self):
        """Test that log files rotate when they reach max size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"
            setup_logging(
                log_dir=str(log_dir),
                max_bytes=1024,  # Small size to trigger rotation
                backup_count=3
            )
            
            logger = get_logger("test")
            
            # Write enough logs to trigger rotation
            for i in range(100):
                logger.info(f"Log message {i}" * 50)  # Long message
            
            # Check that backup files were created
            log_files = list(log_dir.glob("health_assistant.log*"))
            assert len(log_files) > 1  # Main log + at least one backup
            assert any(".log." in str(f) for f in log_files)  # Backup files exist