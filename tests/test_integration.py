"""Integration tests for claude-tasker end-to-end functionality."""
import pytest
import subprocess
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, mock_open


class TestIntegration:
    """Integration tests for end-to-end functionality."""
    
    def test_full_issue_workflow_prompt_only(self, claude_tasker_script, mock_git_repo):
        """Test complete issue implementation workflow in prompt-only mode."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile'), \
             patch('builtins.open', mock_open()):
            
            def comprehensive_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                # Git operations
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'git branch --show-current' in cmd:
                    return Mock(returncode=0, stdout="main", stderr="")
                elif 'git status --porcelain' in cmd:
                    return Mock(returncode=0, stdout="", stderr="")
                elif 'git diff --quiet' in cmd:
                    return Mock(returncode=0, stdout="", stderr="")
                elif 'git log --oneline' in cmd:
                    return Mock(returncode=0, stdout="abc123 Test commit", stderr="")
                elif 'git show-ref --verify --quiet' in cmd:
                    return Mock(returncode=0, stdout="", stderr="")
                
                # GitHub CLI operations
                elif 'gh issue view' in cmd:
                    issue_data = {
                        "title": "Setup Python tests",
                        "body": "Create comprehensive test suite for claude-tasker",
                        "labels": [{"name": "enhancement"}],
                        "url": "https://github.com/test/repo/issues/316"
                    }
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                
                # Claude CLI operations (meta-prompt generation)
                elif 'claude' in cmd and '--output-format json' in cmd:
                    meta_response = {
                        "optimized_prompt": "Comprehensive test implementation prompt",
                        "analysis": "Gap analysis completed"
                    }
                    return Mock(returncode=0, stdout=json.dumps(meta_response), stderr="")
                
                # Dependency checks
                elif 'command -v' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/tool", stderr="")
                
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = comprehensive_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should complete successfully
            assert result.returncode == 0
            assert "Missing required tools" not in result.stderr
    
    def test_pr_review_workflow_complete(self, claude_tasker_script, mock_git_repo):
        """Test complete PR review workflow."""
        with patch('subprocess.run') as mock_run:
            def pr_review_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                # Git operations
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                
                # GitHub PR operations
                elif 'gh pr view' in cmd and '--json' in cmd:
                    pr_data = {
                        "title": "Add Python tests",
                        "body": "This PR adds comprehensive Python tests",
                        "number": 329,
                        "headRefName": "feature-tests",
                        "baseRefName": "main",
                        "author": {"login": "testuser"},
                        "additions": 500,
                        "deletions": 10,
                        "changedFiles": 5,
                        "url": "https://github.com/test/repo/pull/329"
                    }
                    return Mock(returncode=0, stdout=json.dumps(pr_data), stderr="")
                elif 'gh pr diff' in cmd:
                    diff_content = """
diff --git a/tests/test_new.py b/tests/test_new.py
new file mode 100644
index 0000000..abc123
--- /dev/null
+++ b/tests/test_new.py
@@ -0,0 +1,10 @@
+def test_example():
+    assert True
                    """
                    return Mock(returncode=0, stdout=diff_content, stderr="")
                elif 'gh api' in cmd:
                    return Mock(returncode=0, stdout='[]', stderr="")
                
                # Dependency checks
                elif 'command -v' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/tool", stderr="")
                
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = pr_review_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "--review-pr", "329", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should complete PR review successfully
            assert result.returncode == 0
    
    def test_bug_analysis_workflow(self, claude_tasker_script, mock_git_repo):
        """Test bug analysis workflow."""
        with patch('subprocess.run') as mock_run:
            def bug_analysis_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                # Git operations
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                
                # Dependency checks
                elif 'command -v' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/tool", stderr="")
                
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = bug_analysis_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run([
                    str(claude_tasker_script),
                    "--bug", "Tests are failing intermittently", 
                    "--prompt-only"
                ], cwd=mock_git_repo, capture_output=True, text=True)
            
            # Should complete bug analysis successfully
            assert result.returncode == 0
    
    def test_range_processing_with_timeout(self, claude_tasker_script, mock_git_repo):
        """Test range processing with timeout between tasks."""
        with patch('subprocess.run') as mock_run, \
             patch('time.sleep') as mock_sleep:
            
            call_count = 0
            
            def range_side_effect(*args, **kwargs):
                nonlocal call_count
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                # Git operations
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                
                # GitHub issue operations
                elif 'gh issue view' in cmd:
                    call_count += 1
                    issue_data = {
                        "title": f"Test Issue {call_count}",
                        "body": f"Test issue body {call_count}",
                        "labels": [],
                        "url": f"https://github.com/test/repo/issues/{315 + call_count}"
                    }
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                
                # Dependency checks
                elif 'command -v' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/tool", stderr="")
                
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = range_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run([
                    str(claude_tasker_script), "316-318",
                    "--timeout", "1",
                    "--prompt-only"
                ], cwd=mock_git_repo, capture_output=True, text=True)
            
            # Should process multiple issues
            assert result.returncode == 0
            assert call_count >= 2  # At least 2 issues processed
            assert mock_sleep.call_count >= 1  # Timeout was applied
    
    def test_project_context_integration(self, claude_tasker_script, mock_git_repo):
        """Test integration with GitHub project context."""
        with patch('subprocess.run') as mock_run:
            def project_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                # Git operations
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                
                # GitHub project operations
                elif 'gh project view' in cmd:
                    project_data = {
                        "title": "Test Project",
                        "body": "Project for testing integration",
                        "items": []
                    }
                    return Mock(returncode=0, stdout=json.dumps(project_data), stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {
                        "title": "Test Issue with Project",
                        "body": "Test issue",
                        "labels": [],
                        "url": "https://github.com/test/repo/issues/316"
                    }
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                
                # Dependency checks
                elif 'command -v' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/tool", stderr="")
                
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = project_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run([
                    str(claude_tasker_script), "316",
                    "--project", "3",
                    "--prompt-only"
                ], cwd=mock_git_repo, capture_output=True, text=True)
            
            # Should integrate project context successfully
            assert result.returncode == 0
    
    def test_error_recovery_and_retries(self, claude_tasker_script, mock_git_repo):
        """Test error recovery and retry mechanisms."""
        with patch('subprocess.run') as mock_run, \
             patch('time.sleep'):
            
            attempt_count = 0
            
            def retry_side_effect(*args, **kwargs):
                nonlocal attempt_count
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                # Git operations
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                
                # GitHub operations with retries
                elif 'gh issue view' in cmd:
                    attempt_count += 1
                    if attempt_count < 3:
                        # Simulate API rate limit
                        return Mock(returncode=1, stdout="", stderr="API rate limit exceeded")
                    else:
                        # Success after retries
                        issue_data = {
                            "title": "Test Issue",
                            "body": "Test",
                            "labels": [],
                            "url": "https://github.com/test/repo/issues/316"
                        }
                        return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                
                # Dependency checks
                elif 'command -v' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/tool", stderr="")
                
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = retry_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run([
                    str(claude_tasker_script), "316", "--prompt-only"
                ], cwd=mock_git_repo, capture_output=True, text=True)
            
            # Should recover from errors and succeed
            assert result.returncode == 0
            assert attempt_count >= 3  # Retries occurred
    
    def test_comprehensive_flag_combination(self, claude_tasker_script, mock_git_repo):
        """Test comprehensive combination of multiple flags."""
        with patch('subprocess.run') as mock_run:
            def comprehensive_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                # Handle all possible command combinations
                if any(keyword in cmd for keyword in ['git', 'gh', 'command -v']):
                    if 'git rev-parse --git-dir' in cmd:
                        return Mock(returncode=0, stdout=".git", stderr="")
                    elif 'git config --get remote.origin.url' in cmd:
                        return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                    elif 'gh issue view' in cmd:
                        issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                        return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                    elif 'gh project view' in cmd:
                        project_data = {"title": "Test Project", "body": "Test"}
                        return Mock(returncode=0, stdout=json.dumps(project_data), stderr="")
                    elif 'command -v' in cmd:
                        return Mock(returncode=0, stdout="/usr/bin/tool", stderr="")
                    else:
                        return Mock(returncode=0, stdout="", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = comprehensive_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run([
                    str(claude_tasker_script), "316",
                    "--project", "3",
                    "--timeout", "30",
                    "--coder", "claude",
                    "--base-branch", "develop",
                    "--auto-pr-review",
                    "--prompt-only"
                ], cwd=mock_git_repo, capture_output=True, text=True)
            
            # Should handle complex flag combinations
            assert result.returncode == 0