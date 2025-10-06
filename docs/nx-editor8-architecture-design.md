# NX-Editor8 Architecture Design
**Version**: 2.0  
**Date**: 2025-10-03  
**Target**: Kafka-based Content Processing Pipeline for nx-maker8 Integration

## 🏛 System Architecture Overview

### High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Input Topics    │───▶│   nx-editor8    │───▶│ Output Topic    │───▶│   nx-maker8     │
│                 │    │                 │    │                 │    │                 │
│ • youtube_content│    │ AI Content      │    │video_input_topic│    │ Video Generation│
│ • tiktok_content │    │ Processing      │    │                 │    │ Service         │
│ • facebook_content│   │ Pipeline        │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                                              │
                                ▼                                              ▼
                       ┌─────────────────┐                            ┌─────────────────┐
                       │   maker8 DB     │                            │video_output_topic│
                       │                 │                            │                 │
                       │ • Articles      │                            │ • Video Results │
                       │ • Images        │                            │ • Upload Status │
                       │ • Embeddings    │                            │ • Metadata      │
                       └─────────────────┘                            └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   LLM APIs      │
                       │                 │
                       │ • Content Gen   │
                       │ • Enhancement   │
                       │ • Analysis      │
                       └─────────────────┘
```

## 🔄 Data Flow Architecture

### Message Processing Pipeline
```
1. Kafka Message Ingestion
   ├── Topic Router (by channel type)
   ├── Message Validation
   └── Content Extraction

2. Requirements Verification Layer
   ├── Word Count Validation (min/max)
   ├── Character Count Validation (min/max)
   ├── Content Format Validation (structured/text)
   ├── Language Detection & Validation
   └── Retry Logic for Failed Requirements

3. Database Integration Layer  
   ├── Related Content Search
   ├── Image Asset Retrieval
   └── Embedding Lookup (future)

4. AI Processing Layer
   ├── LangChain Workflow Engine
   ├── Content Analysis & Enhancement
   └── LLM API Integration

5. Content Generation Layer
   ├── Script Generation
   ├── Scene Creation
   └── Format Transformation

6. Kafka Publishing Layer
   ├── nx-maker8 JSON Format
   ├── Message Validation
   └── Topic Publishing (video_input_topic)
```

## 📊 Component Architecture

### Core Components

#### 1. Kafka Integration Layer
```python
# src/kafka/consumer.py
class ContentKafkaConsumer:
    """
    Kafka consumer following xProjects patterns from ai_broker
    """
    def __init__(self):
        self.bootstrap_servers = "10.113.213.1:9094"
        self.security_protocol = "SASL_PLAINTEXT"
        self.sasl_mechanism = "PLAIN"
        self.sasl_username = "client"
        self.sasl_password = "client-secret"
        
    def consume_messages(self) -> Iterator[ContentMessage]:
        """Consume and yield processed messages"""
        pass
        
    def get_consumer_group(self) -> str:
        return "nx_editor8_consumer"
```

#### 2. Database Integration Layer
```python
# src/database/connection.py
class DatabaseManager:
    """
    Database connection and query management for maker8
    """
    def __init__(self):
        self.connection_string = "postgresql://vubakninh:123456@10.113.213.9:6432/maker8"
        
    def search_related_articles(self, keywords: List[str]) -> List[Article]:
        """Search for related articles using keywords"""
        pass
        
    def get_article_images(self, article_ids: List[int]) -> List[ImageAsset]:
        """Retrieve images associated with articles"""
        pass
        
    def search_by_embedding(self, embedding: List[float]) -> List[Article]:
        """Future: Search using text embeddings"""
        pass
```

#### 3. AI Processing Layer
```python
# src/ai/llm_client.py - Following EngineX LiteLLM patterns
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx
import structlog

from src.core.config import get_settings

logger = structlog.get_logger(__name__)

@dataclass
class LiteLLMClientConfig:
    """Configuration container for LiteLLM client (consistent with EngineX)."""

    api_base: str
    api_key: str
    model: str
    timeout_seconds: int = 60
    max_tokens: int = 4000
    temperature: float = 0.7
    max_retries: int = 3
    backoff_factor: float = 1.5

    @classmethod
    def from_settings(cls) -> "LiteLLMClientConfig":
        settings = get_settings()
        if not settings.llm_api_base:
            raise ValueError(
                "LLM_API_BASE is required for LiteLLM client (consistent with EngineX/x-neews)"
            )
        if not settings.llm_api_key:
            raise ValueError(
                "LLM_API_KEY is required for LiteLLM client (consistent with EngineX/x-neews)"
            )

        return cls(
            api_base=settings.llm_api_base.rstrip("/"),
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )

class LiteLLMClient:
    """Async client for interacting with LiteLLM-compatible endpoints (following EngineX patterns)."""

    def __init__(self, config: LiteLLMClientConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    headers = {
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Accept": "application/json",
                    }
                    self._client = httpx.AsyncClient(
                        base_url=self.config.api_base,
                        headers=headers,
                        timeout=httpx.Timeout(self.config.timeout_seconds),
                    )
                    logger.info(
                        "nx-editor8 LiteLLM client initialised",
                        base_url=self.config.api_base,
                        model=self.config.model,
                    )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("nx-editor8 LiteLLM client closed")

    async def generate(
        self,
        prompt: str,
        *,
        system_message: str = "You are nx-editor8's AI content processing assistant.",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Submit a prompt and return response text."""

        if not prompt.strip():
            raise ValueError("Prompt must not be empty")

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature or self.config.temperature,
        }
        
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        elif self.config.max_tokens:
            payload["max_tokens"] = self.config.max_tokens

        attempt = 0
        wait_time = 0.5
        client = await self._get_client()

        while True:
            attempt += 1
            try:
                response = await client.post("/chat/completions", json=payload)
                if response.status_code == 429:
                    raise httpx.HTTPStatusError(
                        "Rate limited", request=response.request, response=response
                    )
                response.raise_for_status()
                data = response.json()

                logger.info(
                    "LiteLLM response received",
                    model=self.config.model,
                    attempt=attempt,
                )

                choices = data.get("choices", [])
                if not choices:
                    raise RuntimeError("LiteLLM response missing choices")

                message = choices[0].get("message") or {}
                content = message.get("content")
                if not content:
                    raise RuntimeError("LiteLLM response missing content")

                return content

            except (
                httpx.TimeoutException,
                httpx.HTTPStatusError,
                httpx.NetworkError,
            ) as exc:
                if attempt >= self.config.max_retries:
                    logger.error(
                        "LiteLLM invocation failed",
                        attempt=attempt,
                        error=str(exc),
                        status_code=getattr(exc, "response", None)
                        and exc.response.status_code,
                    )
                    raise RuntimeError("LiteLLM request failed") from exc

                wait = wait_time * self.config.backoff_factor ** (attempt - 1)
                logger.warning(
                    "LiteLLM invocation retry",
                    attempt=attempt,
                    wait_seconds=wait,
                    error=str(exc),
                )
                await asyncio.sleep(wait)
            except httpx.HTTPError as exc:
                logger.error(
                    "LiteLLM unexpected HTTP error",
                    error=str(exc),
                    attempt=attempt,
                )
                raise RuntimeError("LiteLLM request failed") from exc

# Singleton client instance (following EngineX patterns)
_cached_client: Optional[LiteLLMClient] = None

def get_llm_client() -> LiteLLMClient:
    """Return singleton LiteLLM client instance."""
    global _cached_client

    if _cached_client is None:
        config = LiteLLMClientConfig.from_settings()
        _cached_client = LiteLLMClient(config)

    return _cached_client

# src/ai/workflows.py - Updated with LiteLLM integration
class ContentProcessingWorkflow:
    """LangGraph workflow for comprehensive content processing"""
    
    def __init__(self):
        self.llm_client = get_llm_client()  # Use EngineX-style LiteLLM client
        self.db_manager = DatabaseManager()
        self.workflow = self._build_workflow()
        
    def _build_workflow(self) -> StateGraph:
        """Build the content processing workflow graph"""
        workflow = StateGraph(ContentState)
        
        # Add processing nodes
        workflow.add_node("verify_requirements", self._verify_requirements)
        workflow.add_node("search_related_content", self._search_related_content)
        workflow.add_node("analyze_content", self._analyze_content)
        workflow.add_node("enhance_content", self._enhance_content)
        workflow.add_node("generate_scenes", self._generate_scenes)
        workflow.add_node("format_and_publish", self._format_and_publish)
        workflow.add_node("handle_retry", self._handle_retry)
        
        # Define workflow edges
        workflow.add_edge("verify_requirements", "search_related_content")
        workflow.add_edge("search_related_content", "analyze_content")
        workflow.add_edge("analyze_content", "enhance_content")
        workflow.add_edge("enhance_content", "generate_scenes")
        workflow.add_edge("generate_scenes", "format_and_publish")
        workflow.add_edge("format_and_publish", END)
        
        # Add conditional edge for retry logic
        workflow.add_conditional_edges(
            "verify_requirements",
            self._should_retry,
            {
                "retry": "handle_retry",
                "continue": "search_related_content"
            }
        )
        workflow.add_edge("handle_retry", "verify_requirements")
        
        # Set entry point
        workflow.set_entry_point("verify_requirements")
        
        return workflow.compile()
    
    def _should_retry(self, state: ContentState) -> str:
        """Determine if content should be retried or processed"""
        if state.get("retry_needed", False):
            # Check retry count to prevent infinite loops
            retry_count = state.get("retry_count", 0)
            max_retries = state.get("max_retries", 3)
            
            if retry_count < max_retries:
                return "retry"
            else:
                # Max retries reached, skip to error handling
                state["processing_error"] = "Max retries exceeded for requirements verification"
                return "continue"  # Continue but mark as error
        return "continue"
    
    async def _handle_retry(self, state: ContentState) -> ContentState:
        """Handle retry logic for failed requirements verification"""
        retry_count = state.get("retry_count", 0) + 1
        state["retry_count"] = retry_count
        
        # Use LLM to enhance content to meet requirements
        if state.get("requirements_verification", {}).get("validation_errors"):
            errors = state["requirements_verification"]["validation_errors"]
            content = state["original_message"].text_content
            
            enhancement_prompt = self._load_prompt_template("content_enhancement", {
                "content": content,
                "validation_errors": "\n".join(errors),
                "requirements": state.get("processing_requirements", {})
            })
            
            try:
                enhanced_content = await self.llm_client.generate(
                    prompt=enhancement_prompt,
                    system_message="You are nx-editor8's content enhancement assistant. Enhance the content to meet the specified requirements.",
                    temperature=0.3
                )
                
                # Update the content in the message
                state["original_message"].text_content = enhanced_content
                state["retry_needed"] = False  # Reset retry flag
                
                logger.info(f"Content enhanced for retry #{retry_count}")
                
            except Exception as e:
                logger.error(f"Failed to enhance content for retry: {e}")
                state["processing_error"] = f"Content enhancement failed: {e}"
                
        return state
        
    async def _verify_requirements(self, state: ContentState) -> ContentState:
        """Verify input message meets processing requirements"""
        message = state["original_message"]
        requirements = state.get("processing_requirements", {})
        
        verification_result = {
            "meets_requirements": True,
            "validation_errors": [],
            "retry_needed": False
        }
        
        # Check minimum word count
        min_words = requirements.get("min_word_count", 50)
        word_count = len(message.text_content.split())
        if word_count < min_words:
            verification_result["meets_requirements"] = False
            verification_result["validation_errors"].append(
                f"Content too short: {word_count} words, minimum required: {min_words}"
            )
        
        # Check maximum word count
        max_words = requirements.get("max_word_count", 2000)
        if word_count > max_words:
            verification_result["meets_requirements"] = False
            verification_result["validation_errors"].append(
                f"Content too long: {word_count} words, maximum allowed: {max_words}"
            )
        
        # Check minimum character count
        min_chars = requirements.get("min_char_count", 200)
        char_count = len(message.text_content)
        if char_count < min_chars:
            verification_result["meets_requirements"] = False
            verification_result["validation_errors"].append(
                f"Content too short: {char_count} characters, minimum required: {min_chars}"
            )
        
        # Check content format requirements
        required_format = requirements.get("content_format", "text")
        if required_format == "structured" and not self._is_structured_content(message.text_content):
            verification_result["meets_requirements"] = False
            verification_result["validation_errors"].append(
                "Content does not meet structured format requirements"
            )
        
        # Check language requirements
        required_language = requirements.get("language", None)
        if required_language and not self._detect_language(message.text_content) == required_language:
            verification_result["meets_requirements"] = False
            verification_result["validation_errors"].append(
                f"Content language does not match required language: {required_language}"
            )
        
        state["requirements_verification"] = verification_result
        
        # If requirements not met, mark for retry
        if not verification_result["meets_requirements"]:
            state["retry_needed"] = True
            state["retry_reason"] = "Requirements verification failed"
            
        return state
    
    def _is_structured_content(self, content: str) -> bool:
        """Check if content meets structured format requirements"""
        # Basic structured content detection (can be enhanced)
        has_headings = any(line.strip().startswith('#') for line in content.split('\n'))
        has_bullet_points = any(line.strip().startswith(('*', '-', '•')) for line in content.split('\n'))
        has_paragraphs = len([p for p in content.split('\n\n') if p.strip()]) >= 2
        
        return has_headings or has_bullet_points or has_paragraphs
    
    def _detect_language(self, content: str) -> str:
        """Detect content language (placeholder implementation)"""
        # Simple language detection - can be enhanced with proper language detection library
        vietnamese_chars = any(char in content for char in ['ă', 'â', 'đ', 'ê', 'ô', 'ơ', 'ư'])
        if vietnamese_chars:
            return "vi"
        return "en"

    async def _analyze_content(self, state: ContentState) -> ContentState:
        """Analyze content using LiteLLM (following EngineX patterns)"""
        # Skip analysis if requirements verification failed
        if state.get("retry_needed", False):
            return state
            
        content = state["original_message"].text_content
        related_content = "\n".join([article.summary for article in state["related_articles"]])
        
        # Load prompt template from file (following EngineX prompts structure)
        prompt = self._load_prompt_template("content_analysis", {
            "content": content,
            "related_content": related_content
        })
        
        try:
            analysis_result = await self.llm_client.generate(
                prompt=prompt,
                system_message="You are nx-editor8's content analysis assistant specialized in video content creation.",
                temperature=0.2
            )
            
            # Parse JSON response
            state["content_analysis"] = json.loads(analysis_result)
        except json.JSONDecodeError:
            # Fallback to raw analysis if JSON parsing fails
            state["content_analysis"] = {"raw_analysis": analysis_result}
            
        return state
        
    def _load_prompt_template(self, template_name: str, variables: dict) -> str:
        """Load and format prompt template (following EngineX prompts patterns)"""
        template_path = f"prompts/{template_name}.md"
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            # Simple template variable substitution
            for key, value in variables.items():
                template = template.replace(f"{{{{{key}}}}}", str(value))
                
            return template
        except FileNotFoundError:
            # Fallback to inline prompt if template file not found
            return f"Analyze the following content for video creation:\n\nContent: {variables.get('content', '')}"
```

#### 4. Content Generation Layer
```python
# src/content/scene_generator.py
class SceneGenerator:
    """
    Generate nx-maker8 compatible scene arrays
    """
    def __init__(self):
        self.scene_types = ["title_scene", "text_scene", "image_scene", "outro_scene"]
        
    def generate_scenes(self, content: ProcessedContent) -> List[Scene]:
        """Convert processed content to nx-maker8 scenes"""
        pass
        
    def create_title_scene(self, title: str) -> Scene:
        """Create title scene with styling"""
        pass
        
    def create_content_scenes(self, content: str, images: List[str]) -> List[Scene]:
        """Create text and image scenes from content"""
        pass
```
#### 5. Kafka Publishing Layer
```python
# src/kafka/publisher.py
class NXMaker8Publisher:
    """
    Kafka publisher for sending formatted content to nx-maker8
    """
    def __init__(self):
        self.bootstrap_servers = "10.113.213.1:9094"
        self.output_topic = "video_input_topic"  # nx-maker8 input topic
        self.security_protocol = "SASL_PLAINTEXT"
        self.sasl_mechanism = "PLAIN"
        self.sasl_username = "client"
        self.sasl_password = "client-secret"
        
    def publish_video_request(self, nx_maker8_input: dict) -> bool:
        """Publish formatted video request to nx-maker8 topic"""
        try:
            producer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'security_protocol': self.security_protocol,
                'sasl_mechanism': self.sasl_mechanism,
                'sasl_plain_username': self.sasl_username,
                'sasl_plain_password': self.sasl_password,
                'value_serializer': lambda x: json.dumps(x).encode('utf-8')
            }
            
            producer = KafkaProducer(**producer_config)
            
            # Validate message format before publishing
            if self.validate_message_format(nx_maker8_input):
                producer.send(self.output_topic, nx_maker8_input)
                producer.flush()  # Ensure message is sent
                return True
            else:
                logger.error("Message validation failed for nx-maker8 format")
                return False
                
        except Exception as e:
            logger.error(f"Failed to publish to Kafka: {e}")
            return False
        finally:
            producer.close()
        
    def validate_message_format(self, data: dict) -> bool:
        """Validate message matches nx-maker8 expected format"""
        # Based on nx-maker8 MessageValidatorProcessor requirements
        required_fields = [
            "title", "category", "description", "keywords",
            "channel_name", "channel_id", "tts_provider", 
            "video_site", "scenes"
        ]
        
        # Check required fields
        if not all(field in data for field in required_fields):
            return False
            
        # Validate TTS provider
        if data.get("tts_provider", "").lower() not in ["googletts", "elevenlabs"]:
            return False
            
        # Validate video site
        if data.get("video_site", "").lower() not in ["youtube", "tiktok", "facebook"]:
            return False
            
        # Validate scenes array
        scenes = data.get("scenes", [])
        if not isinstance(scenes, list) or len(scenes) == 0:
            return False
            
        # Validate each scene
        for scene in scenes:
            if not isinstance(scene, dict):
                return False
            if "type" not in scene or "text" not in scene:
                return False
            if scene["type"] not in ["title_scene", "text_scene", "image_scene", "outro_scene"]:
                return False
                
        return True
```

## 📋 Data Models

### Input Message Format
```python
@dataclass
class ContentMessage:
    """Kafka message format for content input"""
    topic: str              # "youtube", "tiktok", "facebook"
    channel: str            # Channel identifier  
    text_content: str       # Main content text
    metadata: MessageMetadata
    
@dataclass 
class MessageMetadata:
    source: str             # "youtube", "tiktok", "facebook"
    timestamp: datetime
    channel_id: str
    content_id: Optional[str]
    author: Optional[str]
    tags: List[str] = field(default_factory=list)
```

### Database Models
```python
class Article(Base):
    """Article model for maker8 database"""
    __tablename__ = "tbl_articles"
    
    id: int = Column(Integer, primary_key=True)
    title: str = Column(String)
    content: str = Column(Text)
    summary: str = Column(Text)
    keywords: str = Column(String)
    created_at: datetime = Column(DateTime)
    
    # Future embedding field
    embedding: Optional[List[float]] = Column(JSON, nullable=True)

class ImageAsset(Base):
    """Image asset model"""
    __tablename__ = "tbl_images"
    
    id: int = Column(Integer, primary_key=True)
    article_id: int = Column(Integer, ForeignKey("tbl_articles.id"))
    url: str = Column(String)
    alt_text: str = Column(String)
    is_accessible: bool = Column(Boolean, default=True)
```

### Output Format
```python
@dataclass
class NXMaker8Input:
    """Output format for nx-maker8 (published to video_input_topic)"""
    title: str
    category: str
    description: str
    keywords: str
    channel_name: str
    channel_id: str
    tts_provider: str = "googletts"
    video_site: str = "youtube"  # "youtube", "tiktok", "facebook"
    storage: StorageConfig = field(default_factory=lambda: StorageConfig())
    scenes: List[Scene] = field(default_factory=list)
    settings: VideoSettings = field(default_factory=lambda: VideoSettings())

@dataclass
class Scene:
    type: str               # "title_scene", "text_scene", "image_scene", "outro_scene"
    text: str               # Required for all scene types
    image_path: Optional[str] = None    # Required for image_scene
    background_color: Optional[str] = None
    text_color: Optional[str] = None

@dataclass
class StorageConfig:
    provider: str = "dropbox"  # "dropbox" or "gdrive"
    folder_path: str = "/nx-maker8/generated"

@dataclass  
class VideoSettings:
    resolution: str = "1920x1080"
    fps: int = 30
    format: str = "mp4"
```

## 🔧 Configuration Architecture

### Environment Configuration
```python
# src/config.py - Updated following EngineX LLM patterns
import os
from typing import Optional
from pydantic import BaseSettings, Field

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
            "KAFKA_BOOTSTRAP_SERVERS", "NX_EDITOR8_KAFKA_BOOTSTRAP_SERVERS", "10.113.213.1:9094"
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
    input_topics: list = Field(
        default_factory=lambda: _get_env_with_fallback(
            "KAFKA_INPUT_TOPICS", "NX_EDITOR8_INPUT_TOPICS", 
            "youtube_content,tiktok_content,facebook_content"
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
            "DATABASE_URL", "NX_EDITOR8_DATABASE_URL", 
            "postgresql://vubakninh:123456@10.113.213.9:6432/maker8"
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
        description="LiteLLM-compatible model name for content processing"
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
            _get_env_with_fallback("MAX_WORD_COUNT", "NX_EDITOR8_MAX_WORD_COUNT", "2000")
        )
    )
    min_char_count: int = Field(
        default_factory=lambda: int(
            _get_env_with_fallback("MIN_CHAR_COUNT", "NX_EDITOR8_MIN_CHAR_COUNT", "200")
        )
    )
    max_char_count: int = Field(
        default_factory=lambda: int(
            _get_env_with_fallback("MAX_CHAR_COUNT", "NX_EDITOR8_MAX_CHAR_COUNT", "10000")
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
            _get_env_with_fallback("MAX_CONTENT_RETRIES", "NX_EDITOR8_MAX_CONTENT_RETRIES", "3")
        )
    )
    
    # Logging
    log_level: str = Field(
        default_factory=lambda: _get_env_with_fallback(
            "LOG_LEVEL", "NX_EDITOR8_LOG_LEVEL", "INFO"
        )
    )

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

## 🎯 Processing Workflow Design

### LangGraph Workflow Definition
```python
# Workflow States
class ContentState(TypedDict):
    message: ContentMessage
    processing_requirements: Dict[str, Any]  # Requirements for content processing
    requirements_verification: Dict[str, Any]  # Results of requirements verification
    retry_needed: bool  # Flag indicating if content needs retry
    retry_count: int  # Number of retry attempts
    retry_reason: str  # Reason for retry
    max_retries: int  # Maximum allowed retries
    processing_error: Optional[str]  # Error message if processing fails
    related_articles: List[Article]
    images: List[ImageAsset] 
    analyzed_content: Dict[str, Any]
    enhanced_content: str
    generated_scenes: List[Scene]
    final_output: NXMaker8Input

# Workflow Implementation
def build_processing_workflow():
    workflow = StateGraph(ContentState)
    
    # Add processing nodes
    workflow.add_node("validate_input", validate_message)
    workflow.add_node("search_database", search_related_content)
    workflow.add_node("analyze_content", analyze_with_llm)
    workflow.add_node("enhance_content", enhance_with_ai)
    workflow.add_node("generate_scenes", create_scene_array)
    workflow.add_node("format_output", format_for_nx_maker8)
    
    # Define workflow edges
    workflow.add_edge("validate_input", "search_database")
    workflow.add_edge("search_database", "analyze_content")
    workflow.add_edge("analyze_content", "enhance_content")
    workflow.add_edge("enhance_content", "generate_scenes")
    workflow.add_edge("generate_scenes", "format_output")
    
    # Set entry and exit points
    workflow.set_entry_point("validate_input")
    workflow.set_finish_point("format_output")
    
    return workflow.compile()
```

## 🚀 Deployment Architecture

### Docker Configuration
```yaml
# docker-compose.yml
version: '3.8'
services:
  nx-editor8:
    build: .
    environment:
      - KAFKA_BOOTSTRAP_SERVERS=10.113.213.1:9094
      - DATABASE_URL=postgresql://vubakninh:123456@10.113.213.9:6432/maker8
      - LLM_API_KEY=${LLM_API_KEY}
    depends_on:
      - kafka
      - postgres
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    networks:
      - xprojects-network

networks:
  xprojects-network:
    external: true
```

### Service Integration
```python
# main.py - Updated entry point
class NXEditor8Service:
    def __init__(self):
        self.kafka_consumer = ContentKafkaConsumer()
        self.db_manager = DatabaseManager()
        self.ai_workflow = ContentProcessingWorkflow()
        self.scene_generator = SceneGenerator()
        
    async def start_processing(self):
        """Main processing loop"""
        async for message in self.kafka_consumer.consume_messages():
            try:
                # Process through AI workflow (includes publishing to Kafka)
                result = await self.ai_workflow.process_content(message)
                
                # Log successful processing
                logger.info(f"Successfully processed and published message from {message.metadata.source}")
                
            except Exception as e:
                logger.error(f"Processing failed: {e}")
                await self.handle_error(message, e)
```

## 📊 Performance & Scalability

### Performance Targets
- **Message Processing**: <30 seconds per message
- **Database Queries**: <5 seconds average response time
- **LLM API Calls**: <10 seconds per request
- **End-to-End Latency**: <60 seconds total

### Scalability Considerations
- **Horizontal Scaling**: Multiple consumer instances with different partition assignments
- **Database Connection Pooling**: SQLAlchemy connection pool with 10-20 connections
- **LLM Request Batching**: Batch multiple content pieces when possible
- **Caching Strategy**: Redis cache for frequent database queries and LLM responses

### Resource Requirements
```yaml
# Resource allocation
CPU: 2-4 cores per instance
Memory: 4-8 GB RAM
Storage: 20 GB for logs and temporary data
Network: High bandwidth for Kafka and API calls
```

## 🔒 Security & Monitoring

### Security Measures
- **Kafka Authentication**: SASL_PLAINTEXT with username/password
- **Database Security**: Connection string with credentials in environment variables
- **API Security**: LLM API keys stored securely
- **Input Validation**: Comprehensive message validation and sanitization

### Monitoring Strategy
```python
# Metrics to track
class ProcessingMetrics:
    messages_processed_total: Counter
    processing_duration_seconds: Histogram
    database_query_duration: Histogram
    llm_api_duration: Histogram
    errors_total: Counter
    scenes_generated_total: Counter
```

### Logging Architecture
```python
# Enhanced logging with structured data
class StructuredLogger:
    def log_processing_start(self, message_id: str, channel: str):
        logger.info("Processing started", extra={
            "message_id": message_id,
            "channel": channel,
            "stage": "start"
        })
        
    def log_database_query(self, query_type: str, duration: float, results: int):
        logger.info("Database query completed", extra={
            "query_type": query_type,
            "duration_seconds": duration,
            "results_count": results
        })
```

## 🔄 Error Handling & Recovery

### Error Categories
1. **Input Errors**: Invalid message format, missing required fields
2. **Database Errors**: Connection failures, query timeouts
3. **LLM Errors**: API rate limits, service unavailability  
4. **Processing Errors**: Content generation failures, format errors

### Recovery Strategies
```python
class ErrorHandler:
    def handle_processing_error(self, error: Exception, message: ContentMessage):
        if isinstance(error, DatabaseError):
            # Retry with exponential backoff
            return self.retry_with_backoff(self.process_message, message)
        elif isinstance(error, LLMAPIError):
            # Use fallback content generation
            return self.generate_fallback_content(message)
        else:
            # Log and move to dead letter queue
            self.send_to_dlq(message, error)
```

---

This architecture provides a robust, scalable foundation for the nx-editor8 refactoring while integrating seamlessly with the existing xProjects ecosystem. The design emphasizes modularity, testability, and maintainability while meeting all the specified requirements for Kafka integration, database connectivity, and AI-powered content generation.