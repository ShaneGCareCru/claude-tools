"""Unit tests for GhService."""

import pytest
import json
from unittest.mock import Mock, MagicMock
from src.claude_tasker.services.gh_service import (
    GhService, 
    IssueData, 
    PRData, 
    GitHubError
)
from src.claude_tasker.services.command_executor import CommandExecutor, CommandResult, CommandErrorType


class TestGitHubError:
    """Test cases for GitHubError utility class."""
    
    def test_is_rate_limit_with_rate_limit_patterns(self):
        """Test rate limit detection with various patterns."""
        assert GitHubError.is_rate_limit("API rate limit exceeded")
        assert GitHubError.is_rate_limit("rate limit")
        assert GitHubError.is_rate_limit("X-RateLimit-Remaining: 0")
        assert GitHubError.is_rate_limit("RATE LIMIT EXCEEDED")  # Case insensitive
    
    def test_is_rate_limit_without_rate_limit_patterns(self):
        """Test rate limit detection with non-rate-limit errors."""
        assert not GitHubError.is_rate_limit("404 not found")
        assert not GitHubError.is_rate_limit("authentication failed")
        assert not GitHubError.is_rate_limit("")
        assert not GitHubError.is_rate_limit(None)


class TestIssueData:
    """Test cases for IssueData dataclass."""
    
    def test_issue_data_creation(self):
        """Test IssueData creation with required fields."""
        issue = IssueData(
            number=123,
            title="Test issue",
            body="Issue body",
            labels=["bug", "priority:high"],
            url="https://github.com/user/repo/issues/123",
            author="testuser",
            state="open"
        )
        
        assert issue.number == 123
        assert issue.title == "Test issue"
        assert issue.body == "Issue body"
        assert issue.labels == ["bug", "priority:high"]
        assert issue.url == "https://github.com/user/repo/issues/123"
        assert issue.author == "testuser"
        assert issue.state == "open"
        assert issue.assignee is None  # Optional field


class TestPRData:
    """Test cases for PRData dataclass."""
    
    def test_pr_data_creation(self):
        """Test PRData creation."""
        pr = PRData(
            number=456,
            title="Test PR",
            body="PR body",
            head_ref="feature-branch",
            base_ref="main",
            author="contributor",
            additions=10,
            deletions=5,
            changed_files=3,
            url="https://github.com/user/repo/pull/456"
        )
        
        assert pr.number == 456
        assert pr.title == "Test PR"
        assert pr.head_ref == "feature-branch"
        assert pr.base_ref == "main"
        assert pr.author == "contributor"
        assert pr.additions == 10
        assert pr.deletions == 5
        assert pr.changed_files == 3


class TestGhService:
    """Test cases for GhService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_executor = Mock(spec=CommandExecutor)
        self.gh_service = GhService(self.mock_executor)
    
    def _create_command_result(self, success=True, stdout="", stderr="", returncode=0):
        """Helper to create CommandResult objects."""
        return CommandResult(
            returncode=returncode if not success else 0,
            stdout=stdout,
            stderr=stderr,
            command="gh test",
            execution_time=0.1,
            error_type=CommandErrorType.SUCCESS if success else CommandErrorType.GENERAL_ERROR,
            attempts=1,
            success=success
        )
    
    def test_init_default(self):
        """Test GhService initialization with defaults."""
        executor = Mock()
        service = GhService(executor)
        
        assert service.executor == executor
        assert service.prefer_rest is False
        assert service.op_marker == "<!-- claude-tasker-op -->"
    
    def test_init_with_options(self):
        """Test GhService initialization with custom options."""
        executor = Mock()
        logger = Mock()
        service = GhService(executor, prefer_rest=True, logger=logger)
        
        assert service.executor == executor
        assert service.prefer_rest is True
        assert service.logger == logger
    
    def test_add_op_marker_without_id(self):
        """Test adding operation marker without ID."""
        content = "Test content"
        marked = self.gh_service._add_op_marker(content)
        
        expected = "Test content\n\n<!-- claude-tasker-op -->"
        assert marked == expected
    
    def test_add_op_marker_with_id(self):
        """Test adding operation marker with ID."""
        content = "Test content"
        marked = self.gh_service._add_op_marker(content, "test-123")
        
        expected = "Test content\n\n<!-- claude-tasker-op-test-123 -->"
        assert marked == expected
    
    def test_has_op_marker_without_id(self):
        """Test checking for operation marker without ID."""
        content = "Test content\n\n<!-- claude-tasker-op -->"
        assert self.gh_service._has_op_marker(content) is True
        
        content_without = "Test content"
        assert self.gh_service._has_op_marker(content_without) is False
    
    def test_has_op_marker_with_id(self):
        """Test checking for operation marker with ID."""
        content = "Test content\n\n<!-- claude-tasker-op-test-123 -->"
        assert self.gh_service._has_op_marker(content, "test-123") is True
        assert self.gh_service._has_op_marker(content, "different-id") is False
    
    def test_get_issue_success(self):
        """Test successful issue retrieval."""
        issue_json = {
            "number": 123,
            "title": "Test Issue",
            "body": "Issue description",
            "labels": [{"name": "bug"}, {"name": "priority:high"}],
            "url": "https://github.com/user/repo/issues/123",
            "author": {"login": "testuser"},
            "state": "open"
        }
        
        result = self._create_command_result(stdout=json.dumps(issue_json))
        self.mock_executor.execute.return_value = result
        
        issue = self.gh_service.get_issue(123)
        
        self.mock_executor.execute.assert_called_once_with([
            'gh', 'issue', 'view', '123',
            '--json', 'number,title,body,labels,url,author,state'
        ])
        
        assert isinstance(issue, IssueData)
        assert issue.number == 123
        assert issue.title == "Test Issue"
        assert issue.labels == ["bug", "priority:high"]
        assert issue.author == "testuser"
    
    def test_get_issue_failure(self):
        """Test issue retrieval failure."""
        result = self._create_command_result(success=False, stderr="Issue not found")
        self.mock_executor.execute.return_value = result
        
        issue = self.gh_service.get_issue(999)
        
        assert issue is None
    
    def test_get_issue_invalid_json(self):
        """Test issue retrieval with invalid JSON."""
        result = self._create_command_result(stdout="invalid json")
        self.mock_executor.execute.return_value = result
        
        issue = self.gh_service.get_issue(123)
        
        assert issue is None
    
    def test_get_pr_success(self):
        """Test successful PR retrieval."""
        pr_json = {
            "number": 456,
            "title": "Test PR",
            "body": "PR description",
            "headRefName": "feature-branch",
            "baseRefName": "main",
            "author": {"login": "contributor"},
            "additions": 15,
            "deletions": 8,
            "changedFiles": 4,
            "url": "https://github.com/user/repo/pull/456"
        }
        
        result = self._create_command_result(stdout=json.dumps(pr_json))
        self.mock_executor.execute.return_value = result
        
        pr = self.gh_service.get_pr(456)
        
        self.mock_executor.execute.assert_called_once_with([
            'gh', 'pr', 'view', '456',
            '--json', 'number,title,body,headRefName,baseRefName,author,additions,deletions,changedFiles,url'
        ])
        
        assert isinstance(pr, PRData)
        assert pr.number == 456
        assert pr.head_ref == "feature-branch"
        assert pr.base_ref == "main"
        assert pr.additions == 15
    
    def test_get_pr_diff(self):
        """Test PR diff retrieval."""
        diff_content = "diff --git a/file.py b/file.py..."
        result = self._create_command_result(stdout=diff_content)
        self.mock_executor.execute.return_value = result
        
        diff = self.gh_service.get_pr_diff(456)
        
        self.mock_executor.execute.assert_called_once_with(['gh', 'pr', 'diff', '456'])
        assert diff == diff_content
    
    def test_get_pr_files(self):
        """Test PR files retrieval."""
        files_json = {
            "files": [
                {"path": "src/file1.py"},
                {"path": "src/file2.py"},
                {"path": "tests/test_file.py"}
            ]
        }
        
        result = self._create_command_result(stdout=json.dumps(files_json))
        self.mock_executor.execute.return_value = result
        
        files = self.gh_service.get_pr_files(456)
        
        self.mock_executor.execute.assert_called_once_with([
            'gh', 'pr', 'view', '456', '--json', 'files'
        ])
        
        expected_files = ["src/file1.py", "src/file2.py", "tests/test_file.py"]
        assert files == expected_files
    
    def test_comment_on_issue_new_comment(self):
        """Test adding a new comment to an issue."""
        # Mock get_issue_comments to return empty list (no existing comments)
        self.gh_service.get_issue_comments = Mock(return_value=[])
        
        result = self._create_command_result()
        self.mock_executor.execute.return_value = result
        
        success = self.gh_service.comment_on_issue(123, "Test comment")
        
        self.mock_executor.execute.assert_called_once()
        args = self.mock_executor.execute.call_args[0][0]
        assert args[:4] == ['gh', 'issue', 'comment', '123']
        assert '--body' in args
        # Check that the comment includes the operation marker
        body_index = args.index('--body') + 1
        assert '<!-- claude-tasker-op -->' in args[body_index]
        
        assert success is True
    
    def test_comment_on_issue_duplicate_prevention(self):
        """Test duplicate comment prevention."""
        existing_comments = [
            {"body": "Test comment\n\nSome more text"}
        ]
        self.gh_service.get_issue_comments = Mock(return_value=existing_comments)
        
        success = self.gh_service.comment_on_issue(123, "Test comment")
        
        # Should not call execute since it's a duplicate
        self.mock_executor.execute.assert_not_called()
        assert success is True  # Returns True since comment already exists
    
    def test_comment_on_issue_with_op_id_duplicate(self):
        """Test comment with operation ID duplicate prevention."""
        existing_comments = [
            {"body": "Previous comment\n\n<!-- claude-tasker-op-test-123 -->"}
        ]
        self.gh_service.get_issue_comments = Mock(return_value=existing_comments)
        
        success = self.gh_service.comment_on_issue(123, "New comment", op_id="test-123")
        
        # Should not call execute since op_id already exists
        self.mock_executor.execute.assert_not_called()
        assert success is True
    
    def test_comment_on_pr(self):
        """Test commenting on a PR."""
        self.gh_service.get_pr_comments = Mock(return_value=[])
        
        result = self._create_command_result()
        self.mock_executor.execute.return_value = result
        
        success = self.gh_service.comment_on_pr(456, "PR comment")
        
        self.mock_executor.execute.assert_called_once()
        args = self.mock_executor.execute.call_args[0][0]
        assert args[:4] == ['gh', 'pr', 'comment', '456']
        
        assert success is True
    
    def test_create_pr(self):
        """Test PR creation."""
        pr_output = "https://github.com/user/repo/pull/789"
        result = self._create_command_result(stdout=pr_output)
        self.mock_executor.execute.return_value = result
        
        url = self.gh_service.create_pr(
            title="New Feature",
            body="Feature description",
            head="feature-branch",
            base="main"
        )
        
        self.mock_executor.execute.assert_called_once()
        args = self.mock_executor.execute.call_args[0][0]
        assert args[:2] == ['gh', 'pr']
        assert 'create' in args
        assert '--title' in args
        assert 'New Feature' in args
        assert '--body' in args
        # Check that body includes operation marker
        body_index = args.index('--body') + 1
        assert '<!-- claude-tasker-op -->' in args[body_index]
        
        assert url == pr_output
    
    def test_create_issue(self):
        """Test issue creation."""
        issue_output = "https://github.com/user/repo/issues/124"
        result = self._create_command_result(stdout=issue_output)
        self.mock_executor.execute.return_value = result
        
        url = self.gh_service.create_issue(
            title="Bug Report",
            body="Bug description",
            labels=["bug", "needs-triage"]
        )
        
        self.mock_executor.execute.assert_called_once()
        args = self.mock_executor.execute.call_args[0][0]
        assert args[:3] == ['gh', 'issue', 'create']
        assert '--title' in args
        assert 'Bug Report' in args
        assert '--label' in args
        assert 'bug,needs-triage' in args
        
        assert url == issue_output
    
    def test_get_default_branch(self):
        """Test getting default branch."""
        branch_json = {"defaultBranchRef": {"name": "main"}}
        result = self._create_command_result(stdout=json.dumps(branch_json))
        self.mock_executor.execute.return_value = result
        
        branch = self.gh_service.get_default_branch()
        
        self.mock_executor.execute.assert_called_once_with([
            'gh', 'repo', 'view', '--json', 'defaultBranchRef'
        ])
        
        assert branch == "main"
    
    def test_get_issue_comments(self):
        """Test getting issue comments."""
        comments = [
            {"body": "First comment", "author": {"login": "user1"}},
            {"body": "Second comment", "author": {"login": "user2"}}
        ]
        result = self._create_command_result(stdout=json.dumps(comments))
        self.mock_executor.execute.return_value = result
        
        retrieved_comments = self.gh_service.get_issue_comments(123)
        
        self.mock_executor.execute.assert_called_once_with([
            'gh', 'api', 'repos/{owner}/{repo}/issues/123/comments'
        ])
        
        assert retrieved_comments == comments
    
    def test_get_pr_comments(self):
        """Test getting PR comments."""
        comments = [{"body": "PR comment", "author": {"login": "reviewer"}}]
        result = self._create_command_result(stdout=json.dumps(comments))
        self.mock_executor.execute.return_value = result
        
        retrieved_comments = self.gh_service.get_pr_comments(456)
        
        self.mock_executor.execute.assert_called_once_with([
            'gh', 'api', 'repos/{owner}/{repo}/pulls/456/comments'
        ])
        
        assert retrieved_comments == comments
    
    def test_check_pr_status(self):
        """Test checking PR status."""
        status_json = {
            "statusCheckRollup": [{"conclusion": "success"}],
            "reviewDecision": "APPROVED"
        }
        result = self._create_command_result(stdout=json.dumps(status_json))
        self.mock_executor.execute.return_value = result
        
        status = self.gh_service.check_pr_status(456)
        
        self.mock_executor.execute.assert_called_once_with([
            'gh', 'pr', 'view', '456', '--json', 'statusCheckRollup,reviewDecision'
        ])
        
        assert status == status_json
    
    def test_get_repo_info(self):
        """Test getting repository information."""
        repo_json = {
            "name": "test-repo",
            "owner": {"login": "testuser"},
            "description": "Test repository",
            "url": "https://github.com/testuser/test-repo",
            "isPrivate": False,
            "defaultBranchRef": {"name": "main"}
        }
        result = self._create_command_result(stdout=json.dumps(repo_json))
        self.mock_executor.execute.return_value = result
        
        repo_info = self.gh_service.get_repo_info()
        
        self.mock_executor.execute.assert_called_once_with([
            'gh', 'repo', 'view', '--json', 'name,owner,description,url,isPrivate,defaultBranchRef'
        ])
        
        assert repo_info == repo_json
    
    def test_list_issues(self):
        """Test listing issues."""
        issues = [
            {"number": 1, "title": "First issue", "state": "open"},
            {"number": 2, "title": "Second issue", "state": "closed"}
        ]
        result = self._create_command_result(stdout=json.dumps(issues))
        self.mock_executor.execute.return_value = result
        
        retrieved_issues = self.gh_service.list_issues(state="all", limit=50)
        
        self.mock_executor.execute.assert_called_once_with([
            'gh', 'issue', 'list', '--state', 'all', '--limit', '50',
            '--json', 'number,title,labels,url,author,state'
        ])
        
        assert retrieved_issues == issues
    
    def test_list_prs(self):
        """Test listing PRs."""
        prs = [
            {"number": 1, "title": "First PR", "headRefName": "feature-1"},
            {"number": 2, "title": "Second PR", "headRefName": "feature-2"}
        ]
        result = self._create_command_result(stdout=json.dumps(prs))
        self.mock_executor.execute.return_value = result
        
        retrieved_prs = self.gh_service.list_prs()
        
        self.mock_executor.execute.assert_called_once_with([
            'gh', 'pr', 'list', '--state', 'open', '--limit', '30',
            '--json', 'number,title,headRefName,baseRefName,author,url'
        ])
        
        assert retrieved_prs == prs
    
    def test_error_handling_and_logging(self):
        """Test error handling and logging."""
        mock_logger = Mock()
        service = GhService(self.mock_executor, logger=mock_logger)
        
        result = self._create_command_result(success=False, stderr="API error")
        self.mock_executor.execute.return_value = result
        
        issue = service.get_issue(123)
        
        assert issue is None
        mock_logger.error.assert_called_once()
        assert "Failed to fetch issue #123" in mock_logger.error.call_args[0][0]
    
    def test_json_parse_error_handling(self):
        """Test JSON parsing error handling."""
        mock_logger = Mock()
        service = GhService(self.mock_executor, logger=mock_logger)
        
        result = self._create_command_result(stdout="invalid json")
        self.mock_executor.execute.return_value = result
        
        issue = service.get_issue(123)
        
        assert issue is None
        mock_logger.error.assert_called_once()
        assert "Failed to parse issue data" in mock_logger.error.call_args[0][0]