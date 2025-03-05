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

def image_validator_processor(article):
    """Check and replace unreachable image URLs in the article"""
    logger.info("Starting image validator processor")
    
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

def script_processor(article):
    """Perform additional script processing"""
    logger.info("Starting script processor")
    
    # Count existing image lines
    lines = article.strip().split('\n')
    image_lines = [line for line in lines if line.startswith('http://') or line.startswith('https://')]
    image_count = len(image_lines)
    
    logger.info(f"Found {image_count} image lines in the article")
    
    # If we have fewer than 5 images, add more
    if image_count < 5:
        # Extract keywords from the script (lines starting with #)
        keywords = ""
        for line in lines:
            if line.startswith('#'):
                keywords = line.strip('#').strip()
                break
        
        # If no keywords found, set a default
        if not keywords:
            keywords = "generic images"
        
        logger.info(f"Using keywords '{keywords}' to find additional images")
        
        # Initialize image search helper
        image_searcher = ImageSearch()
        
        # Add new image lines
        new_images_needed = 5 - image_count
        added_images = []
        
        for i in range(new_images_needed):
            new_url = image_searcher.get_alternative_image(keywords)
            if new_url:
                added_images.append(new_url)
                logger.info(f"Added new image: {new_url}")
        
        # Insert new image lines after existing images or at the end if no images exist
        if image_lines:
            # Find the position of the last image line
            last_img_pos = 0
            for i, line in enumerate(lines):
                if line.startswith('http://') or line.startswith('https://'):
                    last_img_pos = i
            
            # Add comment and new images after the last image line
            lines.insert(last_img_pos + 1, "# Auto-generated additional images:")
            for i, img in enumerate(added_images):
                lines.insert(last_img_pos + 2 + i, img)
        else:
            # If no images exist, add them at the end
            lines.append("# Auto-generated images:")
            lines.extend(added_images)
        
        # Join lines back into a single string
        article = '\n'.join(lines)
        logger.info(f"Added {len(added_images)} new images to reach minimum of 5 images")
    
    return article

def s2j_processor(script):
    """Convert script to JSON format"""
    logger.info("Starting script2json processor")
    return script2json(script)

def create_complete_pipeline():
    chain = ProcessorChain("complete_pipeline")
    chain.add_processor(extract_article, "extract_article")
    chain.add_processor(image_validator_processor, "image_validator_processor")
    chain.add_processor(script_processor, "script_processor")
    chain.add_processor(s2j_processor, "script2json")
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
