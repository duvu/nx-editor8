# nx-editor8 Project Documentation

## Project Status (as of May 2025)

**Core Features Implemented:**
- Modular message processing pipeline using `ProcessorChain` (supports both functions and class-based processors, with error handling and timing).
- RabbitMQ integration for message consumption and processing.
- Processors for articles, images, and videos (including Pexels video integration).
- Utility scripts such as `skip.py` for skipping messages in RabbitMQ queues.
- Logging system with configurable log level and file output.
- Dockerized deployment with `docker-compose.yml` and `.env` configuration.
- Example and test scripts for local development and validation.

**Recent Improvements:**
- Refactored `ProcessorChain` for better type safety, extensibility, and error handling.
- Vietnamese and English docstrings for processors (see `pexels_video_processor.py`).
- Improved modularity and code documentation.
- Enhanced test coverage and example usage in `tests/` and `examples/`.

**Areas in Progress / To Do:**
- Expand and document advanced processors (NLP, image recognition, etc.).
- Add more integration and end-to-end tests.
- Improve error handling and logging consistency across all modules.
- Centralize configuration and support dynamic reloading if needed.
- Add metrics and monitoring for performance and reliability.
- Harden Docker and deployment for production use.
- Expand user and developer documentation, including onboarding guides and API references.

---

## What the Project Does

The `nx-editor8` project is a modular, Python-based system for processing and managing messages from RabbitMQ queues. It is designed to support workflows involving scripts, images, and videos, with extensible processors for each type. The project can be run locally or in Docker, and is configured via environment variables in a `.env` file.

**Key features:**
- Consumes messages from RabbitMQ queues for further processing.
- Includes a utility (`skip.py`) to skip (acknowledge and discard) a specified number of messages from a queue.
- Modular processors for handling scripts, images, and videos, making it easy to extend or customize processing logic.
- Logging and configuration management for robust operation.
- Dockerized for easy deployment and consistent environments.

## What Should Be Implemented / Next Steps

- **Processor Enhancements:**
  - Expand and document the logic in `src/processor_chain.py` and `src/rabbitmq_processor.py` for chaining and managing multiple processors.
  - Add more processors or improve existing ones in `processor/` for new data types or advanced processing (e.g., NLP, image recognition, video summarization).

- **Testing:**
  - Increase test coverage in `tests/` for all processors and utility functions.
  - Add integration tests for end-to-end message processing.

- **Documentation:**
  - Add detailed docstrings and usage examples for each processor and utility module.
  - Provide example `.env` and sample input/output files in `examples/`.

- **Error Handling & Logging:**
  - Improve error handling in all message processing scripts.
  - Enhance logging for better traceability and debugging.

- **Configuration:**
  - Centralize and document all configuration options in `src/config.py`.
  - Allow dynamic reloading of configuration if possible.

- **Docker & Deployment:**
  - Add production-ready Dockerfiles and compose files.
  - Document deployment and scaling strategies.

- **Performance & Monitoring:**
  - Add metrics and monitoring for message throughput and processing times.
  - Optimize for high-throughput scenarios if needed.

---

## Overview

This project provides tools and scripts for processing messages via RabbitMQ, including a message skipping utility, and various processors for handling scripts, images, and videos. The project is containerized using Docker and can be configured via environment variables in a `.env` file.

## Key Components

### 1. skip.py
- **Purpose:** Skips (acknowledges and discards) a specified number of messages from a RabbitMQ queue.
- **Usage:**
  ```bash
  python skip.py -n 5
  ```
  - `-n`: Number of messages to skip (default: 1).
- **Configuration:** Reads RabbitMQ connection parameters from `.env`.

### 2. .env
- Stores RabbitMQ connection details and other environment variables.
- Example:
  ```ini
  RABBITMQ_HOST=10.113.213.1
  RABBITMQ_PORT=5672
  RABBITMQ_USER=youruser
  RABBITMQ_PASS=yourpass
  INPUT_QUEUE=nx_01_ai_queue
  OUTPUT_QUEUE=nx_02_queue
  LOG_LEVEL=DEBUG
  ```

### 3. docker-compose.yml
- Defines the `nx-editor` service for running the project in Docker.
- Uses environment variables for RabbitMQ configuration.

### 4. requirements.txt
- Lists Python dependencies, including `pika` and `python-dotenv`.

### 5. src/ and processor/
- Contains core processing logic for scripts, images, and videos.
- Modular design for extensibility.

## Getting Started

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure environment:**
   - Edit `.env` with your RabbitMQ and other settings.
3. **Run skip.py:**
   - To skip messages in the queue as needed.
4. **Docker:**
   - Use `docker-compose up` to start the service in a containerized environment.

## Directory Structure
- `skip.py` — Message skipping script
- `src/` — Core source code
- `processor/` — Processing modules
- `utils/` — Utility functions
- `tests/` — Test suite
- `docker-compose.yml` — Docker Compose config
- `.env` — Environment variables
- `requirements.txt` — Python dependencies

## Notes
- Ensure RabbitMQ is accessible from your environment or container.
- All scripts are Python 3 compatible.

---

For more details, see individual module docstrings and comments.
