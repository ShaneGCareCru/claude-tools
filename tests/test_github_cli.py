"""Tests for claude-tasker GitHub CLI integrations."""
import pytest
import subprocess
import json
import time
from pathlib import Path
from unittest.mock import patch, Mock, call
from src.claude_tasker.github_client import GitHubClient, GitHubError, IssueData, PRData


class TestGitHubError:
    """Test GitHubError utility class."""
    
    def test_is_rate_limit_true(self):
        """Test rate limit detection with positive cases."""
        test_cases = [
            "API rate limit exceeded",
            "rate limit",
            "X-RateLimit-Remaining: 0",
            "ERROR: API RATE LIMIT EXCEEDED",
            "Rate Limit Error"
        ]
        
        for stderr in test_cases:
            assert GitHubError.is_rate_limit(stderr) is True
    
    def test_is_rate_limit_false(self):
        """Test rate limit detection with negative cases."""
        test_cases = [
            "Authentication failed",
            "Not found",
            "Permission denied",
            "",
            None
        ]
        
        for stderr in test_cases:
            assert GitHubError.is_rate_limit(stderr) is False


class TestIssueData:
    """Test IssueData dataclass."""
    
    def test_issue_data_creation(self):
        """Test IssueData creation and attributes."""
        issue = IssueData(
            number=123,
            title="Test Issue",
            body="Test body",
            labels=["bug", "urgent"],
            url="https://github.com/test/repo/issues/123",
            author="testuser",
            state="open"
        )
        
        assert issue.number == 123
        assert issue.title == "Test Issue"
        assert issue.body == "Test body"
        assert issue.labels == ["bug", "urgent"]
        assert issue.url == "https://github.com/test/repo/issues/123"
        assert issue.author == "testuser"
        assert issue.state == "open"


class TestPRData:
    """Test PRData dataclass."""
    
    def test_pr_data_creation(self):
        """Test PRData creation and attributes."""
        pr = PRData(
            number=456,
            title="Test PR",
            body="Test PR body",
            head_ref="feature-branch",
            base_ref="main",
            author="prauthor",
            additions=50,
            deletions=10,
            changed_files=3,
            url="https://github.com/test/repo/pull/456"
        )
        
        assert pr.number == 456
        assert pr.title == "Test PR"
        assert pr.body == "Test PR body"
        assert pr.head_ref == "feature-branch"
        assert pr.base_ref == "main"
        assert pr.author == "prauthor"
        assert pr.additions == 50
        assert pr.deletions == 10
        assert pr.changed_files == 3
        assert pr.url == "https://github.com/test/repo/pull/456"


class TestGitHubClient:
    """Test GitHubClient class directly."""
    
    def test_init_default_values(self):
        """Test GitHubClient initialization with default values."""
        client = GitHubClient()
        assert client.retry_attempts == 3
        assert client.base_delay == 1.0
    
    def test_init_custom_values(self):
        """Test GitHubClient initialization with custom values."""
        client = GitHubClient(retry_attempts=5, base_delay=2.0)
        assert client.retry_attempts == 5
        assert client.base_delay == 2.0
    
    def test_run_gh_command_success(self):
        """Test successful GitHub CLI command execution."""
        client = GitHubClient()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")
            
            result = client._run_gh_command(['issue', 'list'])
            
            assert result.returncode == 0
            assert result.stdout == "success"
            mock_run.assert_called_once_with(
                ['gh', 'issue', 'list'],
                capture_output=True,
                text=True,
                check=False
            )
    
    def test_run_gh_command_failure(self):
        """Test GitHub CLI command execution failure."""
        client = GitHubClient()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error")
            
            result = client._run_gh_command(['issue', 'view', '999'])
            
            assert result.returncode == 1
            assert result.stderr == "Error"
    
    def test_run_gh_command_rate_limit_retry(self):
        """Test rate limit handling with retry logic."""
        client = GitHubClient(retry_attempts=2, base_delay=0.1)
        
        with patch('subprocess.run') as mock_run, \
             patch('time.sleep') as mock_sleep:
            
            # First call rate limited, second call succeeds
            mock_run.side_effect = [
                Mock(returncode=1, stdout="", stderr="API rate limit exceeded"),
                Mock(returncode=0, stdout="success", stderr="")
            ]
            
            result = client._run_gh_command(['issue', 'list'])
            
            assert result.returncode == 0
            assert result.stdout == "success"
            assert mock_run.call_count == 2
            mock_sleep.assert_called_once_with(0.1)  # base_delay * 2^0
    
    def test_run_gh_command_rate_limit_max_retries(self):
        """Test rate limit handling when max retries exceeded."""
        client = GitHubClient(retry_attempts=2, base_delay=0.1)
        
        with patch('subprocess.run') as mock_run, \
             patch('time.sleep') as mock_sleep:
            
            # All calls rate limited
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="API rate limit exceeded")
            
            result = client._run_gh_command(['issue', 'list'])
            
            assert result.returncode == 1
            assert "API rate limit exceeded" in result.stderr
            assert mock_run.call_count == 2
            assert mock_sleep.call_count == 1  # Only retries once before giving up
    
    def test_run_gh_command_exception_retry(self):
        """Test exception handling with retry logic."""
        client = GitHubClient(retry_attempts=2, base_delay=0.1)
        
        with patch('subprocess.run') as mock_run, \
             patch('time.sleep') as mock_sleep:
            
            # First call raises exception, second succeeds
            mock_run.side_effect = [
                Exception("Connection error"),
                Mock(returncode=0, stdout="success", stderr="")
            ]
            
            result = client._run_gh_command(['issue', 'list'])
            
            assert result.returncode == 0
            assert result.stdout == "success"
            assert mock_run.call_count == 2
            mock_sleep.assert_called_once_with(0.1)
    
    def test_run_gh_command_exception_max_retries(self):
        """Test exception handling when max retries exceeded."""
        client = GitHubClient(retry_attempts=2, base_delay=0.1)
        
        with patch('subprocess.run') as mock_run, \
             patch('time.sleep') as mock_sleep:
            
            # All calls raise exceptions
            mock_run.side_effect = Exception("Connection error")
            
            with pytest.raises(Exception, match="Connection error"):
                client._run_gh_command(['issue', 'list'])
            
            assert mock_run.call_count == 2
            assert mock_sleep.call_count == 1
    
    def test_get_issue_success(self):
        """Test successful issue retrieval."""
        client = GitHubClient()
        
        issue_json = {
            "number": 123,
            "title": "Test Issue",
            "body": "Test body",
            "labels": [{"name": "bug"}, {"name": "urgent"}],
            "url": "https://github.com/test/repo/issues/123",
            "author": {"login": "testuser"},
            "state": "open"
        }
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(issue_json))
            
            issue = client.get_issue(123)
            
            assert issue is not None
            assert issue.number == 123
            assert issue.title == "Test Issue"
            assert issue.body == "Test body"
            assert issue.labels == ["bug", "urgent"]
            assert issue.url == "https://github.com/test/repo/issues/123"
            assert issue.author == "testuser"
            assert issue.state == "open"
            
            mock_run.assert_called_once_with([
                'issue', 'view', '123',
                '--json', 'number,title,body,labels,url,author,state'
            ])
    
    def test_get_issue_command_failure(self):
        """Test issue retrieval when command fails."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Issue not found")
            
            issue = client.get_issue(999)
            
            assert issue is None
    
    def test_get_issue_json_decode_error(self):
        """Test issue retrieval with JSON decode error."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="invalid json")
            
            issue = client.get_issue(123)
            
            assert issue is None
    
    def test_get_issue_missing_fields(self):
        """Test issue retrieval with missing required fields."""
        client = GitHubClient()
        
        incomplete_json = {"number": 123}  # Missing required fields
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(incomplete_json))
            
            issue = client.get_issue(123)
            
            assert issue is None
    
    def test_get_issue_optional_fields(self):
        """Test issue retrieval with optional fields missing."""
        client = GitHubClient()
        
        issue_json = {
            "number": 123,
            "title": "Test Issue",
            # "body" missing - should default to empty string
            "labels": [],  # Empty labels array
            "url": "https://github.com/test/repo/issues/123",
            "author": {"login": "testuser"},
            "state": "open"
        }
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(issue_json))
            
            issue = client.get_issue(123)
            
            assert issue is not None
            assert issue.body == ""  # Should default to empty string
            assert issue.labels == []  # Should handle empty array
    
    def test_get_pr_success(self):
        """Test successful PR retrieval."""
        client = GitHubClient()
        
        pr_json = {
            "number": 456,
            "title": "Test PR",
            "body": "Test PR body",
            "headRefName": "feature-branch",
            "baseRefName": "main",
            "author": {"login": "prauthor"},
            "additions": 50,
            "deletions": 10,
            "changedFiles": 3,
            "url": "https://github.com/test/repo/pull/456"
        }
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(pr_json))
            
            pr = client.get_pr(456)
            
            assert pr is not None
            assert pr.number == 456
            assert pr.title == "Test PR"
            assert pr.body == "Test PR body"
            assert pr.head_ref == "feature-branch"
            assert pr.base_ref == "main"
            assert pr.author == "prauthor"
            assert pr.additions == 50
            assert pr.deletions == 10
            assert pr.changed_files == 3
            assert pr.url == "https://github.com/test/repo/pull/456"
            
            mock_run.assert_called_once_with([
                'pr', 'view', '456',
                '--json', 'number,title,body,headRefName,baseRefName,author,additions,deletions,changedFiles,url'
            ])
    
    def test_get_pr_command_failure(self):
        """Test PR retrieval when command fails."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="PR not found")
            
            pr = client.get_pr(999)
            
            assert pr is None
    
    def test_get_pr_optional_fields_missing(self):
        """Test PR retrieval with optional fields missing."""
        client = GitHubClient()
        
        pr_json = {
            "number": 456,
            "title": "Test PR",
            # Optional fields missing
            "headRefName": "feature-branch",
            "baseRefName": "main",
            "author": {"login": "prauthor"},
            "url": "https://github.com/test/repo/pull/456"
        }
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(pr_json))
            
            pr = client.get_pr(456)
            
            assert pr is not None
            assert pr.body == ""  # Should default to empty string
            assert pr.additions == 0  # Should default to 0
            assert pr.deletions == 0  # Should default to 0
            assert pr.changed_files == 0  # Should default to 0
    
    def test_get_pr_diff_success(self):
        """Test successful PR diff retrieval."""
        client = GitHubClient()
        
        diff_content = "diff --git a/file.py b/file.py\n+new line"
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=diff_content)
            
            diff = client.get_pr_diff(456)
            
            assert diff == diff_content
            mock_run.assert_called_once_with(['pr', 'diff', '456'])
    
    def test_get_pr_diff_failure(self):
        """Test PR diff retrieval when command fails."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="PR not found")
            
            diff = client.get_pr_diff(999)
            
            assert diff is None
    
    def test_get_pr_files_success(self):
        """Test successful PR files retrieval."""
        client = GitHubClient()
        
        files_json = {
            "files": [
                {"path": "src/file1.py"},
                {"path": "tests/test_file1.py"},
                {"path": "README.md"}
            ]
        }
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(files_json))
            
            files = client.get_pr_files(456)
            
            assert files == ["src/file1.py", "tests/test_file1.py", "README.md"]
            mock_run.assert_called_once_with(['pr', 'view', '456', '--json', 'files'])
    
    def test_get_pr_files_failure(self):
        """Test PR files retrieval when command fails."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="PR not found")
            
            files = client.get_pr_files(999)
            
            assert files == []
    
    def test_get_pr_files_no_files(self):
        """Test PR files retrieval when no files changed."""
        client = GitHubClient()
        
        files_json = {"files": []}
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(files_json))
            
            files = client.get_pr_files(456)
            
            assert files == []
    
    def test_comment_on_issue_success(self):
        """Test successful issue commenting."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = client.comment_on_issue(123, "Test comment")
            
            assert result is True
            mock_run.assert_called_once_with([
                'issue', 'comment', '123', '--body', 'Test comment'
            ])
    
    def test_comment_on_issue_failure(self):
        """Test issue commenting when command fails."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Permission denied")
            
            result = client.comment_on_issue(123, "Test comment")
            
            assert result is False
    
    def test_comment_on_pr_success(self):
        """Test successful PR commenting."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = client.comment_on_pr(456, "PR looks good!")
            
            assert result is True
            mock_run.assert_called_once_with([
                'pr', 'comment', '456', '--body', 'PR looks good!'
            ])
    
    def test_comment_on_pr_failure(self):
        """Test PR commenting when command fails."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Permission denied")
            
            result = client.comment_on_pr(456, "PR looks good!")
            
            assert result is False
    
    def test_create_pr_success(self):
        """Test successful PR creation."""
        client = GitHubClient()
        
        pr_output = "\nhttps://github.com/test/repo/pull/789\n"
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=pr_output)
            
            url = client.create_pr("New Feature", "Description", "feature-branch", "main")
            
            assert url == "https://github.com/test/repo/pull/789"
            mock_run.assert_called_once_with([
                'pr', 'create',
                '--title', 'New Feature',
                '--body', 'Description',
                '--head', 'feature-branch',
                '--base', 'main'
            ])
    
    def test_create_pr_default_base(self):
        """Test PR creation with default base branch."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="https://github.com/test/repo/pull/789")
            
            url = client.create_pr("New Feature", "Description", "feature-branch")
            
            assert url == "https://github.com/test/repo/pull/789"
            # Should use default base "main"
            expected_call = [
                'pr', 'create',
                '--title', 'New Feature',
                '--body', 'Description',
                '--head', 'feature-branch',
                '--base', 'main'
            ]
            mock_run.assert_called_once_with(expected_call)
    
    def test_create_pr_failure(self):
        """Test PR creation when command fails."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Branch not found")
            
            url = client.create_pr("New Feature", "Description", "nonexistent-branch")
            
            assert url is None
    
    def test_create_pr_no_url_in_output(self):
        """Test PR creation when no URL found in output."""
        client = GitHubClient()
        
        output_without_url = "PR created successfully but no URL found"
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=output_without_url)
            
            url = client.create_pr("New Feature", "Description", "feature-branch")
            
            assert url is None
    
    def test_get_project_info_success(self):
        """Test successful project info retrieval."""
        client = GitHubClient()
        
        project_json = {
            "title": "Test Project",
            "body": "Project description"
        }
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(project_json))
            
            info = client.get_project_info(1)
            
            assert info == project_json
            mock_run.assert_called_once_with(['project', 'view', '1', '--json', 'title,body'])
    
    def test_get_project_info_failure(self):
        """Test project info retrieval when command fails."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Project not found")
            
            info = client.get_project_info(999)
            
            assert info is None
    
    def test_create_issue_success(self):
        """Test successful issue creation."""
        client = GitHubClient()
        
        issue_output = "\nhttps://github.com/test/repo/issues/124\n"
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=issue_output)
            
            url = client.create_issue("Bug Report", "Description", ["bug", "urgent"])
            
            assert url == "https://github.com/test/repo/issues/124"
            mock_run.assert_called_once_with([
                'issue', 'create',
                '--title', 'Bug Report',
                '--body', 'Description',
                '--label', 'bug,urgent'
            ])
    
    def test_create_issue_no_labels(self):
        """Test issue creation without labels."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="https://github.com/test/repo/issues/125")
            
            url = client.create_issue("Feature Request", "Description")
            
            assert url == "https://github.com/test/repo/issues/125"
            expected_call = [
                'issue', 'create',
                '--title', 'Feature Request',
                '--body', 'Description'
            ]
            mock_run.assert_called_once_with(expected_call)
    
    def test_create_issue_failure(self):
        """Test issue creation when command fails."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Permission denied")
            
            url = client.create_issue("Bug Report", "Description")
            
            assert url is None
    
    def test_get_issue_comments_success(self):
        """Test successful issue comments retrieval."""
        client = GitHubClient()
        
        comments_json = [
            {"id": 1, "body": "First comment"},
            {"id": 2, "body": "Second comment"}
        ]
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(comments_json))
            
            comments = client.get_issue_comments(123)
            
            assert comments == comments_json
            mock_run.assert_called_once_with(['api', 'repos/{owner}/{repo}/issues/123/comments'])
    
    def test_get_issue_comments_failure(self):
        """Test issue comments retrieval when command fails."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Issue not found")
            
            comments = client.get_issue_comments(999)
            
            assert comments == []
    
    def test_get_pr_comments_success(self):
        """Test successful PR comments retrieval."""
        client = GitHubClient()
        
        comments_json = [
            {"id": 3, "body": "PR comment 1"},
            {"id": 4, "body": "PR comment 2"}
        ]
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(comments_json))
            
            comments = client.get_pr_comments(456)
            
            assert comments == comments_json
            mock_run.assert_called_once_with(['api', 'repos/{owner}/{repo}/pulls/456/comments'])
    
    def test_get_pr_comments_failure(self):
        """Test PR comments retrieval when command fails."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="PR not found")
            
            comments = client.get_pr_comments(999)
            
            assert comments == []
    
    def test_check_pr_status_success(self):
        """Test successful PR status check."""
        client = GitHubClient()
        
        status_json = {
            "statusCheckRollup": [{"state": "SUCCESS"}],
            "reviewDecision": "APPROVED"
        }
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(status_json))
            
            status = client.check_pr_status(456)
            
            assert status == status_json
            mock_run.assert_called_once_with([
                'pr', 'view', '456',
                '--json', 'statusCheckRollup,reviewDecision'
            ])
    
    def test_check_pr_status_failure(self):
        """Test PR status check when command fails."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="PR not found")
            
            status = client.check_pr_status(999)
            
            assert status == {}
    
    def test_check_pr_status_json_decode_error(self):
        """Test PR status check with JSON decode error."""
        client = GitHubClient()
        
        with patch.object(client, '_run_gh_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="invalid json")
            
            status = client.check_pr_status(456)
            
            assert status == {}


# Legacy bash script tests have been replaced by GitHubClient tests above
