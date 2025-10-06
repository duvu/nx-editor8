# NX-Editor8 Kafka Integration Plan
**Date**: 2025-10-04  
**Focus**: Kafka-to-Kafka pipeline for content processing and video generation  

## 🎯 Updated Architecture: Kafka-Centric Pipeline

Based on nx-maker8 analysis, nx-editor8 should function as a Kafka-to-Kafka processor:

```
Input Topics          nx-editor8 Pipeline          Output Topic           nx-maker8
┌─────────────────┐   ┌─────────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│youtube_content  │──▶│ 1. Content Analysis │──▶│video_input_topic│──▶│Video Generation │
│tiktok_content   │   │ 2. AI Enhancement   │   │                 │   │& Publishing     │
│facebook_content │   │ 3. Scene Generation │   │                 │   │                 │
└─────────────────┘   │ 4. Format Validation│   │                 │   │                 │
                      │ 5. Kafka Publishing │   │                 │   │                 │
                      └─────────────────────┘   └─────────────────┘   └─────────────────┘
                               │                                               │
                               ▼                                               ▼
                      ┌─────────────────────┐                       ┌─────────────────┐
                      │   maker8 DB         │                       │video_output_topic│
                      │ • Article Content   │                       │ • Video Results │
                      │ • Image Assets      │                       │ • Upload Status │
                      │ • Text Embeddings   │                       │ • Publishing    │
                      └─────────────────────┘                       └─────────────────┘
```

## 📋 Key Integration Points

### 1. Input Topics (Consuming)
- **youtube_content**: Content from YouTube channels
- **tiktok_content**: Content from TikTok channels  
- **facebook_content**: Content from Facebook pages
- **Consumer Group**: `nx_editor8_consumer`

### 2. Output Topic (Publishing)
- **video_input_topic**: nx-maker8's input topic
- **Message Format**: Validated nx-maker8 JSON format
- **Publisher Config**: SASL_PLAINTEXT with client credentials

### 3. nx-maker8 Expected Input Format
Based on `nx-maker8/app/pipeline/processors.py` MessageValidatorProcessor:

```json
{
  "title": "AI-Generated Video Title",
  "category": "Technology",  
  "description": "Enhanced content description",
  "keywords": "keyword1, keyword2, keyword3",
  "channel_name": "Source Channel Name",
  "channel_id": "source_channel_id_123", 
  "tts_provider": "googletts",  // "googletts" or "elevenlabs"
  "video_site": "youtube",      // "youtube", "tiktok", "facebook"
  "storage": {
    "provider": "dropbox",      // "dropbox" or "gdrive"
    "folder_path": "/nx-maker8/generated"
  },
  "scenes": [
    {
      "type": "title_scene",
      "text": "Video Title",
      "background_color": "#1a73e8",
      "text_color": "#ffffff"
    },
    {
      "type": "text_scene", 
      "text": "Main content narration text..."
    },
    {
      "type": "image_scene",
      "text": "Content with image",
      "image_path": "https://example.com/image.jpg"
    },
    {
      "type": "outro_scene",
      "text": "Thanks for watching!",
      "background_color": "#34a853"
    }
  ],
  "settings": {
    "resolution": "1920x1080",
    "fps": 30,
    "format": "mp4"
  }
}
```

## 🔧 Implementation Updates

### 1. Kafka Publisher Implementation
```python
# src/kafka/publisher.py
from kafka import KafkaProducer
import json
from ..logger import logger

class NXMaker8Publisher:
    """Publishes processed content to nx-maker8 input topic"""
    
    def __init__(self):
        self.producer_config = {
            'bootstrap_servers': '10.113.213.1:9094',
            'security_protocol': 'SASL_PLAINTEXT',
            'sasl_mechanism': 'PLAIN',
            'sasl_plain_username': 'client',
            'sasl_plain_password': 'client-secret',
            'value_serializer': lambda x: json.dumps(x, ensure_ascii=False).encode('utf-8'),
            'key_serializer': lambda x: x.encode('utf-8') if x else None
        }
        self.output_topic = "video_input_topic"
        
    def publish_video_request(self, video_data: dict) -> bool:
        """Publish video request to nx-maker8"""
        try:
            # Validate format before publishing
            if not self._validate_nx_maker8_format(video_data):
                logger.error("Invalid nx-maker8 format")
                return False
                
            producer = KafkaProducer(**self.producer_config)
            
            # Use channel_id as message key for partitioning
            key = video_data.get('channel_id', 'default')
            
            future = producer.send(self.output_topic, value=video_data, key=key)
            producer.flush(timeout=10)  # Wait for send confirmation
            
            logger.info(f"Published video request: {video_data.get('title', 'Unknown')} to {self.output_topic}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish to Kafka: {e}")
            return False
        finally:
            if 'producer' in locals():
                producer.close()
                
    def _validate_nx_maker8_format(self, data: dict) -> bool:
        """Validate against nx-maker8 MessageValidatorProcessor requirements"""
        required_fields = [
            "title", "category", "description", "keywords",
            "channel_name", "channel_id", "tts_provider",
            "video_site", "scenes"
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return False
                
        # Validate TTS provider
        if data["tts_provider"].lower() not in ["googletts", "elevenlabs"]:
            logger.error(f"Invalid tts_provider: {data['tts_provider']}")
            return False
            
        # Validate video site
        if data["video_site"].lower() not in ["youtube", "tiktok", "facebook"]:
            logger.error(f"Invalid video_site: {data['video_site']}")
            return False
            
        # Validate scenes
        scenes = data["scenes"]
        if not isinstance(scenes, list) or len(scenes) == 0:
            logger.error("Scenes must be non-empty array")
            return False
            
        valid_scene_types = ["title_scene", "text_scene", "image_scene", "outro_scene"]
        for i, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                logger.error(f"Scene {i+1} must be object")
                return False
            if "type" not in scene or "text" not in scene:
                logger.error(f"Scene {i+1} missing type or text")
                return False
            if scene["type"] not in valid_scene_types:
                logger.error(f"Scene {i+1} invalid type: {scene['type']}")
                return False
                
        return True
```

### 2. Updated AI Workflow with Publishing
```python
# src/ai/workflows.py - Updated to include publishing
def _format_and_publish(self, state: ContentState) -> ContentState:
    """Format output and publish to nx-maker8 topic"""
    message = state["original_message"]
    analysis = state["content_analysis"]
    scenes = state["generated_scenes"]
    
    # Map source to video_site
    video_site_mapping = {
        "youtube_content": "youtube",
        "tiktok_content": "tiktok",
        "facebook_content": "facebook"
    }
    video_site = video_site_mapping.get(message.topic, "youtube")
    
    # Determine TTS provider based on video site or content analysis
    tts_provider = "googletts"  # Default
    if video_site == "tiktok":
        tts_provider = "elevenlabs"  # Better for short-form content
        
    final_output = {
        "title": analysis.get("title", "AI Generated Video"),
        "category": analysis.get("category", "General"),
        "description": analysis.get("description", f"AI-enhanced content from {message.metadata.source}"),
        "keywords": ", ".join(analysis.get("keywords", [])),
        "channel_name": message.channel,
        "channel_id": message.metadata.channel_id,
        "tts_provider": tts_provider,
        "video_site": video_site,
        "storage": {
            "provider": "dropbox",
            "folder_path": f"/nx-maker8/{video_site}"
        },
        "scenes": scenes,
        "settings": {
            "resolution": "1920x1080" if video_site != "tiktok" else "1080x1920",
            "fps": 30,
            "format": "mp4"
        }
    }
    
    # Publish to Kafka
    publisher = NXMaker8Publisher()
    success = publisher.publish_video_request(final_output)
    
    if success:
        logger.info(f"Successfully published video request for: {final_output['title']}")
        state["published"] = True
    else:
        logger.error("Failed to publish video request")
        state["published"] = False
        
    state["final_output"] = final_output
    return state
```

### 3. Updated Main Service
```python
# main.py - Simplified for Kafka-to-Kafka processing
class NXEditor8Service:
    """Content processing service: Kafka input → AI processing → Kafka output"""
    
    def __init__(self):
        self.kafka_consumer = NXEditor8KafkaConsumer()
        self.ai_workflow = ContentProcessingWorkflow()
        self.stats = {"processed": 0, "published": 0, "errors": 0}
        
    async def start_processing(self):
        """Main processing loop"""
        logger.info("Starting nx-editor8 content processing service")
        
        try:
            for message in self.kafka_consumer.start_consuming():
                try:
                    # Process message through AI workflow (includes Kafka publishing)
                    result = self.ai_workflow.process_content(message)
                    
                    # Update statistics
                    self.stats["processed"] += 1
                    if result.get("published", False):
                        self.stats["published"] += 1
                        
                    # Log progress
                    if self.stats["processed"] % 10 == 0:
                        logger.info(f"Processed: {self.stats['processed']}, "
                                  f"Published: {self.stats['published']}, "
                                  f"Errors: {self.stats['errors']}")
                    
                except Exception as e:
                    self.stats["errors"] += 1
                    logger.error(f"Processing error: {e}")
                    self._handle_error(message, e)
                    
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
        except Exception as e:
            logger.error(f"Service error: {e}")
            raise
    
    def _handle_error(self, message: ContentMessage, error: Exception):
        """Handle processing errors with retry logic"""
        error_data = {
            "error": str(error),
            "message_topic": message.topic,
            "channel": message.channel,
            "timestamp": message.metadata.timestamp.isoformat(),
            "retry_count": getattr(message, 'retry_count', 0)
        }
        
        # Log error details
        logger.error(f"Error processing message: {error_data}")
        
        # TODO: Implement retry logic with exponential backoff
        # TODO: Send to dead letter queue after max retries
```

## 🚀 Updated Configuration

### Environment Variables
```bash
# .env for nx-editor8 (following EngineX LLM patterns)

# Kafka Input Configuration
KAFKA_BOOTSTRAP_SERVERS=10.113.213.1:9094
KAFKA_SECURITY_PROTOCOL=SASL_PLAINTEXT
KAFKA_SASL_MECHANISM=PLAIN
KAFKA_SASL_USERNAME=client
KAFKA_SASL_PASSWORD=client-secret

# Consumer Configuration
KAFKA_CONSUMER_GROUP=nx_editor8_consumer
KAFKA_INPUT_TOPICS=youtube_content,tiktok_content,facebook_content

# Publisher Configuration
KAFKA_OUTPUT_TOPIC=video_input_topic

# Database Configuration (consistent with EngineX)
DATABASE_URL=postgresql://vubakninh:123456@10.113.213.9:6432/maker8

# LLM Configuration (following EngineX patterns - consistent with x-neews)
LLM_API_BASE=https://litellm.x51.vn/v1
LLM_API_KEY=your_litellm_api_key_here
LLM_MODEL=gpt-3.5-turbo
LLM_TIMEOUT_SECONDS=60
LLM_MAX_TOKENS=4000
LLM_TEMPERATURE=0.7

# Processing Configuration
BATCH_SIZE=1
MAX_RETRY_ATTEMPTS=3
PROCESSING_TIMEOUT=60
LOG_LEVEL=INFO
```

## 📊 Benefits of Kafka-to-Kafka Architecture

### 1. **Decoupling**: nx-editor8 and nx-maker8 are completely decoupled
### 2. **Scalability**: Each service can scale independently
### 3. **Reliability**: Kafka provides message persistence and delivery guarantees
### 4. **Monitoring**: Clear message flow tracking through Kafka topics
### 5. **Flexibility**: Easy to add new consumers or modify processing logic

## 🔄 Data Flow Summary

1. **Input**: Content from youtube_content, tiktok_content, facebook_content topics
2. **Processing**: AI-enhanced content analysis and scene generation
3. **Output**: Validated nx-maker8 JSON published to video_input_topic
4. **Result**: nx-maker8 consumes and generates videos, publishes results to video_output_topic

This architecture ensures nx-editor8 focuses solely on content processing and formatting, while nx-maker8 handles video generation and publishing - creating a clean, scalable pipeline.