import json
import sys
import time
import signal
import random
from processor_chain import ProcessorChain
from chained_rabbitmq_processor import ChainedRabbitMQProcessor
from utils.logger import logger

# Example processor functions for different processing chains

def validate_structure(message):
    """Validate the basic structure of incoming messages"""
    if not isinstance(message, dict):
        raise ValueError("Message must be a dictionary")
    
    if "id" not in message:
        message["id"] = f"auto_generated_{int(time.time())}"
        logger.info(f"Added auto-generated ID to message: {message['id']}")
        
    return message

def clean_data(message):
    """Clean and normalize data fields"""
    if isinstance(message, dict):
        # Trim string values
        for key, value in message.items():
            if isinstance(value, str):
                message[key] = value.strip()
        
        # Ensure timestamp
        if "timestamp" not in message:
            message["timestamp"] = time.time()
            logger.debug("Added timestamp to message")
            
    return message

def enrich_data(message):
    """Add additional information to the message"""
    if isinstance(message, dict):
        message["enriched"] = True
        message["processing_host"] = "worker-01"
        message["enriched_at"] = time.time()
        
        # Example: Add geo data if message has coordinates
        if "lat" in message and "lon" in message:
            message["location"] = {
                "coordinates": [message["lat"], message["lon"]],
                "accuracy": "high" 
            }
            
    return message

def compute_metrics(message):
    """Calculate metrics based on message data"""
    if isinstance(message, dict):
        # Example: Calculate a risk score based on some fields
        if "age" in message and "value" in message:
            age = message["age"]
            value = message["value"]
            # Simple mock formula
            risk_score = (100 - min(age, 100)) * (value / 1000)
            message["metrics"] = {"risk_score": risk_score}
            
    return message

def transform_format(message):
    """Transform message to a different format"""
    if isinstance(message, dict):
        # Create new message structure
        return {
            "messageId": message.get("id"),
            "data": {
                "content": message.get("content"),
                "source": message.get("source")
            },
            "metadata": {
                "timestamp": message.get("timestamp", time.time()),
                "enriched": message.get("enriched", False),
                "metrics": message.get("metrics", {})
            }
        }
    return message

def filter_by_condition(message):
    """Filter messages based on conditions"""
    if isinstance(message, dict):
        # Example: Only allow messages with certain criteria
        if message.get("priority", 0) >= 5:
            return message
        
        if message.get("source") == "critical-system":
            return message
            
        # Return None to drop the message
        return None
        
    return message

def add_routing_info(message):
    """Add routing information for message delivery"""
    if isinstance(message, dict):
        # Example routing logic
        message["routing"] = {
            "destination": "primary",
            "timestamp": time.time(),
            "ttl": 3600  # Time to live in seconds
        }
        
        # Add routing based on message content
        if "metrics" in message:
            risk_score = message.get("metrics", {}).get("risk_score", 0)
            if risk_score > 70:
                message["routing"]["destination"] = "high-priority"
                message["routing"]["ttl"] = 7200
            
    return message

def error_handler(message, error, processor_name):
    """Handle errors in processors"""
    logger.error(f"Error occurred in {processor_name}: {str(error)}")
    
    if isinstance(message, dict):
        message["processing_error"] = {
            "processor": processor_name,
            "error": str(error),
            "timestamp": time.time()
        }
        return message  # Continue with error information added
    
    return None  # Drop the message if it's not a dict

def create_validation_chain():
    """Create a chain that validates and cleans data"""
    chain = ProcessorChain("validation_chain")
    chain.add_processor(validate_structure, "structure_validator")
    chain.add_processor(clean_data, "data_cleaner")
    chain.set_error_handler(error_handler)
    return chain

def create_enrichment_chain():
    """Create a chain that enriches data with additional information"""
    chain = ProcessorChain("enrichment_chain")
    chain.add_processor(enrich_data, "data_enricher")
    chain.add_processor(compute_metrics, "metrics_calculator")
    chain.set_error_handler(error_handler)
    return chain

def create_delivery_chain():
    """Create a chain that prepares messages for delivery"""
    chain = ProcessorChain("delivery_chain")
    chain.add_processor(filter_by_condition, "content_filter")
    chain.add_processor(transform_format, "format_transformer")
    chain.add_processor(add_routing_info, "routing_director")
    chain.set_error_handler(error_handler)
    return chain

def create_complete_pipeline():
    """Create a complete processing pipeline combining all steps"""
    chain = ProcessorChain("complete_pipeline")
    # Validation & cleaning
    chain.add_processor(validate_structure, "structure_validator")
    chain.add_processor(clean_data, "data_cleaner")
    # Enrichment
    chain.add_processor(enrich_data, "data_enricher")
    chain.add_processor(compute_metrics, "metrics_calculator")
    # Delivery preparation
    chain.add_processor(filter_by_condition, "content_filter")
    chain.add_processor(transform_format, "format_transformer")
    chain.add_processor(add_routing_info, "routing_director")
    chain.set_error_handler(error_handler)
    return chain

def main():
    # Configure logger for more detailed output
    logger.set_level('INFO')
    
    # Available chains
    chains = {
        "validation": create_validation_chain,
        "enrichment": create_enrichment_chain,
        "delivery": create_delivery_chain,
        "complete": create_complete_pipeline
    }
    
    # Parse command line arguments
    chain_name = "complete"
    if len(sys.argv) > 1 and sys.argv[1] in chains:
        chain_name = sys.argv[1]
    
    # Get queue names from command line or use defaults
    input_queue = 'chain_input'
    if len(sys.argv) > 2:
        input_queue = sys.argv[2]
    
    output_queue = f'{input_queue}_processed'
    if len(sys.argv) > 3:
        output_queue = sys.argv[3]
    
    # Create chain
    chain = chains[chain_name]()
    
    # Create RabbitMQ processor
    processor = ChainedRabbitMQProcessor()
    
    # Connect to RabbitMQ
    if not processor.connect():
        logger.critical("Failed to connect to RabbitMQ. Exiting.")
        sys.exit(1)
    
    # Set up signal handlers for graceful shutdown
    def handle_shutdown(sig, frame):
        logger.info("\nShutting down processor...")
        processor.close()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Process queue with chain
    processor.process_with_chain(input_queue, chain, output_queue)
    
    logger.info(f"Started {chain_name} processing chain from {input_queue} to {output_queue}")
    
    # Publish test message if requested
    if "--test" in sys.argv:
        test_message = {
            "id": f"test_{int(time.time())}",
            "content": "Test message for chain processing",
            "source": "test-script",
            "priority": random.randint(1, 10),
            "value": random.randint(100, 1000),
            "age": random.randint(10, 90),
            "timestamp": time.time()
        }
        processor.publish(input_queue, test_message)
        logger.info(f"Published test message to {input_queue}")
        logger.debug(f"Test message content: {test_message}")
    
    logger.info(f"Chain processor '{chain_name}' running. Press Ctrl+C to exit.")
    
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
