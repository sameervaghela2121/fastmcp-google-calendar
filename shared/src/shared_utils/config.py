"""
Shared configuration module for MCP servers.
Provides common configuration management and environment variable handling.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from .logger import setup_logger

logger = setup_logger("shared-config")

# Load environment variables from .env file
load_dotenv()


class SharedConfig:
    """
    Shared configuration manager for MCP servers.
    Provides centralized access to common environment variables and settings.
    """
    
    def __init__(self):
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables."""
        # Supabase Configuration
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
        
        # Google OAuth Configuration
        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
        self.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
        
        # Common webhook settings
        self.WEBHOOK_TIMEOUT_SECONDS = float(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "20.0"))
        
        # Google Calendar specific webhook URL
        self.GOOGLE_CALENDAR_WEBHOOK_URL = os.getenv("GOOGLE_CALENDAR_WEBHOOK_URL")
        
        # Logging level
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # Environment
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        
        logger.info(f"Shared configuration loaded for environment: {self.ENVIRONMENT}")
    
    def get_supabase_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """
        Get Supabase credentials.
        
        Returns:
            Tuple of (url, key) or (None, None) if not configured
        """
        return self.SUPABASE_URL, self.SUPABASE_ANON_KEY
    
    def get_google_oauth_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """
        Get Google OAuth credentials.
        
        Returns:
            Tuple of (client_id, client_secret) or (None, None) if not configured
        """
        return self.GOOGLE_CLIENT_ID, self.GOOGLE_CLIENT_SECRET
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"
    
    def validate_required_config(self, required_vars: list[str]) -> bool:
        """
        Validate that required configuration variables are set.
        
        Args:
            required_vars: List of required configuration variable names
            
        Returns:
            True if all required variables are set, False otherwise
        """
        missing_vars = []
        for var in required_vars:
            if not hasattr(self, var) or not getattr(self, var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing required configuration variables: {missing_vars}")
            return False
        
        return True


# Global shared config instance
_shared_config = None


def get_shared_config() -> SharedConfig:
    """
    Get the global shared configuration instance.
    
    Returns:
        SharedConfig: The shared configuration instance
    """
    global _shared_config
    if _shared_config is None:
        _shared_config = SharedConfig()
    return _shared_config


def reload_config():
    """Reload the shared configuration from environment variables."""
    global _shared_config
    _shared_config = SharedConfig()
    logger.info("Shared configuration reloaded")


# Convenience functions for backward compatibility
def get_supabase_url() -> Optional[str]:
    """Get Supabase URL from shared config."""
    return get_shared_config().SUPABASE_URL


def get_supabase_key() -> Optional[str]:
    """Get Supabase anon key from shared config."""
    return get_shared_config().SUPABASE_ANON_KEY


def get_google_client_id() -> Optional[str]:
    """Get Google OAuth client ID from shared config."""
    return get_shared_config().GOOGLE_CLIENT_ID


def get_google_client_secret() -> Optional[str]:
    """Get Google OAuth client secret from shared config."""
    return get_shared_config().GOOGLE_CLIENT_SECRET


def get_webhook_timeout() -> float:
    """Get webhook timeout from shared config."""
    return get_shared_config().WEBHOOK_TIMEOUT_SECONDS


def get_google_calendar_webhook_url() -> Optional[str]:
    """Get Google Calendar webhook URL from shared config."""
    return get_shared_config().GOOGLE_CALENDAR_WEBHOOK_URL
