import time
from typing import Any, Callable, Dict, List, Optional, Union
from utils.logger import logger

class ProcessorChain:
    """
    Chains multiple message processors together in a processing pipeline.
    Each processor receives the output of the previous processor.
    """
    def __init__(self, name: str = "chain"):
        self.name = name
        self.processors = []
        self.error_handler = None
        logger.info(f"Created processor chain: {name}")
        
    def add_processor(self, processor_fn: Callable, name: str = None) -> 'ProcessorChain':
        """
        Add a processor function to the chain
        
        Args:
            processor_fn: Function that takes a message and returns processed result
            name: Optional name for this processor (for logging)
        
        Returns:
            Self for method chaining
        """
        processor_name = name or f"processor_{len(self.processors) + 1}"
        self.processors.append((processor_fn, processor_name))
        logger.info(f"Added {processor_name} to chain {self.name}")
        return self
        
    def set_error_handler(self, handler_fn: Callable) -> 'ProcessorChain':
        """
        Set a function to handle errors in the processing chain
        
        Args:
            handler_fn: Function that takes (message, error, processor_name)
                        and returns a message or None
        
        Returns:
            Self for method chaining
        """
        self.error_handler = handler_fn
        logger.info(f"Set error handler for chain {self.name}")
        return self
        
    def process(self, message: Any) -> Any:
        """
        Process a message through the entire chain
        
        Args:
            message: The input message
            
        Returns:
            The processed message after passing through all processors,
            or None if the message was dropped
        """
        current_message = message
        start_time = time.time()
        
        logger.debug(f"Chain {self.name}: Starting processing")
        
        for processor_fn, processor_name in self.processors:
            if current_message is None:
                logger.debug(f"Chain {self.name}: Message dropped by previous processor")
                return None
                
            processor_start = time.time()
            
            try:
                logger.debug(f"Chain {self.name}: Running {processor_name}")
                current_message = processor_fn(current_message)
                processor_time = time.time() - processor_start
                logger.debug(f"Chain {self.name}: {processor_name} completed in {processor_time:.3f}s")
                
            except Exception as e:
                logger.error(f"Chain {self.name}: Error in {processor_name}: {str(e)}")
                
                if self.error_handler:
                    try:
                        logger.debug(f"Chain {self.name}: Attempting error recovery")
                        current_message = self.error_handler(message, e, processor_name)
                        if current_message is None:
                            logger.debug(f"Chain {self.name}: Message dropped by error handler")
                            return None
                    except Exception as handler_error:
                        logger.error(f"Chain {self.name}: Error handler failed: {str(handler_error)}")
                        return None
                else:
                    # No error handler, so the chain is broken
                    return None
        
        total_time = time.time() - start_time
        logger.debug(f"Chain {self.name}: Processing completed in {total_time:.3f}s")
        return current_message


# Example usage when running directly
if __name__ == "__main__":
    # Set up logging to see debug messages
    logger.set_level('DEBUG')
    
    # Example processors
    def add_timestamp(message):
        if isinstance(message, dict):
            message["timestamp"] = time.time()
        return message
        
    def uppercase_strings(message):
        if isinstance(message, dict):
            for key, value in message.items():
                if isinstance(value, str):
                    message[key] = value.upper()
        return message
        
    def validate_message(message):
        if isinstance(message, dict) and "id" in message:
            return message
        raise ValueError("Invalid message: missing 'id' field")
    
    # Example error handler
    def handle_error(message, error, processor_name):
        logger.warning(f"Error in {processor_name}: {error}")
        if isinstance(message, dict):
            message["error"] = str(error)
            message["failed_processor"] = processor_name
            return message
        return None
    
    # Create a chain
    chain = ProcessorChain("example_chain")
    chain.add_processor(add_timestamp, "add_timestamp")
    chain.add_processor(uppercase_strings, "uppercase")
    chain.add_processor(validate_message, "validate")
    chain.set_error_handler(handle_error)
    
    # Process a valid message
    result1 = chain.process({"id": 1, "content": "test message"})
    logger.info(f"Valid message result: {result1}")
    
    # Process an invalid message
    result2 = chain.process({"content": "invalid message"})
    logger.info(f"Invalid message result: {result2}")
