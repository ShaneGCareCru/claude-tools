"""Pytest configuration and shared fixtures."""
import pytest
import subprocess
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for testing shell commands."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="success",
            stderr="",
            check=Mock()
        )
        yield mock_run


@pytest.fixture
def mock_git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    
    # Create CLAUDE.md file
    (repo_dir / "CLAUDE.md").write_text("# Test CLAUDE.md\nTest content")
    
    # Mock git commands
    with patch('subprocess.run') as mock_run:
        def git_side_effect(*args, **kwargs):
            if 'git rev-parse --git-dir' in ' '.join(args[0]):
                return Mock(returncode=0, stdout=".git", stderr="")
            elif 'git config --get remote.origin.url' in ' '.join(args[0]):
                return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
            elif 'git branch --show-current' in ' '.join(args[0]):
                return Mock(returncode=0, stdout="main", stderr="")
            elif 'git show-ref --verify --quiet' in ' '.join(args[0]):
                return Mock(returncode=0, stdout="", stderr="")
            elif 'git status --porcelain' in ' '.join(args[0]):
                return Mock(returncode=0, stdout="", stderr="")
            elif 'git diff --quiet' in ' '.join(args[0]):
                return Mock(returncode=0, stdout="", stderr="")
            elif 'git log --oneline' in ' '.join(args[0]):
                return Mock(returncode=0, stdout="abc123 Test commit", stderr="")
            else:
                return Mock(returncode=0, stdout="", stderr="")
        
        mock_run.side_effect = git_side_effect
        yield repo_dir


@pytest.fixture
def mock_gh_cli():
    """Mock GitHub CLI commands."""
    with patch('subprocess.run') as mock_run:
        def gh_side_effect(*args, **kwargs):
            cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
            
            if 'gh issue view' in cmd:
                return Mock(
                    returncode=0,
                    stdout='{"title":"Test Issue","body":"Test body","labels":[],"url":"https://github.com/test/repo/issues/1"}',
                    stderr=""
                )
            elif 'gh pr view' in cmd:
                return Mock(
                    returncode=0,
                    stdout='{"title":"Test PR","body":"Test PR body","number":1,"url":"https://github.com/test/repo/pull/1"}',
                    stderr=""
                )
            elif 'gh pr create' in cmd:
                return Mock(returncode=0, stdout="https://github.com/test/repo/pull/1", stderr="")
            elif 'gh issue comment' in cmd or 'gh pr comment' in cmd:
                return Mock(returncode=0, stdout="", stderr="")
            else:
                return Mock(returncode=0, stdout="", stderr="")
        
        mock_run.side_effect = gh_side_effect
        yield mock_run


@pytest.fixture
def mock_claude_cli():
    """Mock Claude CLI commands."""
    with patch('subprocess.run') as mock_run:
        def claude_side_effect(*args, **kwargs):
            if 'claude' in ' '.join(args[0]):
                return Mock(
                    returncode=0,
                    stdout='{"result":"Test Claude output"}',
                    stderr=""
                )
            else:
                return Mock(returncode=0, stdout="", stderr="")
        
        mock_run.side_effect = claude_side_effect
        yield mock_run



@pytest.fixture
def mock_environment_vars():
    """Mock environment variables."""
    env_vars = {
        'HOME': '/tmp/test_home',
        'USER': 'testuser',
        'CLAUDE_TASKER_AUTO_CLEANUP': '',
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars