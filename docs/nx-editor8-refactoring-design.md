# NX-Editor8 Refactoring Technical Design
**Date**: 2025-10-03  
**Author**: AI Assistant  
**Status**: Draft

## 🎯 Refactoring Objectives

Transform nx-editor8 from a RabbitMQ-based article processor to a comprehensive Kafka-based content pipeline that:
1. Consumes multi-channel content from Kafka topics
2. Integrates with maker8 database for content enrichment
3. Uses LangChain/LangGraph for AI-powered content processing
4. Generates nx-maker8 compatible video input with scene arrays

## 🔄 Migration Strategy

### Current vs Target State

| Component | Current State | Target State | Migration Approach |
|-----------|---------------|--------------|-------------------|
| **Message Bus** | RabbitMQ with pika | Kafka with kafka-python | Replace rabbitmq_processor.py with kafka consumer |
| **Content Source** | Single queue input | Multi-channel topics (youtube, tiktok, facebook) | Add topic routing and channel-specific processing |
| **Processing** | Simple pipeline | AI-enhanced workflow with LangGraph | Wrap existing processors in LangGraph nodes |
| **Database** | No database integration | maker8 PostgreSQL with SQLAlchemy | Add database layer for content search and images |
| **AI Integration** | Basic text processing | LLM-powered content generation | Add langchain/langgraph with prompt templates |
| **Output Format** | Generic JSON | nx-maker8 scenes array | Transform output to match video generation requirements |

## 📋 Detailed Implementation Plan

### Step 1: Infrastructure Migration (Day 1)

#### 1.1 Kafka Consumer Implementation
```python
# src/kafka/consumer.py
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import json
from typing import Iterator, Dict, Any
from ..logger import logger

class NXEditor8KafkaConsumer:
    """
    Kafka consumer implementing xProjects patterns from ai_broker
    """
    def __init__(self):
        self.bootstrap_servers = "10.113.213.1:9094"
        self.consumer_group = "nx_editor8_consumer"
        self.topics = ["youtube_content", "tiktok_content", "facebook_content"]
        
        # Kafka configuration following xProjects standards
        self.consumer_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'group_id': self.consumer_group,
            'security_protocol': 'SASL_PLAINTEXT',
            'sasl_mechanism': 'PLAIN',
            'sasl_plain_username': 'client',
            'sasl_plain_password': 'client-secret',
            'auto_offset_reset': 'latest',
            'enable_auto_commit': True,
            'session_timeout_ms': 30000,
            'max_poll_interval_ms': 300000,
            'value_deserializer': lambda x: json.loads(x.decode('utf-8'))
        }
        
    def start_consuming(self) -> Iterator[ContentMessage]:
        """Start consuming messages from configured topics"""
        consumer = KafkaConsumer(**self.consumer_config)
        consumer.subscribe(self.topics)
        
        logger.info(f"Started consuming from topics: {self.topics}")
        
        try:
            for message in consumer:
                try:
                    content_message = self._parse_message(message)
                    yield content_message
                except Exception as e:
                    logger.error(f"Error parsing message: {e}")
                    continue
        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
            raise
        finally:
            consumer.close()
            
    def _parse_message(self, kafka_message) -> ContentMessage:
        """Parse Kafka message into ContentMessage object"""
        data = kafka_message.value
        
        return ContentMessage(
            topic=kafka_message.topic,
            channel=data.get('channel', ''),
            text_content=data.get('text_content', ''),
            metadata=MessageMetadata(
                source=data.get('source', kafka_message.topic.replace('_content', '')),
                timestamp=datetime.fromtimestamp(kafka_message.timestamp / 1000),
                channel_id=data.get('channel_id', ''),
                content_id=data.get('content_id'),
                author=data.get('author'),
                tags=data.get('tags', [])
            )
        )
```

#### 1.2 Database Integration Setup
```python
# src/database/connection.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional
import os

Base = declarative_base()

class DatabaseManager:
    """Database connection and query manager for maker8"""
    
    def __init__(self):
        self.connection_string = "postgresql://vubakninh:123456@10.113.213.9:6432/maker8"
        self.engine = create_engine(self.connection_string, pool_size=10, max_overflow=20)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
        
    def search_related_articles(self, keywords: List[str], limit: int = 10) -> List[Article]:
        """Search for articles related to given keywords"""
        with self.get_session() as session:
            # Simple keyword search - will be enhanced with embeddings later
            keyword_filter = ' | '.join(keywords)
            articles = session.query(Article).filter(
                Article.content.op('@@')(func.to_tsquery(keyword_filter))
            ).limit(limit).all()
            return articles
            
    def get_article_images(self, article_ids: List[int]) -> List[ImageAsset]:
        """Get images associated with specific articles"""
        with self.get_session() as session:
            images = session.query(ImageAsset).filter(
                ImageAsset.article_id.in_(article_ids)
            ).all()
            return images

# Database Models
class Article(Base):
    __tablename__ = "tbl_articles"
    
    id = Column(Integer, primary_key=True)
    title = Column(String)
    content = Column(Text)
    summary = Column(Text)
    keywords = Column(String)
    created_at = Column(DateTime)
    # Future: embedding field for semantic search
    embedding = Column(JSON, nullable=True)

class ImageAsset(Base):
    __tablename__ = "tbl_images"
    
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer)
    url = Column(String)
    alt_text = Column(String)
    is_accessible = Column(Boolean, default=True)
    created_at = Column(DateTime)
```

### Step 2: AI Integration Layer (Days 2-3)

#### 2.1 LangChain/LangGraph Integration
```python
# src/ai/workflows.py
from langgraph import StateGraph, END
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from typing import TypedDict, Dict, Any, List
from ..database.connection import DatabaseManager
from ..logger import logger

class ContentState(TypedDict):
    """State object for content processing workflow"""
    original_message: ContentMessage
    related_articles: List[Article]
    images: List[ImageAsset]
    content_analysis: Dict[str, Any]
    enhanced_content: str
    generated_scenes: List[Dict[str, Any]]
    final_output: Dict[str, Any]

class ContentProcessingWorkflow:
    """LangGraph workflow for comprehensive content processing"""
    
    def __init__(self):
        self.llm = OpenAI(temperature=0.7)
        self.db_manager = DatabaseManager()
        self.workflow = self._build_workflow()
        
    def _build_workflow(self) -> StateGraph:
        """Build the content processing workflow graph"""
        workflow = StateGraph(ContentState)
        
        # Add processing nodes
        workflow.add_node("search_related_content", self._search_related_content)
        workflow.add_node("analyze_content", self._analyze_content)
        workflow.add_node("enhance_content", self._enhance_content)
        workflow.add_node("generate_scenes", self._generate_scenes)
        workflow.add_node("format_output", self._format_output)
        
        # Define workflow edges
        workflow.add_edge("search_related_content", "analyze_content")
        workflow.add_edge("analyze_content", "enhance_content")
        workflow.add_edge("enhance_content", "generate_scenes")
        workflow.add_edge("generate_scenes", "format_output")
        workflow.add_edge("format_output", END)
        
        # Set entry point
        workflow.set_entry_point("search_related_content")
        
        return workflow.compile()
        
    def _search_related_content(self, state: ContentState) -> ContentState:
        """Search for related articles and images"""
        message = state["original_message"]
        
        # Extract keywords from content
        keywords = self._extract_keywords(message.text_content)
        
        # Search database for related articles
        related_articles = self.db_manager.search_related_articles(keywords)
        
        # Get images from related articles
        article_ids = [article.id for article in related_articles]
        images = self.db_manager.get_article_images(article_ids)
        
        state["related_articles"] = related_articles
        state["images"] = images
        
        logger.info(f"Found {len(related_articles)} related articles and {len(images)} images")
        return state
        
    def _analyze_content(self, state: ContentState) -> ContentState:
        """Analyze content using LLM"""
        content = state["original_message"].text_content
        related_content = "\n".join([article.summary for article in state["related_articles"]])
        
        analysis_prompt = PromptTemplate(
            input_variables=["content", "related_content"],
            template="""
            Analyze the following content and provide insights for video creation:
            
            Original Content: {content}
            
            Related Context: {related_content}
            
            Please provide:
            1. Main topics and themes
            2. Key points to highlight
            3. Suggested video structure
            4. Target audience insights
            5. Content category classification
            
            Format your response as JSON with the above categories as keys.
            """
        )
        
        analysis_result = self.llm(analysis_prompt.format(
            content=content,
            related_content=related_content
        ))
        
        try:
            state["content_analysis"] = json.loads(analysis_result)
        except json.JSONDecodeError:
            state["content_analysis"] = {"raw_analysis": analysis_result}
            
        return state
        
    def _enhance_content(self, state: ContentState) -> ContentState:
        """Enhance content for video script generation"""
        original_content = state["original_message"].text_content
        analysis = state["content_analysis"]
        
        enhancement_prompt = PromptTemplate(
            input_variables=["content", "analysis"],
            template="""
            Create an enhanced video script based on the original content and analysis:
            
            Original Content: {content}
            
            Content Analysis: {analysis}
            
            Please create a comprehensive script that:
            1. Has a compelling introduction
            2. Covers all key points clearly
            3. Includes smooth transitions between topics
            4. Has a strong conclusion
            5. Is suitable for video narration
            6. Is approximately 500-800 words
            
            Format as a continuous script suitable for text-to-speech conversion.
            """
        )
        
        enhanced_content = self.llm(enhancement_prompt.format(
            content=original_content,
            analysis=json.dumps(analysis)
        ))
        
        state["enhanced_content"] = enhanced_content
        return state
        
    def _generate_scenes(self, state: ContentState) -> List[Dict[str, Any]]:
        """Generate scene array for nx-maker8"""
        enhanced_content = state["enhanced_content"]
        images = state["images"]
        analysis = state["content_analysis"]
        
        # Create scenes based on enhanced content
        scenes = []
        
        # Title scene
        title = analysis.get("main_topics", ["Video Title"])[0] if analysis.get("main_topics") else "Video Title"
        scenes.append({
            "type": "title_scene",
            "text": title,
            "background_color": "#1a73e8",
            "text_color": "#ffffff"
        })
        
        # Split content into segments for scenes
        content_segments = self._split_content_into_segments(enhanced_content)
        
        for i, segment in enumerate(content_segments):
            # Alternate between text and image scenes
            if i % 2 == 0:
                scenes.append({
                    "type": "text_scene",
                    "text": segment
                })
            else:
                # Use image if available
                if images and len(images) > (i // 2):
                    image = images[i // 2]
                    scenes.append({
                        "type": "image_scene",
                        "image_path": image.url,
                        "text": segment
                    })
                else:
                    scenes.append({
                        "type": "text_scene",
                        "text": segment
                    })
        
        # Outro scene
        scenes.append({
            "type": "outro_scene",
            "text": "Thanks for watching!",
            "background_color": "#34a853"
        })
        
        state["generated_scenes"] = scenes
        return state
        
    def _format_output(self, state: ContentState) -> ContentState:
        """Format final output for nx-maker8"""
        message = state["original_message"]
        analysis = state["content_analysis"]
        scenes = state["generated_scenes"]
        
        # Extract title from analysis or use default
        title = analysis.get("main_topics", ["Generated Video"])[0] if analysis.get("main_topics") else "Generated Video"
        category = analysis.get("content_category", "General")
        
        final_output = {
            "title": title,
            "category": category,
            "description": f"Generated from {message.metadata.source} content",
            "keywords": ", ".join(analysis.get("main_topics", [])),
            "channel_name": message.channel,
            "channel_id": message.metadata.channel_id,
            "tts_provider": "googletts",
            "video_site": "youtube",
            "storage": {
                "provider": "dropbox",
                "folder_path": "/nx-maker8/generated"
            },
            "scenes": scenes,
            "settings": {
                "resolution": "1920x1080",
                "fps": 30,
                "format": "mp4"
            }
        }
        
        state["final_output"] = final_output
        return state
        
    def process_content(self, message: ContentMessage) -> Dict[str, Any]:
        """Process content message through the complete workflow"""
        initial_state = {
            "original_message": message,
            "related_articles": [],
            "images": [],
            "content_analysis": {},
            "enhanced_content": "",
            "generated_scenes": [],
            "final_output": {}
        }
        
        result = self.workflow.invoke(initial_state)
        return result["final_output"]
```

### Step 3: Integration and Testing (Days 4-5)

#### 3.1 Main Service Integration
```python
# main.py - Updated main entry point
import asyncio
from src.kafka.consumer import NXEditor8KafkaConsumer
from src.ai.workflows import ContentProcessingWorkflow
from src.logger import logger
import json

class NXEditor8Service:
    """Main service orchestrating the content processing pipeline"""
    
    def __init__(self):
        self.kafka_consumer = NXEditor8KafkaConsumer()
        self.ai_workflow = ContentProcessingWorkflow()
        
    async def start_processing(self):
        """Start the main processing loop"""
        logger.info("Starting NX-Editor8 content processing service")
        
        try:
            for message in self.kafka_consumer.start_consuming():
                try:
                    # Process message through AI workflow
                    result = self.ai_workflow.process_content(message)
                    
                    # Log successful processing
                    logger.info(f"Successfully processed message from {message.metadata.source}")
                    
                    # Output result (could be published to another Kafka topic)
                    self._output_result(result)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    self._handle_processing_error(message, e)
                    
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
        except Exception as e:
            logger.error(f"Service error: {e}")
            raise
            
    def _output_result(self, result: Dict[str, Any]):
        """Output processed result (placeholder for Kafka publishing)"""
        # For now, write to file - later publish to Kafka topic
        output_file = f"output_{int(time.time())}.json"
        with open(f"data/{output_file}", 'w') as f:
            json.dump(result, f, indent=2)
        logger.info(f"Result written to {output_file}")
        
    def _handle_processing_error(self, message: ContentMessage, error: Exception):
        """Handle processing errors"""
        error_data = {
            "error": str(error),
            "message_source": message.metadata.source,
            "timestamp": message.metadata.timestamp.isoformat()
        }
        
        # Write error to error queue/file
        with open("logs/processing_errors.jsonl", 'a') as f:
            f.write(json.dumps(error_data) + '\n')

if __name__ == "__main__":
    service = NXEditor8Service()
    asyncio.run(service.start_processing())
```

#### 3.2 Updated Configuration
```python
# src/config.py - Enhanced configuration
import os
from typing import List

class Config:
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "10.113.213.1:9094")
    KAFKA_SECURITY_PROTOCOL = "SASL_PLAINTEXT"
    KAFKA_SASL_MECHANISM = "PLAIN"
    KAFKA_SASL_USERNAME = os.getenv("KAFKA_USERNAME", "client")
    KAFKA_SASL_PASSWORD = os.getenv("KAFKA_PASSWORD", "client-secret")
    KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "nx_editor8_consumer")
    
    # Kafka Topics
    INPUT_TOPICS = ["youtube_content", "tiktok_content", "facebook_content"]
    OUTPUT_TOPIC = "nx_maker8_input"
    
    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://vubakninh:123456@10.113.213.9:6432/maker8")
    
    # AI Configuration
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    LLM_API_KEY = os.getenv("OPENAI_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4000"))
    
    # Processing Configuration
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
    MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    PROCESSING_TIMEOUT = int(os.getenv("PROCESSING_TIMEOUT", "300"))
    
    # Content Generation
    MIN_SCENES = int(os.getenv("MIN_SCENES", "3"))
    MAX_SCENES = int(os.getenv("MAX_SCENES", "10"))
    DEFAULT_VIDEO_RESOLUTION = os.getenv("DEFAULT_VIDEO_RESOLUTION", "1920x1080")
    DEFAULT_VIDEO_FPS = int(os.getenv("DEFAULT_VIDEO_FPS", "30"))
```

### Step 4: Testing and Validation (Days 6-7)

#### 4.1 Unit Tests
```python
# tests/test_kafka_consumer.py
import pytest
from unittest.mock import Mock, patch
from src.kafka.consumer import NXEditor8KafkaConsumer

class TestKafkaConsumer:
    def test_consumer_initialization(self):
        consumer = NXEditor8KafkaConsumer()
        assert consumer.bootstrap_servers == "10.113.213.1:9094"
        assert consumer.consumer_group == "nx_editor8_consumer"
        
    @patch('src.kafka.consumer.KafkaConsumer')
    def test_message_parsing(self, mock_kafka_consumer):
        consumer = NXEditor8KafkaConsumer()
        
        # Mock Kafka message
        mock_message = Mock()
        mock_message.topic = "youtube_content"
        mock_message.value = {
            "channel": "test_channel",
            "text_content": "Test content",
            "source": "youtube"
        }
        mock_message.timestamp = 1696320000000
        
        content_message = consumer._parse_message(mock_message)
        
        assert content_message.topic == "youtube_content"
        assert content_message.channel == "test_channel"
        assert content_message.text_content == "Test content"
```

#### 4.2 Integration Tests
```python
# tests/test_integration.py
import pytest
from src.kafka.consumer import ContentMessage, MessageMetadata
from src.ai.workflows import ContentProcessingWorkflow
from datetime import datetime

class TestIntegration:
    def test_end_to_end_processing(self):
        # Create test message
        test_message = ContentMessage(
            topic="youtube_content",
            channel="test_channel",
            text_content="This is a test video about cloud computing and its benefits.",
            metadata=MessageMetadata(
                source="youtube",
                timestamp=datetime.now(),
                channel_id="UC123456",
                content_id="video123"
            )
        )
        
        # Process through workflow
        workflow = ContentProcessingWorkflow()
        result = workflow.process_content(test_message)
        
        # Validate output format
        assert "title" in result
        assert "scenes" in result
        assert "settings" in result
        assert len(result["scenes"]) >= 3  # Minimum scenes
        
    def test_scene_generation(self):
        # Test that scenes are properly formatted for nx-maker8
        workflow = ContentProcessingWorkflow()
        # Add specific scene generation tests
```

## 🚀 Deployment Strategy

### Environment Setup
```bash
# .env.example
KAFKA_BOOTSTRAP_SERVERS=10.113.213.1:9094
KAFKA_USERNAME=client
KAFKA_PASSWORD=client-secret
KAFKA_CONSUMER_GROUP=nx_editor8_consumer

DATABASE_URL=postgresql://vubakninh:123456@10.113.213.9:6432/maker8

OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-3.5-turbo
LLM_MAX_TOKENS=4000

LOG_LEVEL=INFO
BATCH_SIZE=10
PROCESSING_TIMEOUT=300
```

### Docker Configuration
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose health check port
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]
```

### Requirements Update
```txt
# requirements.txt - additions for refactoring
langchain==0.1.0
langgraph==0.0.40
psycopg2-binary==2.9.7
kafka-python==2.0.2
sqlalchemy==2.0.21
openai==1.3.0
asyncio==3.4.3

# Keep existing requirements
certifi==2025.1.31
charset-normalizer==3.4.1
click==8.1.8
idna==3.10
lxml==5.3.1
python-dotenv==1.0.1
PyYAML==6.0.2
requests==2.32.3
urllib3==2.3.0
pillow==11.1.0
duckduckgo_search==7.5.0
yt-dlp==2024.3.10
```

## 📊 Success Criteria

### Functional Requirements ✅
- [x] Kafka integration with multi-topic support
- [x] Database connectivity to maker8
- [x] LangChain/LangGraph AI workflow
- [x] nx-maker8 compatible output format
- [x] Image search and integration
- [x] Error handling and logging

### Performance Requirements 🎯
- Message processing: <30 seconds per message
- Database queries: <5 seconds average
- LLM API calls: <10 seconds per request
- End-to-end latency: <60 seconds total

### Quality Requirements 📈
- 95% successful processing rate
- 90% image retrieval success
- Comprehensive error logging
- Unit test coverage >80%

---

This technical design provides a complete roadmap for refactoring nx-editor8 into a modern, AI-powered content processing pipeline that integrates seamlessly with the xProjects ecosystem while meeting all specified requirements for Kafka integration, database connectivity, and nx-maker8 compatibility.