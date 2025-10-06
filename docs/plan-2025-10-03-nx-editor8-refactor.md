# NX-Editor8 Refactoring Plan
**Date**: 2025-10-03  
**Objective**: Refactor nx-editor8 to consume Kafka topics, integrate with maker8 database, and generate comprehensive article/script input for nx-maker8

## 📊 Problem Statement

The current nx-editor8 system:
- Uses RabbitMQ for message processing (needs to migrate to Kafka for consistency with the rest of the xProjects ecosystem)
- Currently processes messages in a simple pipeline without database integration
- Lacks LLM-powered content generation capabilities
- Does not integrate with the maker8 database for text embeddings and content enrichment
- Missing langchain/langgraph integration for advanced AI workflows

**Requirements**:
1. Listen to Kafka topics for content from various channels (YouTube, TikTok, Facebook)
2. Query maker8 database for related content with embeddings (to be added later)
3. Use langchain/langgraph with LLM APIs for content processing
4. Search/retrieve images from articles in database  
5. Generate comprehensive articles/scripts as input for nx-maker8

## 🏗 Current Architecture Analysis

### Existing Components
```
nx-editor8/
├── src/
│   ├── config.py              # RabbitMQ config (needs Kafka migration)
│   ├── logger.py              # Logging utilities ✓
│   ├── processor/             # Content processors
│   │   ├── article_processor.py    # Article extraction ✓
│   │   ├── image_processor.py      # Image processing ✓
│   │   ├── script_processor.py     # Script enhancement ✓ 
│   │   └── s2j_processor.py        # Script to JSON conversion ✓
│   ├── processor_chain.py     # Processing pipeline ✓
│   ├── rabbitmq_processor.py  # RabbitMQ consumer (needs replacement)
│   └── utils/                 # Utility modules ✓
├── mainZ.py                   # Main entry point ✓
└── requirements.txt           # Dependencies (needs langchain/langgraph)
```

### Current Data Flow
```
RabbitMQ Topic → Article Processor → Image Processor → Script Processor → S2J Processor → Output
```

## 🎯 Proposed Solution

### New Architecture: Kafka-to-Kafka Pipeline
```
Input Topics → nx-editor8 AI Processing → Output Topic → nx-maker8 → Video Results
     ↓              ↓                        ↓              ↓              ↓
Channel Content → Content Enhancement → video_input_topic → Video Gen → video_output_topic
```

### Target Data Flow
```
1. Kafka Consumer receives: {topic, channel, text_content, metadata} from input topics
2. Database Query: Search maker8 for related content using text search/embeddings
3. LLM Processing: Use langchain/langgraph for content analysis and enhancement  
4. Scene Generation: Create nx-maker8 compatible scene arrays
5. Format Validation: Ensure compliance with nx-maker8 MessageValidatorProcessor
6. Kafka Publishing: Publish to video_input_topic for nx-maker8 consumption
7. nx-maker8: Consumes, generates video, publishes results to video_output_topic
```

## 📋 Implementation Steps

### Phase 1: Infrastructure Migration (Days 1-2)
1. **Kafka Integration**
   - Replace RabbitMQ with Kafka consumer using existing xProjects patterns
   - Update config.py with Kafka bootstrap servers: `10.113.213.1:9094`
   - Implement SASL_PLAINTEXT authentication (`client`/`client-secret`)
   - Create Kafka consumer following `ai_broker` patterns

2. **Database Integration Setup**
   - Add PostgreSQL dependencies and SQLAlchemy models
   - Create database connection to maker8: `postgresql://vubakninh:123456@10.113.213.9:6432/maker8`
   - Design schema for text embeddings (placeholder for future implementation)
   - Add database query utilities

### Phase 2: LLM Integration (Days 3-4)
3. **Langchain/LangGraph Setup**
   - Add langchain, langgraph dependencies
   - Configure LLM provider (compatible with existing LiteLLM setup)
   - Create AI workflow graphs for content processing
   - Implement prompt templates for article generation

4. **Content Processing Enhancement**
   - Upgrade article_processor.py with LLM-powered analysis
   - Enhance image_processor.py with database image search
   - Modify script_processor.py for AI-generated improvements
   - Update s2j_processor.py for nx-maker8 format compatibility

### Phase 3: Content Generation (Days 5-6)
5. **Image Integration**
   - Connect to maker8 database for image retrieval
   - Implement image search from article content
   - Add image URL validation and accessibility checks
   - Integrate with existing ImageSearch utilities

6. **Output Format Adaptation & Kafka Publishing**
   - Modify output to match nx-maker8 input format exactly
   - Generate scenes array with proper scene types (title_scene, text_scene, image_scene, outro_scene)
   - Include required metadata for video generation settings
   - Implement Kafka publisher to video_input_topic
   - Validate JSON output against nx-maker8 MessageValidatorProcessor requirements

### Phase 4: Testing & Integration (Day 7)
7. **Integration Testing**
   - Test end-to-end pipeline with sample Kafka messages
   - Validate database queries and embedding searches
   - Test LLM processing and content generation
   - Verify nx-maker8 input compatibility

8. **Performance Optimization**
   - Implement batch processing for efficiency
   - Add caching for database queries
   - Optimize LLM API calls
   - Monitor processing times and throughput

## 📁 Files to be Modified/Created

### New Files to Create
```
src/
├── kafka/
│   ├── __init__.py
│   ├── consumer.py              # Kafka consumer implementation
│   ├── publisher.py             # Kafka publisher for nx-maker8 topic
│   └── message_handler.py       # Message routing and validation
├── database/
│   ├── __init__.py
│   ├── connection.py            # Database connection manager
│   ├── models.py                # SQLAlchemy models for maker8
│   ├── queries.py               # Database query utilities
│   └── embedding_search.py      # Text embedding search (placeholder)
├── ai/
│   ├── __init__.py
│   ├── llm_client.py            # LLM API client
│   ├── workflows.py             # LangGraph workflow definitions
│   ├── prompts.py               # Prompt templates
│   └── content_generator.py     # AI-powered content generation
└── output/
    ├── __init__.py
    ├── formatter.py             # nx-maker8 JSON formatter
    ├── validator.py             # Message validation for nx-maker8
    └── scene_generator.py       # Scene array generation
```

### Files to Modify
```
src/
├── config.py                   # Add Kafka config, database config, LLM config
├── processor/
│   ├── article_processor.py    # Add LLM analysis
│   ├── image_processor.py      # Add database image search
│   ├── script_processor.py     # Add AI enhancement
│   └── s2j_processor.py        # Update for nx-maker8 format
├── processor_chain.py          # Update for new workflow
└── utils/
    └── image_search.py          # Integrate with database
```

### Configuration Files
```
├── .env                        # Add Kafka, database, LLM config
├── requirements.txt            # Add langchain, langgraph, psycopg2
├── docker-compose.yml          # Update for new dependencies
└── Dockerfile                  # Update for new requirements
```

## 🧪 Testing Strategy

### Unit Tests
- Test Kafka consumer with mock messages
- Test database queries with test data
- Test LLM integration with mock responses
- Test nx-maker8 format generation

### Integration Tests
- End-to-end Kafka pipeline testing
- Database connectivity testing  
- LLM API integration testing
- nx-maker8 format validation
- Message publishing verification

### Test Data
```json
// Sample Kafka message format
{
  "topic": "youtube_content",
  "channel": "tech_channel_001",
  "text_content": "Today we'll explore cloud computing...",
  "metadata": {
    "source": "youtube",
    "timestamp": "2025-10-03T10:00:00Z",
    "channel_id": "UC123456789",
    "video_id": "dQw4w9WgXcQ"
  }
}

// Expected nx-maker8 output format (published to video_input_topic)
{
  "title": "Cloud Computing Explained",
  "category": "Technology", 
  "description": "AI-enhanced content about cloud computing",
  "keywords": "cloud computing, technology, AI",
  "channel_name": "tech_channel_001",
  "channel_id": "UC123456789",
  "tts_provider": "googletts",
  "video_site": "youtube",
  "storage": {
    "provider": "dropbox",
    "folder_path": "/nx-maker8/youtube"
  },
  "scenes": [
    {"type": "title_scene", "text": "Cloud Computing Explained", "background_color": "#1a73e8"},
    {"type": "text_scene", "text": "Enhanced narration content..."},
    {"type": "image_scene", "image_path": "https://...", "text": "Visual explanation..."},
    {"type": "outro_scene", "text": "Thanks for watching!", "background_color": "#34a853"}
  ],
  "settings": {"resolution": "1920x1080", "fps": 30, "format": "mp4"}
}
```

## 🔄 Rollback Strategy

### Database Changes
- Keep existing tables intact during development
- Use migrations for any schema changes
- Maintain backward compatibility

### Code Changes
- Create feature branch: `feature/nx-editor8-kafka-refactor`
- Keep existing RabbitMQ code until Kafka implementation is stable
- Use feature flags for gradual migration

### Configuration
- Maintain separate config files for development/production
- Use environment variables for easy rollback
- Keep old Docker images tagged for quick restoration

## 🔗 Dependencies

### New Dependencies
```python
# requirements.txt additions
langchain==0.1.0
langgraph==0.0.40
psycopg2-binary==2.9.7
kafka-python==2.0.2
sqlalchemy==2.0.21
openai==1.3.0  # or compatible LLM client
```

### External Services
- Kafka cluster: `10.113.213.1:9094`
- PostgreSQL database: `10.113.213.9:6432/maker8` 
- LLM API service (existing LiteLLM setup)
- Redis (for caching, if needed)

### Internal Dependencies
- Follow existing xProjects Kafka patterns from `ai_broker`
- Reuse database connection patterns from `kafka2db`
- Integrate with existing LLM setup from `ai_service`

## ⚠ Risk Assessment

### High Risks
1. **Database Performance**: Complex embedding searches may be slow
   - *Mitigation*: Implement caching and query optimization
2. **LLM API Limits**: Rate limiting and cost management
   - *Mitigation*: Implement request queuing and monitoring
3. **Kafka Message Volume**: High throughput processing
   - *Mitigation*: Implement batch processing and backpressure handling

### Medium Risks
1. **Content Quality**: AI-generated content may need human review
   - *Mitigation*: Implement quality scoring and validation
2. **Image Availability**: Database images may be broken/inaccessible
   - *Mitigation*: Implement fallback image sources
3. **Format Compatibility**: nx-maker8 input format changes
   - *Mitigation*: Version the output format and maintain compatibility

### Low Risks
1. **Development Environment**: Local testing complexity
   - *Mitigation*: Use Docker for consistent environments
2. **Documentation**: Keeping docs updated during rapid development
   - *Mitigation*: Update docs as part of each PR

## 📈 Success Metrics

### Performance Targets
- Message processing: <30 seconds per message
- Database queries: <5 seconds average
- LLM API calls: <10 seconds average
- End-to-end latency: <60 seconds

### Quality Targets  
- 95% successful nx-maker8 format generation
- 90% image retrieval success rate
- 80% content quality score (to be defined)
- Zero message loss in Kafka processing

### Monitoring
- Processing time metrics
- Error rates and types
- Resource utilization
- Output quality scores

---

## 📝 Next Steps

1. **Get approval** for this refactoring plan
2. **Set up development environment** with all required services
3. **Create feature branch** and begin Phase 1 implementation
4. **Establish testing pipeline** for continuous validation
5. **Define content quality metrics** for AI-generated output

**Estimated Timeline**: 7 working days  
**Resources Required**: 1 senior developer, access to all required services  
**Dependencies**: Stable Kafka cluster, database access, LLM API access