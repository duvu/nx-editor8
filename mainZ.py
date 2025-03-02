import json
import sys
import time
import signal
import random
import os

# Update imports to reference the src directory
from src.script2json import script2json
from src.chained_processor import ProcessorChain
from src.rabbitmq_processor import ChainedRabbitMQProcessor
from src.logger import logger
from src.config import INPUT_QUEUE, OUTPUT_QUEUE, PROCESSOR_ID, get_log_level

# Make sure the working directory is correctly set
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

def error_handler(message, error, processor_name):
    """Handle errors in processors"""
    logger.info(f"Starting error_handler for processor: {processor_name}")
    logger.error(f"Error occurred in {processor_name}: {str(error)}")
    
    if isinstance(message, dict):
        message["processing_error"] = {
            "processor": processor_name,
            "error": str(error),
            "timestamp": time.time()
        }
        return message  # Continue with error information added
    
    return None  # Drop the message if it's not a dict

def extract_article(message):
    """Extract article from message"""
    logger.info("Starting extract_article processor")
    # extract article from message. It's the field "article"
    article = message.get("article", "")
    if not article:
        logger.error("No article found in message")
        return None
    return article
def generate_script(article):
    """Generate script from article"""
    logger.info("Starting generate_script processor")
    return article

def s2j(script):
    """Convert script to JSON format"""
    logger.info("Starting script2json processor")
    return script2json(script)

def create_complete_pipeline():
    chain = ProcessorChain("complete_pipeline")
    chain.add_processor(extract_article, "extract_article")
    chain.add_processor(generate_script, "generate_script")
    chain.add_processor(s2j, "script2json")
    chain.set_error_handler(error_handler)
    return chain

def run_processor(input_queue="chain_input", output_queue=None):
    # Create RabbitMQ processor
    processor = ChainedRabbitMQProcessor()
    
    # Connect to RabbitMQ
    if not processor.connect():
        logger.critical("Failed to connect to RabbitMQ. Exiting.")
        return False
    
    # Process queue with chain
    processor.process_with_chain(input_queue, create_complete_pipeline(), output_queue)
    logger.info(f"Started processing chain from {input_queue} to {output_queue}")
    return processor

def main():
    logger.set_level(get_log_level())
    
    # Use configuration values instead of hardcoded strings
    processor = run_processor(INPUT_QUEUE, OUTPUT_QUEUE)

    if not processor:
        sys.exit(1)
    
    def handle_shutdown(sig, frame):
        logger.info("\nShutting down processor...")
        processor.close()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    logger.info(f"Chain processor '{PROCESSOR_ID}' running. Press Ctrl+C to exit.")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        processor.close()

if __name__ == "__main__":
    main()
