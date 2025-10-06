# nx-editor8 Implementation Plan
**Created:** 2025-01-19  
**Purpose:** Transform nx-editor8 from RabbitMQ-based to Kafka-to-Kafka pipeline with LLM integration  
**Priority:** High - Foundation for video content pipeline  

## Problem Statement
Current nx-editor8 uses RabbitMQ and lacks AI capabilities. Need to:
1. Migrate to Kafka infrastructure (input and output)
2. Add LLM-powered content analysis and script generation
3. Generate compatible output for nx-maker8 video pipeline
4. Follow EngineX LLM configuration patterns for consistency

## Proposed Solution
**Architecture:** Kafka Consumer → AI Processing → Kafka Publisher
- **Input:** Multiple Kafka topics (youtube_content, tiktok_content, facebook_content)
- **Processing:** LangChain/LangGraph workflows with LiteLLM backend
- **Output:** video_input_topic with nx-maker8 compatible format
- **Configuration:** EngineX-style LLM patterns with multi-fallback system

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
**Objectives:**
- Set up Kafka consumer infrastructure
- Implement LiteLLM client following EngineX patterns
- Create basic message processing pipeline

**Files to Create/Modify:**
1. `nx-editor8/src/core/config.py` - Configuration management with EngineX patterns
2. `nx-editor8/src/integrations/kafka_client.py` - Kafka consumer/producer
3. `nx-editor8/src/integrations/llm_client.py` - LiteLLM client (based on EngineX)
4. `nx-editor8/src/core/message_processor.py` - Main processing pipeline
5. `nx-editor8/requirements.txt` - Add dependencies
6. `nx-editor8/.env.example` - Environment template

**Technical Specifications:**
```python
# Configuration hierarchy (following EngineX patterns)
class LiteLLMConfig:
    api_base: str = "https://litellm.x51.vn/v1"  # workspace default
    api_key: str = ""  # project-specific
    model: str = "gpt-3.5-turbo"  # default fallback
    timeout: int = 60
    max_tokens: int = 4000
    temperature: float = 0.7

# Kafka configuration
class KafkaConfig:
    bootstrap_servers: str = "10.113.213.1:9094"
    security_protocol: str = "SASL_PLAINTEXT"
    sasl_mechanism: str = "PLAIN"
    sasl_username: str = "client"
    sasl_password: str = "client-secret"
    consumer_group: str = "nx_editor8_consumer"
    input_topics: List[str] = ["youtube_content", "tiktok_content", "facebook_content"]
    output_topic: str = "video_input_topic"
```

**Testing Approach:**
- Unit tests for configuration loading
- Kafka connectivity tests
- LLM client integration tests
- Message processing pipeline tests

### Phase 2: Content Analysis AI (Week 2)
**Objectives:**
- Implement LangChain/LangGraph workflows
- Create content analysis and categorization
- Build script generation capabilities

**Files to Create/Modify:**
1. `nx-editor8/src/ai/content_analyzer.py` - LangGraph workflow for content analysis
2. `nx-editor8/src/ai/script_generator.py` - Video script generation
3. `nx-editor8/src/ai/prompts/` - Prompt templates directory
4. `nx-editor8/src/models/content_models.py` - Pydantic models for content

**AI Workflow Architecture:**
```python
# LangGraph workflow nodes
class ContentAnalysisWorkflow:
    1. content_validation()     # Validate input content
    2. content_categorization() # Categorize content type
    3. sentiment_analysis()     # Analyze sentiment
    4. script_generation()      # Generate video script
    5. output_formatting()      # Format for nx-maker8
```

**Testing Approach:**
- LangGraph workflow tests
- Prompt template validation
- Content analysis accuracy tests
- Script generation quality tests

### Phase 3: Database Integration (Week 3)
**Objectives:**
- Add PostgreSQL connectivity for image search
- Implement content enrichment
- Add caching mechanisms

**Files to Create/Modify:**
1. `nx-editor8/src/database/db_client.py` - PostgreSQL client
2. `nx-editor8/src/services/image_search.py` - Enhanced image search
3. `nx-editor8/src/services/content_enrichment.py` - Content enhancement
4. `nx-editor8/src/models/database_models.py` - Database models

**Database Integration:**
```python
# Database connectivity (consistent with EngineX)
DATABASE_URL = "postgresql://vubakninh:123456@10.113.213.9:6432/maker8"

class DatabaseClient:
    async def search_images(self, query: str) -> List[ImageResult]
    async def get_content_metadata(self, content_id: str) -> ContentMetadata
    async def cache_processing_result(self, result: ProcessingResult)
```

**Testing Approach:**
- Database connectivity tests
- Image search functionality tests
- Content enrichment tests
- Caching mechanism tests

### Phase 4: nx-maker8 Compatibility (Week 4)
**Objectives:**
- Ensure output format matches nx-maker8 MessageValidatorProcessor requirements
- Implement comprehensive validation
- Add error handling and retry logic

**Files to Create/Modify:**
1. `nx-editor8/src/output/message_formatter.py` - nx-maker8 format compliance
2. `nx-editor8/src/validation/output_validator.py` - Message validation
3. `nx-editor8/src/core/error_handler.py` - Error handling
4. `nx-editor8/tests/integration/` - Integration tests

**nx-maker8 Output Format:**
```python
# Required format for video_input_topic
{
    "title": str,  # Required
    "description": str,  # Required
    "scenes": [  # Required array
        {
            "type": "intro|main|outro",  # Required
            "content": str,  # Required
            "duration": float,  # Required
            "tts_text": str,  # Required
            "image_query": str,  # Optional
            "video_site": str  # Optional: youtube|tiktok|facebook
        }
    ],
    "metadata": {  # Optional
        "source": str,
        "processed_at": str,
        "ai_model": str
    }
}
```

**Testing Approach:**
- MessageValidatorProcessor compatibility tests
- End-to-end pipeline tests
- Error scenario tests
- Performance benchmarks

## Dependencies and Risks

### External Dependencies
- **Kafka cluster:** 10.113.213.1:9094 availability
- **LiteLLM service:** https://litellm.x51.vn/v1 reliability
- **PostgreSQL:** maker8 database access
- **nx-maker8:** MessageValidatorProcessor compatibility

### Risk Mitigation
1. **Kafka connection failures:** Implement retry logic with exponential backoff
2. **LLM service downtime:** Multi-fallback configuration (workspace → project → default)
3. **Database connectivity:** Connection pooling and retry mechanisms
4. **Format compatibility:** Comprehensive validation against nx-maker8 requirements

### Success Metrics
- **Performance:** Process 100+ messages/hour
- **Reliability:** 99%+ uptime with error recovery
- **Compatibility:** 100% nx-maker8 MessageValidatorProcessor compliance
- **Quality:** AI-generated scripts pass manual review

## Rollback Plan
1. Keep current nx-editor8 RabbitMQ version as backup
2. Implement feature flags for gradual rollout
3. Monitor error rates and performance metrics
4. Quick rollback to previous version if critical issues arise

## Testing Strategy
- **Unit tests:** All new modules with 80%+ coverage
- **Integration tests:** Kafka, LLM, and database connectivity
- **End-to-end tests:** Full pipeline from input to nx-maker8 compatibility
- **Performance tests:** Load testing with realistic message volumes

## Documentation Requirements
- API documentation for all new modules
- Configuration guide following EngineX patterns
- Troubleshooting guide for common issues
- Integration guide for nx-maker8 compatibility

---
**Next Steps:**
1. Begin Phase 1 implementation with core infrastructure
2. Set up development environment with Kafka and LiteLLM access
3. Create initial project structure following xProjects conventions
4. Implement basic Kafka consumer/producer following EngineX patterns