"""
Kafka integration for nx-editor8 following xProjects patterns.

This module provides Kafka consumer and producer functionality compatible with
the existing xProjects Kafka infrastructure and authentication.
"""

import asyncio
import json
import logging
from typing import AsyncIterator, Dict, List, Optional

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError
import structlog

from src.core.config import get_settings
from src.models.content_models import ContentMessage, MessageMetadata, NXMaker8Input

logger = structlog.get_logger(__name__)


class KafkaConnectionError(Exception):
    """Raised when Kafka connection fails."""

    pass


class ContentKafkaConsumer:
    """
    Kafka consumer following xProjects patterns from ai_broker
    """

    def __init__(self):
        self.settings = get_settings()
        self.consumer: Optional[KafkaConsumer] = None
        self._setup_consumer()

    def _setup_consumer(self) -> None:
        """Initialize Kafka consumer with SASL authentication."""
        try:
            consumer_config = {
                "bootstrap_servers": self.settings.kafka_bootstrap_servers,
                "security_protocol": self.settings.kafka_security_protocol,
                "sasl_mechanism": self.settings.kafka_sasl_mechanism,
                "sasl_plain_username": self.settings.kafka_sasl_username,
                "sasl_plain_password": self.settings.kafka_sasl_password,
                "group_id": self.settings.kafka_consumer_group,
                "auto_offset_reset": "latest",
                "enable_auto_commit": True,
                "value_deserializer": lambda x: (
                    json.loads(x.decode("utf-8")) if x else None
                ),
                "session_timeout_ms": 30000,
                "max_poll_interval_ms": 300000,
                "request_timeout_ms": 30000,
            }

            self.consumer = KafkaConsumer(
                *self.settings.input_topics, **consumer_config
            )

            logger.info(
                "Kafka consumer initialized",
                topics=self.settings.input_topics,
                group_id=self.settings.kafka_consumer_group,
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
            )

        except Exception as e:
            logger.error("Failed to initialize Kafka consumer", error=str(e))
            raise KafkaConnectionError(f"Failed to initialize Kafka consumer: {e}")

    def get_consumer_group(self) -> str:
        """Return consumer group ID."""
        return self.settings.kafka_consumer_group

    async def consume_messages(self) -> AsyncIterator[ContentMessage]:
        """Consume and yield processed messages."""
        if not self.consumer:
            raise KafkaConnectionError("Consumer not initialized")

        logger.info("Starting message consumption", topics=self.settings.input_topics)

        try:
            while True:
                # Poll for messages with timeout
                message_batch = self.consumer.poll(
                    timeout_ms=1000, max_records=self.settings.batch_size
                )

                if not message_batch:
                    # Allow other async tasks to run
                    await asyncio.sleep(0.1)
                    continue

                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        try:
                            # Convert Kafka message to ContentMessage
                            content_message = self._parse_message(message)
                            if content_message:
                                logger.debug(
                                    "Message consumed",
                                    topic=message.topic,
                                    partition=message.partition,
                                    offset=message.offset,
                                )
                                yield content_message

                        except Exception as e:
                            logger.error(
                                "Failed to parse message",
                                topic=message.topic,
                                error=str(e),
                                raw_value=str(message.value)[:200],
                            )
                            continue

                # Allow other async tasks to run
                await asyncio.sleep(0.01)

        except Exception as e:
            logger.error("Error in message consumption", error=str(e))
            raise

    def _parse_message(self, kafka_message) -> Optional[ContentMessage]:
        """Parse Kafka message into ContentMessage format."""
        try:
            if not kafka_message.value:
                return None

            data = kafka_message.value

            # Extract required fields
            text_content = data.get(
                "content", data.get("text", data.get("message", ""))
            )
            if not text_content:
                logger.warning("Message missing content field", data=data)
                return None

            # Create metadata
            metadata = MessageMetadata(
                source=kafka_message.topic,
                timestamp=kafka_message.timestamp,
                channel_id=data.get("channel_id", "unknown"),
                content_id=data.get("id", data.get("content_id")),
                author=data.get("author", data.get("user_id")),
                tags=data.get("tags", []),
            )

            # Create content message
            return ContentMessage(
                topic=kafka_message.topic,
                channel=data.get("channel", "default"),
                text_content=text_content,
                metadata=metadata,
            )

        except Exception as e:
            logger.error("Failed to parse Kafka message", error=str(e))
            return None

    def close(self) -> None:
        """Close the Kafka consumer."""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")


class NXMaker8Publisher:
    """
    Kafka publisher for sending formatted content to nx-maker8
    """

    def __init__(self):
        self.settings = get_settings()
        self.producer: Optional[KafkaProducer] = None
        self._setup_producer()

    def _setup_producer(self) -> None:
        """Initialize Kafka producer with SASL authentication."""
        try:
            producer_config = {
                "bootstrap_servers": self.settings.kafka_bootstrap_servers,
                "security_protocol": self.settings.kafka_security_protocol,
                "sasl_mechanism": self.settings.kafka_sasl_mechanism,
                "sasl_plain_username": self.settings.kafka_sasl_username,
                "sasl_plain_password": self.settings.kafka_sasl_password,
                "value_serializer": lambda x: json.dumps(x).encode("utf-8"),
                "acks": "all",  # Wait for all replicas
                "retries": 3,
                "delivery_timeout_ms": 30000,
            }

            self.producer = KafkaProducer(**producer_config)

            logger.info(
                "Kafka producer initialized",
                output_topic=self.settings.output_topic,
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
            )

        except Exception as e:
            logger.error("Failed to initialize Kafka producer", error=str(e))
            raise KafkaConnectionError(f"Failed to initialize Kafka producer: {e}")

    async def publish_video_request(self, nx_maker8_input: NXMaker8Input) -> bool:
        """Publish formatted video request to nx-maker8 topic."""
        if not self.producer:
            raise KafkaConnectionError("Producer not initialized")

        try:
            # Convert Pydantic model to dict
            message_data = nx_maker8_input.dict()

            # Validate message format before publishing
            if not self._validate_message_format(message_data):
                logger.error("Message validation failed for nx-maker8 format")
                return False

            # Send message
            future = self.producer.send(self.settings.output_topic, message_data)

            # Wait for send to complete (with timeout)
            record_metadata = future.get(timeout=10)

            logger.info(
                "Message published to nx-maker8",
                topic=record_metadata.topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
                title=nx_maker8_input.title,
            )

            return True

        except KafkaTimeoutError as e:
            logger.error("Kafka timeout while publishing message", error=str(e))
            return False
        except KafkaError as e:
            logger.error("Kafka error while publishing message", error=str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error while publishing message", error=str(e))
            return False

    def _validate_message_format(self, data: dict) -> bool:
        """Validate message matches nx-maker8 expected format."""
        # Based on nx-maker8 MessageValidatorProcessor requirements
        required_fields = [
            "title",
            "category",
            "description",
            "keywords",
            "channel_name",
            "channel_id",
            "tts_provider",
            "video_site",
            "scenes",
        ]

        # Check required fields
        if not all(field in data for field in required_fields):
            missing_fields = [field for field in required_fields if field not in data]
            logger.error("Missing required fields", missing_fields=missing_fields)
            return False

        # Validate TTS provider
        tts_provider = data.get("tts_provider", "").lower()
        if tts_provider not in ["googletts", "elevenlabs"]:
            logger.error("Invalid TTS provider", tts_provider=tts_provider)
            return False

        # Validate video site
        video_site = data.get("video_site", "").lower()
        if video_site not in ["youtube", "tiktok", "facebook"]:
            logger.error("Invalid video site", video_site=video_site)
            return False

        # Validate scenes array
        scenes = data.get("scenes", [])
        if not isinstance(scenes, list) or len(scenes) == 0:
            logger.error(
                "Invalid scenes array",
                scenes_count=len(scenes) if isinstance(scenes, list) else "not_list",
            )
            return False

        # Validate each scene
        scene_types = ["title_scene", "text_scene", "image_scene", "outro_scene"]
        for i, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                logger.error(
                    "Invalid scene format", scene_index=i, scene_type=type(scene)
                )
                return False
            if "type" not in scene or "text" not in scene:
                logger.error(
                    "Scene missing required fields",
                    scene_index=i,
                    scene_keys=list(scene.keys()),
                )
                return False
            if scene["type"] not in scene_types:
                logger.error(
                    "Invalid scene type", scene_index=i, scene_type=scene["type"]
                )
                return False

        return True

    def close(self) -> None:
        """Close the Kafka producer."""
        if self.producer:
            self.producer.flush()  # Ensure all messages are sent
            self.producer.close()
            logger.info("Kafka producer closed")
