"""Configuration management for URL Sandbox"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    virustotal_api_key: str = ""
    urlscan_api_key: str = ""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = True
    
    # Timeouts (seconds)
    virustotal_timeout: int = 10
    urlscan_timeout: int = 30
    playwright_timeout: int = 15
    
    # Risk scoring weights (must sum to 1.0)
    vt_weight: float = 0.35
    urlscan_weight: float = 0.35
    playwright_weight: float = 0.30
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
