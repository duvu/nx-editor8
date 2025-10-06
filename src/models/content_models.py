"""
Data models for nx-editor8 content processing pipeline.

This module defines Pydantic models for message handling, content validation,
and nx-maker8 output format compatibility.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from pydantic import BaseModel, Field


class ContentSource(str, Enum):
    """Supported content sources."""

    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"


class SceneType(str, Enum):
    """Scene types for video generation."""

    TITLE_SCENE = "title_scene"
    TEXT_SCENE = "text_scene"
    IMAGE_SCENE = "image_scene"
    OUTRO_SCENE = "outro_scene"


class TTSProvider(str, Enum):
    """Text-to-speech providers."""

    GOOGLE_TTS = "googletts"
    ELEVEN_LABS = "elevenlabs"


class VideoSite(str, Enum):
    """Video platforms."""

    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"


class StorageProvider(str, Enum):
    """Storage providers."""

    DROPBOX = "dropbox"
    GDRIVE = "gdrive"


class ContentFormat(str, Enum):
    """Content format types."""

    TEXT = "text"
    STRUCTURED = "structured"


@dataclass
class MessageMetadata:
    """Metadata for incoming content messages."""

    source: str
    timestamp: datetime
    channel_id: str
    content_id: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ContentMessage:
    """Kafka message format for content input."""

    topic: str
    channel: str
    text_content: str
    metadata: MessageMetadata


class ProcessingRequirements(BaseModel):
    """Requirements for content processing validation."""

    min_word_count: int = Field(default=50, description="Minimum word count required")
    max_word_count: int = Field(default=2000, description="Maximum word count allowed")
    min_char_count: int = Field(
        default=200, description="Minimum character count required"
    )
    max_char_count: int = Field(
        default=10000, description="Maximum character count allowed"
    )
    content_format: ContentFormat = Field(
        default=ContentFormat.TEXT, description="Required content format"
    )
    language: Optional[str] = Field(
        default=None, description="Required language (en/vi/auto)"
    )
    max_retries: int = Field(default=3, description="Maximum retry attempts")


class RequirementsVerification(BaseModel):
    """Results of requirements verification."""

    meets_requirements: bool = Field(
        description="Whether content meets all requirements"
    )
    validation_errors: List[str] = Field(
        default_factory=list, description="List of validation errors"
    )
    retry_needed: bool = Field(default=False, description="Whether retry is needed")
    word_count: int = Field(description="Actual word count")
    char_count: int = Field(description="Actual character count")
    detected_language: Optional[str] = Field(
        default=None, description="Detected content language"
    )
    format_compliance: bool = Field(
        default=True, description="Whether format requirements are met"
    )


class Scene(BaseModel):
    """Scene definition for video generation."""

    type: SceneType = Field(description="Type of scene")
    text: str = Field(description="Text content for the scene")
    image_path: Optional[str] = Field(
        default=None, description="Path to image for image scenes"
    )
    background_color: Optional[str] = Field(
        default=None, description="Background color"
    )
    text_color: Optional[str] = Field(default=None, description="Text color")
    duration: Optional[float] = Field(
        default=None, description="Scene duration in seconds"
    )


class StorageConfig(BaseModel):
    """Storage configuration for video output."""

    provider: StorageProvider = Field(
        default=StorageProvider.DROPBOX, description="Storage provider"
    )
    folder_path: str = Field(
        default="/nx-maker8/generated", description="Storage folder path"
    )


class VideoSettings(BaseModel):
    """Video generation settings."""

    resolution: str = Field(default="1920x1080", description="Video resolution")
    fps: int = Field(default=30, description="Frames per second")
    format: str = Field(default="mp4", description="Video format")


class NXMaker8Input(BaseModel):
    """Output format for nx-maker8 (published to video_input_topic)."""

    title: str = Field(description="Video title")
    category: str = Field(description="Video category")
    description: str = Field(description="Video description")
    keywords: str = Field(description="Video keywords")
    channel_name: str = Field(description="Channel name")
    channel_id: str = Field(description="Channel ID")
    tts_provider: TTSProvider = Field(
        default=TTSProvider.GOOGLE_TTS, description="TTS provider"
    )
    video_site: VideoSite = Field(
        default=VideoSite.YOUTUBE, description="Target video platform"
    )
    storage: StorageConfig = Field(
        default_factory=StorageConfig, description="Storage configuration"
    )
    scenes: List[Scene] = Field(description="List of video scenes")
    settings: VideoSettings = Field(
        default_factory=VideoSettings, description="Video settings"
    )

    # Optional metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ContentAnalysis(BaseModel):
    """Results of AI content analysis."""

    sentiment: Optional[str] = Field(default=None, description="Content sentiment")
    topics: List[str] = Field(default_factory=list, description="Identified topics")
    key_points: List[str] = Field(
        default_factory=list, description="Key content points"
    )
    suggested_title: Optional[str] = Field(
        default=None, description="AI-suggested title"
    )
    suggested_description: Optional[str] = Field(
        default=None, description="AI-suggested description"
    )
    suggested_keywords: List[str] = Field(
        default_factory=list, description="AI-suggested keywords"
    )
    content_type: Optional[str] = Field(
        default=None, description="Identified content type"
    )
    quality_score: Optional[float] = Field(
        default=None, description="Content quality score (0-1)"
    )


class ProcessingResult(BaseModel):
    """Result of content processing pipeline."""

    success: bool = Field(description="Whether processing was successful")
    original_message: ContentMessage = Field(description="Original input message")
    requirements_verification: RequirementsVerification = Field(
        description="Requirements check results"
    )
    content_analysis: Optional[ContentAnalysis] = Field(
        default=None, description="AI analysis results"
    )
    enhanced_content: Optional[str] = Field(
        default=None, description="Enhanced content if retry was needed"
    )
    generated_scenes: List[Scene] = Field(
        default_factory=list, description="Generated video scenes"
    )
    final_output: Optional[NXMaker8Input] = Field(
        default=None, description="Final nx-maker8 input"
    )
    processing_time: Optional[float] = Field(
        default=None, description="Processing time in seconds"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    error_message: Optional[str] = Field(
        default=None, description="Error message if processing failed"
    )


# Database Models (for SQLAlchemy integration)
class Article(BaseModel):
    """Article model for maker8 database integration."""

    id: int
    title: str
    content: str
    summary: Optional[str] = None
    keywords: Optional[str] = None
    created_at: datetime
    # Future embedding field
    embedding: Optional[List[float]] = None


class ImageAsset(BaseModel):
    """Image asset model for maker8 database integration."""

    id: int
    article_id: int
    url: str
    alt_text: Optional[str] = None
    is_accessible: bool = True
