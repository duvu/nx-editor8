import argparse
import json
import os
import re
import signal
import sys
import time
import threading
import random
from typing import Any, Dict, List, Optional, Tuple, Union

# Third-party imports
# No third-party imports in this file

# Local application imports
from src.config import INPUT_QUEUE, OUTPUT_QUEUE, PROCESSOR_ID, get_log_level
from src.logger import logger
from src.processor_chain import ProcessorChain
from src.rabbitmq_processor import ChainedRabbitMQProcessor

# Import processors, raise error if not found
from src.processor import (
    extract_article,
    image_processor,
    script_processor,
    s2j_processor,
    video_processor
)
from src.processor.s2j_processor import s2j_processor

# Import ImageSearch, raise error if not found
from src.utils.image_search import ImageSearch
# Import from utils instead of defining locally
from src.utils.keyword_utils import select_random_keywords, extract_keywords

# Constants
MIN_REQUIRED_IMAGES = 5
IMAGE_EXTENSIONS = r'\.(jpg|jpeg|png|gif|bmp|webp|tiff|svg)(\?|$|#)'

# Make sure the working directory is correctly set
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

def error_handler(message: Dict[str, Any], error: Exception, processor_name: str) -> Optional[Dict[str, Any]]:
    """Handle errors in processors.
    
    Args:
        message: The message being processed when the error occurred
        error: The exception that was raised
        processor_name: Name of the processor where the error occurred
        
    Returns:
        Dict with error information added, or None if message is not a dict
    """
    logger.info(f"Starting error_handler for processor: {processor_name}")
    logger.error(f"Error occurred in {processor_name}: {str(error)}")
    
    if isinstance(message, dict):
        message["processing_error"] = {
            "processor": processor_name,
            "error": str(error),
            "timestamp": time.time()
        }
        return message
    
    return None

def process_image_url(line: str, url: str, url_parts: List[str], 
                    image_searcher: ImageSearch, keywords: str) -> str:
    """Process and validate a single image URL.
    
    Args:
        line: Original line containing the URL
        url: Extracted URL
        url_parts: URL parts split by comma
        image_searcher: ImageSearch instance
        keywords: Keywords for finding replacement images
        
    Returns:
        The processed line with replaced URL if needed
    """
    is_image = bool(re.search(IMAGE_EXTENSIONS, url.lower()))
    
    if is_image and not image_searcher.is_url_accessible(url):
        logger.warning(f"Image URL not accessible: {url}")
        
        new_url = image_searcher.get_alternative_image(keywords)
        
        if new_url:
            logger.info(f"Replacing with alternative image: {new_url}")
            
            if len(url_parts) > 1:
                return f"{new_url},{url_parts[1]}"
            else:
                return new_url
    
    return line

def find_last_image_position(lines: List[str]) -> int:
    """Find the position of the last image URL in the lines.
    
    Args:
        lines: List of lines from the article
        
    Returns:
        Index of the last image URL line
    """
    last_img_pos = 0
    for i, line in enumerate(lines):
        if line.startswith('http://') or line.startswith('https://'):
            last_img_pos = i
    
    return last_img_pos

def add_additional_images(lines: List[str], image_lines: List[str], 
                         needed_images: int, image_searcher: ImageSearch, 
                         keywords: str) -> List[str]:
    """Add additional images to reach the minimum required count.
    
    Args:
        lines: List of lines from the article
        image_lines: List of existing image URL lines
        needed_images: Number of additional images needed
        image_searcher: ImageSearch instance
        keywords: Keywords for finding images
        
    Returns:
        Updated list of lines with added images
    """
    added_images = []
    
    for i in range(needed_images):
        new_url = image_searcher.get_alternative_image(keywords)
        if new_url:
            added_images.append(new_url)
            logger.info(f"Added new image: {new_url}")
    
    if image_lines:
        last_img_pos = find_last_image_position(lines)
        
        for i, img in enumerate(added_images):
            lines.insert(last_img_pos + 1 + i, img)
    else:
        lines.extend(added_images)
    
    logger.info(f"Added {len(added_images)} new images to reach minimum of {MIN_REQUIRED_IMAGES} images")
    return lines

def get_image_lines(lines: List[str]) -> List[str]:
    """Extract image lines from the article.
    
    Args:
        lines: List of lines from the article
        
    Returns:
        List of image URL lines
    """
    return [line for line in lines if line.startswith('http://') or line.startswith('https://')]

def create_complete_pipeline() -> ProcessorChain:
    """Create and configure the complete processing pipeline.
    
    Returns:
        Configured processing pipeline
    """
    chain = ProcessorChain("complete_pipeline")
    chain.add_processor(extract_article, "extract_article")
    
    # Add image processor 
    chain.add_processor(image_processor, "image_processor")
    
    # Add video processor
    # Create a wrapper function that passes the creative_commons_only parameter
    def video_processor_with_cc(data):
        return video_processor(data, creative_commons_only=True)
    
    chain.add_processor(video_processor_with_cc, "video_processor")
    
    # Add script processor
    chain.add_processor(script_processor, "script_processor")
    
    # Add JSON conversion processor
    chain.add_processor(s2j_processor, "s2j_processor")
    
    # Set error handler
    chain.set_error_handler(error_handler)
    return chain

def run_processor(input_queue: str = "chain_input", 
                output_queue: Optional[str] = None) -> Union[ChainedRabbitMQProcessor, bool]:
    """Initialize and run the RabbitMQ processor.
    
    Args:
        input_queue: Name of the input queue
        output_queue: Optional name of the output queue
        
    Returns:
        Processor instance if successful, False if connection failed
    """
    processor = ChainedRabbitMQProcessor()
    
    if not processor.connect():
        logger.critical("Failed to connect to RabbitMQ. Exiting.")
        return False
    
    processor.process_with_chain(input_queue, create_complete_pipeline(), output_queue)
    logger.info(f"Started processing chain from {input_queue} to {output_queue}")
    return processor

def handle_shutdown(processor: ChainedRabbitMQProcessor, sig: int, frame: Any) -> None:
    """Handle shutdown signals for graceful exit.
    
    Args:
        processor: The RabbitMQ processor to close
        sig: Signal number received
        frame: Current stack frame
    """
    logger.info("\nShutting down processor...")
    try:
        # Start a timer thread that will force exit after a timeout
        def force_exit():
            time.sleep(10)  # Wait 10 seconds max for graceful shutdown
            logger.warning("Shutdown taking too long! Forcing exit...")
            os._exit(1)
            
        force_thread = threading.Thread(target=force_exit, daemon=True)
        force_thread.start()
        
        # Try graceful shutdown
        if processor:
            processor.close()
            logger.info("Processor closed successfully")
    except Exception as e:
        logger.error(f"Error closing processor during shutdown: {e}")
    finally:
        # Force exit - don't return to caller
        logger.info("Exiting application")
        sys.stdout.flush()  # Ensure logs are displayed
        os._exit(0)  # Use os._exit to ensure immediate termination

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        Namespace containing the parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Process article scripts with image validation and JSON conversion"
    )
    
    # Add queue processing mode arguments
    parser.add_argument(
        "--queue-mode", 
        action="store_true",
        help="Run in queue processing mode (using RabbitMQ)"
    )
    parser.add_argument(
        "--input-queue", 
        type=str,
        default=INPUT_QUEUE,
        help=f"Input queue name for RabbitMQ (default: {INPUT_QUEUE})"
    )
    parser.add_argument(
        "--output-queue", 
        type=str,
        default=OUTPUT_QUEUE,
        help=f"Output queue name for RabbitMQ (default: {OUTPUT_QUEUE})"
    )
    
    # Add file processing mode arguments
    parser.add_argument(
        "--input-file", 
        type=str,
        help="Path to input file containing article text to process"
    )
    parser.add_argument(
        "--output-file", 
        type=str,
        help="Path to output file for the processed JSON result"
    )
    parser.add_argument(
        "--title", 
        type=str,
        default="",
        help="Article title (used for keyword extraction if not found in content)"
    )
    
    # Add general arguments
    parser.add_argument(
        "--log-level", 
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level"
    )
    
    return parser.parse_args()

def process_file(input_file: str, output_file: str, title: str = "") -> bool:
    """Process an input file and write results to output file.
    
    Args:
        input_file: Path to the input file
        output_file: Path to the output file
        title: Optional title for the article
        
    Returns:
        True if processing was successful, False otherwise
    """
    try:
        # Read input file
        logger.info(f"Reading input file: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            article = f.read()
        
        if not article:
            logger.error(f"Input file is empty: {input_file}")
            return False
        
        # Create initial data structure
        data = {"article": article, "title": title}
        
        # Process the data through the pipeline
        pipeline = create_complete_pipeline()
        
        # Use the pipeline's process method instead of manually iterating
        result = pipeline.process(data)
        
        if result is None:
            logger.error("Pipeline processing failed with None result")
            return False
            
        # Write result to output file
        logger.info(f"Writing output to: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Processing completed successfully: {input_file} -> {output_file}")
        return True
        
    except Exception as e:
        logger.exception(f"Error processing file: {e}")
        return False

def main() -> None:
    """Main application function."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging
    if args.log_level:
        logger.set_level(args.log_level)
    else:
        logger.set_level(get_log_level())
    
    # Determine processing mode
    file_mode = args.input_file is not None and args.output_file is not None
    queue_mode = args.queue_mode or (not file_mode)
    
    # Handle file processing mode
    if file_mode:
        success = process_file(args.input_file, args.output_file, args.title)
        sys.exit(0 if success else 1)
    
    # Handle queue processing mode
    if queue_mode:
        processor = None
        try:
            # Initialize processor
            processor = run_processor(args.input_queue, args.output_queue)
            if not processor:
                logger.critical("Failed to initialize processor. Exiting.")
                sys.exit(1)
            
            # Set up signal handlers for graceful shutdown
            # Use stronger signal handling that can't be overridden
            signal.signal(signal.SIGINT, lambda sig, frame: handle_shutdown(processor, sig, frame))
            signal.signal(signal.SIGTERM, lambda sig, frame: handle_shutdown(processor, sig, frame))
            
            # Original shutdown handler as a backup
            original_sigint = signal.getsignal(signal.SIGINT)
            
            logger.info(f"Chain processor '{PROCESSOR_ID}' running. Press Ctrl+C to exit.")
            
            # Keep main thread alive with shorter sleep to be more responsive to signals
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                # This should be reached if the signal handler doesn't work
                logger.info("KeyboardInterrupt received. Shutting down...")
                handle_shutdown(processor, signal.SIGINT, None)
                
        except KeyboardInterrupt:
            # Extra fallback, should not normally be reached
            logger.info("KeyboardInterrupt received directly. Forcing shutdown...")
            if processor:
                try:
                    processor.close()
                except Exception as ex:
                    logger.error(f"Error closing processor during forced shutdown: {ex}")
            sys.stdout.flush()
            os._exit(0)
        except Exception as e:
            logger.exception(f"Unhandled exception in main function: {e}")
            if processor:
                try:
                    processor.close()
                except Exception as ex:
                    logger.error(f"Error closing processor after exception: {ex}")
            sys.exit(1)

if __name__ == "__main__":
    main()
