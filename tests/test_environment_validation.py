"""Tests for claude-tasker environment validation and dependency checking."""
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, Mock


class TestEnvironmentValidation:
    """Test environment validation and dependency checking."""
    
    def test_missing_gh_cli(self, claude_tasker_script, mock_git_repo):
        """Test behavior when gh CLI is missing."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'command -v gh' in cmd:
                    return Mock(returncode=1, stdout="", stderr="gh: command not found")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            assert result.returncode != 0
            assert "Missing required tools" in result.stderr or "gh" in result.stderr
    
    def test_missing_jq_tool(self, claude_tasker_script, mock_git_repo):
        """Test behavior when jq tool is missing."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'command -v jq' in cmd:
                    return Mock(returncode=1, stdout="", stderr="jq: command not found")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            assert result.returncode != 0
            assert "Missing required tools" in result.stderr or "jq" in result.stderr
    
    def test_missing_claude_cli(self, claude_tasker_script, mock_git_repo):
        """Test behavior when claude CLI is missing (non-prompt-only mode)."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'command -v claude' in cmd:
                    return Mock(returncode=1, stdout="", stderr="claude: command not found")
                elif 'command -v gh' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/gh", stderr="")
                elif 'command -v jq' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/jq", stderr="")
                elif 'command -v git' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316"],  # No --prompt-only flag
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            assert result.returncode != 0
            assert "Missing required tools" in result.stderr or "claude" in result.stderr
    
    def test_claude_cli_not_required_prompt_only(self, claude_tasker_script, mock_git_repo):
        """Test that claude CLI is not required in prompt-only mode."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'command -v claude' in cmd:
                    return Mock(returncode=1, stdout="", stderr="claude: command not found")
                elif 'command -v gh' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/gh", stderr="")
                elif 'command -v jq' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/jq", stderr="")
                elif 'command -v git' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/git", stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=str(issue_data), stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should not error about missing claude in prompt-only mode
            assert "claude" not in result.stderr or result.returncode == 0
    
    def test_missing_git_tool(self, claude_tasker_script, mock_git_repo):
        """Test behavior when git is missing."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'command -v git' in cmd:
                    return Mock(returncode=1, stdout="", stderr="git: command not found")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            assert result.returncode != 0
            assert "Missing required tools" in result.stderr or "git" in result.stderr
    
    def test_codex_cli_validation(self, claude_tasker_script, mock_git_repo):
        """Test validation when using codex coder."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'command -v codex' in cmd:
                    return Mock(returncode=1, stdout="", stderr="codex: command not found")
                elif 'command -v gh' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/gh", stderr="")
                elif 'command -v jq' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/jq", stderr="")
                elif 'command -v git' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--coder", "codex"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            assert result.returncode != 0
            assert "Missing required tools" in result.stderr or "codex" in result.stderr
    
    def test_all_dependencies_present(self, claude_tasker_script, mock_git_repo):
        """Test successful validation when all dependencies are present."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'command -v' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/tool", stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=str(issue_data), stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should not error about missing tools
            assert "Missing required tools" not in result.stderr
    
    def test_github_remote_url_validation(self, claude_tasker_script, mock_git_repo):
        """Test validation of GitHub remote URL."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://gitlab.com/test/repo.git", stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should error about non-GitHub remote
            assert result.returncode != 0
            assert "GitHub" in result.stderr or "repository" in result.stderr
    
    def test_no_remote_url(self, claude_tasker_script, mock_git_repo):
        """Test behavior when no remote URL is configured."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=1, stdout="", stderr="No remote URL")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should error about missing remote
            assert result.returncode != 0
    
    def test_ssh_github_url_format(self, claude_tasker_script, mock_git_repo):
        """Test handling of SSH GitHub URL format."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="git@github.com:test/repo.git", stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=str(issue_data), stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should handle SSH format correctly
            assert "Could not determine repository" not in result.stderr
    
    def test_interactive_mode_tty_check(self, claude_tasker_script, mock_git_repo):
        """Test TTY check for interactive mode."""
        with patch('subprocess.run') as mock_run, \
             patch('os.isatty', return_value=False):  # Simulate non-TTY environment
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--interactive"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should warn about non-interactive environment
            assert "interactive" in result.stderr or result.returncode != 0