# NX Editor 8

AI-powered content processing service that transforms social media content into structured scenes for the xProjects ecosystem. Integrates with Kafka topics and provides intelligent content enhancement through LLM processing.

## ✅ Implementation Status

**Phase 1: Core Infrastructure** - ✅ **COMPLETED**
- ✅ Requirements verification system with intelligent content validation
- ✅ Kafka integration (multi-topic consumption + nx-maker8 publishing)
- ✅ LiteLLM client with EngineX compatibility and multi-fallback configuration
- ✅ Main processing pipeline with async processing and comprehensive error handling
- ✅ Complete configuration system with 40+ environment variables
- ✅ Pydantic models for entire processing pipeline
- ✅ Prompt templates for content analysis, enhancement, and scene generation
- ✅ Comprehensive test suite and documentation

**Phase 2: Database Integration** - 🔄 **PLANNED**
- 🔄 PostgreSQL maker8 database integration
- 🔄 Content persistence and retrieval
- 🔄 Historical analysis capabilities

**Phase 3: Advanced Features** - 📋 **PLANNED**
- 📋 Real-time processing dashboard
- 📋 Content analytics and insights
- 📋 Performance optimization

## 🏗 Architecture

```
Kafka Topics → Content Processing → Requirements Verification → AI Enhancement → Scene Generation → nx-maker8 Publishing
```

**Input Sources:**
- `youtube_content` - YouTube video analysis
- `tiktok_content` - TikTok content processing  
- `facebook_content` - Facebook post analysis

**Output Target:**
- `nx-maker8` topic - Structured scene data for maker8 ecosystem

**Core Components:**
- **Requirements Validator**: Intelligent content validation with LLM-powered enhancement
- **LiteLLM Client**: EngineX-compatible AI processing with retry logic
- **Kafka Integration**: SASL-authenticated consumer/producer with message validation
- **Message Processor**: Async pipeline coordinating all processing stages

## ⚙ Configuration

Create `.env` file from template:

```bash
cp .env.example .env
```

### Essential Configuration

```bash
# Kafka Configuration (Required)
KAFKA_BOOTSTRAP_SERVERS=10.113.213.1:9094
KAFKA_USERNAME=client
KAFKA_PASSWORD=client-secret

# LiteLLM Configuration (Required)
LITELLM_API_BASE=http://10.113.213.1:4000
LITELLM_API_KEY=your-api-key

# Content Requirements (Configurable)
MIN_WORD_COUNT=50
MAX_WORD_COUNT=2000
MIN_CHAR_COUNT=200
MAX_CHAR_COUNT=10000
```

See `.env.example` for complete configuration options with fallback patterns.

## 🚀 Installation & Setup

1. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure Environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Run Service:**
```bash
python src/main_new.py
```

## 🔧 Usage

### Service Mode (Default)
```bash
python src/main_new.py
```

Runs continuous Kafka consumer processing multiple content topics.

### Development & Testing
```bash
# Run tests
pytest tests/

# Check configuration
python -c "from src.core.config import Settings; print(Settings().dict())"

# Test Kafka connectivity  
python -c "from src.integrations.kafka_client import ContentKafkaConsumer; consumer = ContentKafkaConsumer(); print('Kafka OK')"

# Test LLM client
python -c "from src.integrations.llm_client import get_llm_client; import asyncio; asyncio.run(get_llm_client().generate('test'))"
```

## 📊 Features

### Content Requirements Verification
- **Word/Character Count Validation**: Configurable min/max limits
- **Format Detection**: Automatic content type identification
- **Language Validation**: Multi-language content support
- **LLM Enhancement**: Intelligent content expansion when requirements not met
- **Retry Logic**: Robust enhancement with intelligent fallback

### AI Processing Pipeline
- **Content Analysis**: Deep content understanding and categorization
- **Scene Generation**: Transform content into structured scene format
- **Enhancement**: LLM-powered content improvement
- **Validation**: Multi-stage content quality verification

### Kafka Integration
- **Multi-topic Consumption**: YouTube, TikTok, Facebook content sources
- **SASL Authentication**: Secure xProjects ecosystem integration
- **Message Validation**: Structured format verification
- **Error Handling**: Comprehensive error topic publishing

### Technical Features
- **EngineX Compatibility**: Follows established xProjects patterns
- **Async Processing**: High-performance async/await implementation
- **Configuration Fallbacks**: Multi-level environment variable fallbacks
- **Comprehensive Logging**: Structured logging throughout pipeline
- **Error Recovery**: Intelligent retry and fallback mechanisms

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_config.py                 # Configuration tests
pytest tests/test_requirements_validator.py # Requirements validation tests
pytest tests/test_llm_client.py            # LLM client tests
pytest tests/test_kafka_client.py          # Kafka integration tests
pytest tests/test_message_processor.py     # Pipeline tests

# Run with coverage
pytest --cov=src tests/
```

## 📁 Project Structure

```
nx-editor8/
├── src/
│   ├── core/
│   │   ├── config.py              # Multi-fallback configuration system
│   │   └── message_processor.py   # Main processing pipeline
│   ├── integrations/
│   │   ├── kafka_client.py        # Kafka consumer/producer
│   │   └── llm_client.py          # LiteLLM client with EngineX compatibility
│   ├── validation/
│   │   └── requirements_validator.py # Content validation and enhancement
│   ├── models/
│   │   └── content_models.py      # Pydantic models for pipeline
│   ├── ai/
│   │   └── prompt_templates/      # LLM prompt templates
│   └── main_new.py               # Service entry point
├── tests/                        # Comprehensive test suite
├── .env.example                  # Configuration template
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🔗 Integration

### xProjects Ecosystem Integration
- **Kafka Topics**: Consumes from social media content topics
- **nx-maker8**: Publishes structured scene data
- **EngineX Patterns**: Follows established configuration and client patterns
- **Infrastructure**: Uses shared Kafka cluster and LiteLLM service

### Dependencies
- **kafka-python**: Kafka client library
- **litellm**: LLM client library  
- **pydantic**: Data validation and settings
- **httpx**: Async HTTP client
- **pytest**: Testing framework

## 📋 Development Roadmap

### Phase 2: Database Integration
- PostgreSQL maker8 integration for content persistence
- Historical content analysis and retrieval
- Content versioning and audit trail

### Phase 3: Advanced Features  
- Real-time processing dashboard
- Content analytics and performance metrics
- Advanced AI model selection and optimization
- Content recommendation system

## 🐛 Troubleshooting

### Common Issues

**Kafka Connection Issues:**
```bash
# Check Kafka connectivity
kafkacat -b 10.113.213.1:9094 -L

# Verify SASL authentication
kafkacat -b 10.113.213.1:9094 -X security.protocol=SASL_PLAINTEXT -X sasl.mechanisms=PLAIN -X sasl.username=client -X sasl.password=client-secret -L
```

**LiteLLM Issues:**
```bash
# Test LiteLLM endpoint
curl http://10.113.213.1:4000/health

# Check API key configuration
echo $LITELLM_API_KEY
```

**Configuration Issues:**
```bash
# Validate configuration
python -c "from src.core.config import Settings; s = Settings(); print('✅ Configuration valid')"

# Check environment variables
env | grep -E "(KAFKA|LITELLM|NX_EDITOR)"
```

## 🤝 Contributing

1. Follow xProjects coding conventions
2. Maintain file size limits (≤350 lines)
3. Include comprehensive tests for new features
4. Update documentation for changes
5. Follow established architecture patterns

## 📄 License

Part of the xProjects ecosystem. See project root for license information.