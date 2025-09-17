"""
Session-level settings for the health assistant.
These can be configured per user/session and override defaults.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from src.config.settings import settings


class SessionSettings(BaseModel):
    """Configurable settings for a user session."""
    
    # Safety Settings
    enable_input_guardrails: bool = Field(
        default=True,
        description="Enable input safety checks before processing queries"
    )
    enable_output_guardrails: bool = Field(
        default=False,  # Default to OFF for performance
        description="Enable output safety checks after generating response"
    )
    guardrail_mode: Literal["regex", "llm", "hybrid"] = Field(
        default="llm",
        description="Type of guardrail checking to use"
    )
    
    # Performance Settings
    enable_streaming: bool = Field(
        default=True,
        description="Stream responses for better perceived performance"
    )
    max_web_searches: int = Field(
        default=1,
        ge=0,
        le=5,
        description="Maximum number of web searches per query"
    )
    max_web_fetches: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Maximum number of web pages to fetch per query"
    )
    response_timeout: int = Field(
        default=30,
        ge=10,
        le=60,
        description="Maximum seconds to wait for response"
    )
    
    # Content Settings
    enable_trusted_domains: bool = Field(
        default=True,
        description="Restrict web searches to trusted medical domains"
    )
    custom_trusted_domains: List[str] = Field(
        default_factory=list,
        description="Additional trusted domains to include"
    )
    blocked_domains: List[str] = Field(
        default_factory=list,
        description="Domains to exclude from searches"
    )
    include_citations: Literal["always", "never", "auto"] = Field(
        default="always",
        description="When to include source citations"
    )
    response_detail_level: Literal["brief", "standard", "comprehensive"] = Field(
        default="standard",
        description="Level of detail in responses"
    )
    show_confidence_scores: bool = Field(
        default=False,
        description="Display confidence levels for medical information"
    )
    
    # Model Settings
    model: Literal[
        "claude-3-5-sonnet-20241022",
        "claude-opus-4-1-20250805", 
        "claude-sonnet-4-20250514"
    ] = Field(
        default="claude-3-5-sonnet-20241022",
        description="AI model to use for responses"
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Creativity/randomness of responses (0=deterministic, 1=creative)"
    )
    max_tokens: int = Field(
        default=1000,
        ge=500,
        le=2000,
        description="Maximum length of response in tokens"
    )
    
    # Display Settings
    show_tool_calls: bool = Field(
        default=False,
        description="Display web searches and fetches in UI"
    )
    show_response_timing: bool = Field(
        default=False,
        description="Show response generation timing metrics"
    )
    markdown_rendering: bool = Field(
        default=True,
        description="Render markdown formatting in responses"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "enable_input_guardrails": True,
                "enable_output_guardrails": False,
                "enable_streaming": True,
                "max_web_searches": 1,
                "max_web_fetches": 2,
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.3
            }
        }
    
    def get_effective_domains(self) -> List[str]:
        """Get the effective list of trusted domains."""
        if not self.enable_trusted_domains:
            return []
        
        # Start with default trusted domains
        domains = settings.trusted_domains.copy()
        
        # Add custom domains
        domains.extend(self.custom_trusted_domains)
        
        # Remove blocked domains
        domains = [d for d in domains if d not in self.blocked_domains]
        
        return list(set(domains))  # Remove duplicates
    
    def should_use_streaming(self) -> bool:
        """Determine if streaming should be used based on settings."""
        # Can't stream if output guardrails are enabled
        if self.enable_output_guardrails:
            return False
        return self.enable_streaming
    
    def to_assistant_config(self) -> dict:
        """Convert settings to config dict for assistant initialization."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "enable_guardrails": self.enable_input_guardrails or self.enable_output_guardrails,
            "guardrail_mode": self.guardrail_mode,
            "trusted_domains": self.get_effective_domains(),
            "max_web_searches": self.max_web_searches,
            "max_web_fetches": self.max_web_fetches,
            "response_detail_level": self.response_detail_level,
            "include_citations": self.include_citations != "never",
            # Pass individual guardrail flags
            "enable_input_guardrails": self.enable_input_guardrails,
            "enable_output_guardrails": self.enable_output_guardrails,
        }


# Default settings instance
default_session_settings = SessionSettings()