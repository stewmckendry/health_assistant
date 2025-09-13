"""Configuration management using Pydantic settings."""
import os
import yaml
from typing import List, Optional, Dict, Any
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Configuration
    anthropic_api_key: str = Field(
        default="",
        env="ANTHROPIC_API_KEY",
        description="Anthropic API key for Claude"
    )
    
    # Model Configuration
    primary_model: str = Field(
        default="claude-3-opus-20240229",
        env="PRIMARY_MODEL",
        description="Primary Claude model to use"
    )
    fallback_model: str = Field(
        default="claude-3-sonnet-20240229",
        env="FALLBACK_MODEL",
        description="Fallback model if primary fails"
    )
    max_tokens: int = Field(
        default=1500,
        env="MAX_TOKENS",
        description="Maximum tokens in response"
    )
    temperature: float = Field(
        default=0.7,
        env="TEMPERATURE",
        description="Model temperature (0.0-1.0)"
    )
    
    # Web Fetch Configuration
    enable_web_fetch: bool = Field(
        default=True,
        env="ENABLE_WEB_FETCH",
        description="Enable web fetch tool for Claude"
    )
    max_web_fetch_uses: int = Field(
        default=5,
        env="MAX_WEB_FETCH_USES",
        description="Maximum web fetches per query"
    )
    citations_enabled: bool = Field(
        default=True,
        env="CITATIONS_ENABLED",
        description="Include citations in responses"
    )
    
    # Response Configuration
    max_response_length: int = Field(
        default=1500,
        env="MAX_RESPONSE_LENGTH",
        description="Maximum response length in tokens"
    )
    include_disclaimers: bool = Field(
        default=True,
        env="INCLUDE_DISCLAIMERS",
        description="Include medical disclaimers"
    )
    disclaimer_position: str = Field(
        default="both",
        env="DISCLAIMER_POSITION",
        description="Where to place disclaimers: 'start', 'end', or 'both'"
    )
    
    # Guardrails Configuration
    enable_guardrails: bool = Field(
        default=True,
        env="ENABLE_GUARDRAILS",
        description="Enable response guardrails"
    )
    forbidden_phrases: List[str] = Field(
        default=[
            "you have",
            "you should take",
            "your diagnosis",
            "diagnosis is",
            "treatment plan",
            "prescribe",
            "medication dosage",
            "stop taking",
            "you are suffering from",
            "you need to",
            "your condition",
            "your illness"
        ],
        env="FORBIDDEN_PHRASES",
        description="Phrases that trigger guardrails"
    )
    
    # Logging Configuration
    log_dir: str = Field(
        default="logs",
        env="LOG_DIR",
        description="Directory for log files"
    )
    log_file: str = Field(
        default="health_assistant.log",
        env="LOG_FILE",
        description="Log file name"
    )
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level"
    )
    log_max_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        env="LOG_MAX_BYTES",
        description="Maximum log file size"
    )
    log_backup_count: int = Field(
        default=5,
        env="LOG_BACKUP_COUNT",
        description="Number of log backups to keep"
    )
    
    # Assistant Mode Configuration
    assistant_mode: str = Field(
        default="patient",
        env="ASSISTANT_MODE",
        description="Assistant mode: 'patient' or 'physician'"
    )
    
    # File paths for external configurations
    prompts_file: str = Field(
        default="src/config/prompts.yaml",
        env="PROMPTS_FILE",
        description="Path to prompts YAML file"
    )
    disclaimers_file: str = Field(
        default="src/config/disclaimers.yaml",
        env="DISCLAIMERS_FILE",
        description="Path to disclaimers YAML file"
    )
    domains_file: str = Field(
        default="src/config/domains.yaml",
        env="DOMAINS_FILE",
        description="Path to trusted domains YAML file"
    )
    
    # Cached loaded configurations
    _prompts: Optional[Dict[str, Any]] = None
    _disclaimers: Optional[Dict[str, Any]] = None
    _domains: Optional[Dict[str, Any]] = None
    
    def load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """Load a YAML configuration file."""
        path = Path(file_path)
        if not path.exists():
            # Try relative to project root
            project_root = Path(__file__).parent.parent.parent
            path = project_root / file_path
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    @property
    def prompts(self) -> Dict[str, Any]:
        """Load and cache prompts configuration."""
        if self._prompts is None:
            self._prompts = self.load_yaml_file(self.prompts_file)
        return self._prompts
    
    @property
    def disclaimers(self) -> Dict[str, Any]:
        """Load and cache disclaimers configuration."""
        if self._disclaimers is None:
            self._disclaimers = self.load_yaml_file(self.disclaimers_file)
        return self._disclaimers
    
    @property
    def domains(self) -> Dict[str, Any]:
        """Load and cache domains configuration."""
        if self._domains is None:
            self._domains = self.load_yaml_file(self.domains_file)
        return self._domains
    
    @property
    def system_prompt(self) -> str:
        """Get the appropriate system prompt based on mode."""
        mode = self.assistant_mode.lower()
        if mode not in self.prompts:
            mode = "patient"  # Default to patient mode
        return self.prompts[mode]["system_prompt"]
    
    @property
    def disclaimer_start(self) -> str:
        """Get the appropriate starting disclaimer based on mode."""
        if not self.include_disclaimers:
            return ""
        
        mode = self.assistant_mode.lower()
        if mode not in self.disclaimers:
            mode = "patient"
        
        if self.disclaimer_position in ["start", "both"]:
            return self.disclaimers[mode]["start"]
        return ""
    
    @property
    def disclaimer_end(self) -> str:
        """Get the appropriate ending disclaimer based on mode."""
        if not self.include_disclaimers:
            return ""
        
        mode = self.assistant_mode.lower()
        if mode not in self.disclaimers:
            mode = "patient"
        
        if self.disclaimer_position in ["end", "both"]:
            return self.disclaimers[mode]["end"]
        return ""
    
    @property
    def emergency_resources(self) -> str:
        """Get emergency resources information."""
        return self.disclaimers.get("emergency", {}).get("resources", "")
    
    @property
    def mental_health_resources(self) -> str:
        """Get mental health resources information."""
        return self.disclaimers.get("emergency", {}).get("mental_health", "")
    
    @property
    def emergency_redirect(self) -> str:
        """Get emergency redirect message."""
        return self.disclaimers.get("emergency", {}).get("redirect", "")
    
    @property
    def trusted_domains(self) -> List[str]:
        """Get list of all trusted domains."""
        domains_list = []
        medical_domains = self.domains.get("medical", {})
        
        # Flatten all medical domain categories
        for category in medical_domains.values():
            if isinstance(category, list):
                domains_list.extend(category)
        
        # Add organization-specific domains
        org_domains = self.domains.get("organization_specific", [])
        if org_domains:
            domains_list.extend(org_domains)
        
        # Remove duplicates and return
        return list(set(domains_list))
    
    def get_domains_by_category(self, category: str) -> List[str]:
        """Get domains for a specific category."""
        medical_domains = self.domains.get("medical", {})
        return medical_domains.get(category, [])
    
    def validate_api_key(self) -> bool:
        """Validate that API key is set."""
        return bool(self.anthropic_api_key)
    
    def get_log_level(self) -> int:
        """Convert string log level to logging constant."""
        import logging
        return getattr(logging, self.log_level.upper(), logging.INFO)
    
    @field_validator('assistant_mode')
    @classmethod
    def validate_assistant_mode(cls, v: str) -> str:
        """Validate assistant mode is valid."""
        valid_modes = ["patient", "physician"]
        if v.lower() not in valid_modes:
            raise ValueError(f"assistant_mode must be one of {valid_modes}")
        return v.lower()
    
    @field_validator('disclaimer_position')
    @classmethod
    def validate_disclaimer_position(cls, v: str) -> str:
        """Validate disclaimer position is valid."""
        valid_positions = ["start", "end", "both"]
        if v.lower() not in valid_positions:
            raise ValueError(f"disclaimer_position must be one of {valid_positions}")
        return v.lower()


# Singleton settings instance
settings = Settings()