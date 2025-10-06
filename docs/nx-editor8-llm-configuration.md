# nx-editor8 Environment Configuration
**Following EngineX LLM patterns for consistency across xProjects**

## 📋 Environment Variables

### Kafka Configuration
```bash
# Kafka Broker Configuration
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

# Alternative project-specific variables (fallback support)
# NX_EDITOR8_KAFKA_BOOTSTRAP_SERVERS=10.113.213.1:9094
# NX_EDITOR8_CONSUMER_GROUP=nx_editor8_consumer
# NX_EDITOR8_OUTPUT_TOPIC=video_input_topic
```

### Database Configuration
```bash
# Database Connection (consistent with EngineX)
DATABASE_URL=postgresql://vubakninh:123456@10.113.213.9:6432/maker8

# Alternative project-specific variable
# NX_EDITOR8_DATABASE_URL=postgresql://vubakninh:123456@10.113.213.9:6432/maker8
```

### LLM Configuration (Following EngineX Patterns)
```bash
# LiteLLM Configuration (consistent with EngineX and x-neews)
LLM_API_BASE=https://litellm.x51.vn/v1
LLM_API_KEY=your_litellm_api_key_here
LLM_MODEL=gpt-3.5-turbo
LLM_TIMEOUT_SECONDS=60
LLM_MAX_TOKENS=4000
LLM_TEMPERATURE=0.7

# Alternative project-specific variables (fallback support)
# NX_EDITOR8_LLM_API_BASE=https://litellm.x51.vn/v1
# NX_EDITOR8_LLM_API_KEY=your_key_here
# NX_EDITOR8_LLM_MODEL=gpt-3.5-turbo
# NX_EDITOR8_LLM_TIMEOUT_SECONDS=60
# NX_EDITOR8_LLM_MAX_TOKENS=4000
# NX_EDITOR8_LLM_TEMPERATURE=0.7
```

### Processing Configuration
```bash
# Processing Limits
BATCH_SIZE=1
MAX_RETRY_ATTEMPTS=3
PROCESSING_TIMEOUT=300

# Content Generation
MIN_SCENES=3
MAX_SCENES=10
DEFAULT_VIDEO_RESOLUTION=1920x1080
DEFAULT_VIDEO_FPS=30
DEFAULT_TTS_PROVIDER=googletts

# Logging
LOG_LEVEL=INFO

# Alternative project-specific variables
# NX_EDITOR8_BATCH_SIZE=1
# NX_EDITOR8_MAX_RETRIES=3
# NX_EDITOR8_TIMEOUT=300
# NX_EDITOR8_MIN_SCENES=3
# NX_EDITOR8_MAX_SCENES=10
# NX_EDITOR8_VIDEO_RESOLUTION=1920x1080
# NX_EDITOR8_VIDEO_FPS=30
# NX_EDITOR8_TTS_PROVIDER=googletts
# NX_EDITOR8_LOG_LEVEL=INFO
```

## 🏗️ Configuration Architecture

### Multi-Level Fallback System (Following EngineX Patterns)
nx-editor8 uses the same configuration fallback system as EngineX for consistency:

1. **Workspace-standard variables** (highest priority): `LLM_API_BASE`, `LLM_API_KEY`, etc.
2. **Project-specific variables** (fallback): `NX_EDITOR8_LLM_API_BASE`, etc.
3. **Default values** (last resort): Hard-coded defaults in configuration

### Configuration Loading Example
```python
# src/core/config.py
def _get_env_with_multi_fallback(*keys: str, default: str = None) -> Optional[str]:
    """Get environment variable with multiple fallback keys for workspace consistency."""
    for key in keys:
        value = os.getenv(key)
        if value is not None:
            return value
    return default

# Usage example
llm_api_base: Optional[str] = Field(
    default_factory=lambda: _get_env_with_multi_fallback(
        "LLM_API_BASE",           # Workspace standard (highest priority)
        "NX_EDITOR8_LLM_API_BASE" # Project-specific fallback
    )
)
```

## 📝 Example .env File
```bash
# nx-editor8 Configuration
# Copy to .env and update with your actual values

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=10.113.213.1:9094
KAFKA_SASL_USERNAME=client
KAFKA_SASL_PASSWORD=client-secret
KAFKA_INPUT_TOPICS=youtube_content,tiktok_content,facebook_content
KAFKA_OUTPUT_TOPIC=video_input_topic

# Database Configuration
DATABASE_URL=postgresql://vubakninh:123456@10.113.213.9:6432/maker8

# LLM Configuration (consistent with EngineX/x-neews)
LLM_API_BASE=https://litellm.x51.vn/v1
LLM_API_KEY=changeme
LLM_MODEL=gpt-3.5-turbo
LLM_TIMEOUT_SECONDS=60
LLM_MAX_TOKENS=4000
LLM_TEMPERATURE=0.7

# Processing Configuration
BATCH_SIZE=1
MAX_RETRY_ATTEMPTS=3
PROCESSING_TIMEOUT=300
MIN_SCENES=3
MAX_SCENES=10
DEFAULT_TTS_PROVIDER=googletts
LOG_LEVEL=INFO
```

## 🔧 LiteLLM Client Integration

### Client Configuration (Following EngineX)
```python
# src/integrations/llm_client.py
@dataclass
class LiteLLMClientConfig:
    """Configuration for LiteLLM client (consistent with EngineX)"""
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
            raise ValueError("LLM_API_BASE is required")
        if not settings.llm_api_key:
            raise ValueError("LLM_API_KEY is required")

        return cls(
            api_base=settings.llm_api_base.rstrip("/"),
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )
```

### Usage in Content Processing
```python
# src/ai/workflows.py
class ContentProcessingWorkflow:
    def __init__(self):
        self.llm_client = get_llm_client()  # Singleton LiteLLM client
        
    async def _analyze_content(self, state: ContentState) -> ContentState:
        prompt = self._load_prompt_template("content_analysis", {
            "content": state["original_message"].text_content
        })
        
        analysis_result = await self.llm_client.generate(
            prompt=prompt,
            system_message="You are nx-editor8's content analysis assistant.",
            temperature=0.2
        )
        
        state["content_analysis"] = json.loads(analysis_result)
        return state
```

## 🔗 Integration with xProjects Ecosystem

### Shared LLM Infrastructure
- **LiteLLM Endpoint**: Uses same LiteLLM server as EngineX and x-neews
- **API Key Management**: Consistent authentication across services
- **Model Configuration**: Flexible model selection with fallback defaults
- **Error Handling**: Standardized retry logic and timeout handling

### Configuration Consistency
- **Environment Variables**: Same naming conventions as EngineX
- **Fallback System**: Backward compatibility with project-specific variables
- **Default Values**: Sensible defaults that work across the ecosystem
- **Documentation**: Clear configuration examples and patterns

This configuration approach ensures nx-editor8 integrates seamlessly with the existing xProjects LLM infrastructure while maintaining flexibility for project-specific customization.