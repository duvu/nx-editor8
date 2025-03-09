import json
import sys
import time
import signal
import random
import os
import re
import traceback
from datetime import datetime

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
    logger.debug(f"Added {current_dir} to sys.path")

# Khởi tạo thời gian bắt đầu ứng dụng cho logs
START_TIME = datetime.now()
logger.info(f"Application starting at {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"Running from directory: {current_dir}")
logger.info(f"Python version: {sys.version}")

def error_handler(message, error, processor_name):
    """Handle errors in processors"""
    logger.info(f"Starting error_handler for processor: {processor_name}")
    logger.error(f"Error occurred in {processor_name}: {str(error)}")
    logger.error(f"Error stack trace: {traceback.format_exc()}")
    
    # Ghi log thêm thông tin về message để debug
    if isinstance(message, dict):
        keys = list(message.keys())
        logger.debug(f"Message keys available: {keys}")
        
        # Tạo ID lỗi duy nhất để dễ theo dõi
        error_id = f"ERR-{int(time.time())}-{random.randint(1000, 9999)}"
        logger.error(f"Error ID: {error_id}")
        
        message["processing_error"] = {
            "error_id": error_id,
            "processor": processor_name,
            "error": str(error),
            "timestamp": time.time(),
            "error_type": type(error).__name__
        }
        logger.info(f"Added error information to message with error_id: {error_id}")
        return message  # Continue with error information added
    
    logger.warning(f"Message is not a dict, cannot add error information. Type: {type(message)}")
    return None  # Drop the message if it's not a dict

def extract_article(message):
    """Extract article and title from message"""
    logger.info("Starting extract_article processor")
    
    # Log message type and structure
    logger.debug(f"Message type: {type(message)}")
    if isinstance(message, dict):
        keys = list(message.keys())
        logger.debug(f"Message keys: {keys}")
    
    # Extract article from message. It's the field "article"
    article = message.get("article", "")
    title = message.get("title", "")  # Extract the title
    
    # Logging article length and title for debugging
    article_length = len(article) if article else 0
    logger.info(f"Extracted article (length: {article_length} chars)")
    logger.info(f"Extracted title: '{title}'")
    
    if not article:
        logger.error("No article found in message")
        return None
    
    # Log the first few lines of the article for context
    if article_length > 0:
        preview_lines = article.split('\n')[:3]
        preview = '\n'.join(preview_lines)
        logger.debug(f"Article preview (first 3 lines):\n{preview}...")
    
    return {"article": article, "title": title}  # Return both as a dictionary

def image_validator_processor(data):
    """Check and replace unreachable image URLs in the article"""
    logger.info("Starting image validator processor")
    start_time = time.time()
    
    # Validate input
    if not isinstance(data, dict):
        logger.error(f"Expected dict input but got {type(data)}")
        return None
    
    # Extract article and title from the input data
    article = data.get("article", "")
    title = data.get("title", "")
    
    if not article:
        logger.warning("Empty article received in image validator processor")
        return data
    
    logger.debug(f"Processing article with {len(article)} chars and title: '{title}'")
    
    # Initialize image search helper
    image_searcher = ImageSearch()
    
    # Extract keywords from the script (lines starting with #)
    keywords = ""
    lines = article.strip().split('\n')
    logger.debug(f"Article split into {len(lines)} lines")
    
    for i, line in enumerate(lines):
        if line.startswith('#'):
            keywords = line.strip('#').strip()
            logger.debug(f"Found keywords at line {i+1}: '{keywords}'")
            break
    
    # If no keywords found, use title instead of default
    if not keywords:
        keywords = title if title else "generic images"
        logger.info(f"No keywords found in text, using title as keywords: '{keywords}'")
    
    logger.info(f"Using keywords for image search: '{keywords}'")
    
    # Process each line and replace unreachable image URLs
    modified_lines = []
    replaced_count = 0
    checked_count = 0
    
    for i, line in enumerate(lines):
        if line.startswith('http://') or line.startswith('https://'):
            # Extract the URL part (before any comma)
            url_parts = line.split(',', 1)
            url = url_parts[0].strip()
            
            # Check if this URL is an image (not a video)
            is_image = bool(re.search(r'\.(jpg|jpeg|png|gif|bmp|webp|tiff|svg)(\?|$|#)', url.lower()))
            
            if is_image:
                logger.debug(f"Checking image URL at line {i+1}: {url}")
                checked_count += 1
                
                # For images, check if URL is accessible
                url_start_time = time.time()
                is_accessible = image_searcher.is_url_accessible(url)
                url_check_time = time.time() - url_start_time
                
                logger.debug(f"URL check took {url_check_time:.2f}s, accessible: {is_accessible}")
                
                if not is_accessible:
                    logger.warning(f"Image URL not accessible at line {i+1}: {url}")
                    
                    # Get alternative image based on keywords
                    search_start_time = time.time()
                    new_url = image_searcher.get_alternative_image(keywords)
                    search_time = time.time() - search_start_time
                    
                    if new_url:
                        logger.info(f"Found replacement image in {search_time:.2f}s: {new_url}")
                        replaced_count += 1
                        
                        # Replace the URL in the original line
                        if len(url_parts) > 1:
                            line = f"{new_url},{url_parts[1]}"
                            logger.debug(f"Replaced URL with parameters: {line}")
                        else:
                            line = new_url
                            logger.debug(f"Replaced URL: {line}")
                    else:
                        logger.warning(f"Failed to find alternative image for '{keywords}'")
            else:
                logger.debug(f"Line {i+1} contains URL but not an image: {url}")
            
        modified_lines.append(line)
    
    # Join lines back into a single string
    data["article"] = '\n'.join(modified_lines)
    
    processing_time = time.time() - start_time
    logger.info(f"Image validation complete. Checked {checked_count} images, replaced {replaced_count} unreachable images in {processing_time:.2f}s")
    
    return data

def script_processor(data):
    """Perform additional script processing"""
    logger.info("Starting script processor")
    start_time = time.time()
    
    # Validate input
    if not isinstance(data, dict):
        logger.error(f"Expected dict input but got {type(data)}")
        return None
    
    # Extract article and title
    article = data.get("article", "")
    title = data.get("title", "")
    
    if not article:
        logger.warning("Empty article received in script processor")
        return data
    
    logger.debug(f"Processing article with {len(article)} chars and title: '{title}'")
    
    # Count existing image lines
    lines = article.strip().split('\n')
    logger.debug(f"Article split into {len(lines)} lines")
    
    image_lines = [line for line in lines if line.startswith('http://') or line.startswith('https://')]
    image_count = len(image_lines)
    
    logger.info(f"Found {image_count} image lines in the article")
    
    # If we have fewer than 5 images, add more
    if image_count < 5:
        logger.info(f"Article has fewer than 5 images ({image_count}). Adding more images...")
        
        # Extract keywords from the script (lines starting with #)
        keywords = ""
        for i, line in enumerate(lines):
            if line.startswith('#'):
                keywords = line.strip('#').strip()
                logger.debug(f"Found keywords at line {i+1}: '{keywords}'")
                break
        
        # If no keywords found, use title instead of default
        if not keywords:
            keywords = title if title else "generic images"
            logger.info(f"No keywords found in text, using title as keywords: '{keywords}'")
        
        logger.info(f"Using keywords for additional images: '{keywords}'")
        
        # Initialize image search helper
        image_searcher = ImageSearch()
        
        # Add new image lines
        new_images_needed = 5 - image_count
        added_images = []
        
        logger.info(f"Attempting to add {new_images_needed} new images")
        
        for i in range(new_images_needed):
            search_start_time = time.time()
            new_url = image_searcher.get_alternative_image(keywords)
            search_time = time.time() - search_start_time
            
            if new_url:
                added_images.append(new_url)
                logger.info(f"Added new image ({i+1}/{new_images_needed}) in {search_time:.2f}s: {new_url}")
            else:
                logger.warning(f"Failed to find image {i+1}/{new_images_needed} for '{keywords}'")
        
        # Insert new image lines after existing images or at the end if no images exist
        if image_lines:
            # Find the position of the last image line
            last_img_pos = 0
            for i, line in enumerate(lines):
                if line.startswith('http://') or line.startswith('https://'):
                    last_img_pos = i
                    logger.debug(f"Found last image at line {i+1}: {line[:60]}...")
            
            # Add new images after the last image line
            logger.debug(f"Inserting new images after position {last_img_pos}")
            for i, img in enumerate(added_images):
                insert_pos = last_img_pos + 1 + i
                lines.insert(insert_pos, img)
                logger.debug(f"Inserted image at position {insert_pos}")
        else:
            # If no images exist, add them at the end
            logger.debug(f"No existing images. Adding {len(added_images)} images to the end")
            lines.extend(added_images)
        
        # Join lines back into a single string
        data["article"] = '\n'.join(lines)
        logger.info(f"Added {len(added_images)} new images to reach minimum of 5 images")
    else:
        logger.info(f"Article already has {image_count} images (≥5). No need to add more.")
    
    processing_time = time.time() - start_time
    logger.info(f"Script processing completed in {processing_time:.2f}s")
    
    return data

def s2j_processor(data):
    """Convert script to JSON format"""
    logger.info("Starting script2json processor")
    start_time = time.time()
    
    # Validate input
    if not isinstance(data, dict):
        logger.error(f"Expected dict input but got {type(data)}")
        return None
    
    # Extract article
    article = data.get("article", "")
    if not article:
        logger.error("Empty article received in script2json processor")
        return None
        
    logger.debug(f"Converting article to JSON (length: {len(article)} chars)")
    
    try:
        # Thực hiện chuyển đổi sang JSON
        result = script2json(article)
        
        # Log kết quả
        if isinstance(result, dict):
            sections = result.get("sections", [])
            section_count = len(sections) if sections else 0
            logger.info(f"Converted script to JSON with {section_count} sections")
            
            # Log chi tiết hơn về cấu trúc JSON
            logger.debug(f"JSON result keys: {list(result.keys())}")
            if section_count > 0:
                logger.debug(f"First section: {sections[0] if sections else 'No sections'}")
        else:
            logger.warning(f"Unexpected result type from script2json: {type(result)}")
        
        processing_time = time.time() - start_time
        logger.info(f"script2json conversion completed in {processing_time:.2f}s")
        
        return result
    except Exception as e:
        logger.error(f"Error in script2json conversion: {str(e)}")
        logger.error(f"Error stack trace: {traceback.format_exc()}")
        
        # Tạo một JSON lỗi tối thiểu thay vì trả về None
        error_json = {
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": time.time(),
            "original_length": len(article)
        }
        logger.warning("Returning error JSON instead of None")
        return error_json

def create_complete_pipeline():
    """Tạo và cấu hình pipeline xử lý hoàn chỉnh"""
    logger.info(f"Creating processing pipeline for processor ID: {PROCESSOR_ID}")
    
    chain = ProcessorChain("complete_pipeline")
    
    # Thêm các bước xử lý vào pipeline
    logger.debug("Adding extract_article processor to pipeline")
    chain.add_processor(extract_article, "extract_article")
    
    logger.debug("Adding image_validator_processor to pipeline")
    chain.add_processor(image_validator_processor, "image_validator_processor")
    
    logger.debug("Adding script_processor to pipeline")
    chain.add_processor(script_processor, "script_processor")
    
    logger.debug("Adding s2j_processor to pipeline")
    chain.add_processor(s2j_processor, "script2json")
    
    logger.debug("Setting error handler")
    chain.set_error_handler(error_handler)
    
    logger.info("Complete processing pipeline created successfully")
    return chain

def run_processor(input_queue="chain_input", output_queue=None):
    """Khởi tạo và chạy bộ xử lý RabbitMQ"""
    logger.info(f"Initializing processor with input queue: '{input_queue}', output queue: '{output_queue}'")
    
    # Create RabbitMQ processor
    processor = ChainedRabbitMQProcessor()
    
    # Connect to RabbitMQ
    logger.info("Attempting to connect to RabbitMQ...")
    if not processor.connect():
        logger.critical("Failed to connect to RabbitMQ. Exiting.")
        return False
    
    # Tạo pipeline xử lý
    pipeline = create_complete_pipeline()
    
    # Process queue with chain
    logger.info(f"Setting up message processing from '{input_queue}' to '{output_queue}'")
    processor.process_with_chain(input_queue, pipeline, output_queue)
    logger.info(f"Successfully started processing chain from '{input_queue}' to '{output_queue}'")
    
    return processor

def main():
    """Hàm chính của ứng dụng"""
    # Đặt cấp độ log dựa trên cấu hình
    log_level = get_log_level()
    logger.info(f"Setting log level to: {log_level}")
    logger.set_level(log_level)
    
    # In thông tin cấu hình để debug
    logger.info(f"Processor ID: {PROCESSOR_ID}")
    logger.info(f"Input Queue: {INPUT_QUEUE}")
    logger.info(f"Output Queue: {OUTPUT_QUEUE}")
    
    # Flag kiểm soát vòng lặp chính
    should_run = True
    
    # Khởi tạo bộ xử lý với các queue được cấu hình
    logger.info("Initializing message processor...")
    processor = run_processor(INPUT_QUEUE, OUTPUT_QUEUE)

    if not processor:
        logger.critical("Failed to initialize processor. Exiting.")
        sys.exit(1)
    
    # Xử lý tắt hệ thống một cách an toàn
    def handle_shutdown(sig, frame):
        nonlocal should_run
        
        # Ngăn xử lý nhiều lần
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        
        sig_name = signal.Signals(sig).name if hasattr(signal, 'Signals') else str(sig)
        logger.info(f"\nReceived signal {sig_name}. Initiating graceful shutdown...")
        
        # Đặt cờ thoát
        should_run = False
        
        # Tắt processor
        shutdown_start = time.time()
        try:
            processor.close()
            shutdown_time = time.time() - shutdown_start
            logger.info(f"Processor shutdown completed in {shutdown_time:.2f}s")
        except Exception as e:
            logger.error(f"Error during processor shutdown: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
        
        # Tính toán thời gian hoạt động
        uptime = datetime.now() - START_TIME
        hours, remainder = divmod(uptime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        logger.info(f"Application uptime: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        logger.info("Exiting application")
        
        # Không gọi sys.exit() từ handler tín hiệu - để main loop thoát tự nhiên
    
    # Đăng ký các xử lý tín hiệu
    logger.debug("Registering signal handlers for SIGINT and SIGTERM")
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    logger.info(f"Chain processor '{PROCESSOR_ID}' running. Press Ctrl+C to exit.")
    logger.info(f"Listening for messages on queue '{INPUT_QUEUE}'")
    
    # Keep main thread alive
    try:
        logger.debug("Entering main loop")
        uptime_logged = 0
        
        # Thay đổi vòng lặp để kiểm tra cờ should_run
        while should_run:
            time.sleep(0.5)  # Giảm thời gian chờ để phản ứng nhanh hơn với tín hiệu
            
            # Log uptime hàng giờ để biết ứng dụng vẫn hoạt động
            uptime = (datetime.now() - START_TIME).total_seconds()
            hours = int(uptime // 3600)
            
            if hours > uptime_logged:
                uptime_logged = hours
                logger.info(f"Application uptime: {hours} hours")
                
        logger.info("Main loop exited cleanly")
    except KeyboardInterrupt:
        # Điều này có thể không được gọi vì chúng ta đã xử lý SIGINT với handler
        logger.info("KeyboardInterrupt received in main loop")
        should_run = False
    except Exception as e:
        # Bắt các ngoại lệ khác trong vòng lặp chính
        logger.error(f"Unexpected error in main loop: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
    finally:
        # Đảm bảo processor được đóng dù có lỗi xảy ra
        if processor:
            logger.info("Shutting down processor from finally block")
            try:
                processor.close()
                logger.info("Processor closed successfully")
            except Exception as e:
                logger.error(f"Error closing processor in finally block: {str(e)}")
                logger.error(f"Stack trace: {traceback.format_exc()}")
        
        logger.info("Application shutdown complete")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {str(e)}")
        logger.critical(f"Stack trace: {traceback.format_exc()}")
        sys.exit(1)
