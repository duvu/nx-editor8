import os
import logging
import sys
import json
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from logging import Filter
from typing import Optional, Union, Dict, Any, List, Callable

# Version of the logger module
__version__ = '1.2.0'

# Default log formats
DEFAULT_LOG_FORMAT = "%(asctime)s - %(levelname)s - [%(process)d:%(thread)d] - %(name)s - %(message)s"
DEFAULT_SIMPLE_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DEFAULT_DETAILED_FORMAT = "%(asctime)s - %(levelname)s - [%(process)d:%(thread)d] - %(name)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s"

# Default date format
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Supported log levels
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

class SensitiveDataFilter(Filter):
    """
    Filter to remove sensitive data from logs.
    Example: passwords, credit card info, tokens, etc.
    """
    def __init__(self, patterns: List[str] = None):
        """
        Initialize filter with list of patterns to filter.
        
        Args:
            patterns: List of patterns to mask, defaults to password, token, key
        """
        super().__init__()
        if patterns is None:
            self.patterns = ['password', 'token', 'secret', 'key', 'auth', 'credential']
        else:
            self.patterns = patterns
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter and replace sensitive data in log message.
        
        Args:
            record: Log record to filter
            
        Returns:
            True to keep the record (after filtering), False to discard
        """
        if isinstance(record.msg, str):
            for pattern in self.patterns:
                # Find and replace fields containing sensitive data
                # Regex pattern: "password": "abc123" -> "password": "***"
                # Or password=abc123 -> password=***
                record.msg = self._mask_pattern(record.msg, pattern)
        return True
    
    def _mask_pattern(self, text: str, pattern: str) -> str:
        """
        Find and replace sensitive data in text.
        
        Args:
            text: Text to check
            pattern: Pattern to find and replace
            
        Returns:
            Text with masked sensitive data
        """
        # Handle JSON format: "password": "value"
        import re
        json_pattern = fr'["\']({pattern})["\']:\s*["\']([^"\']+)["\']'
        text = re.sub(json_pattern, fr'"\1": "***"', text, flags=re.IGNORECASE)
        
        # Handle query string format: password=value
        query_pattern = fr'({pattern})=([^&\s]+)'
        text = re.sub(query_pattern, r'\1=***', text, flags=re.IGNORECASE)
        
        return text

class Logger:
    """
    Centralized logger configuration for the application.
    Supports console and file output with rotation.
    """
    
    def __init__(self, name: str = 'nx-editor8', level: Union[str, int] = 'INFO'):
        """
        Initialize logger with specified name and level.
        
        Args:
            name: Logger name, used in logs
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        self.name = name
        
        # Convert level from string to int if needed
        if isinstance(level, str):
            level = LOG_LEVELS.get(level.upper(), logging.INFO)
            
        self.logger.setLevel(level)
        self.handlers = []
        
        # Avoid duplicate handlers
        self.logger.handlers = []
        
        # Default: add console handler
        self.add_console_handler()
    
    def add_console_handler(self, 
                           level: Union[str, int] = 'INFO', 
                           format_str: str = DEFAULT_SIMPLE_FORMAT,
                           use_colors: bool = True) -> None:
        """
        Add console handler to display logs to screen.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_str: Log format
            use_colors: Use colors for different log levels
        """
        # Convert level from string to int if needed
        if isinstance(level, str):
            level = LOG_LEVELS.get(level.upper(), logging.INFO)
        
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(format_str, DEFAULT_DATE_FORMAT)
        
        # Add colors if requested
        if use_colors:
            formatter = self._get_colored_formatter(format_str)
        
        console.setFormatter(formatter)
        
        # Add sensitive data filter
        console.addFilter(SensitiveDataFilter())
        
        self.logger.addHandler(console)
        self.handlers.append(console)
        self.debug(f"Added console handler with level {logging.getLevelName(level)}")
    
    def add_file_handler(self, 
                        filename: str, 
                        level: Union[str, int] = 'INFO',
                        format_str: str = DEFAULT_LOG_FORMAT,
                        max_bytes: int = 10485760,  # 10MB
                        backup_count: int = 5,
                        encoding: str = 'utf-8') -> None:
        """
        Add rotating file handler to save logs to file with size-based rotation.
        
        Args:
            filename: Path to log file
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_str: Log format
            max_bytes: Maximum size before rotation (bytes)
            backup_count: Number of backup files to keep
            encoding: Encoding for log file
        """
        # Convert level from string to int if needed
        if isinstance(level, str):
            level = LOG_LEVELS.get(level.upper(), logging.INFO)
        
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(os.path.abspath(filename))
        os.makedirs(log_dir, exist_ok=True)
        
        # Create handler
        file_handler = RotatingFileHandler(
            filename=filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=encoding
        )
        file_handler.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(format_str, DEFAULT_DATE_FORMAT)
        file_handler.setFormatter(formatter)
        
        # Add sensitive data filter
        file_handler.addFilter(SensitiveDataFilter())
        
        self.logger.addHandler(file_handler)
        self.handlers.append(file_handler)
        self.debug(f"Added size-based rotating file handler to {filename} with level {logging.getLevelName(level)}")
    
    def add_daily_file_handler(self,
                             filename: str,
                             level: Union[str, int] = 'INFO',
                             format_str: str = DEFAULT_LOG_FORMAT,
                             backup_count: int = 30,
                             when: str = 'midnight',
                             encoding: str = 'utf-8') -> None:
        """
        Add timed rotating file handler to save logs to file with time-based rotation.
        
        Args:
            filename: Path to log file
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_str: Log format
            backup_count: Number of backup files to keep
            when: Rotation time ('midnight', 'h', 'd', 'w0'-'w6')
            encoding: Encoding for log file
        """
        # Convert level from string to int if needed
        if isinstance(level, str):
            level = LOG_LEVELS.get(level.upper(), logging.INFO)
        
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(os.path.abspath(filename))
        os.makedirs(log_dir, exist_ok=True)
        
        # Create handler
        file_handler = TimedRotatingFileHandler(
            filename=filename,
            when=when,
            backupCount=backup_count,
            encoding=encoding
        )
        file_handler.setLevel(level)
        
        # Format backup filename
        file_handler.suffix = "%Y-%m-%d"
        
        # Create formatter
        formatter = logging.Formatter(format_str, DEFAULT_DATE_FORMAT)
        file_handler.setFormatter(formatter)
        
        # Add sensitive data filter
        file_handler.addFilter(SensitiveDataFilter())
        
        self.logger.addHandler(file_handler)
        self.handlers.append(file_handler)
        self.debug(f"Added daily rotating file handler to {filename} with level {logging.getLevelName(level)}")
    
    def setup_for_production(self, app_name: str, log_dir: str) -> None:
        """
        Set up logger configuration for production environment.
        
        Args:
            app_name: Application name
            log_dir: Log directory
        """
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Clear existing handlers
        self.logger.handlers = []
        self.handlers = []
        
        # Add console handler with INFO level
        self.add_console_handler(level='INFO', format_str=DEFAULT_SIMPLE_FORMAT)
        
        # Add rotating file handler
        log_file = os.path.join(log_dir, f"{app_name}.log")
        self.add_daily_file_handler(
            filename=log_file,
            level='INFO',
            format_str=DEFAULT_LOG_FORMAT,
            backup_count=30  # 30 days
        )
        
        # Add file handler just for errors
        error_log_file = os.path.join(log_dir, f"{app_name}_error.log")
        self.add_daily_file_handler(
            filename=error_log_file,
            level='ERROR',
            format_str=DEFAULT_DETAILED_FORMAT,
            backup_count=90  # Keep for 90 days
        )
        
        self.info(f"Production logging setup completed for {app_name}")
    
    def setup_for_development(self, app_name: str, log_dir: str) -> None:
        """
        Set up logger configuration for development environment.
        
        Args:
            app_name: Application name
            log_dir: Log directory
        """
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Clear existing handlers
        self.logger.handlers = []
        self.handlers = []
        
        # Add console handler with DEBUG level and colors
        self.add_console_handler(level='DEBUG', format_str=DEFAULT_DETAILED_FORMAT, use_colors=True)
        
        # Add file handler
        log_file = os.path.join(log_dir, f"{app_name}_dev.log")
        self.add_daily_file_handler(
            filename=log_file,
            level='DEBUG',
            format_str=DEFAULT_DETAILED_FORMAT,
            backup_count=7  # Only keep for 1 week
        )
        
        self.info(f"Development logging setup completed for {app_name}")
    
    def _get_colored_formatter(self, format_str: str) -> logging.Formatter:
        """
        Create formatter with colors for different levels.
        
        Args:
            format_str: Log format
            
        Returns:
            Formatter with colors
        """
        # ANSI color codes
        RESET = "\033[0m"
        RED = "\033[31m"
        GREEN = "\033[32m"
        YELLOW = "\033[33m"
        CYAN = "\033[36m"
        MAGENTA = "\033[35m"
        BOLD = "\033[1m"
        
        class ColoredFormatter(logging.Formatter):
            COLORS = {
                'DEBUG': CYAN,
                'INFO': GREEN,
                'WARNING': YELLOW,
                'ERROR': RED,
                'CRITICAL': MAGENTA + BOLD
            }
            
            def format(self, record):
                levelname = record.levelname
                if levelname in self.COLORS:
                    record.levelname = f"{self.COLORS[levelname]}{levelname}{RESET}"
                return super().format(record)
        
        return ColoredFormatter(format_str, DEFAULT_DATE_FORMAT)
    
    def set_level(self, level: Union[int, str]) -> None:
        """
        Set log level for logger.
        
        Args:
            level: Log level (can be int or string like 'INFO', 'DEBUG')
        """
        if isinstance(level, str):
            level = LOG_LEVELS.get(level.upper(), logging.INFO)
        
        self.logger.setLevel(level)
        self.info(f"Log level set to {logging.getLevelName(level)}")
    
    def get_level(self) -> str:
        """
        Get current log level of logger.
        
        Returns:
            Log level name
        """
        return logging.getLevelName(self.logger.level)
    
    def clear_handlers(self) -> None:
        """Remove all current handlers."""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
        self.handlers = []
    
    def debug(self, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log debug message.
        
        Args:
            msg: Log message
            extra: Additional data
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log info message.
        
        Args:
            msg: Log message
            extra: Additional data
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log warning message.
        
        Args:
            msg: Log message
            extra: Additional data
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log error message.
        
        Args:
            msg: Log message
            extra: Additional data
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log critical message.
        
        Args:
            msg: Log message
            extra: Additional data
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log exception message with traceback.
        
        Args:
            msg: Log message
            extra: Additional data
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.exception(msg, *args, **kwargs)
    
    def log(self, level: int, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log message with specified level.
        
        Args:
            level: Log level
            msg: Log message
            extra: Additional data
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.log(level, msg, *args, **kwargs)

    def measure_performance(self, func_name: str = None) -> Callable:
        """
        Decorator to measure execution time of a function and log it.
        
        Args:
            func_name: Function name to display in log
            
        Returns:
            Decorator function
        """
        def decorator(func):
            nonlocal func_name
            if func_name is None:
                func_name = func.__name__
                
            def wrapper(*args, **kwargs):
                start_time = time.time()
                self.debug(f"Starting {func_name}")
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    self.debug(f"Finished {func_name} in {execution_time:.4f} seconds")
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.error(f"Exception in {func_name} after {execution_time:.4f} seconds: {str(e)}")
                    raise
            return wrapper
        return decorator

# Create default logger instance
logger = Logger('nx-editor8')

# Default configuration for file logging
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
if not os.path.exists(logs_dir):
    try:
        os.makedirs(logs_dir)
        logger.add_daily_file_handler(os.path.join(logs_dir, 'nx-editor8.log'))
        logger.add_daily_file_handler(
            os.path.join(logs_dir, 'nx-editor8_error.log'),
            level='ERROR',
            format_str=DEFAULT_DETAILED_FORMAT
        )
    except Exception as e:
        logger.error(f"Failed to set up file logging: {e}")

# Export logger instance
__all__ = ['logger', 'Logger', 'LOG_LEVELS']
