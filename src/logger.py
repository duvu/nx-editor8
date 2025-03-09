import os
import logging
import sys
import json
import time
import socket
import platform
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler, SMTPHandler
from logging import Filter
from typing import Optional, Union, Dict, Any, List, Callable

# Phiên bản của module logger
__version__ = '1.1.0'

# Định dạng mặc định cho logs
DEFAULT_LOG_FORMAT = "%(asctime)s - %(levelname)s - [%(process)d:%(thread)d] - %(name)s - %(message)s"
DEFAULT_SIMPLE_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DEFAULT_DETAILED_FORMAT = "%(asctime)s - %(levelname)s - [%(process)d:%(thread)d] - %(name)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s"
DEFAULT_JSON_FORMAT = '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "pid": %(process)d, "message": "%(message)s"}'

# Định dạng ngày tháng mặc định
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Các level logging được hỗ trợ
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

class SensitiveDataFilter(Filter):
    """
    Bộ lọc để loại bỏ dữ liệu nhạy cảm khỏi logs.
    Ví dụ: mật khẩu, thông tin thẻ tín dụng, tokens, etc.
    """
    def __init__(self, patterns: List[str] = None):
        """
        Khởi tạo bộ lọc với danh sách các mẫu cần lọc.
        
        Args:
            patterns: Danh sách các pattern cần che giấu, mặc định là password, token, key
        """
        super().__init__()
        if patterns is None:
            self.patterns = ['password', 'token', 'secret', 'key', 'auth', 'credential']
        else:
            self.patterns = patterns
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Lọc và thay thế các dữ liệu nhạy cảm trong log message.
        
        Args:
            record: Bản ghi log cần lọc
            
        Returns:
            True để giữ lại bản ghi (đã được lọc), False để loại bỏ
        """
        if isinstance(record.msg, str):
            for pattern in self.patterns:
                # Tìm và thay thế các trường chứa dữ liệu nhạy cảm
                # Mẫu regex: "password": "abc123" -> "password": "***"
                # Hoặc password=abc123 -> password=***
                record.msg = self._mask_pattern(record.msg, pattern)
        return True
    
    def _mask_pattern(self, text: str, pattern: str) -> str:
        """
        Tìm và thay thế dữ liệu nhạy cảm trong text.
        
        Args:
            text: Văn bản cần kiểm tra
            pattern: Mẫu cần tìm và thay thế
            
        Returns:
            Văn bản đã được che giấu dữ liệu nhạy cảm
        """
        # Xử lý định dạng JSON: "password": "giá_trị"
        import re
        json_pattern = fr'["\']({pattern})["\']:\s*["\']([^"\']+)["\']'
        text = re.sub(json_pattern, fr'"\1": "***"', text, flags=re.IGNORECASE)
        
        # Xử lý định dạng query string: password=giá_trị
        query_pattern = fr'({pattern})=([^&\s]+)'
        text = re.sub(query_pattern, r'\1=***', text, flags=re.IGNORECASE)
        
        return text

class JsonFormatter(logging.Formatter):
    """
    Định dạng log message thành JSON để dễ dàng parse và phân tích.
    """
    def __init__(self, fmt=None, datefmt=None, style='%'):
        """
        Khởi tạo JSON formatter.
        
        Args:
            fmt: Định dạng log
            datefmt: Định dạng ngày tháng
            style: Kiểu định dạng (%, {, $)
        """
        super().__init__(fmt, datefmt, style)
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Định dạng bản ghi log thành JSON.
        
        Args:
            record: Bản ghi log
            
        Returns:
            Chuỗi JSON
        """
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'process': record.process,
            'thread': record.thread,
            'module': record.module,
            'lineno': record.lineno,
        }
        
        # Thêm exception info nếu có
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Thêm các trường bổ sung nếu có
        if hasattr(record, 'extra_data') and isinstance(record.extra_data, dict):
            for key, value in record.extra_data.items():
                log_data[key] = value
                
        return json.dumps(log_data)

class Logger:
    """
    Centralized logger configuration for the application.
    Hỗ trợ nhiều kiểu output (console, file) và định dạng logs.
    Tích hợp rotation, lọc dữ liệu nhạy cảm, và nhiều tính năng khác.
    """
    
    def __init__(self, name: str = 'nx-editor8', level: Union[str, int] = 'INFO'):
        """
        Khởi tạo logger với tên và level chỉ định.
        
        Args:
            name: Tên logger, sử dụng trong logs
            level: Cấp độ log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        self.name = name
        
        # Convert level từ string sang int nếu cần
        if isinstance(level, str):
            level = LOG_LEVELS.get(level.upper(), logging.INFO)
            
        self.logger.setLevel(level)
        self.handlers = []
        
        # Tránh duplicate handlers
        self.logger.handlers = []
        
        # Thông tin hệ thống để debug
        self.system_info = {
            'hostname': socket.gethostname(),
            'platform': platform.platform(),
            'python': platform.python_version(),
            'start_time': datetime.now().strftime(DEFAULT_DATE_FORMAT)
        }
        
        # Mặc định thêm console handler
        self.add_console_handler()
    
    def add_console_handler(self, 
                           level: Union[str, int] = 'INFO', 
                           format_str: str = DEFAULT_LOG_FORMAT,
                           use_colors: bool = True) -> None:
        """
        Thêm console handler để hiển thị logs ra màn hình.
        
        Args:
            level: Cấp độ log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_str: Định dạng log
            use_colors: Sử dụng màu cho các level log khác nhau
        """
        # Convert level từ string sang int nếu cần
        if isinstance(level, str):
            level = LOG_LEVELS.get(level.upper(), logging.INFO)
        
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level)
        
        # Tạo formatter
        formatter = logging.Formatter(format_str, DEFAULT_DATE_FORMAT)
        
        # Thêm màu sắc nếu được yêu cầu
        if use_colors:
            formatter = self._get_colored_formatter(format_str)
        
        console.setFormatter(formatter)
        
        # Thêm bộ lọc dữ liệu nhạy cảm
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
        Thêm rotating file handler để lưu logs vào file với rotation theo kích thước.
        
        Args:
            filename: Đường dẫn tới file log
            level: Cấp độ log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_str: Định dạng log
            max_bytes: Kích thước tối đa trước khi rotate (bytes)
            backup_count: Số lượng file backup giữ lại
            encoding: Mã hóa cho file log
        """
        # Convert level từ string sang int nếu cần
        if isinstance(level, str):
            level = LOG_LEVELS.get(level.upper(), logging.INFO)
        
        # Tạo thư mục nếu chưa tồn tại
        log_dir = os.path.dirname(os.path.abspath(filename))
        os.makedirs(log_dir, exist_ok=True)
        
        # Tạo handler
        file_handler = RotatingFileHandler(
            filename=filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=encoding
        )
        file_handler.setLevel(level)
        
        # Tạo formatter
        formatter = logging.Formatter(format_str, DEFAULT_DATE_FORMAT)
        file_handler.setFormatter(formatter)
        
        # Thêm bộ lọc dữ liệu nhạy cảm
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
        Thêm timed rotating file handler để lưu logs vào file với rotation theo thời gian.
        
        Args:
            filename: Đường dẫn tới file log
            level: Cấp độ log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_str: Định dạng log
            backup_count: Số lượng file backup giữ lại
            when: Thời điểm rotate ('midnight', 'h', 'd', 'w0'-'w6')
            encoding: Mã hóa cho file log
        """
        # Convert level từ string sang int nếu cần
        if isinstance(level, str):
            level = LOG_LEVELS.get(level.upper(), logging.INFO)
        
        # Tạo thư mục nếu chưa tồn tại
        log_dir = os.path.dirname(os.path.abspath(filename))
        os.makedirs(log_dir, exist_ok=True)
        
        # Tạo handler
        file_handler = TimedRotatingFileHandler(
            filename=filename,
            when=when,
            backupCount=backup_count,
            encoding=encoding
        )
        file_handler.setLevel(level)
        
        # Định dạng tên file backup
        file_handler.suffix = "%Y-%m-%d"
        
        # Tạo formatter
        formatter = logging.Formatter(format_str, DEFAULT_DATE_FORMAT)
        file_handler.setFormatter(formatter)
        
        # Thêm bộ lọc dữ liệu nhạy cảm
        file_handler.addFilter(SensitiveDataFilter())
        
        self.logger.addHandler(file_handler)
        self.handlers.append(file_handler)
        self.debug(f"Added daily rotating file handler to {filename} with level {logging.getLevelName(level)}")
    
    def add_json_file_handler(self,
                            filename: str,
                            level: Union[str, int] = 'INFO',
                            backup_count: int = 30,
                            when: str = 'midnight',
                            encoding: str = 'utf-8') -> None:
        """
        Thêm file handler với định dạng JSON cho logs.
        
        Args:
            filename: Đường dẫn tới file log
            level: Cấp độ log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            backup_count: Số lượng file backup giữ lại
            when: Thời điểm rotate ('midnight', 'h', 'd', 'w0'-'w6')
            encoding: Mã hóa cho file log
        """
        # Convert level từ string sang int nếu cần
        if isinstance(level, str):
            level = LOG_LEVELS.get(level.upper(), logging.INFO)
        
        # Tạo thư mục nếu chưa tồn tại
        log_dir = os.path.dirname(os.path.abspath(filename))
        os.makedirs(log_dir, exist_ok=True)
        
        # Tạo handler
        file_handler = TimedRotatingFileHandler(
            filename=filename,
            when=when,
            backupCount=backup_count,
            encoding=encoding
        )
        file_handler.setLevel(level)
        
        # Định dạng tên file backup
        file_handler.suffix = "%Y-%m-%d"
        
        # Tạo JSON formatter
        formatter = JsonFormatter()
        file_handler.setFormatter(formatter)
        
        # Thêm bộ lọc dữ liệu nhạy cảm
        file_handler.addFilter(SensitiveDataFilter())
        
        self.logger.addHandler(file_handler)
        self.handlers.append(file_handler)
        self.debug(f"Added JSON file handler to {filename} with level {logging.getLevelName(level)}")
    
    def add_dual_rotation_handler(self,
                                filename: str,
                                level: Union[str, int] = 'INFO',
                                format_str: str = DEFAULT_LOG_FORMAT,
                                max_bytes: int = 52428800,  # 50MB
                                time_backup_count: int = 30,
                                size_backup_count: int = 5,
                                when: str = 'midnight',
                                encoding: str = 'utf-8') -> None:
        """
        Thêm cả hai loại rotation (size và time) cho logs.
        
        Args:
            filename: Đường dẫn tới file log
            level: Cấp độ log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_str: Định dạng log
            max_bytes: Kích thước tối đa trước khi rotate (bytes)
            time_backup_count: Số lượng file backup theo thời gian
            size_backup_count: Số lượng file backup theo kích thước
            when: Thời điểm rotate ('midnight', 'h', 'd', 'w0'-'w6')
            encoding: Mã hóa cho file log
        """
        # Thêm cả hai loại handlers
        time_filename = f"{filename}.time"
        size_filename = f"{filename}.size"
        
        self.add_daily_file_handler(
            time_filename, level, format_str, time_backup_count, when, encoding
        )
        
        self.add_file_handler(
            size_filename, level, format_str, max_bytes, size_backup_count, encoding
        )
        
        self.debug(f"Added dual rotation handler to {filename}")
    
    def add_email_handler(self,
                        mailhost: str,
                        fromaddr: str,
                        toaddrs: List[str],
                        subject: str,
                        credentials: tuple = None,
                        secure: tuple = None,
                        level: Union[str, int] = 'ERROR') -> None:
        """
        Thêm email handler để gửi log qua email.
        
        Args:
            mailhost: SMTP mail host
            fromaddr: Địa chỉ email gửi
            toaddrs: Danh sách địa chỉ email nhận
            subject: Chủ đề email
            credentials: (username, password) cho SMTP
            secure: Tuple cho secure connection
            level: Cấp độ log kích hoạt gửi mail (thường là ERROR hoặc CRITICAL)
        """
        # Convert level từ string sang int nếu cần
        if isinstance(level, str):
            level = LOG_LEVELS.get(level.upper(), logging.ERROR)
        
        # Tạo handler
        mail_handler = SMTPHandler(
            mailhost=mailhost,
            fromaddr=fromaddr,
            toaddrs=toaddrs,
            subject=subject,
            credentials=credentials,
            secure=secure
        )
        mail_handler.setLevel(level)
        
        # Tạo formatter chi tiết cho email
        formatter = logging.Formatter(DEFAULT_DETAILED_FORMAT, DEFAULT_DATE_FORMAT)
        mail_handler.setFormatter(formatter)
        
        self.logger.addHandler(mail_handler)
        self.handlers.append(mail_handler)
        self.debug(f"Added email handler to {toaddrs} with level {logging.getLevelName(level)}")
    
    def setup_for_production(self, app_name: str, log_dir: str) -> None:
        """
        Thiết lập cấu hình logger cho môi trường sản xuất.
        
        Args:
            app_name: Tên ứng dụng
            log_dir: Thư mục lưu logs
        """
        # Đảm bảo thư mục log tồn tại
        os.makedirs(log_dir, exist_ok=True)
        
        # Xóa handlers hiện tại
        self.logger.handlers = []
        self.handlers = []
        
        # Thêm console handler với level INFO
        self.add_console_handler(level='INFO', format_str=DEFAULT_SIMPLE_FORMAT)
        
        # Thêm file handler thường xuyên rotate
        log_file = os.path.join(log_dir, f"{app_name}.log")
        self.add_dual_rotation_handler(
            filename=log_file,
            level='INFO',
            format_str=DEFAULT_LOG_FORMAT,
            max_bytes=50*1024*1024,  # 50MB
            time_backup_count=30,     # 30 ngày
            size_backup_count=10      # 10 files
        )
        
        # Thêm file handler riêng cho errors
        error_log_file = os.path.join(log_dir, f"{app_name}_error.log")
        self.add_daily_file_handler(
            filename=error_log_file,
            level='ERROR',
            format_str=DEFAULT_DETAILED_FORMAT,
            backup_count=90  # Giữ lại 90 ngày
        )
        
        # Thêm JSON handler để phân tích logs
        json_log_file = os.path.join(log_dir, f"{app_name}_json.log")
        self.add_json_file_handler(
            filename=json_log_file,
            level='INFO',
            backup_count=30
        )
        
        self.info(f"Production logging setup completed for {app_name}")
    
    def setup_for_development(self, app_name: str, log_dir: str) -> None:
        """
        Thiết lập cấu hình logger cho môi trường phát triển.
        
        Args:
            app_name: Tên ứng dụng
            log_dir: Thư mục lưu logs
        """
        # Đảm bảo thư mục log tồn tại
        os.makedirs(log_dir, exist_ok=True)
        
        # Xóa handlers hiện tại
        self.logger.handlers = []
        self.handlers = []
        
        # Thêm console handler với level DEBUG và màu sắc
        self.add_console_handler(level='DEBUG', format_str=DEFAULT_DETAILED_FORMAT, use_colors=True)
        
        # Thêm file handler
        log_file = os.path.join(log_dir, f"{app_name}_dev.log")
        self.add_daily_file_handler(
            filename=log_file,
            level='DEBUG',
            format_str=DEFAULT_DETAILED_FORMAT,
            backup_count=7  # Chỉ giữ 1 tuần
        )
        
        self.info(f"Development logging setup completed for {app_name}")
    
    def _get_colored_formatter(self, format_str: str) -> logging.Formatter:
        """
        Tạo formatter với màu sắc cho các level khác nhau.
        
        Args:
            format_str: Định dạng log
            
        Returns:
            Formatter có màu sắc
        """
        # ANSI color codes
        RESET = "\033[0m"
        BLACK = "\033[30m"
        RED = "\033[31m"
        GREEN = "\033[32m"
        YELLOW = "\033[33m"
        BLUE = "\033[34m"
        MAGENTA = "\033[35m"
        CYAN = "\033[36m"
        WHITE = "\033[37m"
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
        Đặt cấp độ log cho logger.
        
        Args:
            level: Cấp độ log (có thể là int hoặc string như 'INFO', 'DEBUG')
        """
        if isinstance(level, str):
            level = LOG_LEVELS.get(level.upper(), logging.INFO)
        
        self.logger.setLevel(level)
        self.info(f"Log level set to {logging.getLevelName(level)}")
    
    def get_level(self) -> str:
        """
        Lấy cấp độ log hiện tại của logger.
        
        Returns:
            Tên cấp độ log
        """
        return logging.getLevelName(self.logger.level)
    
    def clear_handlers(self) -> None:
        """Xóa tất cả handlers hiện tại."""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
        self.handlers = []
    
    def debug(self, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log debug message.
        
        Args:
            msg: Thông điệp log
            extra: Dữ liệu bổ sung
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log info message.
        
        Args:
            msg: Thông điệp log
            extra: Dữ liệu bổ sung
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log warning message.
        
        Args:
            msg: Thông điệp log
            extra: Dữ liệu bổ sung
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log error message.
        
        Args:
            msg: Thông điệp log
            extra: Dữ liệu bổ sung
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log critical message.
        
        Args:
            msg: Thông điệp log
            extra: Dữ liệu bổ sung
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log exception message với traceback.
        
        Args:
            msg: Thông điệp log
            extra: Dữ liệu bổ sung
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.exception(msg, *args, **kwargs)
    
    def log(self, level: int, msg: str, *args, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Log message với level chỉ định.
        
        Args:
            level: Cấp độ log
            msg: Thông điệp log
            extra: Dữ liệu bổ sung
        """
        if extra is not None:
            kwargs['extra'] = {'extra_data': extra}
        self.logger.log(level, msg, *args, **kwargs)
    
    def log_system_info(self) -> None:
        """Log thông tin hệ thống."""
        self.info("=== System Information ===")
        self.info(f"Hostname: {self.system_info['hostname']}")
        self.info(f"Platform: {self.system_info['platform']}")
        self.info(f"Python version: {self.system_info['python']}")
        self.info(f"Application start time: {self.system_info['start_time']}")
        self.info(f"Logger: {self.name} (level: {self.get_level()})")
        self.info("=========================")

    def measure_performance(self, func_name: str = None) -> Callable:
        """
        Decorator để đo thời gian thực thi của một hàm và ghi vào log.
        
        Args:
            func_name: Tên hàm để hiển thị trong log
            
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

# Tạo instance logger mặc định
logger = Logger('nx-editor8')

# Cấu hình mặc định cho file logging
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

# Xuất logger instance
__all__ = ['logger', 'Logger', 'LOG_LEVELS']
