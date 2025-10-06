"""
Test core configuration functionality for nx-editor8.
"""

import pytest
from src.core.config import Settings, get_settings


def test_settings_creation():
    """Test that Settings can be created with defaults."""
    settings = Settings()
    assert settings.service_name == "nx-editor8"
    assert settings.kafka_bootstrap_servers == "10.113.213.1:9094"
    assert isinstance(settings.min_word_count, int)
    assert settings.min_word_count > 0


def test_get_settings_singleton():
    """Test that get_settings returns the same instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2


def test_content_requirements_defaults():
    """Test content requirements have sensible defaults."""
    settings = Settings()
    assert settings.min_word_count == 50
    assert settings.max_word_count == 2000
    assert settings.min_char_count == 200
    assert settings.max_char_count == 10000


def test_kafka_configuration():
    """Test Kafka configuration defaults."""
    settings = Settings()
    assert ":" in settings.kafka_bootstrap_servers  # Should have host:port format
    assert settings.kafka_security_protocol == "SASL_PLAINTEXT"
    assert settings.kafka_sasl_mechanism == "PLAIN"


def test_ai_processing_defaults():
    """Test AI processing configuration."""
    settings = Settings()
    # Test that LLM configuration exists
    assert hasattr(settings, "llm_api_base")
    assert hasattr(settings, "llm_model")
    # Test LLM settings
    assert settings.llm_max_tokens > 0
    assert settings.llm_timeout_seconds > 0
    assert 0 <= settings.llm_temperature <= 2
