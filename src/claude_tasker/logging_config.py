"""
Logging configuration module for Claude Tasker.
Provides centralized logging setup with environment-based configuration.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON for structured logging."""
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_obj.update(record.extra_fields)
            
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Add color to log level for console output."""
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    enable_colors: bool = True,
    enable_json: bool = False,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    log_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Setup comprehensive logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        log_format: Custom log format string
        enable_colors: Enable colored console output
        enable_json: Enable JSON structured logging
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        log_dir: Directory for log files
        
    Returns:
        Dict containing logging configuration details
    """
    # Get configuration from environment variables with defaults
    log_level = log_level or os.getenv('CLAUDE_LOG_LEVEL', 'INFO')
    log_file = log_file or os.getenv('CLAUDE_LOG_FILE')
    log_format = log_format or os.getenv(
        'CLAUDE_LOG_FORMAT',
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    enable_colors = os.getenv('CLAUDE_LOG_COLORS', str(enable_colors)).lower() == 'true'
    enable_json = os.getenv('CLAUDE_LOG_JSON', str(enable_json)).lower() == 'true'
    max_bytes = int(os.getenv('CLAUDE_LOG_MAX_BYTES', str(max_bytes)))
    backup_count = int(os.getenv('CLAUDE_LOG_BACKUP_COUNT', str(backup_count)))
    log_dir = log_dir or os.getenv('CLAUDE_LOG_DIR', 'logs')
    
    # Validate log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if enable_json:
        console_formatter = StructuredFormatter()
    elif enable_colors and sys.stdout.isatty():
        console_formatter = ColoredFormatter(log_format)
    else:
        console_formatter = logging.Formatter(log_format)
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if configured)
    if log_file:
        # Create log directory if needed
        if not os.path.isabs(log_file):
            Path(log_dir).mkdir(parents=True, exist_ok=True)
            log_file = os.path.join(log_dir, log_file)
        else:
            Path(os.path.dirname(log_file)).mkdir(parents=True, exist_ok=True)
        
        # Use rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(numeric_level)
        
        # Always use structured logging for files
        file_formatter = StructuredFormatter() if enable_json else logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers to avoid noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    config_info = {
        'log_level': log_level,
        'log_file': log_file,
        'log_format': log_format,
        'enable_colors': enable_colors,
        'enable_json': enable_json,
        'max_bytes': max_bytes,
        'backup_count': backup_count,
        'log_dir': log_dir,
        'handlers': len(root_logger.handlers)
    }
    
    # Log initial configuration
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully", extra={'extra_fields': config_info})
    
    return config_info


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Name of the module/logger
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding contextual information to logs."""
    
    def __init__(self, logger: logging.Logger, **context):
        """
        Initialize log context.
        
        Args:
            logger: Logger instance
            **context: Key-value pairs to add to log context
        """
        self.logger = logger
        self.context = context
        self.old_adapter = None
        
    def __enter__(self):
        """Enter context and set up logging adapter."""
        self.old_adapter = self.logger
        adapter = logging.LoggerAdapter(self.logger, {'extra_fields': self.context})
        return adapter
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original logger."""
        return False


def log_exception(logger: logging.Logger, message: str = "An error occurred"):
    """
    Decorator to log exceptions from functions.
    
    Args:
        logger: Logger instance to use
        message: Custom error message
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{message}: {str(e)}", exc_info=True)
                raise
        return wrapper
    return decorator


# Initialize logging on module import if running as main application
if __name__ != "__main__":
    # Only auto-setup if we're being imported by the main application
    if os.getenv('CLAUDE_AUTO_SETUP_LOGGING', 'true').lower() == 'true':
        setup_logging()