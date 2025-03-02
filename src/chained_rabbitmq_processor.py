import json
import os
import signal
import sys
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Union
import pika
from dotenv import load_dotenv
from processor_chain import ProcessorChain
from utils.logger import logger

# Load environment variables
load_dotenv()

class ChainedRabbitMQProcessor:
    """
    RabbitMQ processor that supports chaining multiple processors together.
    Messages flow through a sequence of processors before being published to output.
    """
    def __init__(self):
        # Connection parameters
        self.user = os.getenv('RABBITMQ_USER', 'guest')
        self.password = os.getenv('RABBITMQ_PASSWORD', 'guest')
        self.host = os.getenv('RABBITMQ_URL', 'localhost').split('://')[1] if '://' in os.getenv('RABBITMQ_URL', 'localhost') else os.getenv('RABBITMQ_URL', 'localhost')
        self.port = 5672
        if ':' in self.host:
            self.host, port = self.host.split(':')
            self.port = int(port)
        self.vhost = os.getenv('RABBITMQ_VHOST', '/')
        
        # Connection state
        self.connection = None
        self.channel = None
        self.is_connected = False
        self._subscriptions = {}
        self._running = True
        self._lock = threading.Lock()
        
        logger.info(f"Initialized RabbitMQ processor with host {self.host}:{self.port}")
        
    def connect(self) -> bool:
        """Establish connection to RabbitMQ server"""
        try:
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.vhost,
                credentials=credentials,
                heartbeat=60,
                blocked_connection_timeout=300
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.is_connected = True
            
            logger.info(f"Connected to RabbitMQ at {self.host}:{self.port}{self.vhost}")
            
            # Restore subscriptions after reconnection
            self._restore_subscriptions()
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def _restore_subscriptions(self) -> None:
        """Restore all active subscriptions after reconnection"""
        for queue, data in self._subscriptions.items():
            chain, output_queue, options = data
            logger.info(f"Restoring subscription: {queue} → {output_queue}")
            self.process_with_chain(queue, chain, output_queue, options)
    
    def publish(self, queue: str, message: Any, options: Optional[Dict] = None) -> bool:
        """Publish a message to a queue"""
        if not self.is_connected:
            if not self.connect():
                return False
            
        try:
            # Ensure queue exists
            self.channel.queue_declare(queue=queue, durable=True)
            
            # Convert message to JSON if it's a dict or list
            if isinstance(message, (dict, list)):
                message_body = json.dumps(message)
            elif not isinstance(message, str):
                message_body = str(message)
            else:
                message_body = message
                
            # Set message properties
            properties = pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json',
                **(options or {})
            )
            
            # Publish the message
            self.channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=message_body,
                properties=properties
            )
            logger.debug(f"Published message to {queue}")
            return True
        except Exception as e:
            logger.error(f"Error publishing to queue {queue}: {e}")
            self.is_connected = False
            return False
    
    def process_with_chain(self, input_queue: str, processor_chain: ProcessorChain, 
                          output_queue: str, options: Optional[Dict] = None) -> None:
        """
        Process messages from input_queue through a chain of processors and send to output_queue
        
        Args:
            input_queue: Queue to consume messages from
            processor_chain: ProcessorChain instance containing the processing logic
            output_queue: Queue to publish processed messages to
            options: Additional options for queue declarations
        """
        if not self.is_connected:
            if not self.connect():
                logger.error(f"Cannot process queue {input_queue}: not connected")
                return
        
        try:
            # Store subscription info for reconnection
            self._subscriptions[input_queue] = (processor_chain, output_queue, options)
            
            # Declare queues
            self.channel.queue_declare(queue=input_queue, durable=True)
            self.channel.queue_declare(queue=output_queue, durable=True)
            
            # Set up QoS (prefetch_count)
            self.channel.basic_qos(prefetch_count=1)
            
            def message_handler(ch, method, properties, body):
                try:
                    # Parse message
                    try:
                        message = json.loads(body)
                    except json.JSONDecodeError:
                        message = body.decode('utf-8')
                    
                    logger.info(f"Received message from {input_queue}")
                    logger.debug(f"Message content: {message}")
                    
                    # Process message through the chain
                    processed_message = processor_chain.process(message)
                    
                    # Skip publishing if processor chain returns None
                    if processed_message is not None:
                        # Publish to output queue
                        success = self.publish(output_queue, processed_message)
                        if success:
                            logger.info(f"Processed message published to {output_queue}")
                        else:
                            logger.error(f"Failed to publish processed message to {output_queue}")
                            # Reject and requeue the original message
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                            return
                    else:
                        logger.info(f"Message dropped by processor chain (no output)")
                    
                    # Acknowledge successful processing
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    # Reject and requeue
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
            # Start consuming messages
            self.channel.basic_consume(
                queue=input_queue,
                on_message_callback=message_handler
            )
            
            logger.info(f"Started processing messages from {input_queue} to {output_queue}")
            
            # Start consuming in a separate thread
            consume_thread = threading.Thread(target=self._start_consuming)
            consume_thread.daemon = True
            consume_thread.start()
            
        except Exception as e:
            logger.error(f"Error setting up queue processing {input_queue} → {output_queue}: {e}", exc_info=True)
            self.is_connected = False
    
    def _start_consuming(self) -> None:
        """Start consuming messages in a non-blocking way"""
        try:
            while self._running and self.is_connected:
                with self._lock:
                    if self.channel and self.channel.is_open:
                        # Process messages for a short time then check conditions
                        self.connection.process_data_events(time_limit=1)
                time.sleep(0.1)  # Small sleep to avoid CPU spinning
        except Exception as e:
            logger.error(f"Error in consumer thread: {e}")
            self.is_connected = False
            # Try to reconnect if we're still supposed to be running
            if self._running:
                self._reconnect()
    
    def _reconnect(self, delay: int = 5) -> None:
        """Attempt to reconnect to RabbitMQ after a delay"""
        while self._running:
            logger.info(f"Attempting to reconnect to RabbitMQ in {delay} seconds...")
            time.sleep(delay)
            if self.connect():
                break
    
    def close(self) -> None:
        """Close the RabbitMQ connection"""
        self._running = False
        
        # Acquire lock to ensure consumer thread isn't mid-process
        with self._lock:
            try:
                if self.channel and self.channel.is_open:
                    self.channel.stop_consuming()
                    self.channel.close()
                
                if self.connection and self.connection.is_open:
                    self.connection.close()
                
                self.is_connected = False
                logger.info("Closed RabbitMQ connection")
            except Exception as e:
                logger.error(f"Error closing RabbitMQ connection: {e}")

# Example usage with processor chain
if __name__ == "__main__":
    # Set logger level to see detailed logs
    logger.set_level('DEBUG')
    
    # Setup processor functions
    def add_timestamp(message):
        """Add timestamp to messages"""
        if isinstance(message, dict):
            message['processed_at'] = time.time()
        return message
    
    def uppercase_strings(message):
        """Convert all string values to uppercase"""
        if isinstance(message, dict):
            for key, value in message.items():
                if isinstance(value, str):
                    message[key] = value.upper()
        return message
    
    def add_counter(message):
        """Add a counter field to track processing steps"""
        if isinstance(message, dict):
            counter = message.get('processing_steps', 0)
            message['processing_steps'] = counter + 1
        return message
    
    # Error handler
    def handle_errors(message, error, processor_name):
        """Handle errors in processors"""
        logger.warning(f"Error in processor {processor_name}: {str(error)}")
        if isinstance(message, dict):
            message['error'] = str(error)
            message['failed_processor'] = processor_name
            return message  # Continue with modified message
        return None  # Drop the message
    
    # Create a processor chain
    chain = ProcessorChain("sample_chain")
    chain.add_processor(add_timestamp, "timestamp")
    chain.add_processor(uppercase_strings, "uppercase")
    chain.add_processor(add_counter, "counter")
    chain.set_error_handler(handle_errors)
    
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
    processor.process_with_chain('input_queue', chain, 'output_queue')
    
    # Publish test message
    test_message = {
        "id": 12345,
        "content": "This is a test message",
        "source": "example script"
    }
    processor.publish('input_queue', test_message)
    
    logger.info("Chain processor running. Press Ctrl+C to exit.")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        processor.close()
