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
# Import các processor từ package mới
from src.processor import extract_article, image_processor, script_processor, s2j_processor, video_processor

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

def create_complete_pipeline():
    """Tạo và cấu hình pipeline xử lý hoàn chỉnh"""
    logger.info(f"Creating processing pipeline for processor ID: {PROCESSOR_ID}")
    
    chain = ProcessorChain("complete_pipeline")
    
    # Thêm các bước xử lý vào pipeline
    logger.debug("Adding extract_article processor to pipeline")
    chain.add_processor(extract_article, "extract_article")
    
    logger.debug("Adding image_processor to pipeline")
    chain.add_processor(image_processor, "image_processor")
    
    logger.debug("Adding video_processor to pipeline")
    chain.add_processor(video_processor, "video_processor")
    
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
    logger.set_level(log_level)
    logger.info(f"Set log level to: {log_level}")
    
    # Cấu hình xử lý tín hiệu shutdown
    def handle_shutdown(sig, frame):
        logger.warning(f"Received signal {sig}. Shutting down...")
        # Ghi thời gian shutdown và thời gian chạy
        run_time = datetime.now() - START_TIME
        logger.info(f"Application shutting down after running for {run_time}")
        sys.exit(0)
    
    # Đăng ký các tín hiệu cần bắt
    signal.signal(signal.SIGINT, handle_shutdown)  # Ctrl+C
    signal.signal(signal.SIGTERM, handle_shutdown)  # kill
    
    try:
        # Bắt đầu hoạt động của máy xử lý thông điệp
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
