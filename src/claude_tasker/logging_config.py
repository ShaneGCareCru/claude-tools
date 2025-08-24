"""
Logging configuration module for Claude Tasker.
Provides centralized logging setup with environment-based configuration.
"""

import logging
import logging.handlers
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Pattern
import json
import functools


class SensitiveDataFilter:
    """Filter to mask sensitive data in logs."""
    
    # Common patterns for sensitive data
    DEFAULT_PATTERNS = [
        (r'password["\']?\s*[:=]\s*["\']?[^\s"\',}]+', 'password=***REDACTED***'),
        (r'token["\']?\s*[:=]\s*["\']?[^\s"\',}]+', 'token=***REDACTED***'),
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?[^\s"\',}]+', 'api_key=***REDACTED***'),
        (r'secret["\']?\s*[:=]\s*["\']?[^\s"\',}]+', 'secret=***REDACTED***'),
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***EMAIL***'),
    ]
    
    def __init__(self, patterns: Optional[List[tuple]] = None):
        """Initialize filter with custom or default patterns."""
        self.patterns = patterns or self.DEFAULT_PATTERNS
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement) 
            for pattern, replacement in self.patterns
        ]
    
    def filter(self, text: str) -> str:
        """Filter sensitive data from text."""
        for pattern, replacement in self.compiled_patterns:
            text = pattern.sub(replacement, text)
        return text


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def __init__(self, *args, sanitize: bool = False, **kwargs):
        """Initialize formatter with optional sanitization."""
        super().__init__(*args, **kwargs)
        self.sanitize = sanitize
        self.filter = SensitiveDataFilter() if sanitize else None
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON for structured logging."""
        message = record.getMessage()
        if self.sanitize and self.filter:
            message = self.filter.filter(message)
        
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': message,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            extra = record.extra_fields
            if self.sanitize and self.filter:
                # Sanitize extra fields
                extra = {k: self.filter.filter(str(v)) if isinstance(v, str) else v 
                        for k, v in extra.items()}
            log_obj.update(extra)
            
        # Add exception info if present
        if record.exc_info:
            exception_text = self.formatException(record.exc_info)
            if self.sanitize and self.filter:
                exception_text = self.filter.filter(exception_text)
            log_obj['exception'] = exception_text
            
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


def validate_path(path: str, path_type: str = "file") -> str:
    """Validate and sanitize file paths.
    
    Args:
        path: Path to validate
        path_type: Type of path ('file' or 'directory')
        
    Returns:
        Validated path
        
    Raises:
        ValueError: If path is invalid or contains suspicious patterns
    """
    # Check for path traversal attempts
    if '..' in path or path.startswith('~'):
        raise ValueError(f"Invalid {path_type} path: contains traversal patterns")
    
    # Normalize and resolve path
    resolved = os.path.normpath(path)
    
    # Check for absolute paths trying to access system directories
    if os.path.isabs(resolved):
        dangerous_dirs = ['/etc', '/sys', '/proc', '/dev', '/root']
        for dangerous in dangerous_dirs:
            if resolved.startswith(dangerous):
                raise ValueError(f"Invalid {path_type} path: attempts to access system directory")
    
    return resolved


def validate_numeric(value: Any, name: str, min_val: Optional[int] = None, 
                    max_val: Optional[int] = None) -> int:
    """Validate numeric configuration values.
    
    Args:
        value: Value to validate
        name: Name of the parameter
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Validated integer value
        
    Raises:
        ValueError: If value is invalid
    """
    try:
        num_value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {name}: must be a number")
    
    if min_val is not None and num_value < min_val:
        raise ValueError(f"Invalid {name}: must be at least {min_val}")
    if max_val is not None and num_value > max_val:
        raise ValueError(f"Invalid {name}: must be at most {max_val}")
    
    return num_value


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    enable_colors: bool = True,
    enable_json: bool = False,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    log_dir: Optional[str] = None,
    sanitize_logs: bool = False,
    file_permissions: int = 0o600,
    log_prompts: bool = None,
    log_responses: bool = None,
    truncate_length: int = None
) -> Dict[str, Any]:
    """
    Setup comprehensive logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        log_format: Custom log format string
        enable_colors: Enable colored console output
        enable_json: Enable JSON structured logging
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
        log_dir: Directory for log files (default: 'logs')
        sanitize_logs: Enable sanitization of sensitive data in logs
        file_permissions: Unix file permissions for log files (default: 0o600)
        log_prompts: Enable full prompt logging in DEBUG mode (default: True)
        log_responses: Enable full response logging in DEBUG mode (default: True)
        truncate_length: Maximum length for logged content before truncation (default: 10000)
        
    Returns:
        Dict containing logging configuration details
        
    Raises:
        ValueError: If configuration parameters are invalid
        
    Example:
        >>> config = setup_logging(
        ...     log_level='INFO',
        ...     log_file='app.log',
        ...     enable_json=True,
        ...     sanitize_logs=True
        ... )
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
    sanitize_logs = os.getenv('CLAUDE_LOG_SANITIZE', str(sanitize_logs)).lower() == 'true'
    
    # Debug logging options
    if log_prompts is None:
        log_prompts = os.getenv('CLAUDE_LOG_PROMPTS', 'true').lower() == 'true'
    if log_responses is None:
        log_responses = os.getenv('CLAUDE_LOG_RESPONSES', 'true').lower() == 'true'
    if truncate_length is None:
        truncate_length = int(os.getenv('CLAUDE_LOG_TRUNCATE_LENGTH', '10000'))
    
    # Validate numeric parameters
    try:
        max_bytes = validate_numeric(
            os.getenv('CLAUDE_LOG_MAX_BYTES', str(max_bytes)),
            'max_bytes', min_val=1024, max_val=1073741824  # 1KB to 1GB
        )
        backup_count = validate_numeric(
            os.getenv('CLAUDE_LOG_BACKUP_COUNT', str(backup_count)),
            'backup_count', min_val=0, max_val=100
        )
    except ValueError as e:
        raise ValueError(f"Invalid logging configuration: {e}")
    
    log_dir = log_dir or os.getenv('CLAUDE_LOG_DIR', 'logs')
    
    # Validate log directory
    if log_dir:
        try:
            log_dir = validate_path(log_dir, 'directory')
        except ValueError as e:
            raise ValueError(f"Invalid log directory: {e}")
    
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
        console_formatter = StructuredFormatter(sanitize=sanitize_logs)
    elif enable_colors and sys.stdout.isatty():
        console_formatter = ColoredFormatter(log_format)
    else:
        console_formatter = logging.Formatter(log_format)
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if configured)
    if log_file:
        try:
            # Validate log file path
            log_file = validate_path(log_file, 'file')
            
            # Create log directory if needed
            if not os.path.isabs(log_file):
                Path(log_dir).mkdir(parents=True, exist_ok=True, mode=0o700)
                log_file = os.path.join(log_dir, log_file)
            else:
                log_dir_path = Path(os.path.dirname(log_file))
                log_dir_path.mkdir(parents=True, exist_ok=True, mode=0o700)
            
            # Use rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            file_handler.setLevel(numeric_level)
            
            # Set restrictive file permissions
            if os.path.exists(log_file):
                os.chmod(log_file, file_permissions)
            
            # Always use structured logging for files
            file_formatter = StructuredFormatter(sanitize=sanitize_logs) if enable_json else logging.Formatter(log_format)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        except (OSError, IOError) as e:
            # Log error but don't fail completely
            print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)
    
    # Configure specific loggers to avoid noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Store debug logging options globally for use by other modules
    os.environ['CLAUDE_LOG_PROMPTS'] = str(log_prompts).lower()
    os.environ['CLAUDE_LOG_RESPONSES'] = str(log_responses).lower()
    os.environ['CLAUDE_LOG_TRUNCATE_LENGTH'] = str(truncate_length)
    
    config_info = {
        'log_level': log_level,
        'log_file': log_file,
        'log_format': log_format,
        'enable_colors': enable_colors,
        'enable_json': enable_json,
        'sanitize_logs': sanitize_logs,
        'max_bytes': max_bytes,
        'backup_count': backup_count,
        'log_dir': log_dir,
        'file_permissions': oct(file_permissions),
        'handlers': len(root_logger.handlers),
        'log_prompts': log_prompts,
        'log_responses': log_responses,
        'truncate_length': truncate_length
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
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding contextual information to logs.
    
    Example:
        >>> logger = get_logger(__name__)
        >>> with LogContext(logger, request_id='123', user='alice') as log:
        ...     log.info("Processing request")
    """
    
    def __init__(self, logger: logging.Logger, **context):
        """
        Initialize log context.
        
        Args:
            logger: Logger instance
            **context: Key-value pairs to add to log context
        """
        self.logger = logger
        self.context = context
        self.adapter = None
        
    def __enter__(self):
        """Enter context and set up logging adapter."""
        self.adapter = logging.LoggerAdapter(self.logger, self.context)
        # Override the process method to inject context into record
        original_process = self.adapter.process
        
        def process_with_context(msg, kwargs):
            # Add our context directly to extra so it becomes record attributes
            extra = kwargs.get('extra', {})
            extra['extra_fields'] = self.context.copy()
            kwargs['extra'] = extra
            return original_process(msg, kwargs)
        
        self.adapter.process = process_with_context
        return self.adapter
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and clean up."""
        self.adapter = None
        return False


def log_exception(logger: logging.Logger, message: str = "An error occurred"):
    """
    Decorator to log exceptions from functions.
    
    Args:
        logger: Logger instance to use
        message: Custom error message
        
    Example:
        >>> logger = get_logger(__name__)
        >>> @log_exception(logger, "Failed to process data")
        ... def process_data(data):
        ...     return data['key']  # May raise KeyError
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{message}: {str(e)}", exc_info=True)
                raise
        return wrapper
    return decorator


def get_debug_config() -> Dict[str, Any]:
    """Get current debug logging configuration.
    
    Returns:
        Dict with debug logging settings
    """
    return {
        'log_prompts': os.getenv('CLAUDE_LOG_PROMPTS', 'true').lower() == 'true',
        'log_responses': os.getenv('CLAUDE_LOG_RESPONSES', 'true').lower() == 'true',
        'truncate_length': int(os.getenv('CLAUDE_LOG_TRUNCATE_LENGTH', '10000')),
        'log_level': os.getenv('CLAUDE_LOG_LEVEL', 'INFO')
    }


def should_log_full_content() -> bool:
    """Check if full content logging is enabled.
    
    Returns:
        True if DEBUG level and full content logging is enabled
    """
    logger = logging.getLogger()
    if not logger.isEnabledFor(logging.DEBUG):
        return False
    
    config = get_debug_config()
    return config['log_prompts'] or config['log_responses']


# Initialize logging on module import if running as main application
if __name__ != "__main__":
    # Only auto-setup if we're being imported by the main application
    if os.getenv('CLAUDE_AUTO_SETUP_LOGGING', 'true').lower() == 'true':
        setup_logging()