import json
import os
import signal
import sys
import time
import threading
import traceback
from typing import Any, Callable, Dict, List, Optional, Union
import pika
from dotenv import load_dotenv
from .processor_chain import ProcessorChain
from .logger import logger

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
        self.password = os.getenv('RABBITMQ_PASS', 'guest')
        self.host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.port = os.getenv('RABBITMQ_PORT', 5672)
        self.vhost = os.getenv('RABBITMQ_VHOST', '/')

        logger.info(f"RabbitMQ connection parameters: {self.host}:{self.port}{self.vhost}")
        logger.info(f"RabbitMQ user: {self.user}")
        # Che dấu mật khẩu trong logs
        masked_password = '*' * (len(self.password) if self.password else 0)
        logger.info(f"RabbitMQ password: {masked_password}")
        
        # Connection state
        self.connection = None
        self.channel = None
        self.is_connected = False
        self._subscriptions = {}
        self._running = True
        self._lock = threading.Lock()
        self._reconnect_attempt = 0
        
        # Consumer thread tracking
        self._consumer_thread = None
        self._shutdown_complete = threading.Event()
        
        logger.info(f"Initialized RabbitMQ processor with host {self.host}:{self.port}")
        
    def connect(self) -> bool:
        """Establish connection to RabbitMQ server"""
        logger.info(f"Attempting to connect to RabbitMQ at {self.host}:{self.port}{self.vhost}")
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
            
            logger.debug(f"Connection parameters: heartbeat=60, blocked_connection_timeout=300")
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.is_connected = True
            self._reconnect_attempt = 0
            
            logger.info(f"Successfully connected to RabbitMQ at {self.host}:{self.port}{self.vhost}")
            logger.debug(f"Channel established: {self.channel}")
            
            # Restore subscriptions after reconnection
            self._restore_subscriptions()
            
            return True
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"AMQP Connection Error: {e}")
            logger.error(f"Connection details: {self.host}:{self.port}{self.vhost}, user={self.user}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return False
    
    def _restore_subscriptions(self) -> None:
        """Restore all active subscriptions after reconnection"""
        logger.info(f"Restoring {len(self._subscriptions)} active subscriptions")
        for queue, data in self._subscriptions.items():
            chain, output_queue, options = data
            logger.info(f"Restoring subscription: {queue} → {output_queue} with chain '{chain.name}'")
            self.process_with_chain(queue, chain, output_queue, options)
    
    def publish(self, queue: str, message: Any, options: Optional[Dict] = None) -> bool:
        """Publish a message to a queue"""
        logger.debug(f"Attempting to publish message to queue '{queue}'")
        if not self.is_connected:
            logger.warning(f"Not connected to RabbitMQ. Attempting to reconnect before publishing to {queue}")
            if not self.connect():
                return False
            
        try:
            # Ensure queue exists
            logger.debug(f"Declaring queue '{queue}' if it doesn't exist")
            self.channel.queue_declare(queue=queue, durable=True)
            
            # Convert message to JSON if it's a dict or list
            if isinstance(message, (dict, list)):
                message_body = json.dumps(message, ensure_ascii=False)
                logger.debug(f"Converted dict/list message to JSON, length: {len(message_body)} bytes")
            elif not isinstance(message, str):
                message_body = str(message)
                logger.debug(f"Converted non-string message to string: {type(message)} -> str")
            else:
                message_body = message
                logger.debug(f"Using message as-is (already string), length: {len(message_body)} bytes")
                
            # Set message properties
            properties = pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json',
                **(options or {})
            )
            
            # Log message content summary for debugging
            if isinstance(message, dict):
                keys = list(message.keys())
                logger.debug(f"Message keys: {keys}")
                msg_summary = {k: str(message[k])[:50] + ('...' if len(str(message[k])) > 50 else '') for k in keys[:5]}
                logger.debug(f"Message content (preview): {msg_summary}")
            
            # Publish the message
            self.channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=message_body,
                properties=properties
            )
            logger.info(f"Successfully published message to '{queue}', size: {len(message_body)} bytes")
            return True
        except pika.exceptions.ChannelClosed as e:
            logger.error(f"Channel closed while publishing to queue '{queue}': {e}")
            self.is_connected = False
            return False
        except pika.exceptions.ConnectionClosed as e:
            logger.error(f"Connection closed while publishing to queue '{queue}': {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"Error publishing to queue '{queue}': {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
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
        logger.info(f"Setting up processor chain '{processor_chain.name}' from '{input_queue}' to '{output_queue}'")
        
        if not self.is_connected:
            logger.warning(f"Not connected to RabbitMQ. Attempting to connect before processing {input_queue}")
            if not self.connect():
                logger.error(f"Cannot process queue '{input_queue}': failed to connect to RabbitMQ")
                return
        
        try:
            # Store subscription info for reconnection
            self._subscriptions[input_queue] = (processor_chain, output_queue, options)
            logger.debug(f"Stored subscription info for reconnection: {input_queue} → {output_queue}")
            
            # Declare queues
            logger.debug(f"Declaring input queue '{input_queue}'")
            self.channel.queue_declare(queue=input_queue, durable=True)
            logger.debug(f"Declaring output queue '{output_queue}'")
            self.channel.queue_declare(queue=output_queue, durable=True)
            
            # Set up QoS (prefetch_count)
            logger.debug(f"Setting QoS prefetch_count=1 for better load distribution")
            self.channel.basic_qos(prefetch_count=1)
            
            def message_handler(ch, method, properties, body):
                message_id = properties.message_id if hasattr(properties, 'message_id') and properties.message_id else 'unknown'
                delivery_tag = method.delivery_tag
                
                logger.info(f"Received message [id:{message_id}, tag:{delivery_tag}] from '{input_queue}'")
                
                try:
                    # Parse message
                    try:
                        message = json.loads(body)
                        logger.debug(f"Successfully parsed JSON message, size: {len(body)} bytes")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse as JSON, treating as text: {e}")
                        message = body.decode('utf-8')
                    
                    # Log message details
                    if isinstance(message, dict):
                        keys = list(message.keys())
                        logger.debug(f"Message keys: {keys}")
                        if 'id' in message:
                            logger.info(f"Message internal ID: {message['id']}")
                    else:
                        logger.debug(f"Message is not a dict: {type(message)}")
                    
                    # Process message through the chain
                    logger.info(f"Processing message [tag:{delivery_tag}] through chain '{processor_chain.name}'")
                    start_time = time.time()
                    processed_message = processor_chain.process(message)
                    processing_time = time.time() - start_time
                    logger.info(f"Processing completed in {processing_time:.3f} seconds")
                    
                    # Skip publishing if processor chain returns None
                    if processed_message is not None:
                        # Publish to output queue
                        logger.info(f"Publishing processed message to '{output_queue}'")
                        success = self.publish(output_queue, processed_message)
                        if success:
                            logger.info(f"Successfully published processed message [tag:{delivery_tag}] to '{output_queue}'")
                        else:
                            logger.error(f"Failed to publish processed message [tag:{delivery_tag}] to '{output_queue}'")
                            # Reject and requeue the original message
                            logger.warning(f"Rejecting message and requesting requeue [tag:{delivery_tag}]")
                            ch.basic_nack(delivery_tag=delivery_tag, requeue=True)
                            return
                    else:
                        logger.info(f"Message [tag:{delivery_tag}] dropped by processor chain (returned None)")

                    # Acknowledge successful processing
                    logger.debug(f"Acknowledging message [tag:{delivery_tag}]")
                    ch.basic_ack(delivery_tag=delivery_tag)
                    logger.info(f"Message [tag:{delivery_tag}] processing complete")
                except Exception as e:
                    logger.error(f"Error processing message [tag:{delivery_tag}]: {e}")
                    logger.error(f"Stack trace: {traceback.format_exc()}")
                    # Reject and requeue
                    logger.warning(f"Rejecting message and requesting requeue [tag:{delivery_tag}]")
                    ch.basic_nack(delivery_tag=delivery_tag, requeue=True)
            
            # Start consuming messages
            logger.info(f"Registering consumer for queue '{input_queue}'")
            self.channel.basic_consume(
                queue=input_queue,
                on_message_callback=message_handler
            )
            
            logger.info(f"Successfully started processing messages from '{input_queue}' to '{output_queue}'")
            
            # Start consuming in a separate thread
            logger.debug("Starting consumer thread")
            self._shutdown_complete.clear()  # Reset shutdown event
            self._consumer_thread = threading.Thread(target=self._start_consuming)
            self._consumer_thread.daemon = True
            self._consumer_thread.start()
            logger.info("Consumer thread started")
            
        except pika.exceptions.ChannelClosed as e:
            logger.error(f"Channel closed while setting up queue processing '{input_queue}' → '{output_queue}': {e}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error setting up queue processing '{input_queue}' → '{output_queue}': {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            self.is_connected = False
    
    def _start_consuming(self) -> None:
        """Start consuming messages in a non-blocking way"""
        logger.info("Starting message consumption loop")
        try:
            while self._running and self.is_connected:
                try:
                    with self._lock:
                        if self.channel and self.channel.is_open:
                            # Process messages for a short time then check conditions
                            self.connection.process_data_events(time_limit=0.2)
                        else:
                            logger.warning("Channel is not open in consumer loop, will attempt reconnect")
                            self.is_connected = False
                            break
                    # Kiểm tra xem cờ chạy có còn bật không sau mỗi lần gọi process_data_events
                    if not self._running:
                        logger.debug("Running flag turned off, breaking out of consumer loop")
                        break
                    
                    time.sleep(0.05)  # Small sleep to avoid CPU spinning
                except pika.exceptions.ConnectionClosed:
                    logger.warning("Connection closed during message processing")
                    self.is_connected = False
                    break
                except Exception as e:
                    logger.error(f"Error in consumer loop: {e}")
                    logger.error(f"Stack trace: {traceback.format_exc()}")
                    time.sleep(0.1)  # Ngăn loop quá nhanh trong trường hợp lỗi
            
            if not self._running:
                logger.info("Consumer loop stopped because processor is no longer running")
            elif not self.is_connected:
                logger.warning("Consumer loop stopped because connection is lost")
                # Try to reconnect if we're still supposed to be running
                if self._running:
                    self._reconnect()
        except pika.exceptions.ConnectionClosed as e:
            logger.error(f"Connection closed in consumer thread: {e}")
            self.is_connected = False
            # Try to reconnect if we're still supposed to be running
            if self._running:
                self._reconnect()
        except pika.exceptions.ChannelClosed as e:
            logger.error(f"Channel closed in consumer thread: {e}")
            self.is_connected = False
            # Try to reconnect if we're still supposed to be running
            if self._running:
                self._reconnect()
        except Exception as e:
            logger.error(f"Error in consumer thread: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            self.is_connected = False
            # Try to reconnect if we're still supposed to be running
            if self._running:
                self._reconnect()
        finally:
            # Đánh dấu rằng thread tiêu thụ đã hoàn thành
            logger.debug("Consumer thread finishing execution")
            self._shutdown_complete.set()
    
    def _reconnect(self, delay: int = 5) -> None:
        """Attempt to reconnect to RabbitMQ after a delay"""
        self._reconnect_attempt += 1
        
        # Calculate exponential backoff with a cap
        backoff_delay = min(delay * (2 ** (self._reconnect_attempt - 1)), 300)  # Cap at 5 minutes
        
        logger.warning(f"Connection lost. Reconnect attempt #{self._reconnect_attempt}")
        logger.info(f"Waiting {backoff_delay} seconds before attempting to reconnect...")
        
        while self._running:
            time.sleep(backoff_delay)
            if not self._running:
                logger.info("Reconnect canceled - processor is shutting down")
                return
                
            logger.info(f"Attempting to reconnect to RabbitMQ (attempt #{self._reconnect_attempt})...")
            if self.connect():
                logger.info(f"Successfully reconnected to RabbitMQ after {self._reconnect_attempt} attempts")
                break
            else:
                logger.error(f"Reconnect attempt #{self._reconnect_attempt} failed")
                self._reconnect_attempt += 1
                # Increase backoff delay with a cap
                backoff_delay = min(delay * (2 ** (self._reconnect_attempt - 1)), 300)
                logger.info(f"Next reconnect attempt in {backoff_delay} seconds...")
    
    def close(self) -> None:
        """Close the RabbitMQ connection"""
        logger.info("Shutting down RabbitMQ processor...")
        
        # Đặt cờ tắt trước khi thực hiện bất kỳ hành động nào
        self._running = False
        
        # Đảm bảo rằng connection.process_data_events() không block khi được gọi
        if self.connection and self.connection.is_open:
            try:
                self.connection._flush_output()
            except:
                pass
                
        # Acquire lock to ensure consumer thread isn't mid-process
        logger.debug("Acquiring lock to safely shut down connection")
        with self._lock:
            try:
                if self.channel and self.channel.is_open:
                    logger.debug("Stopping channel consumers")
                    self.channel.stop_consuming()
                    logger.debug("Closing channel")
                    self.channel.close()
                
                if self.connection and self.connection.is_open:
                    logger.debug("Closing connection")
                    self.connection.close()
                
                self.is_connected = False
            except Exception as e:
                logger.error(f"Error closing RabbitMQ connection: {e}")
                logger.error(f"Stack trace: {traceback.format_exc()}")
        
        # Đợi consumer thread kết thúc với timeout
        if self._consumer_thread and self._consumer_thread.is_alive():
            logger.debug("Waiting for consumer thread to terminate...")
            shutdown_timeout = 5.0  # Seconds
            self._shutdown_complete.wait(shutdown_timeout)
            
            if self._consumer_thread.is_alive():
                logger.warning(f"Consumer thread didn't terminate within {shutdown_timeout}s. Application may not exit cleanly.")
            else:
                logger.info("Consumer thread terminated successfully")
        
        logger.info("RabbitMQ connection closed successfully")

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
        logger.error(f"Stack trace: {traceback.format_exc()}")
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
        logger.info("\nShutdown signal received. Gracefully shutting down processor...")
        processor.close()
        logger.info("Processor shutdown complete. Exiting.")
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
    logger.info(f"Publishing test message to 'input_queue': {test_message}")
    processor.publish('input_queue', test_message)
    
    logger.info("Chain processor running. Press Ctrl+C to exit.")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received in main loop")
    finally:
        processor.close()
