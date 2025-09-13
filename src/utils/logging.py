"""Logging configuration and utilities for the health assistant."""
import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Any, Dict
from pythonjsonlogger import jsonlogger


def setup_logging(
    log_dir: str = "logs",
    log_file: str = "health_assistant.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    level: int = logging.INFO
) -> None:
    """
    Set up logging configuration with rotating file handler.
    
    Args:
        log_dir: Directory for log files
        log_file: Name of the log file
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep
        level: Logging level
    """
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Configure JSON formatter
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
        rename_fields={'levelname': 'level', 'asctime': 'timestamp'},
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    
    # Set up rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    root_logger.addHandler(file_handler)
    
    # Also add console handler for development
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_api_call(
    logger: logging.Logger,
    service: str,
    endpoint: str,
    model: Optional[str] = None,
    tokens: Optional[int] = None,
    session_id: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log an API call with relevant details.
    
    Args:
        logger: Logger instance
        service: API service name (e.g., "anthropic")
        endpoint: API endpoint being called
        model: Model being used
        tokens: Number of tokens in the request
        session_id: Session identifier
        **kwargs: Additional context to log
    """
    extra = {
        "service": service,
        "endpoint": endpoint,
        "session_id": session_id
    }
    
    if model:
        extra["model"] = model
    if tokens is not None:
        extra["tokens"] = tokens
    
    extra.update(kwargs)
    
    logger.info(
        f"Calling {service.title()} API",
        extra=extra
    )


def log_decision(
    logger: logging.Logger,
    decision_type: str,
    decision: str,
    reason: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log a decision made by the system.
    
    Args:
        logger: Logger instance
        decision_type: Type of decision (e.g., "source_selection")
        decision: The decision made
        reason: Reason for the decision
        session_id: Session identifier
        **kwargs: Additional context to log
    """
    extra = {
        "decision_type": decision_type,
        "decision": decision,
        "session_id": session_id
    }
    
    if reason:
        extra["reason"] = reason
    
    extra.update(kwargs)
    
    logger.info(
        f"Decision made: {decision_type}",
        extra=extra
    )


def log_guardrail_trigger(
    logger: logging.Logger,
    rule: str,
    original_response: str,
    modified_response: str,
    session_id: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log when a guardrail is triggered.
    
    Args:
        logger: Logger instance
        rule: Guardrail rule that was triggered
        original_response: Original response before modification
        modified_response: Modified response after guardrail
        session_id: Session identifier
        **kwargs: Additional context to log
    """
    extra = {
        "rule": rule,
        "original_response": original_response,
        "modified_response": modified_response,
        "session_id": session_id
    }
    
    extra.update(kwargs)
    
    logger.warning(
        f"Guardrail triggered: {rule}",
        extra=extra
    )