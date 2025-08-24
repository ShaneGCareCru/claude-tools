"""Tests for base.py module - CommandExecutor class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess

from src.claude_tasker.base import CommandExecutor


class TestCommandExecutor:
    """Test CommandExecutor class."""
    
    def test_run_command_success(self):
        """Test successful command execution."""
        mock_result = Mock(returncode=0, stdout="Success", stderr="")
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            success, stdout, stderr = CommandExecutor.run_command(['echo', 'test'])
        
        assert success is True
        assert stdout == "Success"
        assert stderr == ""
        mock_run.assert_called_once()
    
    def test_run_command_failure(self):
        """Test failed command execution."""
        mock_result = Mock(returncode=1, stdout="", stderr="Error occurred")
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            success, stdout, stderr = CommandExecutor.run_command(['false'])
        
        assert success is False
        assert stdout == ""
        assert stderr == "Error occurred"
    
    def test_run_command_timeout(self):
        """Test command timeout."""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 5)):
            success, stdout, stderr = CommandExecutor.run_command(['sleep', '10'], timeout=5)
        
        assert success is False
        assert stdout == ""
        assert "timed out after 5s" in stderr
    
    def test_run_command_file_not_found(self):
        """Test command not found."""
        with patch('subprocess.run', side_effect=FileNotFoundError("Command not found")):
            success, stdout, stderr = CommandExecutor.run_command(['nonexistent_command'])
        
        assert success is False
        assert stdout == ""
        assert "Command not found: nonexistent_command" in stderr
    
    def test_run_command_generic_exception(self):
        """Test generic exception handling."""
        with patch('subprocess.run', side_effect=Exception("Unexpected error")):
            success, stdout, stderr = CommandExecutor.run_command(['cmd'])
        
        assert success is False
        assert stdout == ""
        assert stderr == "Unexpected error"
    
    def test_run_command_with_kwargs(self):
        """Test passing additional kwargs to subprocess.run."""
        mock_result = Mock(returncode=0, stdout="Output", stderr="")
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            success, stdout, stderr = CommandExecutor.run_command(
                ['echo', 'test'],
                timeout=30,
                cwd='/tmp',
                env={'KEY': 'VALUE'}
            )
        
        assert success is True
        # Verify kwargs were passed
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['timeout'] == 30
        assert call_kwargs['cwd'] == '/tmp'
        assert call_kwargs['env'] == {'KEY': 'VALUE'}
    
    def test_run_with_retry_success_first_attempt(self):
        """Test run_with_retry succeeds on first attempt."""
        mock_result = Mock(returncode=0, stdout="Success", stderr="")
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            success, stdout, stderr = CommandExecutor.run_with_retry(['echo', 'test'])
        
        assert success is True
        assert stdout == "Success"
        assert mock_run.call_count == 1
    
    def test_run_with_retry_success_second_attempt(self):
        """Test run_with_retry succeeds on second attempt."""
        mock_results = [
            Mock(returncode=1, stdout="", stderr="Temporary failure"),
            Mock(returncode=0, stdout="Success", stderr="")
        ]
        
        with patch('subprocess.run', side_effect=mock_results) as mock_run:
            success, stdout, stderr = CommandExecutor.run_with_retry(['cmd'], max_attempts=3)
        
        assert success is True
        assert stdout == "Success"
        assert mock_run.call_count == 2
    
    def test_run_with_retry_all_attempts_fail(self):
        """Test run_with_retry when all attempts fail."""
        mock_result = Mock(returncode=1, stdout="", stderr="Persistent error")
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            success, stdout, stderr = CommandExecutor.run_with_retry(['cmd'], max_attempts=3)
        
        assert success is False
        assert stderr == "Persistent error"
        assert mock_run.call_count == 3
    
    def test_run_with_retry_command_not_found_no_retry(self):
        """Test run_with_retry doesn't retry on command not found."""
        mock_result = Mock(returncode=127, stdout="", stderr="Command not found: invalid")
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            success, stdout, stderr = CommandExecutor.run_with_retry(['invalid'], max_attempts=3)
        
        assert success is False
        assert "Command not found" in stderr
        # Should only try once since command not found
        assert mock_run.call_count == 1
    
    def test_run_with_retry_with_timeout(self):
        """Test run_with_retry with custom timeout."""
        mock_result = Mock(returncode=0, stdout="Success", stderr="")
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            success, stdout, stderr = CommandExecutor.run_with_retry(
                ['cmd'], 
                max_attempts=2,
                timeout=120
            )
        
        assert success is True
        # Verify timeout was passed
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['timeout'] == 120
    
    def test_run_with_retry_mixed_failures(self):
        """Test run_with_retry with different failure types."""
        mock_results = [
            subprocess.TimeoutExpired('cmd', 5),  # First attempt: timeout
            Mock(returncode=1, stdout="", stderr="Error"),  # Second attempt: failure
            Mock(returncode=0, stdout="Success", stderr="")  # Third attempt: success
        ]
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = mock_results
            success, stdout, stderr = CommandExecutor.run_with_retry(['cmd'], max_attempts=3)
        
        assert success is True
        assert stdout == "Success"
        assert mock_run.call_count == 3