"""Command execution service with exponential backoff and structured returns."""
import subprocess
import time
import logging
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum


class CommandErrorType(Enum):
    """Classification of command execution errors."""
    SUCCESS = "success"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"
    GENERAL_ERROR = "general_error"


@dataclass
class CommandResult:
    """Structured result from command execution."""
    returncode: int
    stdout: str
    stderr: str
    command: str
    execution_time: float
    error_type: CommandErrorType
    attempts: int
    success: bool


class CommandExecutor:
    """Service for executing shell commands with retry logic and structured returns."""
    
    def __init__(self, 
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_multiplier: float = 2.0,
                 timeout: Optional[int] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize CommandExecutor.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            max_delay: Maximum delay between retries
            backoff_multiplier: Multiplier for exponential backoff
            timeout: Default timeout for commands
            logger: Logger instance
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.default_timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        
    def _classify_error(self, returncode: int, stderr: str) -> CommandErrorType:
        """Classify the type of error based on return code and stderr."""
        if returncode == 0:
            return CommandErrorType.SUCCESS
        elif returncode == 124:  # timeout command exit code
            return CommandErrorType.TIMEOUT
        elif returncode == 127:  # command not found
            return CommandErrorType.NOT_FOUND
        elif returncode == 126:  # permission denied
            return CommandErrorType.PERMISSION_DENIED
        elif "timeout" in stderr.lower():
            return CommandErrorType.TIMEOUT
        elif any(phrase in stderr.lower() for phrase in ["network", "connection", "dns"]):
            return CommandErrorType.NETWORK_ERROR
        elif any(phrase in stderr.lower() for phrase in ["rate limit", "too many requests", "429"]):
            return CommandErrorType.RATE_LIMITED
        else:
            return CommandErrorType.GENERAL_ERROR
    
    def _should_retry(self, error_type: CommandErrorType) -> bool:
        """Determine if a command should be retried based on error type."""
        retryable_errors = {
            CommandErrorType.TIMEOUT,
            CommandErrorType.NETWORK_ERROR,
            CommandErrorType.RATE_LIMITED
        }
        return error_type in retryable_errors
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for exponential backoff."""
        delay = self.base_delay * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_delay)
    
    def execute(self,
                command: Union[str, List[str]], 
                cwd: Optional[str] = None,
                env: Optional[Dict[str, str]] = None,
                timeout: Optional[int] = None,
                retry: bool = True,
                shell: bool = False) -> CommandResult:
        """
        Execute a command with retry logic and structured return.
        
        Args:
            command: Command to execute (string or list)
            cwd: Working directory
            env: Environment variables
            timeout: Command timeout
            retry: Whether to retry on failure
            shell: Whether to use shell execution
            
        Returns:
            CommandResult with structured information about execution
        """
        if isinstance(command, str):
            cmd_str = command
            if not shell:
                command = command.split()
        else:
            cmd_str = ' '.join(command)
            
        timeout = timeout or self.default_timeout
        attempts = 0
        last_result = None
        
        while attempts <= (self.max_retries if retry else 0):
            attempts += 1
            start_time = time.time()
            
            try:
                self.logger.debug(f"Executing command (attempt {attempts}): {cmd_str}")
                
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    env=env,
                    timeout=timeout,
                    shell=shell
                )
                
                execution_time = time.time() - start_time
                error_type = self._classify_error(result.returncode, result.stderr)
                
                command_result = CommandResult(
                    returncode=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    command=cmd_str,
                    execution_time=execution_time,
                    error_type=error_type,
                    attempts=attempts,
                    success=(result.returncode == 0)
                )
                
                last_result = command_result
                
                if command_result.success:
                    self.logger.debug(f"Command succeeded after {attempts} attempts")
                    return command_result
                
                if not retry or not self._should_retry(error_type) or attempts > self.max_retries:
                    self.logger.warning(f"Command failed: {cmd_str}, error: {error_type.value}")
                    return command_result
                
                # Wait before retry
                delay = self._calculate_delay(attempts - 1)
                self.logger.info(f"Retrying command in {delay}s (attempt {attempts + 1}/{self.max_retries + 1})")
                time.sleep(delay)
                
            except subprocess.TimeoutExpired as e:
                execution_time = time.time() - start_time
                last_result = CommandResult(
                    returncode=124,
                    stdout=e.stdout.decode() if e.stdout else "",
                    stderr=e.stderr.decode() if e.stderr else f"Command timed out after {timeout}s",
                    command=cmd_str,
                    execution_time=execution_time,
                    error_type=CommandErrorType.TIMEOUT,
                    attempts=attempts,
                    success=False
                )
                
                if not retry or attempts > self.max_retries:
                    self.logger.warning(f"Command timed out: {cmd_str}")
                    return last_result
                    
                delay = self._calculate_delay(attempts - 1)
                self.logger.info(f"Retrying timed out command in {delay}s")
                time.sleep(delay)
                
            except Exception as e:
                execution_time = time.time() - start_time
                last_result = CommandResult(
                    returncode=-1,
                    stdout="",
                    stderr=str(e),
                    command=cmd_str,
                    execution_time=execution_time,
                    error_type=CommandErrorType.GENERAL_ERROR,
                    attempts=attempts,
                    success=False
                )
                
                if not retry or attempts > self.max_retries:
                    self.logger.error(f"Command execution failed: {cmd_str}, error: {e}")
                    return last_result
                    
                delay = self._calculate_delay(attempts - 1)
                self.logger.info(f"Retrying failed command in {delay}s")
                time.sleep(delay)
        
        return last_result or CommandResult(
            returncode=-1,
            stdout="",
            stderr="Maximum retries exceeded",
            command=cmd_str,
            execution_time=0.0,
            error_type=CommandErrorType.GENERAL_ERROR,
            attempts=attempts,
            success=False
        )
    
    def execute_simple(self, command: Union[str, List[str]], **kwargs) -> bool:
        """
        Simple execution that returns only success/failure.
        
        Args:
            command: Command to execute
            **kwargs: Additional arguments for execute()
            
        Returns:
            True if command succeeded, False otherwise
        """
        result = self.execute(command, **kwargs)
        return result.success
    
    def execute_with_output(self, command: Union[str, List[str]], **kwargs) -> tuple[bool, str, str]:
        """
        Execute command and return success, stdout, stderr.
        
        Args:
            command: Command to execute
            **kwargs: Additional arguments for execute()
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        result = self.execute(command, **kwargs)
        return result.success, result.stdout, result.stderr