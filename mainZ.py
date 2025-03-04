import json
import sys
import time
import signal
import random
import os
import re

# Update imports to reference the src directory
from src.script2json import script2json
from src.chained_processor import ProcessorChain
from src.rabbitmq_processor import ChainedRabbitMQProcessor
from src.logger import logger
from src.config import INPUT_QUEUE, OUTPUT_QUEUE, PROCESSOR_ID, get_log_level
from src.image_search import ImageSearch

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
    """Generate script from article with image verification and replacement"""
    logger.info("Starting generate_script processor")
    
    # Initialize image search helper
    image_searcher = ImageSearch()
    
    # Extract keywords from the script (lines starting with #)
    keywords = ""
    lines = article.strip().split('\n')
    for line in lines:
        if line.startswith('#'):
            keywords = line.strip('#').strip()
            break
    
    # If no keywords found, set a default
    if not keywords:
        keywords = "generic images"
    
    logger.info(f"Extracted keywords: {keywords}")
    
    # Process each line and replace unreachable image URLs
    modified_lines = []
    for line in lines:
        if line.startswith('http://') or line.startswith('https://'):
            # Extract the URL part (before any comma)
            url_parts = line.split(',', 1)
            url = url_parts[0].strip()
            
            # Check if this URL is an image (not a video)
            is_image = bool(re.search(r'\.(jpg|jpeg|png|gif|bmp|webp|tiff|svg)(\?|$|#)', url.lower()))
            
            # For images, check if URL is accessible
            if is_image and not image_searcher.is_url_accessible(url):
                logger.warning(f"Image URL not accessible: {url}")
                
                # Get alternative image based on keywords
                new_url = image_searcher.get_alternative_image(keywords)
                
                if new_url:
                    logger.info(f"Replacing with alternative image: {new_url}")
                    
                    # Replace the URL in the original line
                    if len(url_parts) > 1:
                        line = f"{new_url},{url_parts[1]}"
                    else:
                        line = new_url
                    
                    # Add a comment to indicate replacement
                    modified_lines.append(f"# Original unreachable image: {url}")
            
        modified_lines.append(line)
    
    # Join lines back into a single string
    return '\n'.join(modified_lines)

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
