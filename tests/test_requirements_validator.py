"""
Test requirements validator functionality.
"""

import pytest
from src.models.content_models import (
    ContentMessage,
    MessageMetadata,
    ProcessingRequirements,
    ContentFormat,
)
from src.validation.requirements_validator import RequirementsValidator
from datetime import datetime


@pytest.fixture
def sample_message():
    """Create a sample content message for testing."""
    metadata = MessageMetadata(
        source="youtube",
        timestamp=datetime.now(),
        channel_id="test_channel",
        content_id="test_content_123",
        author="test_author",
    )

    return ContentMessage(
        topic="youtube_content",
        channel="test_channel",
        text_content="This is a test content message with enough words to meet minimum requirements. "
        * 5,
        metadata=metadata,
    )


@pytest.fixture
def validator():
    """Create a requirements validator instance."""
    return RequirementsValidator()


def test_requirements_creation(validator):
    """Test creation of processing requirements from settings."""
    requirements = validator.create_requirements_from_settings()

    assert isinstance(requirements, ProcessingRequirements)
    assert requirements.min_word_count > 0
    assert requirements.max_word_count > requirements.min_word_count
    assert requirements.min_char_count > 0
    assert requirements.max_char_count > requirements.min_char_count


def test_valid_content_verification(validator, sample_message):
    """Test verification of valid content."""
    requirements = ProcessingRequirements(
        min_word_count=10,
        max_word_count=200,
        min_char_count=50,
        max_char_count=2000,
        content_format=ContentFormat.TEXT,
    )

    verification = validator.verify_requirements(sample_message, requirements)

    assert verification.meets_requirements
    assert len(verification.validation_errors) == 0
    assert not verification.retry_needed
    assert verification.word_count > 0
    assert verification.char_count > 0


def test_short_content_verification(validator):
    """Test verification of content that's too short."""
    metadata = MessageMetadata(
        source="youtube", timestamp=datetime.now(), channel_id="test_channel"
    )

    short_message = ContentMessage(
        topic="youtube_content",
        channel="test_channel",
        text_content="Short",
        metadata=metadata,
    )

    requirements = ProcessingRequirements(
        min_word_count=50, max_word_count=200, min_char_count=200, max_char_count=2000
    )

    verification = validator.verify_requirements(short_message, requirements)

    assert not verification.meets_requirements
    assert len(verification.validation_errors) > 0
    assert verification.retry_needed
    assert "too short" in " ".join(verification.validation_errors).lower()


def test_language_detection(validator):
    """Test language detection functionality."""
    # English content
    english_text = "This is English content without any special characters."
    detected = validator._detect_language(english_text)
    assert detected == "en"

    # Vietnamese content
    vietnamese_text = (
        "Đây là nội dung tiếng Việt với các ký tự đặc biệt như ă, â, đ, ê."
    )
    detected = validator._detect_language(vietnamese_text)
    assert detected == "vi"


def test_structured_content_detection(validator):
    """Test structured content format detection."""
    # Structured content with headings
    structured_content = """
    # Main Heading
    This is some content under the main heading.
    
    ## Subheading
    More content here.
    
    * Bullet point 1
    * Bullet point 2
    """

    assert validator._is_structured_content(structured_content)

    # Plain text content
    plain_content = "This is just plain text without any structure."
    assert not validator._is_structured_content(plain_content)


def test_content_format_validation(validator):
    """Test content format validation."""
    plain_text = "Simple plain text content."

    # Should pass for TEXT format
    assert validator._validate_content_format(plain_text, ContentFormat.TEXT)

    # Should fail for STRUCTURED format
    assert not validator._validate_content_format(plain_text, ContentFormat.STRUCTURED)

    # Structured content should pass for STRUCTURED format
    structured_text = """
    # Heading
    Content with structure.
    * Point 1
    * Point 2
    """
    assert validator._validate_content_format(structured_text, ContentFormat.STRUCTURED)
