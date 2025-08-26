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


class TestBranchManager(unittest.TestCase):
    """Test suite for BranchManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        mock_git_service = Mock(spec=GitService)
        mock_gh_service = Mock(spec=GhService)
        # Mock the remote URL for initialization
        mock_git_service.remote.return_value = Mock(success=True, stdout="https://github.com/owner/repo.git")
        self.branch_manager = BranchManager(
            strategy=BranchStrategy.REUSE_WHEN_POSSIBLE,
            git_service=mock_git_service,
            gh_service=mock_gh_service
        )
    
    @patch('subprocess.run')
    def test_find_existing_branches_for_issue(self, mock_run):
        """Test finding existing branches for an issue."""
        # Mock git branch outputs
        mock_run.side_effect = [
            # Local branches
            Mock(returncode=0, stdout="  issue-123-1234567890\n* issue-123-1234567891"),
            # Remote branches  
            Mock(returncode=0, stdout="  origin/issue-123-1234567892\n  origin/issue-123-1234567893"),
            # Current branch
            Mock(returncode=0, stdout="issue-123-1234567891"),
            # Multiple ls-remote calls for checking remote existence
            Mock(returncode=0, stdout="refs/heads/issue-123-1234567890"),
            Mock(returncode=0, stdout=""),  # No uncommitted changes
            Mock(returncode=0, stdout="refs/heads/issue-123-1234567891"),
            Mock(returncode=0, stdout="modified: file.txt"),  # Has uncommitted changes
            Mock(returncode=0, stdout=""),
            Mock(returncode=0, stdout=""),
        ]
        
        branches = self.branch_manager.find_existing_branches_for_issue(123)
        
        # Should find 4 branches total
        self.assertEqual(len(branches), 4)
        
        # Check current branch is marked correctly
        current_branches = [b for b in branches if b.is_current]
        self.assertEqual(len(current_branches), 1)
        self.assertEqual(current_branches[0].name, "issue-123-1234567891")
        self.assertTrue(current_branches[0].has_uncommitted_changes)
    
    @patch('subprocess.run')
    def test_find_existing_pr_for_issue(self, mock_run):
        """Test finding existing PR for an issue."""
        pr_data = [{
            'number': 456,
            'title': 'Fix issue #123',
            'headRefName': 'issue-123-1234567890',
            'url': 'https://github.com/test/repo/pull/456',
            'isDraft': False
        }]
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(pr_data)
        )
        
        self.branch_manager.repo_owner = "test"
        self.branch_manager.repo_name = "repo"
        
        pr = self.branch_manager.find_existing_pr_for_issue(123)
        
        self.assertIsNotNone(pr)
        self.assertEqual(pr['number'], 456)
        self.assertEqual(pr['headRefName'], 'issue-123-1234567890')
    
    @patch('subprocess.run')
    def test_reuse_existing_pr_branch(self, mock_run):
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
        
        mock_run.side_effect = [
            # find_existing_pr_for_issue
            Mock(returncode=0, stdout=json.dumps(pr_data)),
            # fetch branch
            Mock(returncode=0, stdout=""),
            # check if branch exists locally
            Mock(returncode=0, stdout=""),
            # checkout branch
            Mock(returncode=0, stdout=""),
            # pull latest
            Mock(returncode=0, stdout="")
        ]
        
        success, branch_name, action = self.branch_manager.reuse_or_create_branch(123, "main")
        
        self.assertTrue(success)
        self.assertEqual(branch_name, "issue-123-existing")
        self.assertEqual(action, "reused")
    
    @patch('subprocess.run')
    @patch('time.time')
    def test_create_new_branch_when_no_pr(self, mock_time, mock_run):
        """Test creating new branch when no PR exists."""
        mock_time.return_value = 1234567890
        
        self.branch_manager.repo_owner = "test"
        self.branch_manager.repo_name = "repo"
        
        mock_run.side_effect = [
            # find_existing_pr_for_issue - no PR found
            Mock(returncode=0, stdout="[]"),
            # find_existing_branches_for_issue calls
            Mock(returncode=0, stdout=""),  # No local branches
            Mock(returncode=0, stdout=""),  # No remote branches
            Mock(returncode=0, stdout="main"),  # Current branch
            # checkout base branch
            Mock(returncode=0, stdout=""),
            # pull latest
            Mock(returncode=0, stdout=""),
            # create new branch
            Mock(returncode=0, stdout="")
        ]
        
        success, branch_name, action = self.branch_manager.reuse_or_create_branch(123, "main")
        
        self.assertTrue(success)
        self.assertEqual(branch_name, "issue-123-1234567890")
        self.assertEqual(action, "created")
    
    @patch('subprocess.run')
    def test_checkout_remote_only_branch(self, mock_run):
        """Test checking out a branch that only exists remotely."""
        mock_run.side_effect = [
            # fetch branch
            Mock(returncode=0, stdout=""),
            # check if branch exists locally (doesn't exist)
            Mock(returncode=1, stdout=""),
            # create local branch from remote
            Mock(returncode=0, stdout="")
        ]
        
        success, message = self.branch_manager._checkout_branch("issue-123-remote", "main")
        
        self.assertTrue(success)
        self.assertIn("Created local branch", message)
    
    @patch('subprocess.run')
    def test_cleanup_old_branches(self, mock_run):
        """Test cleanup of old issue branches."""
        # Mock finding 5 branches for the issue
        mock_run.side_effect = [
            # find_existing_branches_for_issue
            Mock(returncode=0, stdout="  issue-123-1000\n  issue-123-2000\n  issue-123-3000\n  issue-123-4000\n  issue-123-5000"),
            Mock(returncode=0, stdout=""),  # No remote branches
            Mock(returncode=0, stdout="main"),  # Current branch
            # Multiple checks for remote existence (first 2 exist remotely)
            Mock(returncode=0, stdout="refs/heads/issue-123-1000"),  # exists remotely
            Mock(returncode=0, stdout=""),  # No uncommitted changes
            Mock(returncode=0, stdout="refs/heads/issue-123-2000"),  # exists remotely  
            Mock(returncode=0, stdout=""),
            Mock(returncode=0, stdout=""),  # issue-123-3000 doesn't exist remotely
            Mock(returncode=0, stdout=""),
            Mock(returncode=0, stdout=""),  # issue-123-4000 doesn't exist remotely
            Mock(returncode=0, stdout=""),
            Mock(returncode=0, stdout=""),  # issue-123-5000 doesn't exist remotely
            Mock(returncode=0, stdout=""),
            # Delete oldest branches (keeping 3) - deletes issue-123-2000 and issue-123-1000
            Mock(returncode=0, stdout=""),  # Delete local issue-123-2000
            Mock(returncode=0, stdout=""),  # Delete remote issue-123-2000  
            Mock(returncode=0, stdout=""),  # Delete local issue-123-1000
            Mock(returncode=1, stdout="", stderr="error"),  # Delete remote issue-123-1000 fails
        ]
        
        deleted_count = self.branch_manager.cleanup_old_issue_branches(123, keep_count=3)
        
        # Should delete 1 branch successfully (one remote delete fails)
        self.assertEqual(deleted_count, 1)
    
    def test_branch_strategy_always_new(self):
        """Test ALWAYS_NEW strategy skips reuse logic."""
        manager = BranchManager(BranchStrategy.ALWAYS_NEW)
        
        with patch.object(manager, '_create_new_branch') as mock_create:
            mock_create.return_value = (True, "issue-123-new", "created")
            
            success, branch_name, action = manager.reuse_or_create_branch(123, "main")
            
            self.assertTrue(success)
            self.assertEqual(action, "created")
            mock_create.assert_called_once_with(123, "main")
    
    def test_branch_strategy_reuse_or_fail(self):
        """Test REUSE_OR_FAIL strategy fails when no branch exists."""
        manager = BranchManager(BranchStrategy.REUSE_OR_FAIL)
        
        with patch.object(manager, 'find_existing_pr_for_issue') as mock_find_pr:
            with patch.object(manager, 'find_existing_branches_for_issue') as mock_find_branches:
                mock_find_pr.return_value = None
                mock_find_branches.return_value = []
                
                success, branch_name, message = manager.reuse_or_create_branch(123, "main")
                
                self.assertFalse(success)
                self.assertIn("No existing branch found", message)
    
    @patch('subprocess.run')
    def test_init_repo_info(self, mock_run):
        """Test initialization of repository information."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="https://github.com/owner/repo.git"
        )
        
        manager = BranchManager()
        
        self.assertEqual(manager.repo_owner, "owner")
        self.assertEqual(manager.repo_name, "repo")
    
    def test_analyze_branch_parses_issue_and_timestamp(self):
        """Test that _analyze_branch correctly parses branch names."""
        branch_info = self.branch_manager._analyze_branch("issue-123-1234567890", "main")
        
        self.assertEqual(branch_info.name, "issue-123-1234567890")
        self.assertEqual(branch_info.issue_number, 123)
        self.assertEqual(branch_info.timestamp, "1234567890")
        self.assertFalse(branch_info.is_current)


if __name__ == '__main__':
    unittest.main()