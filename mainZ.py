import sys
import time
import signal
import random
import os
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Union, Callable, List, TypeVar, cast, Tuple

# Update imports to reference the src directory
from src.processor_chain import ProcessorChain
from src.rabbitmq_processor import ChainedRabbitMQProcessor
from src.logger import logger
from src.config import INPUT_QUEUE, OUTPUT_QUEUE, PROCESSOR_ID, get_log_level
from src.processor import extract_article, image_processor, script_processor, s2j_processor, video_processor

# Make sure the working directory is correctly set
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
    logger.debug(f"Added {current_dir} to sys.path")

# Initialize application start time for logs
START_TIME = datetime.now()
logger.info(f"Application starting at {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"Running from directory: {current_dir}")
logger.info(f"Python version: {sys.version}")

# Type aliases for better readability
MessageType = TypeVar('MessageType', Dict[str, Any], Any)
ProcessorFunction = Callable[[MessageType], MessageType]

# Pipeline configuration - makes it easy to modify the pipeline
PIPELINE_CONFIG: List[Tuple[ProcessorFunction, str]] = [
    (extract_article, "extract_article"),
    (image_processor, "image_processor"),
    (video_processor, "video_processor"),
    (script_processor, "script_processor"),
    (s2j_processor, "script2json")
]

def create_error_info(error: Exception, processor_name: str) -> Dict[str, Any]:
    """Create error information dictionary for tracking.
    
    Args:
        error: The exception that was raised.
        processor_name: Name of the processor where the error occurred.
        
    Returns:
        Dict[str, Any]: Dictionary containing error details.
    """
    error_id = f"ERR-{int(time.time())}-{random.randint(1000, 9999)}"
    logger.error(f"Error ID: {error_id}")
    
    return {
        "error_id": error_id,
        "processor": processor_name,
        "error": str(error),
        "timestamp": time.time(),
        "error_type": type(error).__name__
    }

def error_handler(message: MessageType, error: Exception, processor_name: str) -> Optional[Dict[str, Any]]:
    """Handle errors in processors.
    
    Args:
        message: The message being processed when the error occurred.
        error: The exception that was raised.
        processor_name: Name of the processor where the error occurred.
        
    Returns:
        Optional[Dict[str, Any]]: The original message with added error information if message is a dict,
            None if the message is not a dict.
    """
    logger.info(f"Starting error_handler for processor: {processor_name}")
    logger.error(f"Error occurred in {processor_name}: {str(error)}")
    logger.error(f"Error stack trace: {traceback.format_exc()}")
    
    # Log additional information about the message for debugging
    if isinstance(message, dict):
        keys = list(message.keys())
        logger.debug(f"Message keys available: {keys}")
        
        # Get error tracking information
        error_info = create_error_info(error, processor_name)
        
        # Cast to Dict to satisfy type checker
        message_dict = cast(Dict[str, Any], message)
        message_dict["processing_error"] = error_info
        
        logger.info(f"Added error information to message with error_id: {error_info['error_id']}")
        return message_dict  # Continue with error information added
    
    logger.warning(f"Message is not a dict, cannot add error information. Type: {type(message)}")
    return None  # Drop the message if it's not a dict

def create_complete_pipeline() -> ProcessorChain:
    """Create and configure the complete processing pipeline.
    
    Returns:
        ProcessorChain: A configured processing pipeline with all processors added.
    """
    logger.info(f"Creating processing pipeline for processor ID: {PROCESSOR_ID}")
    
    chain = ProcessorChain("complete_pipeline")
    
    # Add all processors from configuration
    for processor_func, processor_name in PIPELINE_CONFIG:
        logger.debug(f"Adding {processor_name} to pipeline")
        chain.add_processor(processor_func, processor_name)
    
    logger.debug("Setting error handler")
    chain.set_error_handler(error_handler)
    
    logger.info("Complete processing pipeline created successfully")
    return chain

def run_processor(input_queue: str = "chain_input", output_queue: Optional[str] = None) -> Union[ChainedRabbitMQProcessor, bool]:
    """Initialize and run the RabbitMQ processor.
    
    Args:
        input_queue: Name of the input queue to consume messages from.
            Defaults to "chain_input".
        output_queue: Name of the output queue to publish processed
            messages to. Defaults to None.
            
    Returns:
        Union[ChainedRabbitMQProcessor, bool]: The processor instance if successful,
            False if connection failed.
    """
    logger.info(f"Initializing processor with input queue: '{input_queue}', output queue: '{output_queue}'")
    
    # Create RabbitMQ processor
    processor = ChainedRabbitMQProcessor()
    
    # Connect to RabbitMQ
    logger.info("Attempting to connect to RabbitMQ...")
    if not processor.connect():
        logger.critical("Failed to connect to RabbitMQ. Exiting.")
        return False
    
    # Create processing pipeline
    pipeline = create_complete_pipeline()
    
    # Process queue with chain
    logger.info(f"Setting up message processing from '{input_queue}' to '{output_queue}'")
    processor.process_with_chain(input_queue, pipeline, output_queue)
    logger.info(f"Successfully started processing chain from '{input_queue}' to '{output_queue}'")
    
    return processor

def main() -> int:
    """Main application function.
    
    Returns:
        int: Exit code. 0 for success, 1 for failure.
    """
    # Set log level based on configuration
    log_level = get_log_level()
    logger.set_level(log_level)
    logger.info(f"Set log level to: {log_level}")
    
    # Configure shutdown signal handling
    def handle_shutdown(sig: int, frame: Any) -> None:
        logger.warning(f"Received signal {sig}. Shutting down...")
        # Log shutdown time and runtime
        run_time = datetime.now() - START_TIME
        logger.info(f"Application shutting down after running for {run_time}")
        sys.exit(0)
    
    # Register signals to capture
    signal.signal(signal.SIGINT, handle_shutdown)  # Ctrl+C
    signal.signal(signal.SIGTERM, handle_shutdown)  # kill
    
    try:
        # Start the message processor
        input_queue = INPUT_QUEUE
        output_queue = OUTPUT_QUEUE
        
        logger.info(f"Starting message processor with input queue '{input_queue}' and output queue '{output_queue}'")
        processor = run_processor(input_queue, output_queue)
        
        if processor:
            logger.info("Message processor started successfully. Waiting for messages...")
            # Keep the main thread alive
            while True:
                time.sleep(1)
        else:
            logger.critical("Failed to start message processor. Exiting.")
            return 1
        
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {str(e)}")
        logger.critical(f"Traceback: {traceback.format_exc()}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
