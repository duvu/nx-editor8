"""
Core message processor for nx-editor8 content pipeline.

This module implements the main processing pipeline that coordinates requirements verification,
AI analysis, content enhancement, and output formatting for nx-maker8 compatibility.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

import structlog

from src.core.config import get_settings
from src.models.content_models import (
    ContentMessage,
    ProcessingRequirements,
    ProcessingResult,
    ContentAnalysis,
    NXMaker8Input,
    Scene,
    SceneType,
    TTSProvider,
    VideoSite,
    StorageConfig,
    VideoSettings,
)
from src.validation.requirements_validator import RequirementsValidator
from src.integrations.llm_client import get_llm_client
from src.integrations.kafka_client import NXMaker8Publisher

logger = structlog.get_logger(__name__)


class MessageProcessor:
    """
    Main processing pipeline for content messages with requirements verification.
    """

    def __init__(self):
        self.settings = get_settings()
        self.requirements_validator = RequirementsValidator()
        self.llm_client = get_llm_client()
        self.publisher = NXMaker8Publisher()

    async def process_message(self, message: ContentMessage) -> ProcessingResult:
        """
        Process a content message through the complete pipeline.

        Args:
            message: Input content message

        Returns:
            ProcessingResult with detailed processing information
        """
        start_time = time.time()

        logger.info(
            "Starting message processing",
            topic=message.topic,
            channel=message.channel,
            content_length=len(message.text_content),
        )

        try:
            # Create processing requirements from settings
            requirements = (
                self.requirements_validator.create_requirements_from_settings()
            )

            # Process with retry logic
            result = await self._process_with_retry(message, requirements)

            # Set processing time
            result.processing_time = time.time() - start_time

            logger.info(
                "Message processing completed",
                success=result.success,
                retry_count=result.retry_count,
                processing_time=result.processing_time,
                final_scenes=len(result.generated_scenes),
            )

            return result

        except Exception as e:
            logger.error("Message processing failed", error=str(e))
            return ProcessingResult(
                success=False,
                original_message=message,
                requirements_verification=self.requirements_validator.verify_requirements(
                    message
                ),
                processing_time=time.time() - start_time,
                error_message=str(e),
            )

    async def _process_with_retry(
        self, message: ContentMessage, requirements: ProcessingRequirements
    ) -> ProcessingResult:
        """
        Process message with intelligent retry logic for failed requirements.

        Args:
            message: Content message to process
            requirements: Processing requirements

        Returns:
            ProcessingResult with retry information
        """
        retry_count = 0
        current_message = message

        while retry_count <= requirements.max_retries:
            # Verify requirements
            verification = self.requirements_validator.verify_requirements(
                current_message, requirements
            )

            # If requirements are met, proceed with processing
            if verification.meets_requirements:
                return await self._process_validated_content(
                    current_message, verification, retry_count
                )

            # If we've reached max retries, return failure
            if retry_count >= requirements.max_retries:
                logger.warning(
                    "Max retries exceeded for requirements verification",
                    retry_count=retry_count,
                    max_retries=requirements.max_retries,
                    errors=verification.validation_errors,
                )
                return ProcessingResult(
                    success=False,
                    original_message=message,
                    requirements_verification=verification,
                    retry_count=retry_count,
                    error_message=f"Max retries ({requirements.max_retries}) exceeded for requirements verification",
                )

            # Enhance content for retry
            retry_count += 1
            logger.info(
                "Attempting content enhancement for retry",
                retry_count=retry_count,
                errors=verification.validation_errors,
            )

            try:
                enhanced_content = (
                    await self.requirements_validator.enhance_content_for_requirements(
                        current_message, verification, requirements
                    )
                )

                # Create new message with enhanced content
                current_message = ContentMessage(
                    topic=current_message.topic,
                    channel=current_message.channel,
                    text_content=enhanced_content,
                    metadata=current_message.metadata,
                )

            except Exception as e:
                logger.error(
                    "Content enhancement failed", retry_count=retry_count, error=str(e)
                )
                return ProcessingResult(
                    success=False,
                    original_message=message,
                    requirements_verification=verification,
                    retry_count=retry_count,
                    error_message=f"Content enhancement failed: {e}",
                )

        # This should not be reached, but included for completeness
        return ProcessingResult(
            success=False,
            original_message=message,
            requirements_verification=verification,
            retry_count=retry_count,
            error_message="Unexpected end of retry loop",
        )

    async def _process_validated_content(
        self,
        message: ContentMessage,
        verification: RequirementsVerification,
        retry_count: int,
    ) -> ProcessingResult:
        """
        Process content that has passed requirements verification.

        Args:
            message: Validated content message
            verification: Successful verification results
            retry_count: Number of retry attempts made

        Returns:
            ProcessingResult with processing details
        """
        try:
            # Analyze content with AI
            content_analysis = await self._analyze_content(message)

            # Generate video scenes
            scenes = await self._generate_scenes(message, content_analysis)

            # Create nx-maker8 compatible output
            nx_maker8_input = self._create_nx_maker8_input(
                message, content_analysis, scenes
            )

            # Publish to Kafka
            publish_success = await self.publisher.publish_video_request(
                nx_maker8_input
            )

            if not publish_success:
                return ProcessingResult(
                    success=False,
                    original_message=message,
                    requirements_verification=verification,
                    content_analysis=content_analysis,
                    generated_scenes=scenes,
                    retry_count=retry_count,
                    error_message="Failed to publish to nx-maker8 topic",
                )

            return ProcessingResult(
                success=True,
                original_message=message,
                requirements_verification=verification,
                content_analysis=content_analysis,
                enhanced_content=message.text_content if retry_count > 0 else None,
                generated_scenes=scenes,
                final_output=nx_maker8_input,
                retry_count=retry_count,
            )

        except Exception as e:
            logger.error("Content processing failed", error=str(e))
            return ProcessingResult(
                success=False,
                original_message=message,
                requirements_verification=verification,
                retry_count=retry_count,
                error_message=f"Content processing failed: {e}",
            )

    async def _analyze_content(self, message: ContentMessage) -> ContentAnalysis:
        """
        Analyze content using AI to extract insights for video creation.

        Args:
            message: Content message to analyze

        Returns:
            ContentAnalysis with AI insights
        """
        try:
            # Load and format prompt template
            prompt = self._load_prompt_template(
                "content_analysis",
                {
                    "content": message.text_content,
                    "related_content": "",  # TODO: Implement database search for related content
                },
            )

            # Get AI analysis
            analysis_response = await self.llm_client.generate_json(
                prompt=prompt,
                system_message="You are nx-editor8's content analysis assistant specialized in video content creation.",
                temperature=0.2,
            )

            # Parse response into ContentAnalysis model
            return ContentAnalysis(
                sentiment=analysis_response.get("sentiment"),
                topics=analysis_response.get("topics", []),
                key_points=analysis_response.get("key_points", []),
                suggested_title=analysis_response.get("suggested_title"),
                suggested_description=analysis_response.get("suggested_description"),
                suggested_keywords=analysis_response.get("suggested_keywords", []),
                content_type=analysis_response.get("content_type"),
                quality_score=analysis_response.get("quality_score"),
            )

        except Exception as e:
            logger.error("Content analysis failed", error=str(e))
            # Return basic analysis as fallback
            return ContentAnalysis(
                sentiment="neutral",
                topics=["general"],
                key_points=[message.text_content[:100] + "..."],
                suggested_title="Generated Video Content",
                suggested_description="Auto-generated video from content analysis",
                suggested_keywords=["content", "video"],
                content_type="general",
                quality_score=0.7,
            )

    async def _generate_scenes(
        self, message: ContentMessage, analysis: ContentAnalysis
    ) -> list[Scene]:
        """
        Generate video scenes based on content and analysis.

        Args:
            message: Original content message
            analysis: AI content analysis

        Returns:
            List of Scene objects for video generation
        """
        try:
            # Load and format prompt template
            prompt = self._load_prompt_template(
                "scene_generation",
                {
                    "content_analysis": analysis.dict(),
                    "enhanced_content": message.text_content,
                    "available_images": "[]",  # TODO: Implement image search
                    "min_scenes": self.settings.min_scenes,
                    "max_scenes": self.settings.max_scenes,
                },
            )

            # Generate scenes with AI
            scenes_response = await self.llm_client.generate_json(
                prompt=prompt,
                system_message="You are nx-editor8's video scene generation assistant.",
                temperature=0.3,
            )

            # Parse scenes from response
            scenes_data = scenes_response.get("scenes", [])
            scenes = []

            for scene_data in scenes_data:
                scene = Scene(
                    type=SceneType(scene_data.get("type", "text_scene")),
                    text=scene_data.get("text", ""),
                    image_path=scene_data.get("image_path"),
                    background_color=scene_data.get("background_color"),
                    text_color=scene_data.get("text_color"),
                    duration=scene_data.get("duration"),
                )
                scenes.append(scene)

            return scenes

        except Exception as e:
            logger.error("Scene generation failed", error=str(e))
            # Return basic scenes as fallback
            return self._create_fallback_scenes(message, analysis)

    def _create_fallback_scenes(
        self, message: ContentMessage, analysis: ContentAnalysis
    ) -> list[Scene]:
        """
        Create basic fallback scenes when AI generation fails.

        Args:
            message: Original content message
            analysis: Content analysis

        Returns:
            List of basic Scene objects
        """
        scenes = [
            Scene(
                type=SceneType.TITLE_SCENE,
                text=analysis.suggested_title or "Generated Video Content",
                background_color="#1a1a1a",
                text_color="#ffffff",
                duration=3.0,
            ),
            Scene(
                type=SceneType.TEXT_SCENE,
                text=(
                    message.text_content[:150] + "..."
                    if len(message.text_content) > 150
                    else message.text_content
                ),
                background_color="#2c3e50",
                text_color="#ecf0f1",
                duration=5.0,
            ),
            Scene(
                type=SceneType.OUTRO_SCENE,
                text="Thank you for watching! Subscribe for more content.",
                background_color="#34495e",
                text_color="#ffffff",
                duration=3.0,
            ),
        ]
        return scenes

    def _create_nx_maker8_input(
        self, message: ContentMessage, analysis: ContentAnalysis, scenes: list[Scene]
    ) -> NXMaker8Input:
        """
        Create nx-maker8 compatible input from processed content.

        Args:
            message: Original content message
            analysis: AI content analysis
            scenes: Generated video scenes

        Returns:
            NXMaker8Input ready for publishing
        """
        # Map topic to video site
        video_site_mapping = {
            "youtube_content": VideoSite.YOUTUBE,
            "tiktok_content": VideoSite.TIKTOK,
            "facebook_content": VideoSite.FACEBOOK,
        }

        return NXMaker8Input(
            title=analysis.suggested_title or "Generated Video Content",
            category=analysis.content_type or "general",
            description=analysis.suggested_description
            or "Auto-generated video content",
            keywords=(
                ", ".join(analysis.suggested_keywords)
                if analysis.suggested_keywords
                else "video, content"
            ),
            channel_name=message.channel,
            channel_id=message.metadata.channel_id,
            tts_provider=TTSProvider(self.settings.default_tts_provider),
            video_site=video_site_mapping.get(message.topic, VideoSite.YOUTUBE),
            storage=StorageConfig(),
            scenes=scenes,
            settings=VideoSettings(
                resolution=self.settings.default_video_resolution,
                fps=self.settings.default_video_fps,
            ),
            metadata={
                "source_topic": message.topic,
                "processed_at": datetime.now().isoformat(),
                "ai_model": self.settings.llm_model,
                "content_id": message.metadata.content_id,
                "original_author": message.metadata.author,
            },
        )

    def _load_prompt_template(
        self, template_name: str, variables: Dict[str, Any]
    ) -> str:
        """
        Load and format prompt template with variables.

        Args:
            template_name: Name of the template file (without .md extension)
            variables: Variables to substitute in template

        Returns:
            Formatted prompt string
        """
        template_path = f"src/ai/prompts/{template_name}.md"

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()

            # Simple template variable substitution
            for key, value in variables.items():
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, indent=2)
                else:
                    value_str = str(value)
                template = template.replace(f"{{{{{key}}}}}", value_str)

            return template

        except FileNotFoundError:
            logger.warning(f"Prompt template not found: {template_path}")
            # Return a basic fallback prompt
            return f"Analyze the following content: {{content}}"

    async def close(self) -> None:
        """Close all resources."""
        self.publisher.close()
        await self.llm_client.close()
