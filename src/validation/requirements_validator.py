"""
Requirements verification system for content validation and quality assurance.

This module implements comprehensive content validation with intelligent retry logic
and LLM-powered content enhancement for failed requirements.
"""

import re
from typing import Dict, List, Optional

import structlog

from src.core.config import get_settings
from src.models.content_models import (
    ContentMessage,
    ProcessingRequirements,
    RequirementsVerification,
    ContentFormat,
)
from src.integrations.llm_client import get_llm_client

logger = structlog.get_logger(__name__)


class RequirementsValidator:
    """
    Validates content against processing requirements with intelligent enhancement.
    """

    def __init__(self):
        self.settings = get_settings()
        self.llm_client = get_llm_client()

    def create_requirements_from_settings(self) -> ProcessingRequirements:
        """Create ProcessingRequirements from current settings."""
        return ProcessingRequirements(
            min_word_count=self.settings.min_word_count,
            max_word_count=self.settings.max_word_count,
            min_char_count=self.settings.min_char_count,
            max_char_count=self.settings.max_char_count,
            content_format=ContentFormat(self.settings.required_content_format),
            language=self.settings.required_language,
            max_retries=self.settings.max_content_retries,
        )

    def verify_requirements(
        self,
        message: ContentMessage,
        requirements: Optional[ProcessingRequirements] = None,
    ) -> RequirementsVerification:
        """
        Verify content message meets processing requirements.

        Args:
            message: Content message to validate
            requirements: Processing requirements (uses settings defaults if None)

        Returns:
            RequirementsVerification with detailed validation results
        """
        if requirements is None:
            requirements = self.create_requirements_from_settings()

        content = message.text_content
        validation_errors = []

        # Count words and characters
        word_count = len(content.split())
        char_count = len(content)

        # Validate word count
        if word_count < requirements.min_word_count:
            validation_errors.append(
                f"Content too short: {word_count} words, minimum required: {requirements.min_word_count}"
            )
        elif word_count > requirements.max_word_count:
            validation_errors.append(
                f"Content too long: {word_count} words, maximum allowed: {requirements.max_word_count}"
            )

        # Validate character count
        if char_count < requirements.min_char_count:
            validation_errors.append(
                f"Content too short: {char_count} characters, minimum required: {requirements.min_char_count}"
            )
        elif char_count > requirements.max_char_count:
            validation_errors.append(
                f"Content too long: {char_count} characters, maximum allowed: {requirements.max_char_count}"
            )

        # Validate content format
        format_compliance = self._validate_content_format(
            content, requirements.content_format
        )
        if not format_compliance:
            validation_errors.append(
                f"Content does not meet {requirements.content_format.value} format requirements"
            )

        # Validate language if specified
        detected_language = self._detect_language(content)
        language_valid = True
        if requirements.language and requirements.language.lower() != "auto":
            if detected_language != requirements.language.lower():
                validation_errors.append(
                    f"Content language '{detected_language}' does not match required language: {requirements.language}"
                )
                language_valid = False

        # Determine if requirements are met
        meets_requirements = len(validation_errors) == 0

        result = RequirementsVerification(
            meets_requirements=meets_requirements,
            validation_errors=validation_errors,
            retry_needed=not meets_requirements,
            word_count=word_count,
            char_count=char_count,
            detected_language=detected_language,
            format_compliance=format_compliance,
        )

        logger.info(
            "Requirements verification completed",
            meets_requirements=meets_requirements,
            word_count=word_count,
            char_count=char_count,
            detected_language=detected_language,
            error_count=len(validation_errors),
        )

        return result

    def _validate_content_format(
        self, content: str, required_format: ContentFormat
    ) -> bool:
        """
        Validate content format requirements.

        Args:
            content: Text content to validate
            required_format: Required content format

        Returns:
            True if content meets format requirements
        """
        if required_format == ContentFormat.TEXT:
            # Basic text format - just needs to be non-empty
            return len(content.strip()) > 0

        elif required_format == ContentFormat.STRUCTURED:
            # Structured content requires headings, bullets, or multiple paragraphs
            return self._is_structured_content(content)

        return True

    def _is_structured_content(self, content: str) -> bool:
        """
        Check if content meets structured format requirements.

        Args:
            content: Text content to check

        Returns:
            True if content has structured elements
        """
        lines = content.split("\n")

        # Check for headings (lines starting with #)
        has_headings = any(line.strip().startswith("#") for line in lines)

        # Check for bullet points (lines starting with *, -, or •)
        has_bullet_points = any(
            line.strip().startswith(("*", "-", "•", "1.", "2.", "3.")) for line in lines
        )

        # Check for multiple paragraphs (separated by empty lines)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        has_multiple_paragraphs = len(paragraphs) >= 2

        # Check for numbered lists
        has_numbered_lists = any(re.match(r"^\s*\d+\.", line) for line in lines)

        return (
            has_headings
            or has_bullet_points
            or has_multiple_paragraphs
            or has_numbered_lists
        )

    def _detect_language(self, content: str) -> str:
        """
        Detect content language using simple heuristics.

        Args:
            content: Text content to analyze

        Returns:
            Detected language code ('vi' for Vietnamese, 'en' for English)
        """
        # Vietnamese-specific characters
        vietnamese_chars = ["ă", "â", "đ", "ê", "ô", "ơ", "ư", "á", "à", "ả", "ã", "ạ"]
        vietnamese_char_count = sum(
            1 for char in content.lower() if char in vietnamese_chars
        )

        # Vietnamese-specific words
        vietnamese_words = [
            "và",
            "của",
            "có",
            "được",
            "cho",
            "trong",
            "với",
            "này",
            "đó",
            "những",
        ]
        vietnamese_word_count = sum(
            1 for word in vietnamese_words if word in content.lower()
        )

        # Calculate Vietnamese indicators
        total_chars = len(content)
        vietnamese_score = (
            vietnamese_char_count / max(total_chars, 1)
        ) * 100 + vietnamese_word_count

        # Simple threshold-based detection
        if vietnamese_score > 2:  # Adjust threshold as needed
            return "vi"
        else:
            return "en"

    async def enhance_content_for_requirements(
        self,
        message: ContentMessage,
        verification: RequirementsVerification,
        requirements: ProcessingRequirements,
    ) -> str:
        """
        Use LLM to enhance content to meet requirements.

        Args:
            message: Original content message
            verification: Failed verification results
            requirements: Target requirements

        Returns:
            Enhanced content that should meet requirements
        """
        content = message.text_content
        errors = verification.validation_errors

        # Create enhancement prompt
        enhancement_prompt = self._create_enhancement_prompt(
            content, errors, requirements
        )

        try:
            enhanced_content = await self.llm_client.generate(
                prompt=enhancement_prompt,
                system_message=(
                    "You are nx-editor8's content enhancement assistant. "
                    "Your task is to improve content to meet specific requirements while "
                    "preserving the original meaning and intent. Return only the enhanced content."
                ),
                temperature=0.3,  # Lower temperature for more focused improvements
            )

            logger.info(
                "Content enhanced using LLM",
                original_length=len(content),
                enhanced_length=len(enhanced_content),
                error_count=len(errors),
            )

            return enhanced_content.strip()

        except Exception as e:
            logger.error("Failed to enhance content with LLM", error=str(e))
            # Return original content as fallback
            return content

    def _create_enhancement_prompt(
        self, content: str, errors: List[str], requirements: ProcessingRequirements
    ) -> str:
        """
        Create a prompt for LLM content enhancement.

        Args:
            content: Original content
            errors: List of validation errors
            requirements: Target requirements

        Returns:
            Formatted prompt for LLM enhancement
        """
        prompt = f"""Please enhance the following content to fix these validation errors:

VALIDATION ERRORS:
{chr(10).join(f"- {error}" for error in errors)}

REQUIREMENTS:
- Word count: {requirements.min_word_count}-{requirements.max_word_count} words
- Character count: {requirements.min_char_count}-{requirements.max_char_count} characters
- Format: {requirements.content_format.value}
- Language: {requirements.language or 'auto-detect'}

ORIGINAL CONTENT:
{content}

Please provide enhanced content that:
1. Fixes all validation errors listed above
2. Maintains the original meaning and intent
3. Meets all specified requirements
4. Is suitable for video content creation

Enhanced content:"""

        return prompt
