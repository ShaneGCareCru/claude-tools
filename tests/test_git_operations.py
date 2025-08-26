"""Tests for claude-tasker git operations and workspace management."""
import pytest
import subprocess
import os
import time
from pathlib import Path
from unittest.mock import patch, Mock, call, MagicMock
from src.claude_tasker.workspace_manager import WorkspaceManager
from src.claude_tasker.services.command_executor import CommandExecutor
from src.claude_tasker.services.git_service import GitService


class TestWorkspaceManager:
    """Test WorkspaceManager class directly."""
    
    def test_init(self):
        """Test WorkspaceManager initialization."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        assert workspace.cwd == Path(".").resolve()
        assert hasattr(workspace, 'interactive_mode')
    
    def test_init_with_custom_cwd(self, tmp_path):
        """Test WorkspaceManager initialization with custom directory."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            cwd=str(tmp_path),
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        assert workspace.cwd == tmp_path.resolve()
    
    def test_is_interactive_tty(self):
        """Test interactive mode detection with TTY."""
        with patch('os.isatty', return_value=True), \
             patch.dict('os.environ', {}, clear=True):
            mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        assert workspace.interactive_mode is True
    
    def test_is_interactive_ci(self):
        """Test interactive mode detection in CI environment."""
        with patch('os.isatty', return_value=True), \
             patch.dict('os.environ', {'CI': 'true'}):
            mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
            assert workspace.interactive_mode is False
    
    def test_is_interactive_github_actions(self):
        """Test interactive mode detection in GitHub Actions."""
        with patch('os.isatty', return_value=True), \
             patch.dict('os.environ', {'GITHUB_ACTIONS': 'true'}):
            mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
            assert workspace.interactive_mode is False
    
    def test_run_git_command_success(self):
        """Test successful git command execution."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="output", stderr="")
            
            result = workspace._run_git_command(['status'])
            
            assert result.returncode == 0
            assert result.stdout == "output"
            mock_run.assert_called_once_with(
                ['git', 'status'],
                cwd=workspace.cwd,
                capture_output=True,
                text=True,
                check=False
            )
    
    def test_run_git_command_failure(self):
        """Test git command execution failure."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="error")
            
            result = workspace._run_git_command(['invalid-command'])
            
            assert result.returncode == 1
            assert result.stderr == "error"
    
    def test_run_git_command_exception(self):
        """Test git command execution with exception."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        with patch('subprocess.run', side_effect=Exception("Command not found")):
            result = workspace._run_git_command(['status'])
            
            assert result.returncode == 1
            assert "Command not found" in result.stderr
    
    def test_detect_main_branch_current_main(self):
        """Test main branch detection when already on main."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n")
            
            branch = workspace.detect_main_branch()
            
            assert branch == "main"
            mock_run.assert_called_once_with(['branch', '--show-current'])
    
    def test_detect_main_branch_current_master(self):
        """Test main branch detection when already on master."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="master\n")
            
            branch = workspace.detect_main_branch()
            
            assert branch == "master"
    
    def test_detect_main_branch_exists(self):
        """Test main branch detection when main branch exists."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['branch', '--show-current']:
                return Mock(returncode=0, stdout="feature-branch\n")
            elif cmd == ['show-ref', '--verify', '--quiet', 'refs/heads/main']:
                return Mock(returncode=0)
            return Mock(returncode=1)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect):
            branch = workspace.detect_main_branch()
            
            assert branch == "main"
    
    def test_detect_main_branch_master_fallback(self):
        """Test main branch detection falls back to master."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['branch', '--show-current']:
                return Mock(returncode=0, stdout="feature-branch\n")
            elif cmd == ['show-ref', '--verify', '--quiet', 'refs/heads/main']:
                return Mock(returncode=1)  # main doesn't exist
            elif cmd == ['show-ref', '--verify', '--quiet', 'refs/heads/master']:
                return Mock(returncode=0)  # master exists
            return Mock(returncode=1)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect):
            branch = workspace.detect_main_branch()
            
            assert branch == "master"
    
    def test_detect_main_branch_default(self):
        """Test main branch detection defaults to main."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['branch', '--show-current']:
                return Mock(returncode=0, stdout="feature-branch\n")
            # Both main and master don't exist
            return Mock(returncode=1)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect):
            branch = workspace.detect_main_branch()
            
            assert branch == "main"
    
    def test_get_current_branch_success(self):
        """Test getting current branch successfully."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="feature-branch\n")
            
            branch = workspace.get_current_branch()
            
            assert branch == "feature-branch"
            mock_run.assert_called_once_with(['branch', '--show-current'])
    
    def test_get_current_branch_failure(self):
        """Test getting current branch when command fails."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")
            
            branch = workspace.get_current_branch()
            
            assert branch is None
    
    def test_is_working_directory_clean_true(self):
        """Test working directory clean check when clean."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            
            is_clean = workspace.is_working_directory_clean()
            
            assert is_clean is True
            mock_run.assert_called_once_with(['status', '--porcelain'])
    
    def test_is_working_directory_clean_false(self):
        """Test working directory clean check when dirty."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="M file.txt\n")
            
            is_clean = workspace.is_working_directory_clean()
            
            assert is_clean is False
    
    def test_is_working_directory_clean_command_failure(self):
        """Test working directory clean check when git command fails."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")
            
            is_clean = workspace.is_working_directory_clean()
            
            assert is_clean is False
    
    def test_workspace_hygiene_force(self):
        """Test workspace hygiene with force flag."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['reset', '--hard', 'HEAD']:
                return Mock(returncode=0)
            elif cmd == ['clean', '-fd']:
                return Mock(returncode=0)
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect):
            result = workspace.workspace_hygiene(force=True)
            
            assert result is True
    
    def test_workspace_hygiene_interactive_confirm(self):
        """Test workspace hygiene with interactive confirmation."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        workspace.interactive_mode = True
        
        def side_effect(cmd):
            if cmd == ['reset', '--hard', 'HEAD']:
                return Mock(returncode=0)
            elif cmd == ['clean', '-fd']:
                return Mock(returncode=0)
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect), \
             patch.object(workspace, '_confirm_cleanup', return_value=True):
            
            result = workspace.workspace_hygiene()
            
            assert result is True
    
    def test_workspace_hygiene_interactive_decline(self):
        """Test workspace hygiene when user declines cleanup."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        workspace.interactive_mode = True
        
        with patch.object(workspace, '_confirm_cleanup', return_value=False), \
             patch.object(workspace, 'is_working_directory_clean', return_value=False):
            result = workspace.workspace_hygiene()
            
            assert result is False
    
    def test_workspace_hygiene_reset_failure(self):
        """Test workspace hygiene when reset fails."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['reset', '--hard', 'HEAD']:
                return Mock(returncode=1)  # Failed
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect):
            result = workspace.workspace_hygiene(force=True)
            
            assert result is False
    
    def test_workspace_hygiene_clean_failure(self):
        """Test workspace hygiene when clean fails."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['reset', '--hard', 'HEAD']:
                return Mock(returncode=0)
            elif cmd == ['clean', '-fd']:
                return Mock(returncode=1)  # Failed
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect):
            result = workspace.workspace_hygiene(force=True)
            
            assert result is False
    
    def test_confirm_cleanup_yes(self):
        """Test user confirmation for cleanup - yes."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch('builtins.input', return_value='1'), \
             patch('builtins.print'):
            result = workspace._confirm_cleanup()
            
            assert result is True
    
    def test_confirm_cleanup_no(self):
        """Test user confirmation for cleanup - no."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch('builtins.input', return_value='3'), \
             patch('builtins.print'):
            result = workspace._confirm_cleanup()
            
            assert result is False
    
    def test_confirm_cleanup_eof(self):
        """Test user confirmation for cleanup - EOF."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch('builtins.input', side_effect=EOFError()):
            result = workspace._confirm_cleanup()
            
            assert result is False
    
    def test_confirm_cleanup_keyboard_interrupt(self):
        """Test user confirmation for cleanup - KeyboardInterrupt."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch('builtins.input', side_effect=KeyboardInterrupt()):
            result = workspace._confirm_cleanup()
            
            assert result is False
    
    def test_create_timestamped_branch_success(self):
        """Test successful timestamped branch creation."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['checkout', 'main']:
                return Mock(returncode=0)
            elif cmd == ['pull', 'origin', 'main']:
                return Mock(returncode=0)
            elif cmd[0] == 'checkout' and cmd[1] == '-b':
                return Mock(returncode=0)
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect), \
             patch.object(workspace, 'detect_main_branch', return_value='main'), \
             patch('time.time', return_value=1234567890):
            
            success, branch_name = workspace.create_timestamped_branch(123)
            
            assert success is True
            assert branch_name == "issue-123-1234567890"
    
    def test_create_timestamped_branch_checkout_base_failure(self):
        """Test timestamped branch creation when base checkout fails."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['checkout', 'main']:
                return Mock(returncode=1, stderr="checkout failed")
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect), \
             patch.object(workspace, 'detect_main_branch', return_value='main'):
            
            success, message = workspace.create_timestamped_branch(123)
            
            assert success is False
            assert "Failed to checkout main" in message
    
    def test_create_timestamped_branch_create_failure(self):
        """Test timestamped branch creation when branch creation fails."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['checkout', 'main']:
                return Mock(returncode=0)
            elif cmd == ['pull', 'origin', 'main']:
                return Mock(returncode=0)
            elif cmd[0] == 'checkout' and cmd[1] == '-b':
                return Mock(returncode=1, stderr="branch exists")
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect), \
             patch.object(workspace, 'detect_main_branch', return_value='main'), \
             patch('time.time', return_value=1234567890):
            
            success, message = workspace.create_timestamped_branch(123)
            
            assert success is False
            assert "Failed to create branch" in message
    
    def test_create_timestamped_branch_pull_failure_continues(self):
        """Test timestamped branch creation continues when pull fails."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['checkout', 'main']:
                return Mock(returncode=0)
            elif cmd == ['pull', 'origin', 'main']:
                return Mock(returncode=1)  # Pull fails but continues
            elif cmd[0] == 'checkout' and cmd[1] == '-b':
                return Mock(returncode=0)
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect), \
             patch.object(workspace, 'detect_main_branch', return_value='main'), \
             patch('time.time', return_value=1234567890):
            
            success, branch_name = workspace.create_timestamped_branch(123)
            
            assert success is True
            assert branch_name == "issue-123-1234567890"
    
    def test_commit_changes_success(self):
        """Test successful commit creation."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['add', '.']:
                return Mock(returncode=0)
            elif cmd == ['diff', '--cached', '--quiet']:
                return Mock(returncode=1)  # Changes to commit
            elif cmd[0] == 'commit':
                return Mock(returncode=0)
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect):
            result = workspace.commit_changes("test message", "test-branch")
            
            assert result is True
    
    def test_commit_changes_no_changes(self):
        """Test commit when no changes to commit."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['add', '.']:
                return Mock(returncode=0)
            elif cmd == ['diff', '--cached', '--quiet']:
                return Mock(returncode=0)  # No changes to commit
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect):
            result = workspace.commit_changes("test message", "test-branch")
            
            assert result is True  # No changes is still success
    
    def test_commit_changes_add_failure(self):
        """Test commit when add fails."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['add', '.']:
                return Mock(returncode=1)
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect):
            result = workspace.commit_changes("test message", "test-branch")
            
            assert result is False
    
    def test_commit_changes_commit_failure(self):
        """Test commit when commit fails."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['add', '.']:
                return Mock(returncode=0)
            elif cmd == ['diff', '--cached', '--quiet']:
                return Mock(returncode=1)  # Changes to commit
            elif cmd[0] == 'commit':
                return Mock(returncode=1)  # Commit fails
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect):
            result = workspace.commit_changes("test message", "test-branch")
            
            assert result is False
    
    def test_push_branch_success(self):
        """Test successful branch push."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = workspace.push_branch("test-branch")
            
            assert result is True
            mock_run.assert_called_once_with(['push', '-u', 'origin', 'test-branch'])
    
    def test_push_branch_failure(self):
        """Test branch push failure."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            result = workspace.push_branch("test-branch")
            
            assert result is False
    
    def test_has_changes_to_commit_unstaged(self):
        """Test change detection with unstaged changes."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['status', '--porcelain']:
                return Mock(returncode=0, stdout="M  file.py", stderr="")
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect), \
             patch('builtins.print'):  # Suppress debug prints
            
            has_changes = workspace.has_changes_to_commit()
            
            assert has_changes is True
    
    def test_has_changes_to_commit_staged(self):
        """Test change detection with staged changes."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['status', '--porcelain']:
                return Mock(returncode=0, stdout="A  new_file.py", stderr="")
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect), \
             patch('builtins.print'):  # Suppress debug prints
            
            has_changes = workspace.has_changes_to_commit()
            
            assert has_changes is True
    
    def test_has_changes_to_commit_untracked(self):
        """Test change detection with untracked files."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['status', '--porcelain']:
                return Mock(returncode=0, stdout="?? untracked.txt", stderr="")
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect), \
             patch('builtins.print'):  # Suppress debug prints
            
            has_changes = workspace.has_changes_to_commit()
            
            assert has_changes is True
    
    def test_has_changes_to_commit_none(self):
        """Test change detection with no changes."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['status', '--porcelain']:
                return Mock(returncode=0, stdout="", stderr="")  # Clean workspace
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect), \
             patch('builtins.print'):  # Suppress debug prints
            
            has_changes = workspace.has_changes_to_commit()
            
            assert has_changes is False
    
    def test_get_git_diff_with_base_branch(self):
        """Test getting git diff with base branch."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="diff content")
            
            diff = workspace.get_git_diff("main")
            
            assert diff == "diff content"
            mock_run.assert_called_once_with(['diff', 'main...HEAD'])
    
    def test_get_git_diff_no_base_branch(self):
        """Test getting git diff without base branch."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        def side_effect(cmd):
            if cmd == ['diff', 'HEAD']:
                return Mock(returncode=0, stdout="unstaged diff")
            elif cmd == ['diff', '--cached']:
                return Mock(returncode=0, stdout="staged diff")
            return Mock(returncode=0, stdout="")
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect):
            diff = workspace.get_git_diff()
            
            assert diff == "unstaged diffstaged diff"
    
    def test_get_git_diff_failure(self):
        """Test getting git diff when command fails."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")
            
            diff = workspace.get_git_diff("main")
            
            assert diff == ""
    
    def test_get_commit_log_success(self):
        """Test getting commit log successfully."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="abc123 Commit\ndef456 Another")
            
            log = workspace.get_commit_log("main", 5)
            
            assert log == "abc123 Commit\ndef456 Another"
            mock_run.assert_called_once_with([
                'log', 'main..HEAD',
                '--oneline', '--max-count=5'
            ])
    
    def test_get_commit_log_failure(self):
        """Test getting commit log when command fails."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")
            
            log = workspace.get_commit_log("main")
            
            assert log == ""
    
    def test_switch_to_branch_success(self):
        """Test successful branch switch."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = workspace.switch_to_branch("feature-branch")
            
            assert result is True
            mock_run.assert_called_once_with(['checkout', 'feature-branch'])
    
    def test_switch_to_branch_failure(self):
        """Test branch switch failure."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            result = workspace.switch_to_branch("feature-branch")
            
            assert result is False
    
    def test_branch_exists_true(self):
        """Test branch existence check when branch exists."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            exists = workspace.branch_exists("feature-branch")
            
            assert exists is True
            mock_run.assert_called_once_with(['show-ref', '--verify', '--quiet', 'refs/heads/feature-branch'])
    
    def test_branch_exists_false(self):
        """Test branch existence check when branch doesn't exist."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            exists = workspace.branch_exists("nonexistent-branch")
            
            assert exists is False
    
    def test_delete_branch_success(self):
        """Test successful branch deletion."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = workspace.delete_branch("feature-branch")
            
            assert result is True
            mock_run.assert_called_once_with(['branch', '-d', 'feature-branch'])
    
    def test_delete_branch_force(self):
        """Test force branch deletion."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = workspace.delete_branch("feature-branch", force=True)
            
            assert result is True
            mock_run.assert_called_once_with(['branch', '-D', 'feature-branch'])
    
    def test_delete_branch_failure(self):
        """Test branch deletion failure."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            result = workspace.delete_branch("feature-branch")
            
            assert result is False
    
    def test_get_remote_url_success(self):
        """Test getting remote URL successfully."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="https://github.com/user/repo.git\n")
            
            url = workspace.get_remote_url()
            
            assert url == "https://github.com/user/repo.git"
            mock_run.assert_called_once_with(['config', '--get', 'remote.origin.url'])
    
    def test_get_remote_url_failure(self):
        """Test getting remote URL when command fails."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")
            
            url = workspace.get_remote_url()
            
            assert url is None
    
    def test_is_branch_pushed_true(self):
        """Test checking if branch is pushed when it exists on remote."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            is_pushed = workspace.is_branch_pushed("feature-branch")
            
            assert is_pushed is True
            mock_run.assert_called_once_with(['show-ref', '--verify', '--quiet', 'refs/remotes/origin/feature-branch'])
    
    def test_is_branch_pushed_false(self):
        """Test checking if branch is pushed when it doesn't exist on remote."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            is_pushed = workspace.is_branch_pushed("feature-branch")
            
            assert is_pushed is False


class TestEnvironmentValidator:
    """Test environment validation for git operations."""
    
    def test_validate_git_repository_success(self):
        """Test successful git repository validation."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=".git\n", stderr="")
            
            valid, message = validator.validate_git_repository()
            
            assert valid is True
            assert "Valid git repository" in message
            mock_run.assert_called_once_with(
                ['git', 'rev-parse', '--git-dir'],
                cwd=".",
                capture_output=True,
                text=True,
                check=False
            )
    
    def test_validate_git_repository_failure(self):
        """Test failed git repository validation."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="not a git repository")
            
            valid, message = validator.validate_git_repository()
            
            assert valid is False
            assert "Not a git repository" in message
    
    def test_validate_git_repository_file_not_found(self):
        """Test git repository validation when git not found."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            valid, message = validator.validate_git_repository()
            
            assert valid is False
            assert "Git not found" in message
    
    def test_validate_github_remote_success(self):
        """Test successful GitHub remote validation."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="https://github.com/user/repo.git\n", stderr="")
            
            valid, message = validator.validate_github_remote()
            
            assert valid is True
            assert "GitHub remote" in message
            assert "https://github.com/user/repo.git" in message
    
    def test_validate_github_remote_no_github(self):
        """Test GitHub remote validation with non-GitHub remote."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="https://gitlab.com/user/repo.git\n", stderr="")
            
            valid, message = validator.validate_github_remote()
            
            assert valid is False
            assert "No GitHub remote found" in message
    
    def test_check_claude_md_exists(self, tmp_path):
        """Test CLAUDE.md file existence check when file exists."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        # Create CLAUDE.md file
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Test CLAUDE.md\nProject instructions")
        
        valid, message = validator.check_claude_md(str(tmp_path))
        
        assert valid is True
        assert "CLAUDE.md found" in message
    
    def test_check_claude_md_missing(self, tmp_path):
        """Test CLAUDE.md file existence check when file missing."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        valid, message = validator.check_claude_md(str(tmp_path))
        
        assert valid is False
        assert "CLAUDE.md not found" in message
    
    def test_check_tool_availability_success(self):
        """Test successful tool availability check."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="/usr/bin/git\n", stderr="")
            
            available, message = validator.check_tool_availability('git')
            
            assert available is True
            assert "git found at /usr/bin/git" in message
    
    def test_check_tool_availability_failure(self):
        """Test failed tool availability check."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="")
            
            available, message = validator.check_tool_availability('nonexistent')
            
            assert available is False
            assert "nonexistent not found" in message
    
    def test_validate_all_dependencies_success(self, tmp_path):
        """Test comprehensive dependency validation when all pass."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        # Create CLAUDE.md file
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Test CLAUDE.md")
        
        with patch.object(validator, 'validate_git_repository', return_value=(True, "Valid git repository")), \
             patch.object(validator, 'validate_github_remote', return_value=(True, "GitHub remote found")), \
             patch.object(validator, 'check_tool_availability') as mock_tool:
            
            # Mock all tools as available
            mock_tool.return_value = (True, "tool found")
            
            results = validator.validate_all_dependencies(str(tmp_path))
            
            assert results['valid'] is True
            assert len(results['errors']) == 0
            assert len(results['tool_status']) > 0
    
    def test_validate_all_dependencies_failures(self, tmp_path):
        """Test comprehensive dependency validation when some fail."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        with patch.object(validator, 'validate_git_repository', return_value=(False, "Not a git repository")), \
             patch.object(validator, 'validate_github_remote', return_value=(False, "No GitHub remote")), \
             patch.object(validator, 'check_claude_md', return_value=(False, "CLAUDE.md not found")), \
             patch.object(validator, 'check_tool_availability', return_value=(False, "tool not found")):
            
            results = validator.validate_all_dependencies(str(tmp_path))
            
            assert results['valid'] is False
            assert len(results['errors']) > 0
            assert "Git repository check failed" in results['errors'][0]
    
    def test_get_missing_dependencies(self):
        """Test extraction of missing required dependencies."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        validation_results = {
            'tool_status': {
                'git': {'available': True, 'required': True},
                'gh': {'available': False, 'required': True},
                'claude': {'available': False, 'required': False}
            }
        }
        
        missing = validator.get_missing_dependencies(validation_results)
        
        assert 'gh' in missing
        assert 'git' not in missing
        assert 'claude' not in missing  # Not required
    
    def test_format_validation_report_success(self):
        """Test formatting of successful validation report."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'tool_status': {
                'git': {'available': True, 'status': 'found', 'required': True}
            }
        }
        
        report = validator.format_validation_report(validation_results)
        
        assert "✅ Environment validation passed" in report
        assert "✅ git (required): found" in report
    
    def test_format_validation_report_failure(self):
        """Test formatting of failed validation report."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        validator = EnvironmentValidator(mock_git_service)
        
        validation_results = {
            'valid': False,
            'errors': ['Git repository check failed'],
            'warnings': ['Warning: claude not found'],
            'tool_status': {
                'git': {'available': False, 'status': 'not found', 'required': True}
            }
        }
        
        report = validator.format_validation_report(validation_results)
        
        assert "❌ Environment validation failed" in report
        assert "ERROR: Git repository check failed" in report
        assert "WARNING: Warning: claude not found" in report
        assert "❌ git (required): not found" in report
