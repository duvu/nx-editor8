import json
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, Protocol
from dataclasses import dataclass
from .logger import logger

class Processor(Protocol):
    def process(self, message: Any) -> Any:
        ...

@dataclass
class ProcessorResult:
    output: Any
    success: bool
    error: Optional[Exception] = None
    failed_processor: Optional[str] = None
    timings: Optional[List[Tuple[str, float]]] = None

class ProcessorChain:
    """
    Chains multiple message processors together in a processing pipeline.
    Each processor receives the output of the previous processor.
    Processors can be functions or objects with a .process() method.
    """
    def __init__(self, name: str = "chain"):
        self.name = name
        self.processors: List[Tuple[Union[Callable, Processor], str, Optional[str]]] = []
        self.error_handler: Optional[Callable[[Any, Exception, str], Any]] = None
        logger.info(f"Created processor chain: {name}")

    def add_processor(self, processor: Union[Callable, Processor], name: Optional[str] = None, description: Optional[str] = None) -> 'ProcessorChain':
        """
        Add a processor function or object to the chain
        Args:
            processor: Function or object with .process(message) method
            name: Optional name for this processor (for logging)
            description: Optional description for this processor
        Returns:
            Self for method chaining
        """
        processor_name = name or getattr(processor, '__name__', processor.__class__.__name__)
        self.processors.append((processor, processor_name, description))
        logger.info(f"Added {processor_name} to chain {self.name}")
        return self

    def set_error_handler(self, handler_fn: Callable[[Any, Exception, str], Any]) -> 'ProcessorChain':
        """
        Set a function to handle errors in the processing chain
        Args:
            handler_fn: Function that takes (message, error, processor_name) and returns a message or None
        Returns:
            Self for method chaining
        """
        self.error_handler = handler_fn
        logger.info(f"Set error handler for chain {self.name}")
        return self

    def reset(self) -> None:
        """Remove all processors and error handler from the chain."""
        self.processors.clear()
        self.error_handler = None
        logger.info(f"Reset processor chain: {self.name}")

    def __repr__(self) -> str:
        return f"<ProcessorChain name={self.name} processors={[n for _, n, _ in self.processors]}>"

    def process(self, message: Any, return_result: bool = False) -> Union[Any, ProcessorResult]:
        """
        Process a message through the entire chain
        Args:
            message: The input message
            return_result: If True, return a ProcessorResult object
        Returns:
            The processed message after passing through all processors, or None if dropped.
            If return_result is True, returns ProcessorResult with details.
        """
        current_message = message
        start_time = time.time()
        timings: List[Tuple[str, float]] = []
        logger.debug(f"Chain {self.name}: Starting processing")
        for processor, processor_name, _ in self.processors:
            if current_message is None:
                logger.debug(f"Chain {self.name}: Message dropped by previous processor")
                if return_result:
                    return ProcessorResult(None, False, None, processor_name, timings)
                return None
            processor_start = time.time()
            try:
                logger.debug(f"Chain {self.name}: Running {processor_name}")
                if hasattr(processor, 'process') and callable(getattr(processor, 'process')):
                    current_message = processor.process(current_message)
                else:
                    current_message = processor(current_message)
                processor_time = time.time() - processor_start
                timings.append((processor_name, processor_time))
                logger.debug(f"Chain {self.name}: {processor_name} completed in {processor_time:.3f}s")
            except Exception as e:
                logger.error(f"Chain {self.name}: Error in {processor_name}: {str(e)}")
                if not self.error_handler:
                    if return_result:
                        return ProcessorResult(None, False, e, processor_name, timings)
                    return None
                try:
                    logger.debug(f"Chain {self.name}: Attempting error recovery")
                    current_message = self.error_handler(message, e, processor_name)
                except Exception as handler_error:
                    logger.error(f"Chain {self.name}: Error handler failed: {str(handler_error)}")
                    if return_result:
                        return ProcessorResult(None, False, handler_error, processor_name, timings)
                    return None
                if current_message is None:
                    logger.debug(f"Chain {self.name}: Message dropped by error handler")
                    if return_result:
                        return ProcessorResult(None, False, e, processor_name, timings)
                    return None
        total_time = time.time() - start_time
        logger.debug(f"Chain {self.name}: Processing completed in {total_time:.3f}s")
        if return_result:
            return ProcessorResult(current_message, True, None, None, timings)
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
        """
        Validate message structure and add ID if missing
        rather than raising an error.
        """
        logger.info(f"Validating message structure: {message}")
        if not isinstance(message, dict):
            logger.warning(f"Invalid message type: {type(message)}, expected dict")
            # Convert to dict if possible
            try:
                if isinstance(message, str):
                    message = {"content": message}
                else:
                    message = {"data": message}
            except:
                message = {"error": "Could not convert to dict"}
        
        # Add ID if missing
        if "id" not in message:
            logger.warning("Message missing 'id' field, adding auto-generated ID")
            message["id"] = f"auto_{int(time.time())}_{id(message)}"
        
        return message
    
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
    
    # Process an "invalid" message (missing ID)
    result2 = chain.process({"content": "invalid message"})
    logger.info(f"Formerly invalid message result: {result2}")
    
    # Process a non-dict message
    result3 = chain.process("just a string")
    logger.info(f"String message result: {result3}")
