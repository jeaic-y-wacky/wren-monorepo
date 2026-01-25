"""
Wren Configuration Module

Auto-discovers configuration from environment variables.
Zero configuration required - everything has smart defaults.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Load environment variables from .env file if it exists
from dotenv import find_dotenv, load_dotenv

_dotenv_path = find_dotenv(usecwd=True)
if _dotenv_path:
    load_dotenv(_dotenv_path)
else:
    load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class WrenConfig:
    """Central configuration for Wren SDK.

    All settings auto-discovered from environment variables with WREN_ or provider-specific prefixes.
    """

    # AI Provider Settings (OpenAI)
    openai_api_key: str | None = field(default=None)
    default_model: str = field(default="gpt-4o-mini")

    # Behavior Settings
    ai_temperature: float = field(default=0.7)
    ai_max_tokens: int | None = field(default=None)
    ai_timeout: int = field(default=30)  # seconds
    ai_max_retries: int = field(default=3)

    # RAG Settings
    rag_chunk_size: int = field(default=500)
    rag_chunk_overlap: int = field(default=50)
    rag_top_k: int = field(default=5)
    rag_min_confidence: float = field(default=0.7)

    # Storage Settings
    data_dir: Path = field(default_factory=lambda: Path.home() / ".wren")
    cache_enabled: bool = field(default=True)
    cache_ttl: int = field(default=3600)  # seconds

    # Platform Settings
    platform_url: str | None = field(default=None)
    platform_api_key: str | None = field(default=None)

    # Development Settings
    debug: bool = field(default=False)
    verbose: bool = field(default=False)
    show_prompts: bool = field(default=False)

    def __post_init__(self):
        """Validate and process configuration after initialization."""
        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Validate OpenAI API key
        if not self.openai_api_key:
            logger.warning("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for serialization."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                result[key] = str(value)
            else:
                result[key] = value
        return result

    @property
    def has_ai_provider(self) -> bool:
        """Check if OpenAI is configured."""
        return bool(self.openai_api_key)


def load_config() -> WrenConfig:
    """Load configuration from environment variables.

    Supports multiple prefixes for flexibility:
    - WREN_* for Wren-specific settings
    - OPENAI_API_KEY for provider keys
    - Standard environment variables as fallbacks
    """
    config_values = {}

    # Map environment variables to config fields
    env_mapping = {
        # OpenAI API Keys
        "openai_api_key": ["OPENAI_API_KEY", "WREN_OPENAI_API_KEY"],
        "default_model": ["WREN_MODEL", "WREN_DEFAULT_MODEL"],
        # Behavior settings
        "ai_temperature": ["WREN_AI_TEMPERATURE", "WREN_TEMPERATURE"],
        "ai_max_tokens": ["WREN_AI_MAX_TOKENS", "WREN_MAX_TOKENS"],
        "ai_timeout": ["WREN_AI_TIMEOUT", "WREN_TIMEOUT"],
        "ai_max_retries": ["WREN_AI_MAX_RETRIES", "WREN_MAX_RETRIES"],
        # RAG settings
        "rag_chunk_size": ["WREN_RAG_CHUNK_SIZE"],
        "rag_chunk_overlap": ["WREN_RAG_CHUNK_OVERLAP"],
        "rag_top_k": ["WREN_RAG_TOP_K"],
        "rag_min_confidence": ["WREN_RAG_MIN_CONFIDENCE"],
        # Storage settings
        "data_dir": ["WREN_DATA_DIR"],
        "cache_enabled": ["WREN_CACHE_ENABLED"],
        "cache_ttl": ["WREN_CACHE_TTL"],
        # Platform settings
        "platform_url": ["WREN_PLATFORM_URL"],
        "platform_api_key": ["WREN_PLATFORM_API_KEY"],
        # Development settings
        "debug": ["WREN_DEBUG", "DEBUG"],
        "verbose": ["WREN_VERBOSE", "VERBOSE"],
        "show_prompts": ["WREN_SHOW_PROMPTS"],
    }

    # Load values from environment
    for config_key, env_vars in env_mapping.items():
        for env_var in env_vars:
            value = os.environ.get(env_var)
            if value is not None:
                # Type conversion based on field
                if config_key in ["ai_temperature", "rag_min_confidence"]:
                    config_values[config_key] = float(value)
                elif config_key in [
                    "ai_max_tokens",
                    "ai_timeout",
                    "ai_max_retries",
                    "rag_chunk_size",
                    "rag_chunk_overlap",
                    "rag_top_k",
                    "cache_ttl",
                ]:
                    config_values[config_key] = int(value) if value else None
                elif config_key in ["cache_enabled", "debug", "verbose", "show_prompts"]:
                    config_values[config_key] = value.lower() in ["true", "1", "yes", "on"]
                elif config_key == "data_dir":
                    config_values[config_key] = Path(value)
                else:
                    config_values[config_key] = value
                break  # Use first found value

    return WrenConfig(**config_values)


# Global config instance
_config: WrenConfig | None = None


def get_config() -> WrenConfig:
    """Get the global configuration instance.

    Lazy-loads configuration on first access.
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> WrenConfig:
    """Reload configuration from environment variables.

    Useful for testing or when environment changes.
    """
    global _config
    _config = load_config()
    return _config


# Convenience exports
config = get_config
