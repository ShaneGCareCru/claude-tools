"""Test wrapper for Python CLI instead of bash script.

This file provides utilities for testing the Python CLI implementation
rather than the old bash script, ensuring tests match the actual behavior.
"""

import subprocess
from pathlib import Path
from typing import List, Optional
from unittest.mock import patch


def run_claude_tasker_python(args: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run claude-tasker Python module with given arguments.
    
    Args:
        args: Command line arguments (without the command itself)
        cwd: Working directory for the command
        
    Returns:
        subprocess.CompletedProcess result
    """
    cmd = ["python", "-m", "src.claude_tasker"] + args
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )


def test_python_cli_basic():
    """Quick test to verify the Python CLI wrapper works."""
    result = run_claude_tasker_python(["--help"])
    assert result.returncode == 0
    assert "claude-tasker" in result.stdout.lower()


def test_python_cli_invalid_arg():
    """Test invalid argument handling."""
    result = run_claude_tasker_python(["invalid-arg"])
    assert result.returncode != 0
    assert "error" in result.stderr.lower()


def test_python_cli_conflicting_flags():
    """Test conflicting flags behavior.""" 
    result = run_claude_tasker_python(["316", "--review-pr", "329"])
    assert result.returncode != 0
    assert "cannot" in result.stderr.lower() or "multiple" in result.stderr.lower()


if __name__ == "__main__":
    # Quick verification
    test_python_cli_basic()
    test_python_cli_invalid_arg() 
    test_python_cli_conflicting_flags()
    print("✅ Python CLI wrapper tests passed")