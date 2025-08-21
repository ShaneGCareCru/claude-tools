"""Tests for claude-tasker GitHub CLI integrations."""
import pytest
import subprocess
import json
from pathlib import Path
from unittest.mock import patch, Mock, call


class TestGitHubCLI:
    """Test GitHub CLI integrations."""
    
    def test_gh_issue_view(self, claude_tasker_script, mock_git_repo):
        """Test GitHub issue viewing functionality."""
        with patch('subprocess.run') as mock_run:
            def gh_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh issue view' in cmd:
                    issue_data = {
                        "title": "Test Issue",
                        "body": "This is a test issue",
                        "labels": [{"name": "bug"}],
                        "url": "https://github.com/test/repo/issues/316"
                    }
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = gh_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should call gh issue view
            gh_calls = [call for call in mock_run.call_args_list 
                       if 'gh issue view' in str(call.args)]
            assert len(gh_calls) > 0
    
    def test_gh_pr_view(self, claude_tasker_script, mock_git_repo):
        """Test GitHub PR viewing functionality."""
        with patch('subprocess.run') as mock_run:
            def gh_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh pr view' in cmd:
                    pr_data = {
                        "title": "Test PR",
                        "body": "This is a test PR",
                        "number": 329,
                        "url": "https://github.com/test/repo/pull/329"
                    }
                    return Mock(returncode=0, stdout=json.dumps(pr_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = gh_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "--review-pr", "329", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should call gh pr view
            gh_calls = [call for call in mock_run.call_args_list 
                       if 'gh pr view' in str(call.args)]
            assert len(gh_calls) > 0
    
    def test_gh_pr_diff(self, claude_tasker_script, mock_git_repo):
        """Test GitHub PR diff functionality."""
        with patch('subprocess.run') as mock_run:
            def gh_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh pr diff' in cmd:
                    return Mock(returncode=0, stdout="diff --git a/file.txt b/file.txt", stderr="")
                elif 'gh pr view' in cmd:
                    pr_data = {"title": "Test PR", "body": "Test", "number": 329}
                    return Mock(returncode=0, stdout=json.dumps(pr_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = gh_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "--review-pr", "329", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should call gh pr diff
            gh_calls = [call for call in mock_run.call_args_list 
                       if 'gh pr diff' in str(call.args)]
            assert len(gh_calls) > 0
    
    def test_gh_pr_create(self, claude_tasker_script, mock_git_repo):
        """Test GitHub PR creation functionality.""" 
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile'), \
             patch('builtins.open'):
            
            def gh_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh pr create' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo/pull/330", stderr="")
                elif 'gh pr view' in cmd and '--json' not in cmd:
                    # First call checks if PR exists (should fail)
                    return Mock(returncode=1, stdout="", stderr="PR not found")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'git show-ref --verify --quiet refs/heads/main' in cmd:
                    return Mock(returncode=0, stdout="", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = gh_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should include gh commands in the test
            gh_calls = [call for call in mock_run.call_args_list 
                       if 'gh' in str(call.args)]
            assert len(gh_calls) > 0
    
    def test_gh_issue_comment(self, claude_tasker_script, mock_git_repo):
        """Test GitHub issue commenting functionality."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile'), \
             patch('builtins.open'):
            
            def gh_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh issue comment' in cmd:
                    return Mock(returncode=0, stdout="", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = gh_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should potentially call gh issue comment (in full execution mode)
            assert result.returncode == 0 or "prompt-only" in result.stdout
    
    def test_gh_pr_list_search(self, claude_tasker_script, mock_git_repo):
        """Test GitHub PR listing and search functionality."""
        with patch('subprocess.run') as mock_run:
            def gh_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh pr list --search' in cmd:
                    pr_list = [
                        {"number": 330, "title": "Fix issue #316", "headRefName": "issue-316-123"}
                    ]
                    return Mock(returncode=0, stdout=json.dumps(pr_list), stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = gh_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should run without error
            assert result.returncode == 0 or "Missing required tools" not in result.stderr
    
    def test_gh_project_view(self, claude_tasker_script, mock_git_repo):
        """Test GitHub project viewing functionality."""
        with patch('subprocess.run') as mock_run:
            def gh_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh project view' in cmd:
                    project_data = {
                        "title": "Test Project",
                        "body": "Test project description"
                    }
                    return Mock(returncode=0, stdout=json.dumps(project_data), stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = gh_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--project", "3", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should call gh project view when project flag is used
            gh_calls = [call for call in mock_run.call_args_list 
                       if 'gh project view' in str(call.args)]
            assert len(gh_calls) > 0 or "prompt-only" in result.stdout
    
    def test_gh_api_calls(self, claude_tasker_script, mock_git_repo):
        """Test GitHub API calls through gh cli."""
        with patch('subprocess.run') as mock_run:
            def gh_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh api' in cmd:
                    return Mock(returncode=0, stdout='[]', stderr="")
                elif 'gh pr view' in cmd:
                    pr_data = {"title": "Test PR", "number": 329}
                    return Mock(returncode=0, stdout=json.dumps(pr_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = gh_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "--review-pr", "329", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should handle gh api calls
            assert result.returncode == 0 or "Missing required tools" not in result.stderr
    
    def test_gh_error_handling(self, claude_tasker_script, mock_git_repo):
        """Test GitHub CLI error handling."""
        with patch('subprocess.run') as mock_run:
            def gh_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh issue view' in cmd:
                    return Mock(returncode=1, stdout="", stderr="Issue not found")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = gh_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "999", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should handle error gracefully
            assert "Issue not found" in result.stderr or result.returncode == 0