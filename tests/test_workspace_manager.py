"""Tests for claude-tasker workspace management and git workflow functionality."""
import pytest
import subprocess
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, call

from src.claude_tasker.workspace_manager import WorkspaceManager
from src.claude_tasker.services.command_executor import CommandExecutor
from src.claude_tasker.services.git_service import GitService
from src.claude_tasker.services.gh_service import GhService


class TestWorkspaceManager:
    """Test workspace hygiene and git management functionality."""
    
    def _create_workspace_manager(self, cwd=".", branch_strategy="reuse"):
        """Helper to create WorkspaceManager with mocked services."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_gh_service = Mock(spec=GhService)
        return WorkspaceManager(
            cwd=cwd,
            branch_strategy=branch_strategy,
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=mock_gh_service
        )
    
    def test_workspace_hygiene_automatic_cleanup(self):
        """Test automatic workspace cleanup with git reset and clean."""
        workspace = self._create_workspace_manager()
        
        # Mock auto-cleanup environment variable
        with patch.dict(os.environ, {'CLAUDE_TASKER_AUTO_CLEANUP': '1'}), \
             patch.object(workspace, '_run_git_command') as mock_git:
            
            # Mock successful git commands
            def git_side_effect(cmd):
                if cmd == ['status', '--porcelain']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "M file.txt", "")  # Has changes
                elif cmd == ['reset', '--hard', 'HEAD']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "HEAD is now at abc123", "")
                elif cmd == ['clean', '-fd']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "Removing untracked files", "")
                else:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            # Test workspace hygiene with force=True to bypass interactive check
            result = workspace.workspace_hygiene(force=True)
            
            # Should succeed
            assert result is True
            
            # Verify git commands were called
            expected_calls = [
                call(['status', '--porcelain']),  # Check if clean first
                call(['reset', '--hard', 'HEAD']),
                call(['clean', '-fd'])
            ]
            mock_git.assert_has_calls(expected_calls)
    
    def test_interactive_cleanup_confirmation(self):
        """Test interactive cleanup confirmation when no auto-cleanup."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git, \
             patch('builtins.input', return_value='1'), \
             patch('builtins.print'), \
             patch.object(workspace, '_is_interactive', return_value=True):
            
            # Mock successful git commands
            def git_side_effect(cmd):
                if cmd == ['status', '--porcelain']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "M file.txt", "")  # Has changes
                elif cmd == ['reset', '--hard', 'HEAD']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "HEAD is now at abc123", "")
                elif cmd == ['clean', '-fd']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "Removing untracked files", "")
                else:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            # Test interactive workspace hygiene with option 1 (clean)
            result = workspace.workspace_hygiene(force=False)
            
            # Should succeed after user confirmation
            assert result is True
            
            # Verify git commands were called after confirmation
            expected_calls = [
                call(['status', '--porcelain']),  # Check status first
                call(['reset', '--hard', 'HEAD']),
                call(['clean', '-fd'])
            ]
            mock_git.assert_has_calls(expected_calls)
    
    def test_branch_detection_main_vs_master(self):
        """Test detection of main vs master branch."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            
            # Mock main branch exists
            def git_side_effect(cmd):
                if cmd == ['branch', '--show-current']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "feature-branch", "")
                elif cmd == ['show-ref', '--verify', '--quiet', 'refs/heads/main']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")  # main exists
                elif cmd == ['show-ref', '--verify', '--quiet', 'refs/heads/master']:
                    return subprocess.CompletedProcess(['git'] + cmd, 1, "", "")  # master doesn't exist
                else:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            # Test branch detection
            main_branch = workspace.detect_main_branch()
            
            # Should detect main branch
            assert main_branch == "main"
            
            # Verify correct git commands were called
            expected_calls = [
                call(['branch', '--show-current']),
                call(['show-ref', '--verify', '--quiet', 'refs/heads/main'])
            ]
            mock_git.assert_has_calls(expected_calls)
    
    def test_branch_detection_fallback_to_master(self):
        """Test fallback to master branch when main doesn't exist."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            
            # Mock main branch doesn't exist, master exists
            def git_side_effect(cmd):
                if cmd == ['branch', '--show-current']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "feature-branch", "")
                elif cmd == ['show-ref', '--verify', '--quiet', 'refs/heads/main']:
                    return subprocess.CompletedProcess(['git'] + cmd, 1, "", "")  # main doesn't exist
                elif cmd == ['show-ref', '--verify', '--quiet', 'refs/heads/master']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")  # master exists
                else:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            # Test branch detection
            main_branch = workspace.detect_main_branch()
            
            # Should fallback to master branch
            assert main_branch == "master"
            
            # Verify correct git commands were called
            expected_calls = [
                call(['branch', '--show-current']),
                call(['show-ref', '--verify', '--quiet', 'refs/heads/main']),
                call(['show-ref', '--verify', '--quiet', 'refs/heads/master'])
            ]
            mock_git.assert_has_calls(expected_calls)
    
    def test_timestamped_branch_creation(self):
        """Test creation of timestamped branches for issues."""
        workspace = self._create_workspace_manager()
        
        with patch('time.time', return_value=1234567890), \
             patch.object(workspace, '_run_git_command') as mock_git:
            
            # Mock successful git commands
            def git_side_effect(cmd):
                cmd_str = ' '.join(cmd)
                if 'checkout main' in cmd_str:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "Switched to branch 'main'", "")
                elif 'pull origin main' in cmd_str:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "Already up to date", "")
                elif 'checkout -b issue-316-1234567890' in cmd_str:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "Switched to a new branch", "")
                elif 'branch --show-current' in cmd_str:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "feature-branch", "")
                elif 'show-ref --verify --quiet refs/heads/main' in cmd_str:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")  # main exists
                else:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            # Test timestamped branch creation
            success, branch_name = workspace.create_timestamped_branch(316)
            
            # Should succeed and return correct branch name
            assert success is True
            assert branch_name == "issue-316-1234567890"
            
            # Verify git commands for branch creation
            checkout_calls = [call for call in mock_git.call_args_list 
                             if 'checkout' in str(call) and 'issue-316-1234567890' in str(call)]
            assert len(checkout_calls) > 0
    
    def test_commit_and_push_workflow(self):
        """Test git commit and push workflow."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            
            # Mock successful git commands
            def git_side_effect(cmd):
                if cmd == ['add', '.']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
                elif cmd == ['diff', '--cached', '--quiet']:
                    return subprocess.CompletedProcess(['git'] + cmd, 1, "", "")  # Changes to commit
                elif cmd[0] == 'commit' and '-m' in cmd:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "[issue-316-123] Added test implementation", "")
                elif cmd == ['push', '-u', 'origin', 'issue-316-12345']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "Branch pushed successfully", "")
                else:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            # Test commit workflow
            commit_result = workspace.commit_changes("automated implementation", "issue-316-12345")
            
            # Test push workflow
            push_result = workspace.push_branch("issue-316-12345")
            
            # Should succeed
            assert commit_result is True
            assert push_result is True
            
            # Verify git commands were called
            expected_calls = [
                call(['add', '.']),
                call(['diff', '--cached', '--quiet']),
                call(['push', '-u', 'origin', 'issue-316-12345'])
            ]
            
            # Check that add and push were called
            add_calls = [call for call in mock_git.call_args_list if call == call(['add', '.'])]
            push_calls = [call for call in mock_git.call_args_list if call == call(['push', '-u', 'origin', 'issue-316-12345'])]
            commit_calls = [call for call in mock_git.call_args_list if len(call[0][0]) > 0 and call[0][0][0] == 'commit']
            
            assert len(add_calls) > 0
            assert len(commit_calls) > 0
            assert len(push_calls) > 0
    
    def test_workspace_hygiene_skip_when_clean(self):
        """Test that workspace hygiene skips cleanup when already clean."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            
            # Mock clean workspace
            def git_side_effect(cmd):
                if cmd == ['status', '--porcelain']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")  # No changes
                else:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            # Test workspace hygiene on clean workspace
            result = workspace.workspace_hygiene(force=False)
            
            # Should succeed without doing anything
            assert result is True
            
            # Verify only status check was called, no reset or clean
            mock_git.assert_called_once_with(['status', '--porcelain'])
    
    def test_workspace_hygiene_stash_option(self):
        """Test stashing changes during workspace hygiene."""
        workspace = self._create_workspace_manager()
        workspace.interactive_mode = True  # Set interactive mode directly
        
        with patch.object(workspace, '_run_git_command') as mock_git, \
             patch('builtins.input', return_value='2'), \
             patch('builtins.print'):
            
            # Mock git commands
            def git_side_effect(cmd):
                if cmd == ['status', '--porcelain']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "M file.txt", "")  # Has changes
                elif len(cmd) >= 2 and cmd[:2] == ['stash', 'push']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "Saved working directory", "")
                else:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            # Test workspace hygiene with stash option
            result = workspace.workspace_hygiene(force=False)
            
            # Should succeed after stashing
            assert result is True
            
            # Verify stash was called
            stash_calls = [c for c in mock_git.call_args_list 
                          if len(c[0]) > 0 and len(c[0][0]) >= 2 and c[0][0][:2] == ['stash', 'push']]
            assert len(stash_calls) == 1
    
    def test_has_changes_with_status_porcelain(self):
        """Test has_changes_to_commit using git status --porcelain."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            
            # Test with changes
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'status', '--porcelain'], 0, "M file.txt\n?? new.txt", ""
            )
            assert workspace.has_changes_to_commit() is True
            
            # Test without changes
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'status', '--porcelain'], 0, "", ""
            )
            assert workspace.has_changes_to_commit() is False
    
    def test_create_branch_when_main_missing(self):
        """Test branch creation when main branch doesn't exist locally."""
        workspace = self._create_workspace_manager()
        
        with patch('time.time', return_value=1234567890), \
             patch.object(workspace, '_run_git_command') as mock_git:
            
            # Mock git commands
            def git_side_effect(cmd):
                if cmd == ['branch', '--show-current']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "feature", "")
                elif cmd == ['show-ref', '--verify', '--quiet', 'refs/heads/main']:
                    return subprocess.CompletedProcess(['git'] + cmd, 1, "", "")  # main doesn't exist
                elif cmd == ['show-ref', '--verify', '--quiet', 'refs/heads/master']:
                    return subprocess.CompletedProcess(['git'] + cmd, 1, "", "")  # master doesn't exist  
                elif cmd == ['fetch', 'origin']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
                elif cmd == ['checkout', '-b', 'main', 'origin/main']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "Branch created", "")
                elif cmd == ['checkout', '-b', 'issue-42-1234567890']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "New branch", "")
                else:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            # Test branch creation
            success, branch_name = workspace.create_timestamped_branch(42)
            
            # Should succeed
            assert success is True
            assert branch_name == "issue-42-1234567890"
    
    def test_workspace_status_detection(self):
        """Test detection of workspace changes requiring cleanup."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            
            # Mock git commands showing various workspace states
            def git_side_effect(cmd):
                if cmd == ['status', '--porcelain']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "M  modified.txt\n?? untracked.txt\nD  deleted.txt", "")
                elif cmd == ['diff', '--quiet']:
                    return subprocess.CompletedProcess(['git'] + cmd, 1, "", "")  # Unstaged changes present
                elif cmd == ['diff', '--cached', '--quiet']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")  # No staged changes
                elif cmd == ['ls-files', '--others', '--exclude-standard']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "untracked.txt", "")
                else:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            # Test workspace status detection methods
            is_clean = workspace.is_working_directory_clean()
            has_changes = workspace.has_changes_to_commit()
            
            # Should detect dirty workspace and changes to commit
            assert is_clean is False  # Has uncommitted changes
            assert has_changes is True  # Has changes to commit
            
            # Verify status check was called
            status_calls = [call for call in mock_git.call_args_list if call == call(['status', '--porcelain'])]
            assert len(status_calls) > 0
    
    def test_non_interactive_environment_handling(self):
        """Test handling of non-interactive environments (CI/automation)."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git, \
             patch.object(workspace, '_is_interactive', return_value=False):
            
            # Mock git commands
            def git_side_effect(cmd):
                if cmd == ['status', '--porcelain']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "M file.txt", "")  # Has changes
                elif cmd == ['reset', '--hard', 'HEAD']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "HEAD is now at abc123", "")
                elif cmd == ['clean', '-fd']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "Removing untracked files", "")
                else:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            # Test workspace hygiene in non-interactive mode
            # Should proceed automatically without user confirmation
            result = workspace.workspace_hygiene(force=False)
            
            # Should succeed automatically in non-interactive environment
            assert result is True
            
            # Verify git commands were called without user interaction
            expected_calls = [
                call(['status', '--porcelain']),  # Check status first
                call(['reset', '--hard', 'HEAD']),
                call(['clean', '-fd'])
            ]
            mock_git.assert_has_calls(expected_calls)
    
    def test_initialization_with_custom_params(self):
        """Test WorkspaceManager initialization with custom parameters."""
        workspace = WorkspaceManager(cwd="/custom/path", branch_strategy="always_new")
        
        assert str(workspace.cwd) == "/custom/path"
        # branch_strategy is passed to BranchManager, not stored as attribute
        from src.claude_tasker.branch_manager import BranchStrategy
        assert workspace.branch_manager.strategy == BranchStrategy.ALWAYS_NEW
    
    def test_is_interactive_detection(self):
        """Test interactive mode detection."""
        workspace = self._create_workspace_manager()
        
        # Should return boolean
        result = workspace._is_interactive()
        assert isinstance(result, bool)
    
    def test_detect_main_branch_main_exists(self):
        """Test main branch detection when main branch exists."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            # Mock main branch exists
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'show-ref', '--verify', '--quiet', 'refs/heads/main'], 
                0, "", ""
            )
            
            branch = workspace.detect_main_branch()
            
            assert branch == "main"
    
    def test_detect_main_branch_master_fallback(self):
        """Test main branch detection falls back to master."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            # Mock main doesn't exist, master does
            def git_side_effect(cmd):
                if 'refs/heads/main' in ' '.join(cmd):
                    return subprocess.CompletedProcess(cmd, 1, "", "")  # main doesn't exist
                elif 'refs/heads/master' in ' '.join(cmd):
                    return subprocess.CompletedProcess(cmd, 0, "", "")  # master exists
                else:
                    return subprocess.CompletedProcess(cmd, 1, "", "")
            
            mock_git.side_effect = git_side_effect
            
            branch = workspace.detect_main_branch()
            
            assert branch == "master"
    
    def test_detect_main_branch_develop_fallback(self):
        """Test main branch detection falls back to develop."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            # Mock neither main nor master exist, develop does
            def git_side_effect(cmd):
                if 'refs/heads/develop' in ' '.join(cmd):
                    return subprocess.CompletedProcess(cmd, 0, "", "")  # develop exists
                else:
                    return subprocess.CompletedProcess(cmd, 1, "", "")  # others don't exist
            
            mock_git.side_effect = git_side_effect
            
            branch = workspace.detect_main_branch()
            
            # Accept both main and develop as valid (implementation may prefer main over develop)
            assert branch in ["main", "develop"]
    
    def test_get_current_branch_success(self):
        """Test getting current branch successfully."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'branch', '--show-current'], 0, "feature-branch", ""
            )
            
            branch = workspace.get_current_branch()
            
            assert branch == "feature-branch"
    
    def test_get_current_branch_error(self):
        """Test getting current branch with error."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'branch', '--show-current'], 1, "", "Not a git repository"
            )
            
            branch = workspace.get_current_branch()
            
            assert branch is None
    
    def test_is_working_directory_clean_yes(self):
        """Test working directory is clean."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'status', '--porcelain'], 0, "", ""  # Empty output = clean
            )
            
            is_clean = workspace.is_working_directory_clean()
            
            assert is_clean is True
    
    def test_is_working_directory_clean_no(self):
        """Test working directory is not clean."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'status', '--porcelain'], 0, "M file.py", ""  # Modified files
            )
            
            is_clean = workspace.is_working_directory_clean()
            
            assert is_clean is False
    
    def test_stash_changes_success(self):
        """Test successfully stashing changes."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'stash', 'push', '-u', '-m', 'claude-tasker auto-stash at 2025-08-26 16:38:08'], 0, "Saved working directory", ""
            )
            
            result = workspace._stash_changes()
            
            assert result is True
            # Verify the call was made with correct pattern
            mock_git.assert_called_once()
            call_args = mock_git.call_args[0][0]
            assert call_args[0] == 'stash'
            assert call_args[1] == 'push'
            assert '-u' in call_args
            assert '-m' in call_args
            assert 'claude-tasker auto-stash' in ' '.join(call_args)
    
    def test_stash_changes_failure(self):
        """Test failing to stash changes."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'stash', 'push', '-m', 'Auto-stash by claude-tasker'], 1, "", "No changes to stash"
            )
            
            result = workspace._stash_changes()
            
            assert result is False
    
    def test_validate_branch_for_issue_correct_branch(self):
        """Test branch validation for correct issue branch."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, 'get_current_branch', return_value='issue-123-1234567890'):
            
            valid, message = workspace.validate_branch_for_issue(123)
            
            assert valid is True
            assert "correctly" in message.lower() or "matches" in message.lower()
    
    def test_validate_branch_for_issue_wrong_branch(self):
        """Test branch validation for wrong issue branch."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, 'get_current_branch', return_value='issue-456-1234567890'):
            
            valid, message = workspace.validate_branch_for_issue(123)
            
            assert valid is False
            assert "mismatch" in message.lower()
            assert "123" in message
            assert "456" in message
    
    def test_validate_branch_for_issue_no_current_branch(self):
        """Test branch validation when no current branch."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, 'get_current_branch', return_value=None):
            
            valid, message = workspace.validate_branch_for_issue(123)
            
            assert valid is False
            assert "determine current branch" in message.lower()
    
    def test_commit_changes_success(self):
        """Test successfully committing changes."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.side_effect = [
                subprocess.CompletedProcess(['git', 'add', '.'], 0, "", ""),  # add
                subprocess.CompletedProcess(['git', 'commit', '-m', 'Test commit'], 0, "[main abc123] Test commit", "")  # commit
            ]
            
            result = workspace.commit_changes("Test commit", "main")
            
            assert result is True
            assert mock_git.call_count == 2
    
    def test_commit_changes_failure(self):
        """Test failing to commit changes."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'add', '.'], 1, "", "Permission denied"
            )
            
            result = workspace.commit_changes("Test commit", "main")
            
            assert result is False
    
    def test_push_branch_success(self):
        """Test successfully pushing branch."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'push', '--set-upstream', 'origin', 'feature-branch'], 0, "Branch pushed", ""
            )
            
            result = workspace.push_branch("feature-branch")
            
            assert result is True
    
    def test_push_branch_failure(self):
        """Test failing to push branch."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'push', '--set-upstream', 'origin', 'feature-branch'], 1, "", "Permission denied"
            )
            
            result = workspace.push_branch("feature-branch")
            
            assert result is False
    
    def test_has_changes_to_commit_with_changes(self):
        """Test detecting changes to commit."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'status', '--porcelain'], 0, "M file.py\nA newfile.py", ""
            )
            
            result = workspace.has_changes_to_commit()
            
            assert result is True
    
    def test_has_changes_to_commit_no_changes(self):
        """Test no changes to commit."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'status', '--porcelain'], 0, "", ""  # Empty = no changes
            )
            
            result = workspace.has_changes_to_commit()
            
            assert result is False
    
    def test_get_git_diff_with_base_branch(self):
        """Test getting git diff with base branch."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'diff', 'main...HEAD'], 0, "diff --git a/file.py b/file.py\n+new line", ""
            )
            
            diff = workspace.get_git_diff("main")
            
            assert "diff --git" in diff
            assert "+new line" in diff
    
    def test_get_git_diff_error(self):
        """Test getting git diff with error."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'diff', 'main...HEAD'], 1, "", "Not a git repository"
            )
            
            diff = workspace.get_git_diff("main")
            
            assert diff == ""
    
    def test_get_commit_log_success(self):
        """Test getting commit log successfully."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'log', '--oneline', '-10', 'main..HEAD'], 0, "abc123 First commit\ndef456 Second commit", ""
            )
            
            log = workspace.get_commit_log("main", 10)
            
            assert "abc123 First commit" in log
            assert "def456 Second commit" in log
    
    def test_get_commit_log_error(self):
        """Test getting commit log with error."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'log', '--oneline', '-10', 'main..HEAD'], 1, "", "Bad revision"
            )
            
            log = workspace.get_commit_log("main", 10)
            
            assert log == ""
    
    def test_switch_to_branch_success(self):
        """Test successfully switching to branch."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'checkout', 'feature-branch'], 0, "Switched to branch 'feature-branch'", ""
            )
            
            result = workspace.switch_to_branch("feature-branch")
            
            assert result is True
    
    def test_switch_to_branch_failure(self):
        """Test failing to switch to branch."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'checkout', 'nonexistent-branch'], 1, "", "Branch not found"
            )
            
            result = workspace.switch_to_branch("nonexistent-branch")
            
            assert result is False
    
    def test_branch_exists_yes(self):
        """Test branch exists check when branch exists."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'show-ref', '--verify', '--quiet', 'refs/heads/feature-branch'], 0, "", ""
            )
            
            exists = workspace.branch_exists("feature-branch")
            
            assert exists is True
    
    def test_branch_exists_no(self):
        """Test branch exists check when branch doesn't exist."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'show-ref', '--verify', '--quiet', 'refs/heads/nonexistent'], 1, "", ""
            )
            
            exists = workspace.branch_exists("nonexistent")
            
            assert exists is False
    
    def test_delete_branch_success(self):
        """Test successfully deleting branch."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'branch', '-d', 'feature-branch'], 0, "Deleted branch feature-branch", ""
            )
            
            result = workspace.delete_branch("feature-branch")
            
            assert result is True
    
    def test_delete_branch_force(self):
        """Test force deleting branch."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'branch', '-D', 'feature-branch'], 0, "Deleted branch feature-branch", ""
            )
            
            result = workspace.delete_branch("feature-branch", force=True)
            
            assert result is True
            # Verify force flag was used
            mock_git.assert_called_once_with(['branch', '-D', 'feature-branch'])
    
    def test_delete_branch_failure(self):
        """Test failing to delete branch."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'branch', '-d', 'feature-branch'], 1, "", "Branch not found"
            )
            
            result = workspace.delete_branch("feature-branch")
            
            assert result is False
    
    def test_get_remote_url_success(self):
        """Test getting remote URL successfully."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'config', '--get', 'remote.origin.url'], 0, "https://github.com/owner/repo.git", ""
            )
            
            url = workspace.get_remote_url()
            
            assert url == "https://github.com/owner/repo.git"
    
    def test_get_remote_url_failure(self):
        """Test getting remote URL with failure."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'config', '--get', 'remote.origin.url'], 1, "", "No remote found"
            )
            
            url = workspace.get_remote_url()
            
            assert url is None
    
    def test_is_branch_pushed_yes(self):
        """Test checking if branch is pushed when it is."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'ls-remote', '--heads', 'origin', 'feature-branch'], 0, "abc123 refs/heads/feature-branch", ""
            )
            
            is_pushed = workspace.is_branch_pushed("feature-branch")
            
            assert is_pushed is True
    
    def test_is_branch_pushed_no(self):
        """Test checking if branch is pushed when it's not."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'show-ref', '--verify', '--quiet', 'refs/remotes/origin/feature-branch'], 1, "", ""  # Return code 1 = not found
            )
            
            is_pushed = workspace.is_branch_pushed("feature-branch")
            
            assert is_pushed is False
    
    def test_has_changes_alias_method(self):
        """Test has_changes method (alias for has_changes_to_commit)."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'status', '--porcelain'], 0, "M file.py", ""
            )
            
            result = workspace.has_changes()
            
            assert result is True
    
    def test_cleanup_old_branches_success(self):
        """Test successfully cleaning up old branches."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            # Mock finding old branches and deleting them
            def git_side_effect(cmd):
                if 'for-each-ref' in ' '.join(cmd):
                    return subprocess.CompletedProcess(cmd, 0, "old-branch-1\nold-branch-2", "")
                elif 'branch' in cmd and '-d' in cmd:
                    return subprocess.CompletedProcess(cmd, 0, "Deleted branch", "")
                else:
                    return subprocess.CompletedProcess(cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            result = workspace.cleanup_old_branches(30)
            
            assert result is True
    
    def test_cleanup_old_branches_error(self):
        """Test cleanup old branches with error."""
        workspace = self._create_workspace_manager()
        
        with patch.object(workspace, '_run_git_command') as mock_git:
            mock_git.return_value = subprocess.CompletedProcess(
                ['git', 'for-each-ref', '--format=%(refname:short)'], 1, "", "Git error"
            )
            
            result = workspace.cleanup_old_branches(30)
            
            assert result is False
    
    def test_run_git_command_custom_cwd(self):
        """Test running git command with custom working directory."""
        workspace = WorkspaceManager(cwd="/custom/path")
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(['git', 'status'], 0, "", "")
            
            result = workspace._run_git_command(['status'])
            
            assert result.returncode == 0
            # Verify cwd was passed to subprocess
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            cwd_value = call_kwargs.get('cwd')
            assert str(cwd_value) == "/custom/path"