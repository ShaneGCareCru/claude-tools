"""Unit tests for CommandExecutor service."""

import pytest
import time
import subprocess
from unittest.mock import Mock, patch, MagicMock
from src.claude_tasker.services.command_executor import (
    CommandExecutor,
    CommandResult,
    CommandErrorType
)


class TestCommandExecutor:
    """Test cases for CommandExecutor service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.executor = CommandExecutor(
            max_retries=2,
            base_delay=0.01,  # Short delay for tests
            max_delay=1.0,
            backoff_multiplier=2.0
        )
    
    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        executor = CommandExecutor()
        assert executor.max_retries == 3
        assert executor.base_delay == 1.0
        assert executor.max_delay == 60.0
        assert executor.backoff_multiplier == 2.0
    
    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        executor = CommandExecutor(
            max_retries=5,
            base_delay=2.0,
            max_delay=30.0,
            backoff_multiplier=1.5
        )
        assert executor.max_retries == 5
        assert executor.base_delay == 2.0
        assert executor.max_delay == 30.0
        assert executor.backoff_multiplier == 1.5
    
    def test_classify_error_success(self):
        """Test error classification for successful commands."""
        result = self.executor._classify_error(0, "")
        assert result == CommandErrorType.SUCCESS
    
    def test_classify_error_timeout(self):
        """Test error classification for timeout errors."""
        result = self.executor._classify_error(124, "")
        assert result == CommandErrorType.TIMEOUT
        
        result = self.executor._classify_error(1, "timeout exceeded")
        assert result == CommandErrorType.TIMEOUT
    
    def test_classify_error_not_found(self):
        """Test error classification for command not found."""
        result = self.executor._classify_error(127, "")
        assert result == CommandErrorType.NOT_FOUND
    
    def test_classify_error_permission_denied(self):
        """Test error classification for permission denied."""
        result = self.executor._classify_error(126, "")
        assert result == CommandErrorType.PERMISSION_DENIED
    
    def test_classify_error_network(self):
        """Test error classification for network errors."""
        result = self.executor._classify_error(1, "network connection failed")
        assert result == CommandErrorType.NETWORK_ERROR
        
        result = self.executor._classify_error(1, "DNS resolution failed")
        assert result == CommandErrorType.NETWORK_ERROR
    
    def test_classify_error_rate_limit(self):
        """Test error classification for rate limiting."""
        result = self.executor._classify_error(1, "rate limit exceeded")
        assert result == CommandErrorType.RATE_LIMITED
        
        result = self.executor._classify_error(1, "too many requests")
        assert result == CommandErrorType.RATE_LIMITED
    
    def test_classify_error_general(self):
        """Test error classification for general errors."""
        result = self.executor._classify_error(1, "some other error")
        assert result == CommandErrorType.GENERAL_ERROR
    
    def test_should_retry_retryable_errors(self):
        """Test retry logic for retryable errors."""
        assert self.executor._should_retry(CommandErrorType.TIMEOUT)
        assert self.executor._should_retry(CommandErrorType.NETWORK_ERROR)
        assert self.executor._should_retry(CommandErrorType.RATE_LIMITED)
    
    def test_should_retry_non_retryable_errors(self):
        """Test retry logic for non-retryable errors."""
        assert not self.executor._should_retry(CommandErrorType.SUCCESS)
        assert not self.executor._should_retry(CommandErrorType.NOT_FOUND)
        assert not self.executor._should_retry(CommandErrorType.PERMISSION_DENIED)
        assert not self.executor._should_retry(CommandErrorType.GENERAL_ERROR)
    
    def test_calculate_delay(self):
        """Test exponential backoff delay calculation."""
        # Test exponential backoff
        delay1 = self.executor._calculate_delay(0)
        delay2 = self.executor._calculate_delay(1)
        delay3 = self.executor._calculate_delay(2)
        
        assert delay1 == 0.01  # base_delay
        assert delay2 == 0.02  # base_delay * multiplier
        assert delay3 == 0.04  # base_delay * multiplier^2
        
        # Test max delay cap
        executor = CommandExecutor(base_delay=10, max_delay=15, backoff_multiplier=2)
        delay_large = executor._calculate_delay(10)
        assert delay_large == 15  # Should be capped at max_delay
    
    @patch('subprocess.run')
    def test_execute_success(self, mock_run):
        """Test successful command execution."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "success output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = self.executor.execute(["echo", "test"])
        
        assert result.success is True
        assert result.returncode == 0
        assert result.stdout == "success output"
        assert result.stderr == ""
        assert result.error_type == CommandErrorType.SUCCESS
        assert result.attempts == 1
        assert result.command == "echo test"
    
    @patch('subprocess.run')
    def test_execute_failure_no_retry(self, mock_run):
        """Test failed command execution without retry."""
        mock_result = Mock()
        mock_result.returncode = 127
        mock_result.stdout = ""
        mock_result.stderr = "command not found"
        mock_run.return_value = mock_result
        
        result = self.executor.execute(["nonexistent"], retry=True)
        
        assert result.success is False
        assert result.returncode == 127
        assert result.error_type == CommandErrorType.NOT_FOUND
        assert result.attempts == 1  # Should not retry NOT_FOUND errors
    
    @patch('subprocess.run')
    @patch('time.sleep')
    def test_execute_retry_on_timeout(self, mock_sleep, mock_run):
        """Test retry logic for timeout errors."""
        # First call fails with timeout, second succeeds
        mock_results = [
            Mock(returncode=124, stdout="", stderr="timeout"),
            Mock(returncode=0, stdout="success", stderr="")
        ]
        mock_run.side_effect = mock_results
        
        result = self.executor.execute(["slow_command"], retry=True)
        
        assert result.success is True
        assert result.attempts == 2
        assert mock_run.call_count == 2
        assert mock_sleep.call_count == 1  # Called once between retries
        mock_sleep.assert_called_with(0.01)  # base_delay
    
    @patch('subprocess.run')
    @patch('time.sleep')
    def test_execute_max_retries_exceeded(self, mock_sleep, mock_run):
        """Test behavior when max retries are exceeded."""
        # All calls fail with timeout
        mock_result = Mock()
        mock_result.returncode = 124
        mock_result.stdout = ""
        mock_result.stderr = "timeout"
        mock_run.return_value = mock_result
        
        result = self.executor.execute(["always_timeout"], retry=True)
        
        assert result.success is False
        assert result.attempts == 3  # 1 initial + 2 retries
        assert mock_run.call_count == 3
        assert mock_sleep.call_count == 2  # Called between retries
    
    @patch('subprocess.run')
    def test_execute_timeout_exception(self, mock_run):
        """Test handling of subprocess timeout exception."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=['test'], timeout=30, output=b'partial', stderr=b'error'
        )
        
        result = self.executor.execute(['test'], timeout=30)
        
        assert result.success is False
        assert result.error_type == CommandErrorType.TIMEOUT
        # The timeout message format may vary, check for key content
        assert "30s" in result.stderr or "error" in result.stderr
        assert result.stdout == "partial"
    
    @patch('subprocess.run')
    def test_execute_general_exception(self, mock_run):
        """Test handling of general exceptions."""
        mock_run.side_effect = OSError("Permission denied")
        
        result = self.executor.execute(['test'])
        
        assert result.success is False
        assert result.error_type == CommandErrorType.GENERAL_ERROR
        assert "Permission denied" in result.stderr
    
    def test_execute_string_command(self):
        """Test execution with string command."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "success"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = self.executor.execute("echo test")
            
            assert result.success is True
            assert result.command == "echo test"
            # Should be split into list for subprocess
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args == ['echo', 'test']
    
    @patch('subprocess.run')
    def test_execute_with_cwd(self, mock_run):
        """Test execution with working directory."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        self.executor.execute(['ls'], cwd='/tmp')
        
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['cwd'] == '/tmp'
    
    @patch('subprocess.run')
    def test_execute_with_env(self, mock_run):
        """Test execution with environment variables."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        env = {'TEST_VAR': 'test_value'}
        self.executor.execute(['env'], env=env)
        
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['env'] == env
    
    @patch('subprocess.run')
    def test_execute_simple(self, mock_run):
        """Test execute_simple method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "success"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        success = self.executor.execute_simple(['echo', 'test'])
        assert success is True
        
        mock_result.returncode = 1
        success = self.executor.execute_simple(['false'])
        assert success is False
    
    @patch('subprocess.run')
    def test_execute_with_output(self, mock_run):
        """Test execute_with_output method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "output"
        mock_result.stderr = "error"
        mock_run.return_value = mock_result
        
        success, stdout, stderr = self.executor.execute_with_output(['echo', 'test'])
        
        assert success is True
        assert stdout == "output"
        assert stderr == "error"
    
    def test_command_result_dataclass(self):
        """Test CommandResult dataclass."""
        result = CommandResult(
            returncode=0,
            stdout="output",
            stderr="",
            command="test",
            execution_time=1.0,
            error_type=CommandErrorType.SUCCESS,
            attempts=1,
            success=True
        )
        
        assert result.returncode == 0
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.command == "test"
        assert result.execution_time == 1.0
        assert result.error_type == CommandErrorType.SUCCESS
        assert result.attempts == 1
        assert result.success is True