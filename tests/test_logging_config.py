"""
Comprehensive tests for the logging configuration module.
"""

import unittest
import logging
import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.claude_tasker.logging_config import (
    SensitiveDataFilter,
    StructuredFormatter,
    ColoredFormatter,
    setup_logging,
    get_logger,
    LogContext,
    log_exception,
    validate_path,
    validate_numeric
)


class TestSensitiveDataFilter(unittest.TestCase):
    """Test sensitive data filtering functionality."""
    
    def setUp(self):
        self.filter = SensitiveDataFilter()
    
    def test_filter_password(self):
        """Test password filtering."""
        text = "user logged in with password=secret123"
        filtered = self.filter.filter(text)
        self.assertIn("password=***REDACTED***", filtered)
        self.assertNotIn("secret123", filtered)
    
    def test_filter_token(self):
        """Test token filtering."""
        text = 'Authorization: Bearer token="abc123xyz"'
        filtered = self.filter.filter(text)
        self.assertIn("token=***REDACTED***", filtered)
        self.assertNotIn("abc123xyz", filtered)
    
    def test_filter_api_key(self):
        """Test API key filtering."""
        text = "api_key: sk-1234567890abcdef"
        filtered = self.filter.filter(text)
        self.assertIn("api_key=***REDACTED***", filtered)
        self.assertNotIn("sk-1234567890abcdef", filtered)
    
    def test_filter_email(self):
        """Test email filtering."""
        text = "Contact user@example.com for details"
        filtered = self.filter.filter(text)
        self.assertIn("***EMAIL***", filtered)
        self.assertNotIn("user@example.com", filtered)
    
    def test_custom_patterns(self):
        """Test custom filter patterns."""
        custom_patterns = [
            (r'custom_secret=\S+', 'custom_secret=HIDDEN')
        ]
        filter = SensitiveDataFilter(patterns=custom_patterns)
        text = "config: custom_secret=mysecret"
        filtered = filter.filter(text)
        self.assertIn("custom_secret=HIDDEN", filtered)
        self.assertNotIn("mysecret", filtered)


class TestStructuredFormatter(unittest.TestCase):
    """Test structured JSON formatter."""
    
    def test_basic_formatting(self):
        """Test basic JSON formatting."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        self.assertEqual(data['level'], 'INFO')
        self.assertEqual(data['message'], 'Test message')
        self.assertEqual(data['logger'], 'test.logger')
        self.assertEqual(data['line'], 42)
        self.assertIn('timestamp', data)
    
    def test_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.extra_fields = {'request_id': '123', 'user': 'alice'}
        
        output = formatter.format(record)
        data = json.loads(output)
        
        self.assertEqual(data['request_id'], '123')
        self.assertEqual(data['user'], 'alice')
    
    def test_sanitization(self):
        """Test sanitization in formatter."""
        formatter = StructuredFormatter(sanitize=True)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="User logged in with password=secret123",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        self.assertIn("***REDACTED***", data['message'])
        self.assertNotIn("secret123", data['message'])
    
    def test_exception_formatting(self):
        """Test exception formatting."""
        formatter = StructuredFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info()
            )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        self.assertIn('exception', data)
        self.assertIn('ValueError', data['exception'])
        self.assertIn('Test error', data['exception'])


class TestColoredFormatter(unittest.TestCase):
    """Test colored console formatter."""
    
    def test_color_formatting(self):
        """Test that colors are added to log levels."""
        formatter = ColoredFormatter('%(levelname)s: %(message)s')
        
        for level_name, color in ColoredFormatter.COLORS.items():
            level = getattr(logging, level_name)
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None
            )
            
            output = formatter.format(record)
            self.assertIn(color, output)
            self.assertIn(ColoredFormatter.RESET, output)


class TestValidationFunctions(unittest.TestCase):
    """Test validation helper functions."""
    
    def test_validate_path_traversal(self):
        """Test path traversal detection."""
        with self.assertRaises(ValueError):
            validate_path('../etc/passwd')
        
        with self.assertRaises(ValueError):
            validate_path('~/secret')
    
    def test_validate_path_system_dirs(self):
        """Test system directory access detection."""
        with self.assertRaises(ValueError):
            validate_path('/etc/shadow')
        
        with self.assertRaises(ValueError):
            validate_path('/root/.ssh/id_rsa')
    
    def test_validate_path_valid(self):
        """Test valid path validation."""
        # Relative paths should work
        result = validate_path('logs/app.log')
        self.assertEqual(result, 'logs/app.log')
        
        # Safe absolute paths should work
        result = validate_path('/tmp/test.log')
        self.assertEqual(result, '/tmp/test.log')
    
    def test_validate_numeric_valid(self):
        """Test valid numeric validation."""
        result = validate_numeric(42, 'test')
        self.assertEqual(result, 42)
        
        result = validate_numeric('100', 'test')
        self.assertEqual(result, 100)
    
    def test_validate_numeric_invalid(self):
        """Test invalid numeric validation."""
        with self.assertRaises(ValueError):
            validate_numeric('not_a_number', 'test')
        
        with self.assertRaises(ValueError):
            validate_numeric(None, 'test')
    
    def test_validate_numeric_range(self):
        """Test numeric range validation."""
        result = validate_numeric(50, 'test', min_val=10, max_val=100)
        self.assertEqual(result, 50)
        
        with self.assertRaises(ValueError):
            validate_numeric(5, 'test', min_val=10)
        
        with self.assertRaises(ValueError):
            validate_numeric(200, 'test', max_val=100)


class TestSetupLogging(unittest.TestCase):
    """Test logging setup function."""
    
    def setUp(self):
        """Clear environment variables before each test."""
        env_vars = [
            'CLAUDE_LOG_LEVEL', 'CLAUDE_LOG_FILE', 'CLAUDE_LOG_FORMAT',
            'CLAUDE_LOG_COLORS', 'CLAUDE_LOG_JSON', 'CLAUDE_LOG_SANITIZE',
            'CLAUDE_LOG_MAX_BYTES', 'CLAUDE_LOG_BACKUP_COUNT', 'CLAUDE_LOG_DIR',
            'CLAUDE_AUTO_SETUP_LOGGING'
        ]
        for var in env_vars:
            os.environ.pop(var, None)
        
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
    
    def test_basic_setup(self):
        """Test basic logging setup."""
        config = setup_logging(log_level='INFO')
        
        self.assertEqual(config['log_level'], 'INFO')
        self.assertEqual(config['handlers'], 1)  # Console handler only
        
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.INFO)
    
    def test_file_logging(self):
        """Test file logging setup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.log')
            config = setup_logging(
                log_level='DEBUG',
                log_file=log_file,
                enable_json=True
            )
            
            self.assertEqual(config['log_file'], log_file)
            self.assertEqual(config['handlers'], 2)  # Console and file
            self.assertTrue(config['enable_json'])
            
            # Test that file is created
            logger = get_logger('test')
            logger.info('Test message')
            
            self.assertTrue(os.path.exists(log_file))
    
    def test_environment_variables(self):
        """Test configuration from environment variables."""
        # Save original values
        env_vars = ['CLAUDE_LOG_LEVEL', 'CLAUDE_LOG_JSON', 'CLAUDE_LOG_SANITIZE', 'CLAUDE_LOG_MAX_BYTES']
        original_values = {var: os.environ.get(var) for var in env_vars}
        
        try:
            os.environ['CLAUDE_LOG_LEVEL'] = 'DEBUG'
            os.environ['CLAUDE_LOG_JSON'] = 'true'
            os.environ['CLAUDE_LOG_SANITIZE'] = 'true'
            os.environ['CLAUDE_LOG_MAX_BYTES'] = '5000'
            
            config = setup_logging()
            
            self.assertEqual(config['log_level'], 'DEBUG')
            self.assertTrue(config['enable_json'])
            self.assertTrue(config['sanitize_logs'])
            self.assertEqual(config['max_bytes'], 5000)
        finally:
            # Restore original values
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                else:
                    os.environ.pop(var, None)
    
    def test_invalid_log_level(self):
        """Test invalid log level handling."""
        with self.assertRaises(ValueError):
            setup_logging(log_level='INVALID')
    
    def test_invalid_numeric_env_vars(self):
        """Test invalid numeric environment variables."""
        # Save original value
        original_value = os.environ.get('CLAUDE_LOG_MAX_BYTES')
        
        try:
            os.environ['CLAUDE_LOG_MAX_BYTES'] = 'not_a_number'
            
            with self.assertRaises(ValueError):
                setup_logging()
        finally:
            # Restore original value
            if original_value is not None:
                os.environ['CLAUDE_LOG_MAX_BYTES'] = original_value
            else:
                os.environ.pop('CLAUDE_LOG_MAX_BYTES', None)
    
    def test_file_permissions(self):
        """Test file permissions setting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.log')
            
            # Create file first
            Path(log_file).touch()
            
            config = setup_logging(
                log_file=log_file,
                file_permissions=0o600
            )
            
            # Check permissions (on Unix systems)
            if sys.platform != 'win32':
                stat_info = os.stat(log_file)
                mode = stat_info.st_mode & 0o777
                self.assertEqual(mode, 0o600)


class TestLogContext(unittest.TestCase):
    """Test LogContext context manager."""
    
    def test_context_injection(self):
        """Test that context is properly injected into logs."""
        logger = get_logger('test_context')
        
        # Clear any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False  # Don't propagate to root logger
        
        with LogContext(logger, request_id='123', user='alice') as log:
            log.info('Test message')
        
        # Get the logged output
        output = stream.getvalue().strip()
        
        # Check if output is JSON
        try:
            data = json.loads(output)
            self.assertEqual(data['request_id'], '123')
            self.assertEqual(data['user'], 'alice')
        except json.JSONDecodeError:
            # If not JSON, check that context is at least in the message
            self.assertIn('123', output)
            self.assertIn('alice', output)
        
        # Clean up
        logger.removeHandler(handler)
    
    def test_nested_contexts(self):
        """Test nested log contexts."""
        logger = get_logger('test_nested')
        
        # Clear any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        
        with LogContext(logger, outer='value1') as log1:
            with LogContext(log1.logger, inner='value2') as log2:
                log2.info('Nested message')
        
        output = stream.getvalue().strip()
        
        # Check if output is JSON
        try:
            data = json.loads(output)
            self.assertEqual(data['inner'], 'value2')
        except json.JSONDecodeError:
            # If not JSON, check that context is at least in the message
            self.assertIn('value2', output)
        
        logger.removeHandler(handler)


class TestLogException(unittest.TestCase):
    """Test log_exception decorator."""
    
    def test_exception_logging(self):
        """Test that exceptions are logged."""
        logger = get_logger('test')
        
        # Capture log output
        handler = logging.StreamHandler(StringIO())
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        @log_exception(logger, "Test function failed")
        def failing_function():
            raise ValueError("Test error")
        
        with self.assertRaises(ValueError):
            failing_function()
        
        # Check that error was logged
        handler.stream.seek(0)
        output = handler.stream.read()
        
        self.assertIn("Test function failed", output)
        self.assertIn("ValueError", output)
        
        logger.removeHandler(handler)
    
    def test_function_metadata_preserved(self):
        """Test that functools.wraps preserves function metadata."""
        logger = get_logger('test')
        
        @log_exception(logger)
        def test_function():
            """Test function docstring."""
            pass
        
        self.assertEqual(test_function.__name__, 'test_function')
        self.assertEqual(test_function.__doc__, 'Test function docstring.')


class TestIntegration(unittest.TestCase):
    """Integration tests for the logging system."""
    
    def test_full_logging_workflow(self):
        """Test complete logging workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'app.log')
            
            # Setup logging with all features
            config = setup_logging(
                log_level='DEBUG',
                log_file=log_file,
                enable_json=True,
                sanitize_logs=True,
                max_bytes=1024,
                backup_count=2
            )
            
            # Get a logger
            logger = get_logger('integration.test')
            
            # Log various messages
            logger.debug('Debug message')  
            logger.warning('Warning with password=secret123')
            
            # Use context manager
            with LogContext(logger, transaction_id='tx-001') as log:
                log.warning('Context warning')
            
            # Log exception
            try:
                raise RuntimeError("Test error")
            except RuntimeError:
                logger.error("Error occurred", exc_info=True)
            
            # Verify file was created and contains data
            self.assertTrue(os.path.exists(log_file))
            
            with open(log_file, 'r') as f:
                content = f.read()
                
                # Check that sensitive data was sanitized
                self.assertIn('password=***REDACTED***', content)
                self.assertNotIn('secret123', content)
                
                # Check that all log levels are present
                self.assertIn('DEBUG', content)
                self.assertIn('WARNING', content)
                self.assertIn('ERROR', content)
                
                # Check context was added
                self.assertIn('tx-001', content)
    
    def test_rotation(self):
        """Test log file rotation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'rotate.log')
            
            # Setup with small max_bytes to trigger rotation
            setup_logging(
                log_file=log_file,
                max_bytes=1024,  # Small but valid to trigger rotation
                backup_count=2
            )
            
            logger = get_logger('rotation.test')
            
            # Write enough to trigger rotation
            for i in range(50):
                logger.info(f"Message {i}: {'x' * 50}")
            
            # Check that backup files were created
            log_dir = Path(tmpdir)
            log_files = list(log_dir.glob('rotate.log*'))
            
            # Should have main file and at least one backup
            self.assertGreater(len(log_files), 1)


if __name__ == '__main__':
    unittest.main()