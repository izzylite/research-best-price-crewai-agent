"""Application settings and configuration."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Browserbase Configuration
    browserbase_api_key: str = Field(..., env="BROWSERBASE_API_KEY")
    browserbase_project_id: str = Field(..., env="BROWSERBASE_PROJECT_ID")
    
    # LLM Configuration
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    
    # Stagehand Configuration
    stagehand_model_name: str = Field("gpt-4o", env="STAGEHAND_MODEL_NAME")
    stagehand_headless: bool = Field(True, env="STAGEHAND_HEADLESS")
    stagehand_verbose: int = Field(1, env="STAGEHAND_VERBOSE")
    stagehand_dom_settle_timeout_ms: int = Field(5000, env="STAGEHAND_DOM_SETTLE_TIMEOUT_MS")
    
    # Scraping Configuration
    default_delay_between_requests: int = Field(2, env="DEFAULT_DELAY_BETWEEN_REQUESTS")
    max_retries: int = Field(3, env="MAX_RETRIES")
    respect_robots_txt: bool = Field(True, env="RESPECT_ROBOTS_TXT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def get_model_api_key(self) -> str:
        """Get the appropriate API key based on the selected model."""
        if "gpt" in self.stagehand_model_name.lower():
            if not self.openai_api_key:
                raise ValueError("OpenAI API key is required for GPT models")
            return self.openai_api_key
        elif "claude" in self.stagehand_model_name.lower():
            if not self.anthropic_api_key:
                raise ValueError("Anthropic API key is required for Claude models")
            return self.anthropic_api_key
        else:
            # Default to OpenAI if model type is unclear
            if not self.openai_api_key:
                raise ValueError("OpenAI API key is required")
            return self.openai_api_key


# Global settings instance
settings = Settings()
