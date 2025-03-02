import os
import logging

# RabbitMQ Configuration
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'guest')
RABBITMQ_PASS = os.environ.get('RABBITMQ_PASS', 'guest')
RABBITMQ_VHOST = os.environ.get('RABBITMQ_VHOST', '/')

# Queue Configuration
INPUT_QUEUE = os.environ.get('INPUT_QUEUE', 'nx_01_ai_queue')
OUTPUT_QUEUE = os.environ.get('OUTPUT_QUEUE', 'nx_02_queue')

# Logging Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.environ.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Application Configuration
APP_NAME = os.environ.get('APP_NAME', 'NX-Editor8')
PROCESSOR_ID = os.environ.get('PROCESSOR_ID', 'X')

def get_log_level():
    """Convert string log level to logging constant"""
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return levels.get(LOG_LEVEL.upper(), logging.INFO)
