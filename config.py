"""
Configuration module for loading environment variables from .env file.

This module centralizes all configuration management, loading values from
a .env file in the project root directory.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env file from project root
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)


class Config:
    """Application configuration loaded from .env file."""
    
    # API Configuration
    NEWAPI_BASE_URL: str = os.getenv("NEWAPI_BASE_URL", "")
    NEWAPI_KEY_AD: str = os.getenv("NEWAPI_KEY_AD", "")
    
    # Zotero Configuration
    ZOTERO_ID: str = os.getenv("ZOTERO_ID", "")
    ZOTERO_KEY_AD: str = os.getenv("ZOTERO_KEY_AD", "")
    
    # Tavily Configuration
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    
    # Nature API Configuration
    NATURE_API_KEY: str = os.getenv("NATURE_API_KEY", "")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


# Create a singleton instance for easy access
config = Config()
