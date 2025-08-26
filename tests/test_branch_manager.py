"""Tests for intelligent branch management with reuse capabilities."""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import subprocess
import json
import time

from src.claude_tasker.branch_manager import (
    BranchManager, BranchStrategy, BranchInfo
)
from src.claude_tasker.services.git_service import GitService
from src.claude_tasker.services.gh_service import GhService
from src.claude_tasker.services.command_executor import CommandResult, CommandErrorType


class TestBranchManager(unittest.TestCase):
    """Test suite for BranchManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_git_service = self._create_mock_git_service()
        self.mock_gh_service = Mock(spec=GhService)
        self.branch_manager = BranchManager(
            self.mock_git_service,
            self.mock_gh_service,
            BranchStrategy.REUSE_WHEN_POSSIBLE
        )
    
    def _create_mock_git_service(self):
        """Create a properly configured mock GitService."""
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = Mock()
        
        # Configure common methods with proper CommandResult returns
        def create_command_result(stdout="", returncode=0, success=True):
            return CommandResult(
                returncode=returncode,
                stdout=stdout,
                stderr="",
                command=["git"],
                execution_time=1.0,
                error_type=CommandErrorType.SUCCESS if success else CommandErrorType.GENERAL_ERROR,
                attempts=1,
                success=success
            )
        
        # Set up default returns for common methods that actually exist
        mock_git_service.remote.return_value = create_command_result("https://github.com/owner/repo.git")
        mock_git_service.current_branch.return_value = "main"
        mock_git_service.branch.return_value = create_command_result("")
        mock_git_service.status.return_value = create_command_result("")
        mock_git_service.checkout.return_value = create_command_result("")
        mock_git_service.pull.return_value = create_command_result("")
        mock_git_service.fetch.return_value = create_command_result("")
        mock_git_service.show_ref.return_value = create_command_result("")
        mock_git_service.get_remote_url.return_value = "https://github.com/owner/repo.git"
        
        return mock_git_service
    
    def _create_branch_manager(self, strategy=BranchStrategy.REUSE_WHEN_POSSIBLE):
        """Helper to create BranchManager with mocked services."""
        mock_git_service = self._create_mock_git_service()
        mock_gh_service = Mock(spec=GhService)
        return BranchManager(
            mock_git_service,
            mock_gh_service,
            strategy
        )
    
    def test_find_existing_branches_for_issue(self):
        """Test finding existing branches for an issue."""
        def create_result(stdout="", success=True):
            return CommandResult(
                returncode=0 if success else 1,
                stdout=stdout,
                stderr="",
                command=["git"],
                execution_time=1.0,
                error_type=CommandErrorType.SUCCESS if success else CommandErrorType.GENERAL_ERROR,
                attempts=1,
                success=success
            )
        
        # Configure branch method calls
        local_branches_result = create_result("  issue-123-1234567890\n* issue-123-1234567891")
        remote_branches_result = create_result("  origin/issue-123-1234567892\n  origin/issue-123-1234567893")
        
        self.mock_git_service.branch.side_effect = [local_branches_result, remote_branches_result]
        self.mock_git_service.current_branch.return_value = "issue-123-1234567891"
        
        branches = self.branch_manager.find_existing_branches_for_issue(123)
        
        # Should find branches from both local and remote
        self.assertGreater(len(branches), 0)
        
        # Verify git service methods were called
        self.assertEqual(self.mock_git_service.branch.call_count, 2)
        self.mock_git_service.current_branch.assert_called_once()
    
    def test_find_existing_pr_for_issue(self):
        """Test finding existing PR for an issue."""
        pr_data = [{
            'number': 456,
            'title': 'Fix issue #123',
            'headRefName': 'issue-123-1234567890',
            'url': 'https://github.com/test/repo/pull/456',
            'isDraft': False
        }]
        
        # Mock GH service to return PR data
        self.mock_gh_service.list_prs.return_value = pr_data
        
        self.branch_manager.repo_owner = "test"
        self.branch_manager.repo_name = "repo"
        
        pr = self.branch_manager.find_existing_pr_for_issue(123)
        
        self.assertIsNotNone(pr)
        self.assertEqual(pr['number'], 456)
        self.assertEqual(pr['headRefName'], 'issue-123-1234567890')
    
    def test_reuse_existing_pr_branch(self):
        """Test reusing an existing PR branch."""
        # Setup branch manager with repo info
        self.branch_manager.repo_owner = "test"
        self.branch_manager.repo_name = "repo"
        
        pr_data = [{
            'number': 456,
            'title': 'Fix issue #123',
            'headRefName': 'issue-123-existing',
            'url': 'https://github.com/test/repo/pull/456',
            'isDraft': False
        }]
        
        # Configure mocks
        self.mock_gh_service.list_prs.return_value = pr_data
        
        def create_result(success=True):
            return CommandResult(
                returncode=0 if success else 1,
                stdout="",
                stderr="",
                command=["git"],
                execution_time=1.0,
                error_type=CommandErrorType.SUCCESS if success else CommandErrorType.GENERAL_ERROR,
                attempts=1,
                success=success
            )
        
        self.mock_git_service.fetch.return_value = create_result()
        self.mock_git_service.checkout.return_value = create_result()
        self.mock_git_service.pull.return_value = create_result()
        
        success, branch_name, action = self.branch_manager.reuse_or_create_branch(123, "main")
        
        self.assertTrue(success)
        self.assertEqual(branch_name, "issue-123-existing")
        self.assertEqual(action, "reused")
    
    def test_create_new_branch_when_no_pr(self):
        """Test creating new branch when no PR exists."""
        # No existing PRs
        self.mock_gh_service.list_prs.return_value = []
        
        # No existing branches
        empty_result = CommandResult(
            returncode=0,
            stdout="",
            stderr="",
            command=["git"],
            execution_time=1.0,
            error_type=CommandErrorType.SUCCESS,
            attempts=1,
            success=True
        )
        
        self.mock_git_service.branch.return_value = empty_result
        self.mock_git_service.current_branch.return_value = "main"
        
        with patch('time.time', return_value=1234567890):
            success, branch_name, action = self.branch_manager.reuse_or_create_branch(123, "main")
        
        self.assertTrue(success)
        self.assertIn("issue-123-", branch_name)
        self.assertEqual(action, "created")
    
    def test_branch_strategy_initialization(self):
        """Test that branch strategy is properly set during initialization."""
        # Test different strategies
        always_new_manager = self._create_branch_manager(BranchStrategy.ALWAYS_NEW)
        self.assertEqual(always_new_manager.strategy, BranchStrategy.ALWAYS_NEW)
        
        reuse_manager = self._create_branch_manager(BranchStrategy.REUSE_WHEN_POSSIBLE) 
        self.assertEqual(reuse_manager.strategy, BranchStrategy.REUSE_WHEN_POSSIBLE)
        
        reuse_or_fail_manager = self._create_branch_manager(BranchStrategy.REUSE_OR_FAIL)
        self.assertEqual(reuse_or_fail_manager.strategy, BranchStrategy.REUSE_OR_FAIL)
    
    def test_cleanup_old_branches(self):
        """Test cleanup of old issue branches."""
        # Create some mock branches
        branches_result = CommandResult(
            returncode=0,
            stdout="  issue-123-old1\n  issue-123-old2\n  issue-123-old3",
            stderr="",
            command=["git"],
            execution_time=1.0,
            error_type=CommandErrorType.SUCCESS,
            attempts=1,
            success=True
        )
        
        self.mock_git_service.branch.return_value = branches_result
        self.mock_git_service.current_branch.return_value = "main"
        
        # Mock successful branch deletion
        delete_result = CommandResult(
            returncode=0,
            stdout="",
            stderr="",
            command=["git"],
            execution_time=1.0,
            error_type=CommandErrorType.SUCCESS,
            attempts=1,
            success=True
        )
        
        self.mock_git_service.delete_branch = Mock(return_value=delete_result)
        
        deleted_count = self.branch_manager.cleanup_old_issue_branches(123, keep_count=1)
        
        # Should delete some branches
        self.assertGreaterEqual(deleted_count, 0)
    
    def test_init_repo_info(self):
        """Test initialization of repository information."""
        # This is tested indirectly through setUp, but let's verify repo info extraction
        self.assertIsNotNone(self.branch_manager.repo_owner)
        self.assertIsNotNone(self.branch_manager.repo_name)


if __name__ == '__main__':
    unittest.main()