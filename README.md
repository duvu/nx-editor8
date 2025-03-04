# RabbitMQ Message Processor

This project provides a Python-based RabbitMQ message processor that consumes messages from one queue, processes them, and publishes the results to another queue.

## Setup

1. Install dependencies:

```bash
pip install pika python-dotenv
```

2. Configure your `.env` file with RabbitMQ connection details:

```
RABBITMQ_URL=localhost
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/
```

## Usage

### Basic Message Processing

Run the basic processor:

```bash
python src/rabbitmq_processor.py
```

This will:
- Connect to RabbitMQ using settings from your `.env` file
- Start consuming messages from `input_queue`
- Process each message (adding a timestamp)
- Publish results to `output_queue`
- Publish a test message to demonstrate functionality

### Advanced Message Processing Examples

Run one of the predefined processors:

```bash
python src/message_processing_examples.py PROCESSOR_TYPE INPUT_QUEUE OUTPUT_QUEUE [--test]
```

Where:
- `PROCESSOR_TYPE`: one of `uppercase`, `filter`, `enrich`, `validate`, or `transform`
- `INPUT_QUEUE`: the queue to consume messages from (default: `input_queue`)
- `OUTPUT_QUEUE`: the queue to publish processed messages to (default: `{input_queue}_processed`)
- `--test`: optional flag to publish a test message

Examples:

```bash
# Process messages with the uppercase processor
python src/message_processing_examples.py uppercase

# Use the filter processor between custom queues and publish a test message
python src/message_processing_examples.py filter tasks_queue filtered_tasks --test

# Use the default enrich processor 
python src/message_processing_examples.py
```

## Chained Message Processing

The chained message processor allows you to build processing pipelines where messages flow through multiple processing steps in sequence.

### Running Predefined Processing Chains

```bash
python src/processing_chain_examples.py CHAIN_TYPE INPUT_QUEUE OUTPUT_QUEUE [--test]
```

Where:
- `CHAIN_TYPE`: one of `validation`, `enrichment`, `delivery`, or `complete`
- `INPUT_QUEUE`: the queue to consume messages from (default: `chain_input`)
- `OUTPUT_QUEUE`: the queue to publish processed messages to (default: `{input_queue}_processed`)
- `--test`: optional flag to publish a test message

Examples:

```bash
# Run the complete processing pipeline
python src/processing_chain_examples.py complete

# Run only the enrichment chain with custom queues
python src/processing_chain_examples.py enrichment raw_data enriched_data --test
```

## Available Processors

- **uppercase**: Converts all string values to uppercase
- **filter**: Only passes messages with priority > 5 
- **enrich**: Adds timestamp and processor information
- **validate**: Validates message format and marks validity
- **transform**: Restructures messages into a new format

## Available Processing Chains

- **validation**: Validates message structure and cleans data
- **enrichment**: Adds additional information and computes metrics
- **delivery**: Filters, transforms, and adds routing information
- **complete**: Combines all processing steps in sequence

## Creating Custom Processors

Create your own processing function that takes a message and returns a processed message:

```python
def my_processor(message):
    # Process the message
    # Return None to drop the message
    return processed_message

processor.process_queue('input_queue', my_processor, 'output_queue')
```

## Creating Custom Processing Chains

You can create custom processing chains by combining processor functions:

```python
from processor_chain import ProcessorChain
from chained_rabbitmq_processor import ChainedRabbitMQProcessor

# Create processors
def first_step(message):
    # Process message
    return modified_message

def second_step(message):
    # Process message further
    return modified_message

# Create chain
chain = ProcessorChain("my_custom_chain")
chain.add_processor(first_step, "step1")
chain.add_processor(second_step, "step2")
chain.set_error_handler(my_error_handler)

# Use with RabbitMQ
processor = ChainedRabbitMQProcessor()
processor.connect()
processor.process_with_chain('input_queue', chain, 'output_queue')
```

## Features

- Single processors or chains of processors
- Automatic reconnection handling
- Thread-safe message processing
- JSON parsing and serialization
- Graceful shutdown handling
- Error handling in processor chains
- Message routing and transformation

# NX Editor 8

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/nx-editor8.git
   cd nx-editor8
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the processor:
   ```
   python mainZ.py
   ```

## Features

- Script to JSON conversion
- Automatic image replacement for unreachable URLs
- Integration with DuckDuckGo for image search
- RabbitMQ message processing

## Configuration

Adjust the settings in `src/config.py` to configure the application.
