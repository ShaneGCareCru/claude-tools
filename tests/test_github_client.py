"""Comprehensive unit tests for GitHub client module."""

import json
import subprocess
import time
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.claude_tasker.github_client import (
    GitHubClient,
    GitHubError,
    IssueData,
    PRData
)


class TestGitHubError(TestCase):
    """Test GitHub error detection."""
    
    def test_is_rate_limit_empty_stderr(self):
        """Test rate limit detection with empty stderr."""
        self.assertFalse(GitHubError.is_rate_limit(""))
        self.assertFalse(GitHubError.is_rate_limit(None))
    
    def test_is_rate_limit_api_exceeded(self):
        """Test rate limit detection with API rate limit exceeded."""
        stderr = "Error: API rate limit exceeded for user"
        self.assertTrue(GitHubError.is_rate_limit(stderr))
    
    def test_is_rate_limit_generic_rate_limit(self):
        """Test rate limit detection with generic rate limit message."""
        stderr = "Error: rate limit reached, try again later"
        self.assertTrue(GitHubError.is_rate_limit(stderr))
    
    def test_is_rate_limit_header_indication(self):
        """Test rate limit detection with header indication."""
        stderr = "X-RateLimit-Remaining: 0"
        self.assertTrue(GitHubError.is_rate_limit(stderr))
    
    def test_is_rate_limit_case_insensitive(self):
        """Test rate limit detection is case insensitive."""
        stderr = "ERROR: RATE LIMIT EXCEEDED"
        self.assertTrue(GitHubError.is_rate_limit(stderr))
    
    def test_is_rate_limit_false_positive(self):
        """Test rate limit detection doesn't match unrelated errors."""
        stderr = "Error: authentication failed"
        self.assertFalse(GitHubError.is_rate_limit(stderr))
    
    def test_is_rate_limit_mixed_content(self):
        """Test rate limit detection in mixed content."""
        stderr = "Warning: deprecated API\nError: API rate limit exceeded\nOther info"
        self.assertTrue(GitHubError.is_rate_limit(stderr))


class TestGitHubClient(TestCase):
    """Test GitHub client functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = GitHubClient(retry_attempts=3, base_delay=0.1)
    
    @patch('subprocess.run')
    def test_run_gh_command_success(self, mock_run):
        """Test successful GitHub command execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"test": "data"}',
            stderr=''
        )
        
        result = self.client._run_gh_command(['issue', 'list'])
        
        mock_run.assert_called_once_with(
            ['gh', 'issue', 'list'],
            capture_output=True,
            text=True,
            check=False
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '{"test": "data"}')
    
    @patch('subprocess.run')
    @patch('time.sleep')
    def test_run_gh_command_rate_limit_retry(self, mock_sleep, mock_run):
        """Test rate limit retry logic."""
        # First call fails with rate limit, second succeeds
        mock_run.side_effect = [
            Mock(returncode=1, stdout='', stderr='API rate limit exceeded'),
            Mock(returncode=0, stdout='{"success": true}', stderr='')
        ]
        
        result = self.client._run_gh_command(['issue', 'list'])
        
        self.assertEqual(mock_run.call_count, 2)
        mock_sleep.assert_called_once_with(0.1)  # base_delay
        self.assertEqual(result.returncode, 0)
    
    @patch('subprocess.run')
    @patch('time.sleep')
    def test_run_gh_command_max_retries_exceeded(self, mock_sleep, mock_run):
        """Test maximum retries exceeded."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='API rate limit exceeded'
        )
        
        result = self.client._run_gh_command(['issue', 'list'])
        
        self.assertEqual(mock_run.call_count, 3)  # retry_attempts
        self.assertEqual(mock_sleep.call_count, 2)  # One less than attempts
        self.assertEqual(result.returncode, 1)
    
    @patch('subprocess.run')
    def test_run_gh_command_non_rate_limit_error(self, mock_run):
        """Test non-rate-limit error doesn't trigger retry."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='authentication failed'
        )
        
        result = self.client._run_gh_command(['issue', 'list'])
        
        mock_run.assert_called_once()
        self.assertEqual(result.returncode, 1)
    
    @patch('subprocess.run')
    @patch('time.sleep')
    def test_run_gh_command_exception_retry(self, mock_sleep, mock_run):
        """Test exception handling with retry."""
        mock_run.side_effect = [
            Exception("Network error"),
            Mock(returncode=0, stdout='{"success": true}', stderr='')
        ]
        
        result = self.client._run_gh_command(['issue', 'list'])
        
        self.assertEqual(mock_run.call_count, 2)
        mock_sleep.assert_called_once()
        self.assertEqual(result.returncode, 0)
    
    @patch('subprocess.run')
    def test_run_gh_command_exception_max_retries(self, mock_run):
        """Test exception handling with max retries exceeded."""
        mock_run.side_effect = Exception("Persistent error")
        
        with self.assertRaises(Exception):
            self.client._run_gh_command(['issue', 'list'])
        
        self.assertEqual(mock_run.call_count, 3)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_issue_success(self, mock_run_gh):
        """Test successful issue retrieval."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                'number': 123,
                'title': 'Test Issue',
                'body': 'Issue description',
                'labels': [{'name': 'bug'}, {'name': 'high-priority'}],
                'url': 'https://github.com/owner/repo/issues/123',
                'author': {'login': 'testuser'},
                'state': 'open'
            })
        )
        
        issue = self.client.get_issue(123)
        
        mock_run_gh.assert_called_once_with([
            'issue', 'view', '123',
            '--json', 'number,title,body,labels,url,author,state'
        ])
        
        self.assertIsInstance(issue, IssueData)
        self.assertEqual(issue.number, 123)
        self.assertEqual(issue.title, 'Test Issue')
        self.assertEqual(issue.body, 'Issue description')
        self.assertEqual(issue.labels, ['bug', 'high-priority'])
        self.assertEqual(issue.author, 'testuser')
        self.assertEqual(issue.state, 'open')
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_issue_not_found(self, mock_run_gh):
        """Test issue not found."""
        mock_run_gh.return_value = Mock(returncode=1, stdout='')
        
        issue = self.client.get_issue(999)
        
        self.assertIsNone(issue)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_issue_invalid_json(self, mock_run_gh):
        """Test issue retrieval with invalid JSON."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout='invalid json'
        )
        
        issue = self.client.get_issue(123)
        
        self.assertIsNone(issue)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_issue_missing_fields(self, mock_run_gh):
        """Test issue retrieval with missing fields."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                'number': 123,
                'title': 'Test Issue'
                # Missing other required fields
            })
        )
        
        issue = self.client.get_issue(123)
        
        self.assertIsNone(issue)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_issue_with_optional_fields(self, mock_run_gh):
        """Test issue retrieval handles optional fields correctly."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                'number': 123,
                'title': 'Test Issue',
                'body': None,  # Optional field as None
                'labels': [],  # Empty labels
                'url': 'https://github.com/owner/repo/issues/123',
                'author': {'login': 'testuser'},
                'state': 'open'
            })
        )
        
        issue = self.client.get_issue(123)
        
        self.assertIsInstance(issue, IssueData)
        self.assertEqual(issue.body, '')  # None converted to empty string
        self.assertEqual(issue.labels, [])
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_pr_success(self, mock_run_gh):
        """Test successful PR retrieval."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                'number': 456,
                'title': 'Test PR',
                'body': 'PR description',
                'headRefName': 'feature-branch',
                'baseRefName': 'main',
                'author': {'login': 'contributor'},
                'additions': 100,
                'deletions': 50,
                'changedFiles': 5,
                'url': 'https://github.com/owner/repo/pull/456'
            })
        )
        
        pr = self.client.get_pr(456)
        
        mock_run_gh.assert_called_once_with([
            'pr', 'view', '456',
            '--json', 'number,title,body,headRefName,baseRefName,author,additions,deletions,changedFiles,url'
        ])
        
        self.assertIsInstance(pr, PRData)
        self.assertEqual(pr.number, 456)
        self.assertEqual(pr.title, 'Test PR')
        self.assertEqual(pr.head_ref, 'feature-branch')
        self.assertEqual(pr.base_ref, 'main')
        self.assertEqual(pr.additions, 100)
        self.assertEqual(pr.deletions, 50)
        self.assertEqual(pr.changed_files, 5)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_pr_not_found(self, mock_run_gh):
        """Test PR not found."""
        mock_run_gh.return_value = Mock(returncode=1, stdout='')
        
        pr = self.client.get_pr(999)
        
        self.assertIsNone(pr)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_pr_diff_success(self, mock_run_gh):
        """Test successful PR diff retrieval."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout='diff --git a/file.py b/file.py\n+new line\n-old line'
        )
        
        diff = self.client.get_pr_diff(456)
        
        mock_run_gh.assert_called_once_with(['pr', 'diff', '456'])
        self.assertIn('diff --git', diff)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_pr_diff_not_found(self, mock_run_gh):
        """Test PR diff not found."""
        mock_run_gh.return_value = Mock(returncode=1, stdout='')
        
        diff = self.client.get_pr_diff(999)
        
        self.assertIsNone(diff)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_pr_files_success(self, mock_run_gh):
        """Test successful PR files retrieval."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                'files': [
                    {'path': 'src/main.py'},
                    {'path': 'tests/test_main.py'},
                    {'path': 'README.md'}
                ]
            })
        )
        
        files = self.client.get_pr_files(456)
        
        mock_run_gh.assert_called_once_with(['pr', 'view', '456', '--json', 'files'])
        self.assertEqual(files, ['src/main.py', 'tests/test_main.py', 'README.md'])
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_pr_files_empty(self, mock_run_gh):
        """Test PR files retrieval with empty result."""
        mock_run_gh.return_value = Mock(returncode=1, stdout='')
        
        files = self.client.get_pr_files(999)
        
        self.assertEqual(files, [])
    
    @patch.object(GitHubClient, '_run_gh_command')
    @patch.object(GitHubClient, 'get_issue_comments')
    def test_comment_on_issue_new_comment(self, mock_get_comments, mock_run_gh):
        """Test adding new comment to issue."""
        mock_get_comments.return_value = []
        mock_run_gh.return_value = Mock(returncode=0)
        
        result = self.client.comment_on_issue(123, "This is a test comment")
        
        self.assertTrue(result)
        mock_run_gh.assert_called_once_with([
            'issue', 'comment', '123', '--body', 'This is a test comment'
        ])
    
    @patch.object(GitHubClient, '_run_gh_command')
    @patch.object(GitHubClient, 'get_issue_comments')
    def test_comment_on_issue_duplicate_prevention(self, mock_get_comments, mock_run_gh):
        """Test duplicate comment prevention."""
        mock_get_comments.return_value = [
            {'body': 'This is a test comment\nWith more details\nAnd even more'}
        ]
        
        # Use exact same signature (first 3 lines) to trigger duplicate detection
        result = self.client.comment_on_issue(123, "This is a test comment\nWith more details\nAnd even more\nExtra content")
        
        self.assertTrue(result)  # Returns True because duplicate detected
        mock_run_gh.assert_not_called()  # Should not post duplicate
    
    @patch.object(GitHubClient, '_run_gh_command')
    @patch.object(GitHubClient, 'get_issue_comments')
    def test_comment_on_issue_short_comment_no_duplicate(self, mock_get_comments, mock_run_gh):
        """Test that short comments don't trigger duplicate detection."""
        mock_get_comments.return_value = [
            {'body': 'ok'}
        ]
        mock_run_gh.return_value = Mock(returncode=0)
        
        result = self.client.comment_on_issue(123, "ok")
        
        self.assertTrue(result)
        mock_run_gh.assert_called_once()  # Should post because signature too short
    
    @patch.object(GitHubClient, '_run_gh_command')
    @patch.object(GitHubClient, 'get_issue_comments')
    def test_comment_on_issue_failure(self, mock_get_comments, mock_run_gh):
        """Test comment posting failure."""
        mock_get_comments.return_value = []
        mock_run_gh.return_value = Mock(returncode=1)
        
        result = self.client.comment_on_issue(123, "This comment will fail")
        
        self.assertFalse(result)
    
    @patch.object(GitHubClient, '_run_gh_command')
    @patch.object(GitHubClient, 'get_pr_comments')
    def test_comment_on_pr_success(self, mock_get_comments, mock_run_gh):
        """Test successful PR comment."""
        mock_get_comments.return_value = []
        mock_run_gh.return_value = Mock(returncode=0)
        
        result = self.client.comment_on_pr(456, "PR looks good!")
        
        self.assertTrue(result)
        mock_run_gh.assert_called_once_with([
            'pr', 'comment', '456', '--body', 'PR looks good!'
        ])
    
    @patch.object(GitHubClient, '_run_gh_command')
    @patch.object(GitHubClient, 'get_pr_comments')
    def test_comment_on_pr_duplicate_prevention(self, mock_get_comments, mock_run_gh):
        """Test PR duplicate comment prevention."""
        mock_get_comments.return_value = [
            {'body': 'PR looks good!\nAll tests passing\nReady to merge'}
        ]
        
        result = self.client.comment_on_pr(456, "PR looks good!\nDifferent assessment")
        
        self.assertTrue(result)
        mock_run_gh.assert_not_called()
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_create_pr_success(self, mock_run_gh):
        """Test successful PR creation."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout='Creating pull request...\nhttps://github.com/owner/repo/pull/789\nPR created successfully'
        )
        
        pr_url = self.client.create_pr(
            title="New Feature",
            body="Feature description",
            head="feature-branch",
            base="main"
        )
        
        mock_run_gh.assert_called_once_with([
            'pr', 'create',
            '--title', 'New Feature',
            '--body', 'Feature description',
            '--head', 'feature-branch',
            '--base', 'main'
        ])
        self.assertEqual(pr_url, 'https://github.com/owner/repo/pull/789')
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_create_pr_failure(self, mock_run_gh):
        """Test PR creation failure."""
        mock_run_gh.return_value = Mock(returncode=1)
        
        pr_url = self.client.create_pr("Title", "Body", "head", "base")
        
        self.assertIsNone(pr_url)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_create_pr_no_url_in_output(self, mock_run_gh):
        """Test PR creation with no URL in output."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout='PR created successfully but no URL found'
        )
        
        pr_url = self.client.create_pr("Title", "Body", "head", "base")
        
        self.assertIsNone(pr_url)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_default_branch_success(self, mock_run_gh):
        """Test successful default branch retrieval."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                'defaultBranchRef': {'name': 'main'}
            })
        )
        
        branch = self.client.get_default_branch()
        
        mock_run_gh.assert_called_once_with(['repo', 'view', '--json', 'defaultBranchRef'])
        self.assertEqual(branch, 'main')
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_default_branch_failure(self, mock_run_gh):
        """Test default branch retrieval failure."""
        mock_run_gh.return_value = Mock(returncode=1)
        
        branch = self.client.get_default_branch()
        
        self.assertIsNone(branch)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_default_branch_invalid_json(self, mock_run_gh):
        """Test default branch with invalid JSON."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout='invalid json'
        )
        
        branch = self.client.get_default_branch()
        
        self.assertIsNone(branch)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_project_info_success(self, mock_run_gh):
        """Test successful project info retrieval."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                'title': 'My Project',
                'body': 'Project description'
            })
        )
        
        info = self.client.get_project_info(1)
        
        mock_run_gh.assert_called_once_with(['project', 'view', '1', '--json', 'title,body'])
        self.assertEqual(info['title'], 'My Project')
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_project_info_not_found(self, mock_run_gh):
        """Test project info not found."""
        mock_run_gh.return_value = Mock(returncode=1)
        
        info = self.client.get_project_info(999)
        
        self.assertIsNone(info)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_create_issue_success(self, mock_run_gh):
        """Test successful issue creation."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout='Creating issue...\nhttps://github.com/owner/repo/issues/999\nIssue created'
        )
        
        issue_url = self.client.create_issue(
            title="Bug Report",
            body="Found a bug",
            labels=['bug', 'high-priority']
        )
        
        mock_run_gh.assert_called_once_with([
            'issue', 'create',
            '--title', 'Bug Report',
            '--body', 'Found a bug',
            '--label', 'bug,high-priority'
        ])
        self.assertEqual(issue_url, 'https://github.com/owner/repo/issues/999')
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_create_issue_no_labels(self, mock_run_gh):
        """Test issue creation without labels."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout='https://github.com/owner/repo/issues/1000'
        )
        
        issue_url = self.client.create_issue("Title", "Body", None)
        
        # Verify no --label argument is passed
        call_args = mock_run_gh.call_args[0][0]
        self.assertNotIn('--label', call_args)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_create_issue_failure(self, mock_run_gh):
        """Test issue creation failure."""
        mock_run_gh.return_value = Mock(returncode=1)
        
        issue_url = self.client.create_issue("Title", "Body")
        
        self.assertIsNone(issue_url)
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_issue_comments_success(self, mock_run_gh):
        """Test successful issue comments retrieval."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout=json.dumps([
                {'body': 'First comment', 'user': {'login': 'user1'}},
                {'body': 'Second comment', 'user': {'login': 'user2'}}
            ])
        )
        
        comments = self.client.get_issue_comments(123)
        
        mock_run_gh.assert_called_once_with(['api', 'repos/{owner}/{repo}/issues/123/comments'])
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0]['body'], 'First comment')
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_issue_comments_failure(self, mock_run_gh):
        """Test issue comments retrieval failure."""
        mock_run_gh.return_value = Mock(returncode=1)
        
        comments = self.client.get_issue_comments(123)
        
        self.assertEqual(comments, [])
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_pr_comments_success(self, mock_run_gh):
        """Test successful PR comments retrieval."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout=json.dumps([
                {'body': 'Review comment', 'user': {'login': 'reviewer'}}
            ])
        )
        
        comments = self.client.get_pr_comments(456)
        
        mock_run_gh.assert_called_once_with(['api', 'repos/{owner}/{repo}/pulls/456/comments'])
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]['body'], 'Review comment')
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_get_pr_comments_invalid_json(self, mock_run_gh):
        """Test PR comments with invalid JSON."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout='invalid json'
        )
        
        comments = self.client.get_pr_comments(456)
        
        self.assertEqual(comments, [])
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_check_pr_status_success(self, mock_run_gh):
        """Test successful PR status check."""
        mock_run_gh.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                'statusCheckRollup': [
                    {'status': 'COMPLETED', 'conclusion': 'SUCCESS'}
                ],
                'reviewDecision': 'APPROVED'
            })
        )
        
        status = self.client.check_pr_status(456)
        
        mock_run_gh.assert_called_once_with([
            'pr', 'view', '456', '--json', 'statusCheckRollup,reviewDecision'
        ])
        self.assertEqual(status['reviewDecision'], 'APPROVED')
    
    @patch.object(GitHubClient, '_run_gh_command')
    def test_check_pr_status_failure(self, mock_run_gh):
        """Test PR status check failure."""
        mock_run_gh.return_value = Mock(returncode=1)
        
        status = self.client.check_pr_status(456)
        
        self.assertEqual(status, {})
    
    def test_client_initialization(self):
        """Test GitHubClient initialization."""
        client = GitHubClient(retry_attempts=5, base_delay=2.0)
        
        self.assertEqual(client.retry_attempts, 5)
        self.assertEqual(client.base_delay, 2.0)
    
    def test_client_default_initialization(self):
        """Test GitHubClient default initialization."""
        client = GitHubClient()
        
        self.assertEqual(client.retry_attempts, 3)
        self.assertEqual(client.base_delay, 1.0)


class TestDataClasses(TestCase):
    """Test data class functionality."""
    
    def test_issue_data_creation(self):
        """Test IssueData creation."""
        issue = IssueData(
            number=123,
            title="Test Issue",
            body="Issue body",
            labels=["bug", "high"],
            url="https://example.com",
            author="testuser",
            state="open",
            assignee="assignee",
            milestone="v1.0",
            created_at="2023-01-01",
            updated_at="2023-01-02"
        )
        
        self.assertEqual(issue.number, 123)
        self.assertEqual(issue.title, "Test Issue")
        self.assertEqual(issue.assignee, "assignee")
    
    def test_issue_data_optional_fields(self):
        """Test IssueData with optional fields as None."""
        issue = IssueData(
            number=123,
            title="Test Issue",
            body="Issue body",
            labels=[],
            url="https://example.com",
            author="testuser",
            state="open"
        )
        
        self.assertIsNone(issue.assignee)
        self.assertIsNone(issue.milestone)
        self.assertIsNone(issue.created_at)
        self.assertIsNone(issue.updated_at)
    
    def test_pr_data_creation(self):
        """Test PRData creation."""
        pr = PRData(
            number=456,
            title="Test PR",
            body="PR body",
            head_ref="feature",
            base_ref="main",
            author="contributor",
            additions=10,
            deletions=5,
            changed_files=3,
            url="https://example.com/pull/456"
        )
        
        self.assertEqual(pr.number, 456)
        self.assertEqual(pr.head_ref, "feature")
        self.assertEqual(pr.additions, 10)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])