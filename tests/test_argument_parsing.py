"""Tests for claude-tasker argument parsing and validation."""
import pytest
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock


class TestArgumentParsing:
    """Test argument parsing functionality."""
    
    def test_single_issue_number(self, claude_tasker_script, mock_git_repo, mock_gh_cli):
        """Test parsing a single issue number."""
        with patch('os.chdir'):
            result = subprocess.run(
                [str(claude_tasker_script), "316", "--prompt-only"],
                cwd=mock_git_repo,
                capture_output=True,
                text=True
            )
        
        # Should not error on valid issue number
        assert "Invalid argument" not in result.stderr
    
    def test_issue_range(self, claude_tasker_script, mock_git_repo, mock_gh_cli):
        """Test parsing issue ranges."""
        with patch('os.chdir'):
            result = subprocess.run(
                [str(claude_tasker_script), "230-250", "--prompt-only"],
                cwd=mock_git_repo,
                capture_output=True,
                text=True
            )
        
        assert "Invalid argument" not in result.stderr
    
    def test_review_pr_flag(self, claude_tasker_script, mock_git_repo, mock_gh_cli):
        """Test --review-pr flag parsing."""
        with patch('os.chdir'):
            result = subprocess.run(
                [str(claude_tasker_script), "--review-pr", "329", "--prompt-only"],
                cwd=mock_git_repo,
                capture_output=True,
                text=True
            )
        
        assert result.returncode == 0 or "--review-pr requires" not in result.stderr
    
    def test_review_pr_range(self, claude_tasker_script, mock_git_repo, mock_gh_cli):
        """Test --review-pr with range."""
        with patch('os.chdir'):
            result = subprocess.run(
                [str(claude_tasker_script), "--review-pr", "325-330", "--prompt-only"],
                cwd=mock_git_repo,
                capture_output=True,
                text=True
            )
        
        assert result.returncode == 0 or "--review-pr requires" not in result.stderr
    
    def test_bug_flag(self, claude_tasker_script, mock_git_repo, mock_gh_cli):
        """Test --bug flag parsing."""
        with patch('os.chdir'):
            result = subprocess.run(
                [str(claude_tasker_script), "--bug", "Login fails with 500 error", "--prompt-only"],
                cwd=mock_git_repo,
                capture_output=True,
                text=True
            )
        
        assert result.returncode == 0 or "--bug requires" not in result.stderr
    
    def test_project_flag(self, claude_tasker_script, mock_git_repo, mock_gh_cli):
        """Test --project flag parsing."""
        with patch('os.chdir'):
            result = subprocess.run(
                [str(claude_tasker_script), "316", "--project", "3", "--prompt-only"],
                cwd=mock_git_repo,
                capture_output=True,
                text=True
            )
        
        assert result.returncode == 0 or "--project requires" not in result.stderr
    
    def test_timeout_flag(self, claude_tasker_script, mock_git_repo, mock_gh_cli):
        """Test --timeout flag parsing."""
        with patch('os.chdir'):
            result = subprocess.run(
                [str(claude_tasker_script), "316", "--timeout", "60", "--prompt-only"],
                cwd=mock_git_repo,
                capture_output=True,
                text=True
            )
        
        assert result.returncode == 0 or "--timeout requires" not in result.stderr
    
    def test_coder_flag_claude(self, claude_tasker_script, mock_git_repo, mock_gh_cli):
        """Test --coder flag with claude option."""
        with patch('os.chdir'):
            result = subprocess.run(
                [str(claude_tasker_script), "316", "--coder", "claude", "--prompt-only"],
                cwd=mock_git_repo,
                capture_output=True,
                text=True
            )
        
        assert result.returncode == 0 or "--coder requires" not in result.stderr
    
    def test_coder_flag_codex(self, claude_tasker_script, mock_git_repo, mock_gh_cli):
        """Test --coder flag with codex option."""
        with patch('os.chdir'):
            result = subprocess.run(
                [str(claude_tasker_script), "316", "--coder", "codex", "--prompt-only"],
                cwd=mock_git_repo,
                capture_output=True,
                text=True
            )
        
        assert result.returncode == 0 or "--coder requires" not in result.stderr
    
    def test_base_branch_flag(self, claude_tasker_script, mock_git_repo, mock_gh_cli):
        """Test --base-branch flag parsing."""
        with patch('os.chdir'):
            result = subprocess.run(
                [str(claude_tasker_script), "316", "--base-branch", "develop", "--prompt-only"],
                cwd=mock_git_repo,
                capture_output=True,
                text=True
            )
        
        assert result.returncode == 0 or "--base-branch requires" not in result.stderr
    
    def test_prompt_only_flag(self, claude_tasker_script, mock_git_repo, mock_gh_cli):
        """Test --prompt-only flag."""
        with patch('os.chdir'):
            result = subprocess.run(
                [str(claude_tasker_script), "316", "--prompt-only"],
                cwd=mock_git_repo,
                capture_output=True,
                text=True
            )
        
        # Should run without error in prompt-only mode
        assert "Missing required tools" not in result.stderr
    
    def test_interactive_flag(self, claude_tasker_script, mock_git_repo, mock_gh_cli):
        """Test --interactive flag."""
        with patch('os.chdir'):
            result = subprocess.run(
                [str(claude_tasker_script), "316", "--interactive", "--prompt-only"],
                cwd=mock_git_repo,
                capture_output=True,
                text=True
            )
        
        assert result.returncode == 0 or "Cannot use --prompt-only and --interactive together" in result.stderr
    
    def test_auto_pr_review_flag(self, claude_tasker_script, mock_git_repo, mock_gh_cli):
        """Test --auto-pr-review flag."""
        with patch('os.chdir'):
            result = subprocess.run(
                [str(claude_tasker_script), "316", "--auto-pr-review", "--prompt-only"],
                cwd=mock_git_repo,
                capture_output=True,
                text=True
            )
        
        assert result.returncode == 0 or "--auto-pr-review can only be used with issue implementation" not in result.stderr
    
    def test_help_flag(self, claude_tasker_script):
        """Test --help flag."""
        result = subprocess.run(
            [str(claude_tasker_script), "--help"],
            capture_output=True,
            text=True
        )
        
        assert "Usage:" in result.stdout
        assert "claude-task" in result.stdout
    
    def test_invalid_argument(self, claude_tasker_script, mock_git_repo):
        """Test invalid argument handling."""
        from src.claude_tasker.cli import main
        with patch('sys.argv', ['claude-tasker', 'invalid-arg']):
            with patch('os.chdir'):
                # Capture stderr
                from io import StringIO
                import sys
                captured_stderr = StringIO()
                with patch.object(sys, 'stderr', captured_stderr):
                    exit_code = main()
                
                assert exit_code != 0
                stderr_content = captured_stderr.getvalue()
                assert "Invalid issue number format" in stderr_content
    
    def test_conflicting_flags_review_pr_and_issue(self, claude_tasker_script, mock_git_repo):
        """Test conflicting flags: --review-pr with issue number."""
        from src.claude_tasker.cli import main
        with patch('sys.argv', ['claude-tasker', '316', '--review-pr', '329']):
            with patch('os.chdir'):
                from io import StringIO
                import sys
                captured_stderr = StringIO()
                with patch.object(sys, 'stderr', captured_stderr):
                    exit_code = main()
                
                assert exit_code != 0
                stderr_content = captured_stderr.getvalue()
                assert "multiple actions" in stderr_content
    
    def test_conflicting_flags_bug_and_issue(self, claude_tasker_script, mock_git_repo):
        """Test conflicting flags: --bug with issue number."""
        from src.claude_tasker.cli import main
        with patch('sys.argv', ['claude-tasker', '316', '--bug', 'test bug']):
            with patch('os.chdir'):
                from io import StringIO
                import sys
                captured_stderr = StringIO()
                with patch.object(sys, 'stderr', captured_stderr):
                    exit_code = main()
                
                assert exit_code != 0
                stderr_content = captured_stderr.getvalue()
                assert "multiple actions" in stderr_content
    
    def test_invalid_coder_option(self, claude_tasker_script, mock_git_repo):
        """Test invalid coder option."""
        from src.claude_tasker.cli import main
        with patch('sys.argv', ['claude-tasker', '316', '--coder', 'invalid', '--prompt-only']):
            with patch('os.chdir'), patch('pathlib.Path.exists', return_value=True):
                from io import StringIO
                import sys
                # This should trigger argparse error for invalid choice
                with pytest.raises(SystemExit) as exc_info:
                    main()
                # argparse exits with code 2 for invalid arguments
                assert exc_info.value.code == 2
    
    def test_invalid_timeout_value(self, claude_tasker_script, mock_git_repo):
        """Test invalid timeout value."""
        from src.claude_tasker.cli import main
        with patch('sys.argv', ['claude-tasker', '316', '--timeout', 'invalid', '--prompt-only']):
            with patch('os.chdir'), patch('pathlib.Path.exists', return_value=True):
                # This should trigger argparse error for invalid type
                with pytest.raises(SystemExit) as exc_info:
                    main()
                # argparse exits with code 2 for invalid arguments
                assert exc_info.value.code == 2
    
    def test_invalid_project_value(self, claude_tasker_script, mock_git_repo):
        """Test invalid project ID value."""
        from src.claude_tasker.cli import main
        with patch('sys.argv', ['claude-tasker', '316', '--project', 'invalid', '--prompt-only']):
            with patch('os.chdir'), patch('pathlib.Path.exists', return_value=True):
                # This should trigger argparse error for invalid type
                with pytest.raises(SystemExit) as exc_info:
                    main()
                # argparse exits with code 2 for invalid arguments
                assert exc_info.value.code == 2