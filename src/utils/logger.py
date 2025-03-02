import os
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional, Union, Dict, Any

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# Default date format for logging
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class Logger:
    """
    Centralized logger configuration for the application.
    Supports console output and file logging with various configurations.
    """
    
    def __init__(self, name: str = 'nx-editor8'):
        """
        Initialize the logger with a given name.
        
        Args:
            name: Name of the logger
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.handlers = []
        
        # Prevent adding duplicate handlers
        self.logger.handlers = []
        
        # Set default console handler
        self.add_console_handler()
    
    def add_console_handler(self, 
                           level: int = logging.INFO, 
                           format_str: str = DEFAULT_LOG_FORMAT) -> None:
        """
        Add a console (stdout) handler to the logger.
        
        Args:
            level: Logging level (default: INFO)
            format_str: Format string for log messages
        """
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level)
        formatter = logging.Formatter(format_str, DEFAULT_DATE_FORMAT)
        console.setFormatter(formatter)
        self.logger.addHandler(console)
        self.handlers.append(console)
    
    def add_file_handler(self, 
                        filename: str, 
                        level: int = logging.INFO,
                        format_str: str = DEFAULT_LOG_FORMAT,
                        max_bytes: int = 10485760,  # 10MB
                        backup_count: int = 5) -> None:
        """
        Add a rotating file handler to the logger.
        
        Args:
            filename: Path to log file
            level: Logging level (default: INFO)
            format_str: Format string for log messages
            max_bytes: Maximum size of log file before rotating
            backup_count: Number of backup files to keep
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        file_handler = RotatingFileHandler(
            filename=filename,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(level)
        formatter = logging.Formatter(format_str, DEFAULT_DATE_FORMAT)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.handlers.append(file_handler)
    
    def add_daily_file_handler(self,
                             filename: str,
                             level: int = logging.INFO,
                             format_str: str = DEFAULT_LOG_FORMAT,
                             backup_count: int = 30) -> None:
        """
        Add a daily rotating file handler to the logger.
        
        Args:
            filename: Path to log file
            level: Logging level (default: INFO)
            format_str: Format string for log messages
            backup_count: Number of backup files to keep
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        file_handler = TimedRotatingFileHandler(
            filename=filename,
            when='midnight',
            backupCount=backup_count
        )
        file_handler.setLevel(level)
        formatter = logging.Formatter(format_str, DEFAULT_DATE_FORMAT)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.handlers.append(file_handler)
    
    def set_level(self, level: Union[int, str]) -> None:
        """
        Set the logging level for the logger.
        
        Args:
            level: Logging level (can be int or string like 'INFO', 'DEBUG', etc.)
        """
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)
        
        self.logger.setLevel(level)
    
    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log a debug message."""
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs) -> None:
        """Log an info message."""
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log a warning message."""
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs) -> None:
        """Log an error message."""
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs) -> None:
        """Log a critical message."""
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs) -> None:
        """Log an exception message with traceback."""
        self.logger.exception(msg, *args, **kwargs)
    
    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Log a message with specified level."""
        self.logger.log(level, msg, *args, **kwargs)

# Create a default logger instance
logger = Logger('nx-editor8')

# Configure default file logging if required
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
if not os.path.exists(logs_dir):
    try:
        os.makedirs(logs_dir)
        logger.add_daily_file_handler(os.path.join(logs_dir, 'nx-editor8.log'))
    except Exception as e:
        logger.error(f"Failed to set up file logging: {e}")

# Export the logger instance
__all__ = ['logger', 'Logger']
