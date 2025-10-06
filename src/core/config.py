"""
nx-editor8 core configuration following EngineX patterns for consistency.

This module provides configuration management with multi-fallback environment variable support
for seamless integration with the xProjects ecosystem.
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


def _get_env_with_fallback(primary: str, fallback: str, default: str = None) -> str:
    """Get environment variable with fallback support for backward compatibility."""
    return os.getenv(primary) or os.getenv(fallback) or default


def _get_env_with_multi_fallback(*keys: str, default: str = None) -> Optional[str]:
    """Get environment variable with multiple fallback keys for workspace consistency."""
    for key in keys:
        value = os.getenv(key)
        if value is not None:
            return value
    return default


class Settings(BaseSettings):
    """nx-editor8 settings following EngineX patterns for consistency"""

    # Service identification
    service_name: str = Field(default="nx-editor8")

    # Kafka Configuration - Input
    kafka_bootstrap_servers: str = Field(
        default_factory=lambda: _get_env_with_fallback(
            "KAFKA_BOOTSTRAP_SERVERS",
            "NX_EDITOR8_KAFKA_BOOTSTRAP_SERVERS",
            "10.113.213.1:9094",
        )
    )
    kafka_security_protocol: str = Field(default="SASL_PLAINTEXT")
    kafka_sasl_mechanism: str = Field(default="PLAIN")
    kafka_sasl_username: str = Field(
        default_factory=lambda: _get_env_with_fallback(
            "KAFKA_SASL_USERNAME", "NX_EDITOR8_KAFKA_USERNAME", "client"
        )
    )
    kafka_sasl_password: str = Field(
        default_factory=lambda: _get_env_with_fallback(
            "KAFKA_SASL_PASSWORD", "NX_EDITOR8_KAFKA_PASSWORD", "client-secret"
        )
    )

    # Input Topics (consuming from)
    input_topics: List[str] = Field(
        default_factory=lambda: _get_env_with_fallback(
            "KAFKA_INPUT_TOPICS",
            "NX_EDITOR8_INPUT_TOPICS",
            "youtube_content,tiktok_content,facebook_content",
        ).split(",")
    )
    kafka_consumer_group: str = Field(
        default_factory=lambda: _get_env_with_fallback(
            "KAFKA_CONSUMER_GROUP", "NX_EDITOR8_CONSUMER_GROUP", "nx_editor8_consumer"
        )
    )

    # Output Topics (publishing to) - nx-maker8 input
    output_topic: str = Field(
        default_factory=lambda: _get_env_with_fallback(
            "KAFKA_OUTPUT_TOPIC", "NX_EDITOR8_OUTPUT_TOPIC", "video_input_topic"
        )
    )

    # Database Configuration (consistent with EngineX)
    database_url: str = Field(
        default_factory=lambda: _get_env_with_fallback(
            "DATABASE_URL",
            "NX_EDITOR8_DATABASE_URL",
            "postgresql://vubakninh:123456@10.113.213.9:6432/maker8",
        )
    )

    # LLM Configuration (following EngineX patterns - consistent with x-neews project)
    llm_api_base: Optional[str] = Field(
        default_factory=lambda: _get_env_with_multi_fallback(
            "LLM_API_BASE", "NX_EDITOR8_LLM_API_BASE"
        )
    )
    llm_api_key: Optional[str] = Field(
        default_factory=lambda: _get_env_with_multi_fallback(
            "LLM_API_KEY", "NX_EDITOR8_LLM_API_KEY"
        )
    )
    llm_model: str = Field(
        default_factory=lambda: _get_env_with_multi_fallback(
            "LLM_MODEL", "NX_EDITOR8_LLM_MODEL", default="gpt-3.5-turbo"
        ),
        description="LiteLLM-compatible model name for content processing",
    )
    llm_timeout_seconds: int = Field(
        default_factory=lambda: int(
            _get_env_with_multi_fallback(
                "LLM_TIMEOUT_SECONDS", "NX_EDITOR8_LLM_TIMEOUT_SECONDS", default="60"
            )
        )
    )
    llm_max_tokens: int = Field(
        default_factory=lambda: int(
            _get_env_with_multi_fallback(
                "LLM_MAX_TOKENS", "NX_EDITOR8_LLM_MAX_TOKENS", default="4000"
            )
        )
    )
    llm_temperature: float = Field(
        default_factory=lambda: float(
            _get_env_with_multi_fallback(
                "LLM_TEMPERATURE", "NX_EDITOR8_LLM_TEMPERATURE", default="0.7"
            )
        )
    )

    # Processing Configuration
    batch_size: int = Field(
        default_factory=lambda: int(
            _get_env_with_fallback("BATCH_SIZE", "NX_EDITOR8_BATCH_SIZE", "1")
        )
    )
    max_retry_attempts: int = Field(
        default_factory=lambda: int(
            _get_env_with_fallback("MAX_RETRY_ATTEMPTS", "NX_EDITOR8_MAX_RETRIES", "3")
        )
    )
    processing_timeout: int = Field(
        default_factory=lambda: int(
            _get_env_with_fallback("PROCESSING_TIMEOUT", "NX_EDITOR8_TIMEOUT", "300")
        )
    )

    # Content Generation Configuration
    min_scenes: int = Field(
        default_factory=lambda: int(
            _get_env_with_fallback("MIN_SCENES", "NX_EDITOR8_MIN_SCENES", "3")
        )
    )
    max_scenes: int = Field(
        default_factory=lambda: int(
            _get_env_with_fallback("MAX_SCENES", "NX_EDITOR8_MAX_SCENES", "10")
        )
    )
    default_video_resolution: str = Field(
        default_factory=lambda: _get_env_with_fallback(
            "DEFAULT_VIDEO_RESOLUTION", "NX_EDITOR8_VIDEO_RESOLUTION", "1920x1080"
        )
    )
    default_video_fps: int = Field(
        default_factory=lambda: int(
            _get_env_with_fallback("DEFAULT_VIDEO_FPS", "NX_EDITOR8_VIDEO_FPS", "30")
        )
    )
    default_tts_provider: str = Field(
        default_factory=lambda: _get_env_with_fallback(
            "DEFAULT_TTS_PROVIDER", "NX_EDITOR8_TTS_PROVIDER", "googletts"
        )
    )

    # Content Requirements Configuration
    min_word_count: int = Field(
        default_factory=lambda: int(
            _get_env_with_fallback("MIN_WORD_COUNT", "NX_EDITOR8_MIN_WORD_COUNT", "50")
        )
    )
    max_word_count: int = Field(
        default_factory=lambda: int(
            _get_env_with_fallback(
                "MAX_WORD_COUNT", "NX_EDITOR8_MAX_WORD_COUNT", "2000"
            )
        )
    )
    min_char_count: int = Field(
        default_factory=lambda: int(
            _get_env_with_fallback("MIN_CHAR_COUNT", "NX_EDITOR8_MIN_CHAR_COUNT", "200")
        )
    )
    max_char_count: int = Field(
        default_factory=lambda: int(
            _get_env_with_fallback(
                "MAX_CHAR_COUNT", "NX_EDITOR8_MAX_CHAR_COUNT", "10000"
            )
        )
    )
    required_content_format: str = Field(
        default_factory=lambda: _get_env_with_fallback(
            "REQUIRED_CONTENT_FORMAT", "NX_EDITOR8_CONTENT_FORMAT", "text"
        )
    )
    required_language: Optional[str] = Field(
        default_factory=lambda: _get_env_with_multi_fallback(
            "REQUIRED_LANGUAGE", "NX_EDITOR8_LANGUAGE"
        )
    )
    max_content_retries: int = Field(
        default_factory=lambda: int(
            _get_env_with_fallback(
                "MAX_CONTENT_RETRIES", "NX_EDITOR8_MAX_CONTENT_RETRIES", "3"
            )
        )
    )

    # Logging
    log_level: str = Field(
        default_factory=lambda: _get_env_with_fallback(
            "LOG_LEVEL", "NX_EDITOR8_LOG_LEVEL", "INFO"
        )
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow extra fields for backward compatibility with old RabbitMQ config
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
