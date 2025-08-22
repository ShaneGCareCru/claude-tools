"""Base classes for consistent command execution and error handling."""

import subprocess
from typing import List, Tuple


class CommandExecutor:
    """Base class for consistent command execution and error handling."""
    
    @staticmethod
    def run_command(cmd: List[str], timeout: int = 60, **kwargs) -> Tuple[bool, str, str]:
        """
        Run command with consistent error handling.
        
        Args:
            cmd: Command and arguments as list
            timeout: Command timeout in seconds
            **kwargs: Additional arguments for subprocess.run
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                **kwargs
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except FileNotFoundError:
            return False, "", f"Command not found: {cmd[0]}"
        except Exception as e:
            return False, "", str(e)
    
    @staticmethod
    def run_with_retry(cmd: List[str], max_attempts: int = 3, 
                      timeout: int = 60, **kwargs) -> Tuple[bool, str, str]:
        """
        Run command with retry logic.
        
        Args:
            cmd: Command and arguments as list
            max_attempts: Maximum number of retry attempts
            timeout: Command timeout in seconds
            **kwargs: Additional arguments for subprocess.run
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        for attempt in range(max_attempts):
            success, stdout, stderr = CommandExecutor.run_command(cmd, timeout, **kwargs)
            if success:
                return True, stdout, stderr
            
            # Don't retry on command not found
            if "Command not found" in stderr:
                break
                
        return False, stdout, stderr