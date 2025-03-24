import argparse
import json
import os
import re
import signal
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

# Third-party imports
# No third-party imports in this file

# Local application imports
from src.config import INPUT_QUEUE, OUTPUT_QUEUE, PROCESSOR_ID, get_log_level
from src.logger import logger
from src.processor_chain import ProcessorChain
from src.rabbitmq_processor import ChainedRabbitMQProcessor
from src.script2json import script2json

# Try to import video_processor, use a mock if it fails
try:
    from src.processor.video_processor import video_processor
except ImportError as e:
    logger.warning(f"Could not import video_processor: {e}")
    
    def video_processor(data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock video processor when dependencies are missing."""
        logger.warning("Using mock video_processor due to missing dependencies")
        return data

# Try to import ImageSearch, create a mock version if it fails
try:
    from src.image_search import ImageSearch
except ImportError as e:
    logger.warning(f"Could not import ImageSearch: {e}")
    
    # Create a mock ImageSearch class
    class MockImageSearch:
        """Mock version of ImageSearch for when dependencies are missing."""
        
        def __init__(self, *args, **kwargs):
            logger.warning("Using MockImageSearch because duckduckgo_search is not installed")
        
        def is_url_accessible(self, url: str) -> bool:
            """Always return True for URLs in mock mode."""
            logger.info(f"MockImageSearch: Pretending URL is accessible: {url}")
            return True
            
        def get_alternative_image(self, keywords: str, *args, **kwargs) -> Optional[str]:
            """Return a placeholder image URL."""
            logger.info(f"MockImageSearch: Returning placeholder image for keywords: {keywords}")
            # Return a placeholder image URL from a public placeholder service
            return "https://via.placeholder.com/1200x800.png"
    
    # Assign the mock class to the ImageSearch name
    ImageSearch = MockImageSearch

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

def extract_article(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract article and title from message.
    
    Args:
        message: Input message containing article and title
        
    Returns:
        Dict containing article and title, or None if article is missing
    """
    logger.info("Starting extract_article processor")
    article = message.get("article", "")
    title = message.get("title", "")
    
    if not article:
        logger.error("No article found in message")
        return None
        
    return {"article": article, "title": title}

def extract_keywords(lines: List[str], title: str) -> str:
    """Extract keywords from article lines or use title as fallback.
    
    Args:
        lines: List of lines from the article
        title: Article title to use as fallback
        
    Returns:
        Keywords string extracted from article or title
    """
    keywords = ""
    for line in lines:
        if line.startswith('#'):
            keywords = line.strip('#').strip()
            break
    
    if not keywords:
        keywords = title if title else "generic images"
        logger.info(f"No keywords found, using title: {keywords}")
    
    logger.info(f"Extracted keywords: {keywords}")
    return keywords

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

def image_validator_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """Check and replace unreachable image URLs in the article.
    
    Args:
        data: Dictionary containing article and title
        
    Returns:
        Updated data with validated image URLs
    """
    logger.info("Starting image validator processor")
    
    article = data["article"]
    title = data["title"]
    
    image_searcher = ImageSearch()
    lines = article.strip().split('\n')
    keywords = extract_keywords(lines, title)
    
    modified_lines = []
    for line in lines:
        if line.startswith('http://') or line.startswith('https://'):
            url_parts = line.split(',', 1)
            url = url_parts[0].strip()
            line = process_image_url(line, url, url_parts, image_searcher, keywords)
        
        modified_lines.append(line)
    
    data["article"] = '\n'.join(modified_lines)
    return data

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

def script_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """Perform additional script processing including ensuring minimum image count.
    
    Args:
        data: Dictionary containing article and title
        
    Returns:
        Updated data with processed script
    """
    logger.info("Starting script processor")
    
    article = data["article"]
    title = data["title"]
    
    lines = article.strip().split('\n')
    image_lines = get_image_lines(lines)
    image_count = len(image_lines)
    
    logger.info(f"Found {image_count} image lines in the article")
    
    if image_count < MIN_REQUIRED_IMAGES:
        keywords = extract_keywords(lines, title)
        logger.info(f"Using keywords '{keywords}' to find additional images")
        
        image_searcher = ImageSearch()
        new_images_needed = MIN_REQUIRED_IMAGES - image_count
        
        lines = add_additional_images(
            lines, image_lines, new_images_needed, image_searcher, keywords
        )
        
        data["article"] = '\n'.join(lines)
    
    return data

def s2j_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert script to JSON format.
    
    Args:
        data: Dictionary containing article and title
        
    Returns:
        Updated data with JSON-formatted script
    """
    logger.info("Starting script2json processor")
    return script2json(data["article"])

def create_complete_pipeline() -> ProcessorChain:
    """Create and configure the complete processing pipeline.
    
    Returns:
        Configured processing pipeline
    """
    chain = ProcessorChain("complete_pipeline")
    chain.add_processor(extract_article, "extract_article")
    
    # Check if we're using the real ImageSearch or the mock version
    if not isinstance(ImageSearch, type) or ImageSearch.__name__ != "MockImageSearch":
        # Only add image processors if the real ImageSearch is available
        chain.add_processor(image_validator_processor, "image_validator_processor")
        chain.add_processor(video_processor, "video_processor")
        chain.add_processor(script_processor, "script_processor")
    else:
        logger.warning("Skipping image and video processors due to missing dependencies")
    
    chain.add_processor(s2j_processor, "script2json")
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
        if processor:
            processor.close()
            logger.info("Processor closed successfully")
    except Exception as e:
        logger.error(f"Error closing processor during shutdown: {e}")
    finally:
        # Force exit - don't return to caller
        logger.info("Exiting application")
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
            signal.signal(signal.SIGINT, lambda sig, frame: handle_shutdown(processor, sig, frame))
            signal.signal(signal.SIGTERM, lambda sig, frame: handle_shutdown(processor, sig, frame))
            
            logger.info(f"Chain processor '{PROCESSOR_ID}' running. Press Ctrl+C to exit.")
            
            # Keep main thread alive
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            # This should not be reached if signal handler works properly
            # But keeping as a fallback
            logger.info("KeyboardInterrupt received directly. Shutting down...")
            if processor:
                processor.close()
            sys.exit(0)
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
