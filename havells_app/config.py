"""Configuration management for the agent system."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    # Azure OpenAI Settings
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION", "2024-02-01")
    AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    
    # Azure AD Authentication
    TECHDEMO_TENANT_ID = os.getenv("TECHDEMO_TENANT_ID")
    TECHDEMO_CLIENT_ID = os.getenv("TECHDEMO_CLIENT_ID")
    TECHDEMO_CLIENT_SECRET = os.getenv("TECHDEMO_CLIENT_SECRET")
    
    # Model Configuration
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1000"))
    
    # Reset Detection Configuration
    RESET_LATENCY_BUDGET_MS = int(os.getenv("RESET_LATENCY_BUDGET_MS", "500"))
    RESET_ENABLE_LOGGING = os.getenv("RESET_ENABLE_LOGGING", "true").lower() == "true"
    
    # Application Settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        required = [
            ("AZURE_OPENAI_API_KEY", cls.AZURE_OPENAI_API_KEY),
            ("AZURE_OPENAI_ENDPOINT", cls.AZURE_OPENAI_ENDPOINT),
        ]
        
        missing = [name for name, value in required if not value]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")


# Validate on import
Config.validate()
