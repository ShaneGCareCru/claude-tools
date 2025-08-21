"""Tests for all command-line flags and options in claude-tasker."""
import pytest
import subprocess
import json
from pathlib import Path
from unittest.mock import patch, Mock


class TestCommandFlags:
    """Test all command-line flags and options."""
    
    def test_all_flags_combination_valid(self, claude_tasker_script, mock_git_repo):
        """Test valid combination of multiple flags."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'gh project view' in cmd:
                    project_data = {"title": "Test Project", "body": "Test"}
                    return Mock(returncode=0, stdout=json.dumps(project_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run([
                    str(claude_tasker_script), "316",
                    "--project", "3",
                    "--timeout", "60", 
                    "--coder", "claude",
                    "--base-branch", "develop",
                    "--prompt-only"
                ], cwd=mock_git_repo, capture_output=True, text=True)
            
            assert result.returncode == 0
    
    def test_auto_pr_review_with_issue_range(self, claude_tasker_script, mock_git_repo):
        """Test --auto-pr-review with issue range."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'), patch('time.sleep'):
                result = subprocess.run([
                    str(claude_tasker_script), "316-318",
                    "--auto-pr-review",
                    "--timeout", "1",
                    "--prompt-only"
                ], cwd=mock_git_repo, capture_output=True, text=True)
            
            assert result.returncode == 0
    
    def test_review_pr_with_range_and_timeout(self, claude_tasker_script, mock_git_repo):
        """Test --review-pr with range and timeout."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh pr view' in cmd:
                    pr_data = {"title": "Test PR", "body": "Test", "number": 329}
                    return Mock(returncode=0, stdout=json.dumps(pr_data), stderr="")
                elif 'gh pr diff' in cmd:
                    return Mock(returncode=0, stdout="diff --git a/file.txt", stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'), patch('time.sleep'):
                result = subprocess.run([
                    str(claude_tasker_script),
                    "--review-pr", "325-327",
                    "--timeout", "1",
                    "--prompt-only"
                ], cwd=mock_git_repo, capture_output=True, text=True)
            
            assert result.returncode == 0
    
    def test_bug_analysis_with_coder_flag(self, claude_tasker_script, mock_git_repo):
        """Test --bug flag with --coder option."""
        with patch('subprocess.run') as mock_run:
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
                result = subprocess.run([
                    str(claude_tasker_script),
                    "--bug", "Payment processing timeout",
                    "--coder", "codex",
                    "--prompt-only"
                ], cwd=mock_git_repo, capture_output=True, text=True)
            
            assert result.returncode == 0
    
    def test_interactive_with_review_pr(self, claude_tasker_script, mock_git_repo):
        """Test --interactive flag with --review-pr."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh pr view' in cmd:
                    pr_data = {"title": "Test PR", "body": "Test", "number": 329}
                    return Mock(returncode=0, stdout=json.dumps(pr_data), stderr="")
                elif 'gh pr diff' in cmd:
                    return Mock(returncode=0, stdout="diff --git a/file.txt", stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run([
                    str(claude_tasker_script),
                    "--review-pr", "329",
                    "--interactive",
                    "--prompt-only"
                ], cwd=mock_git_repo, capture_output=True, text=True)
            
            # Should error due to conflicting flags
            assert result.returncode != 0 and "Cannot use --prompt-only and --interactive together" in result.stderr
    
    def test_base_branch_with_issue_implementation(self, claude_tasker_script, mock_git_repo):
        """Test --base-branch flag with issue implementation."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git show-ref --verify --quiet refs/heads/develop' in cmd:
                    return Mock(returncode=0, stdout="", stderr="")  # develop branch exists
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run([
                    str(claude_tasker_script), "316",
                    "--base-branch", "develop",
                    "--prompt-only"
                ], cwd=mock_git_repo, capture_output=True, text=True)
            
            assert result.returncode == 0
    
    def test_project_flag_with_invalid_id(self, claude_tasker_script, mock_git_repo):
        """Test --project flag with invalid project ID."""
        with patch('os.chdir'):
            result = subprocess.run([
                str(claude_tasker_script), "316",
                "--project", "invalid-id",
                "--prompt-only"
            ], cwd=mock_git_repo, capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "--project requires a project ID" in result.stderr
    
    def test_timeout_flag_edge_cases(self, claude_tasker_script, mock_git_repo):
        """Test --timeout flag with edge cases."""
        # Test with zero timeout
        with patch('os.chdir'):
            result = subprocess.run([
                str(claude_tasker_script), "316",
                "--timeout", "0",
                "--prompt-only"
            ], cwd=mock_git_repo, capture_output=True, text=True)
        
        # Should accept 0 as valid timeout
        assert "--timeout requires a number of seconds" not in result.stderr
        
        # Test with very large timeout
        with patch('os.chdir'):
            result = subprocess.run([
                str(claude_tasker_script), "316",
                "--timeout", "9999",
                "--prompt-only"
            ], cwd=mock_git_repo, capture_output=True, text=True)
        
        # Should accept large timeout
        assert "--timeout requires a number of seconds" not in result.stderr
    
    def test_coder_flag_case_sensitivity(self, claude_tasker_script, mock_git_repo):
        """Test --coder flag case sensitivity."""
        with patch('os.chdir'):
            result = subprocess.run([
                str(claude_tasker_script), "316",
                "--coder", "CLAUDE",  # uppercase
                "--prompt-only"
            ], cwd=mock_git_repo, capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "--coder requires either 'claude' or 'codex'" in result.stderr
    
    def test_bug_flag_empty_description(self, claude_tasker_script, mock_git_repo):
        """Test --bug flag with empty description."""
        with patch('os.chdir'):
            result = subprocess.run([
                str(claude_tasker_script),
                "--bug", "",  # empty description
                "--prompt-only"
            ], cwd=mock_git_repo, capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "--bug requires a description" in result.stderr
    
    def test_base_branch_flag_empty_value(self, claude_tasker_script, mock_git_repo):
        """Test --base-branch flag with empty value."""
        with patch('os.chdir'):
            result = subprocess.run([
                str(claude_tasker_script), "316",
                "--base-branch", "",  # empty branch name
                "--prompt-only"
            ], cwd=mock_git_repo, capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "--base-branch requires a branch name" in result.stderr
    
    def test_multiple_mode_conflicts(self, claude_tasker_script, mock_git_repo):
        """Test conflicts between multiple modes."""
        # Test --bug with --review-pr
        with patch('os.chdir'):
            result = subprocess.run([
                str(claude_tasker_script),
                "--bug", "test bug",
                "--review-pr", "329"
            ], cwd=mock_git_repo, capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "Cannot specify both" in result.stderr
    
    def test_auto_pr_review_mode_restriction(self, claude_tasker_script, mock_git_repo):
        """Test --auto-pr-review mode restrictions."""
        # Test --auto-pr-review with --review-pr (should fail)
        with patch('os.chdir'):
            result = subprocess.run([
                str(claude_tasker_script),
                "--review-pr", "329",
                "--auto-pr-review"
            ], cwd=mock_git_repo, capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "--auto-pr-review can only be used with issue implementation" in result.stderr
        
        # Test --auto-pr-review with --bug (should fail)
        with patch('os.chdir'):
            result = subprocess.run([
                str(claude_tasker_script),
                "--bug", "test bug",
                "--auto-pr-review"
            ], cwd=mock_git_repo, capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "--auto-pr-review can only be used with issue implementation" in result.stderr
    
    def test_prompt_only_interactive_conflict(self, claude_tasker_script, mock_git_repo):
        """Test --prompt-only and --interactive conflict."""
        with patch('os.chdir'):
            result = subprocess.run([
                str(claude_tasker_script), "316",
                "--prompt-only",
                "--interactive"
            ], cwd=mock_git_repo, capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "Cannot use --prompt-only and --interactive together" in result.stderr
    
    def test_flag_order_independence(self, claude_tasker_script, mock_git_repo):
        """Test that flag order doesn't matter."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            # Test different flag orders
            order1 = [str(claude_tasker_script), "316", "--timeout", "60", "--coder", "claude", "--prompt-only"]
            order2 = [str(claude_tasker_script), "--coder", "claude", "316", "--prompt-only", "--timeout", "60"]
            
            with patch('os.chdir'):
                result1 = subprocess.run(order1, cwd=mock_git_repo, capture_output=True, text=True)
                result2 = subprocess.run(order2, cwd=mock_git_repo, capture_output=True, text=True)
            
            # Both should succeed
            assert result1.returncode == 0
            assert result2.returncode == 0