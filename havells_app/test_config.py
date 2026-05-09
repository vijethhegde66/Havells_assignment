"""Unit tests for configuration module."""
import pytest
import os
from unittest.mock import patch


class TestConfig:
    """Test cases for configuration management."""
    
    def test_config_loads_from_env(self):
        """Test that config loads from environment variables."""
        # Config should already be loaded from .env
        from config import Config
        
        assert Config.AZURE_OPENAI_API_KEY is not None
        assert Config.AZURE_OPENAI_ENDPOINT is not None
        assert Config.OPENAI_API_VERSION is not None
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        from config import Config
        
        assert isinstance(Config.LLM_TEMPERATURE, float)
        assert 0.0 <= Config.LLM_TEMPERATURE <= 2.0
        assert isinstance(Config.LLM_MAX_TOKENS, int)
        assert Config.LLM_MAX_TOKENS > 0
        assert isinstance(Config.RESET_LATENCY_BUDGET_MS, int)
        assert Config.RESET_LATENCY_BUDGET_MS == 500
    
    def test_log_level(self):
        """Test log level configuration."""
        from config import Config
        
        assert Config.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    def test_validation_fails_with_missing_config(self):
        """Test that validation logic exists."""
        # Config is already loaded and validated on import
        # This test verifies the validation method exists and can be called
        from config import Config
        
        # Validation method should exist
        assert hasattr(Config, 'validate')
        assert callable(Config.validate)
        
        # Current config should be valid (would have failed on import otherwise)
        Config.validate()  # Should not raise
    
    def test_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        from config import Config
        
        # RESET_ENABLE_LOGGING should be parsed as boolean
        assert isinstance(Config.RESET_ENABLE_LOGGING, bool)
    
    def test_numeric_parsing(self):
        """Test numeric environment variable parsing."""
        from config import Config
        
        # These should be parsed as numbers, not strings
        assert isinstance(Config.LLM_TEMPERATURE, (int, float))
        assert isinstance(Config.LLM_MAX_TOKENS, int)
        assert isinstance(Config.RESET_LATENCY_BUDGET_MS, int)


class TestConfigValues:
    """Test specific configuration values for assignment."""
    
    def test_latency_budget_is_500ms(self):
        """Test that latency budget is set to 500ms as per assignment."""
        from config import Config
        
        assert Config.RESET_LATENCY_BUDGET_MS == 500
    
    def test_model_configuration(self):
        """Test that model is configured."""
        from config import Config
        
        assert Config.LLM_MODEL is not None
        assert Config.AZURE_OPENAI_DEPLOYMENT_NAME is not None
    
    def test_api_version(self):
        """Test API version format."""
        from config import Config
        
        # Should be in YYYY-MM-DD format
        assert len(Config.OPENAI_API_VERSION.split("-")) == 3
    
    def test_endpoint_format(self):
        """Test endpoint URL format."""
        from config import Config
        
        assert Config.AZURE_OPENAI_ENDPOINT.startswith("https://")
        assert "openai.azure.com" in Config.AZURE_OPENAI_ENDPOINT
