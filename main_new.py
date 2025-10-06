"""
Main application entry point for nx-editor8 content processing service.

This module implements the main service loop that consumes messages from Kafka,
processes them through the requirements verification and AI pipeline, and publishes
results to nx-maker8 compatible topics.
"""

import asyncio
import signal
import sys
from typing import Optional

import structlog

from src.core.config import get_settings
from src.core.message_processor import MessageProcessor
from src.integrations.kafka_client import ContentKafkaConsumer
from src.integrations.llm_client import close_llm_client

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class NXEditor8Service:
    """
    Main nx-editor8 content processing service with requirements verification.
    """

    def __init__(self):
        self.settings = get_settings()
        self.consumer: Optional[ContentKafkaConsumer] = None
        self.processor: Optional[MessageProcessor] = None
        self.running = False

    async def start(self) -> None:
        """Start the nx-editor8 service."""
        logger.info(
            "Starting nx-editor8 content processing service",
            service_name=self.settings.service_name,
            input_topics=self.settings.input_topics,
            output_topic=self.settings.output_topic,
            consumer_group=self.settings.kafka_consumer_group,
        )

        try:
            # Initialize components
            self.consumer = ContentKafkaConsumer()
            self.processor = MessageProcessor()
            self.running = True

            logger.info("nx-editor8 service initialized successfully")

            # Start processing loop
            await self._processing_loop()

        except Exception as e:
            logger.error("Failed to start nx-editor8 service", error=str(e))
            await self.stop()
            raise

    async def _processing_loop(self) -> None:
        """Main processing loop for consuming and processing messages."""
        logger.info("Starting message processing loop")

        processed_count = 0
        error_count = 0

        try:
            async for message in self.consumer.consume_messages():
                if not self.running:
                    break

                try:
                    # Process message through pipeline
                    result = await self.processor.process_message(message)

                    if result.success:
                        processed_count += 1
                        logger.info(
                            "Message processed successfully",
                            topic=message.topic,
                            channel=message.channel,
                            retry_count=result.retry_count,
                            processing_time=result.processing_time,
                            scenes_generated=len(result.generated_scenes),
                            total_processed=processed_count,
                        )
                    else:
                        error_count += 1
                        logger.error(
                            "Message processing failed",
                            topic=message.topic,
                            channel=message.channel,
                            error=result.error_message,
                            retry_count=result.retry_count,
                            total_errors=error_count,
                        )

                except Exception as e:
                    error_count += 1
                    logger.error(
                        "Unexpected error in processing loop",
                        topic=message.topic,
                        error=str(e),
                        total_errors=error_count,
                    )

                # Log statistics every 10 messages
                if (processed_count + error_count) % 10 == 0:
                    logger.info(
                        "Processing statistics",
                        processed=processed_count,
                        errors=error_count,
                        success_rate=f"{(processed_count / (processed_count + error_count)) * 100:.1f}%",
                    )

        except Exception as e:
            logger.error("Critical error in processing loop", error=str(e))
            raise

        finally:
            logger.info(
                "Processing loop ended",
                total_processed=processed_count,
                total_errors=error_count,
            )

    async def stop(self) -> None:
        """Stop the nx-editor8 service gracefully."""
        logger.info("Stopping nx-editor8 service")

        self.running = False

        # Close components
        if self.consumer:
            self.consumer.close()

        if self.processor:
            await self.processor.close()

        # Close LLM client
        await close_llm_client()

        logger.info("nx-editor8 service stopped")

    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main() -> None:
    """Main entry point for nx-editor8 service."""
    # Load settings and validate configuration
    settings = get_settings()

    # Validate critical settings
    if not settings.llm_api_base or not settings.llm_api_key:
        logger.error(
            "LLM configuration missing",
            llm_api_base=bool(settings.llm_api_base),
            llm_api_key=bool(settings.llm_api_key),
        )
        sys.exit(1)

    logger.info(
        "nx-editor8 configuration loaded",
        kafka_servers=settings.kafka_bootstrap_servers,
        input_topics=settings.input_topics,
        output_topic=settings.output_topic,
        llm_model=settings.llm_model,
        min_word_count=settings.min_word_count,
        max_word_count=settings.max_word_count,
        max_content_retries=settings.max_content_retries,
    )

    # Create and start service
    service = NXEditor8Service()
    service.setup_signal_handlers()

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error("Service failed", error=str(e))
        sys.exit(1)
    finally:
        await service.stop()


if __name__ == "__main__":
    # Set up logging level from environment
    import logging

    logging.basicConfig(level=logging.INFO)

    # Run the service
    asyncio.run(main())
