"""Application settings and configuration."""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Browserbase Configuration
    browserbase_api_key: str = Field(..., env="BROWSERBASE_API_KEY")
    browserbase_project_id: str = Field(..., env="BROWSERBASE_PROJECT_ID")
    
    # LLM Configuration
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    
    # Stagehand Configuration
    stagehand_model_name: str = Field("gpt-4o", env="STAGEHAND_MODEL_NAME")
    stagehand_headless: bool = Field(True, env="STAGEHAND_HEADLESS")
    stagehand_verbose: int = Field(1, env="STAGEHAND_VERBOSE")
    stagehand_dom_settle_timeout_ms: int = Field(5000, env="STAGEHAND_DOM_SETTLE_TIMEOUT_MS")
    
    # Scraping Configuration
    default_delay_between_requests: int = Field(2, env="DEFAULT_DELAY_BETWEEN_REQUESTS")
    max_retries: int = Field(3, env="MAX_RETRIES")
    respect_robots_txt: bool = Field(True, env="RESPECT_ROBOTS_TXT")

    # Security Configuration
    enable_variable_substitution: bool = Field(True, env="ENABLE_VARIABLE_SUBSTITUTION")
    log_sensitive_data: bool = Field(False, env="LOG_SENSITIVE_DATA")

    # Performance Configuration
    enable_caching: bool = Field(True, env="ENABLE_CACHING")
    cache_ttl_seconds: int = Field(3600, env="CACHE_TTL_SECONDS")  # 1 hour default

    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT")

    # CrewAI Configuration
    enable_crew_memory: bool = Field(False, env="ENABLE_CREW_MEMORY")

    # Scrappey Configuration
    scrappey_api_key: str = Field("SCmmAiI9H2CnerD8ex4YOcvkmMzQgH0P3DyOWmuqk6Mp9YHmn8Fk2AKxF6nj", env="SCRAPPEY_API_KEY")
    
    @field_validator('browserbase_api_key', 'browserbase_project_id')
    @classmethod
    def validate_required_fields(cls, v, info):
        if not v:
            raise ValueError(f"{info.field_name} is required")
        return v

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    model_config = {
        # Look for .env in the project root directory
        "env_file": Path(__file__).parent.parent.parent / ".env",
        "env_file_encoding": "utf-8"
    }
    
    def get_model_api_key(self) -> str:
        """Get the appropriate API key based on the selected model."""
        model_name = self.stagehand_model_name.lower()
        if "gpt" in model_name:
            if not self.openai_api_key:
                raise ValueError("OpenAI API key is required for GPT models")
            return self.openai_api_key
        elif "claude" in model_name:
            if not self.anthropic_api_key:
                raise ValueError("Anthropic API key is required for Claude models")
            return self.anthropic_api_key
        elif "gemini" in model_name:
            if not self.google_api_key:
                raise ValueError("Google API key is required for Gemini models")
            return self.google_api_key
        else:
            # Default to OpenAI if model type is unclear, but check for key
            if self.openai_api_key:
                return self.openai_api_key
            raise ValueError("Could not determine model type and no default API key is available.")

    def setup_logging(self) -> None:
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format=self.log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('ecommerce_scraper.log', encoding='utf-8')
            ]
        )

    def get_safe_config(self) -> Dict[str, Any]:
        """Get configuration without sensitive data for logging."""
        config = self.model_dump()
        # Remove sensitive fields
        sensitive_fields = ['browserbase_api_key', 'openai_api_key', 'anthropic_api_key', 'google_api_key']
        for field in sensitive_fields:
            if field in config and config[field]:
                config[field] = f"{config[field][:8]}..." if len(config[field]) > 8 else "***"
        return config


# Global settings instance
settings = Settings()
