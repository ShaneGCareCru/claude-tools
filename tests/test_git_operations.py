"""Tests for claude-tasker git operations and workspace management."""
import pytest
import subprocess
import os
import time
from pathlib import Path
from unittest.mock import patch, Mock, call, MagicMock
from src.claude_tasker.workspace_manager import WorkspaceManager


class TestWorkspaceManager:
    """Test WorkspaceManager class directly."""
    
    def test_init(self):
        """Test WorkspaceManager initialization."""
        workspace = WorkspaceManager()
        assert workspace.cwd == Path(".").resolve()
        assert hasattr(workspace, 'interactive_mode')
    
    def test_init_with_custom_cwd(self, tmp_path):
        """Test WorkspaceManager initialization with custom directory."""
        workspace = WorkspaceManager(str(tmp_path))
        assert workspace.cwd == tmp_path.resolve()
    
    def test_is_interactive_tty(self):
        """Test interactive mode detection with TTY."""
        with patch('os.isatty', return_value=True), \
             patch.dict('os.environ', {}, clear=True):
            workspace = WorkspaceManager()
            assert workspace.interactive_mode is True
    
    def test_is_interactive_ci(self):
        """Test interactive mode detection in CI environment."""
        with patch('os.isatty', return_value=True), \
             patch.dict('os.environ', {'CI': 'true'}):
            workspace = WorkspaceManager()
            assert workspace.interactive_mode is False
    
    def test_is_interactive_github_actions(self):
        """Test interactive mode detection in GitHub Actions."""
        with patch('os.isatty', return_value=True), \
             patch.dict('os.environ', {'GITHUB_ACTIONS': 'true'}):
            workspace = WorkspaceManager()
            assert workspace.interactive_mode is False
    
    def test_run_git_command_success(self):
        """Test successful git command execution."""
        workspace = WorkspaceManager()
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
        workspace = WorkspaceManager()
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="error")
            
            result = workspace._run_git_command(['invalid-command'])
            
            assert result.returncode == 1
            assert result.stderr == "error"
    
    def test_run_git_command_exception(self):
        """Test git command execution with exception."""
        workspace = WorkspaceManager()
        with patch('subprocess.run', side_effect=Exception("Command not found")):
            result = workspace._run_git_command(['status'])
            
            assert result.returncode == 1
            assert "Command not found" in result.stderr
    
    def test_detect_main_branch_current_main(self):
        """Test main branch detection when already on main."""
        workspace = WorkspaceManager()
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n")
            
            branch = workspace.detect_main_branch()
            
            assert branch == "main"
            mock_run.assert_called_once_with(['branch', '--show-current'])
    
    def test_detect_main_branch_current_master(self):
        """Test main branch detection when already on master."""
        workspace = WorkspaceManager()
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="master\n")
            
            branch = workspace.detect_main_branch()
            
            assert branch == "master"
    
    def test_detect_main_branch_exists(self):
        """Test main branch detection when main branch exists."""
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="feature-branch\n")
            
            branch = workspace.get_current_branch()
            
            assert branch == "feature-branch"
            mock_run.assert_called_once_with(['branch', '--show-current'])
    
    def test_get_current_branch_failure(self):
        """Test getting current branch when command fails."""
        workspace = WorkspaceManager()
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")
            
            branch = workspace.get_current_branch()
            
            assert branch is None
    
    def test_is_working_directory_clean_true(self):
        """Test working directory clean check when clean."""
        workspace = WorkspaceManager()
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            
            is_clean = workspace.is_working_directory_clean()
            
            assert is_clean is True
            mock_run.assert_called_once_with(['status', '--porcelain'])
    
    def test_is_working_directory_clean_false(self):
        """Test working directory clean check when dirty."""
        workspace = WorkspaceManager()
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="M file.txt\n")
            
            is_clean = workspace.is_working_directory_clean()
            
            assert is_clean is False
    
    def test_is_working_directory_clean_command_failure(self):
        """Test working directory clean check when git command fails."""
        workspace = WorkspaceManager()
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")
            
            is_clean = workspace.is_working_directory_clean()
            
            assert is_clean is False
    
    def test_workspace_hygiene_force(self):
        """Test workspace hygiene with force flag."""
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
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
        workspace = WorkspaceManager()
        workspace.interactive_mode = True
        
        with patch.object(workspace, '_confirm_cleanup', return_value=False):
            result = workspace.workspace_hygiene()
            
            assert result is False
    
    def test_workspace_hygiene_reset_failure(self):
        """Test workspace hygiene when reset fails."""
        workspace = WorkspaceManager()
        
        def side_effect(cmd):
            if cmd == ['reset', '--hard', 'HEAD']:
                return Mock(returncode=1)  # Failed
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect):
            result = workspace.workspace_hygiene(force=True)
            
            assert result is False
    
    def test_workspace_hygiene_clean_failure(self):
        """Test workspace hygiene when clean fails."""
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
        with patch('builtins.input', return_value='y'):
            result = workspace._confirm_cleanup()
            
            assert result is True
    
    def test_confirm_cleanup_no(self):
        """Test user confirmation for cleanup - no."""
        workspace = WorkspaceManager()
        
        with patch('builtins.input', return_value='n'):
            result = workspace._confirm_cleanup()
            
            assert result is False
    
    def test_confirm_cleanup_eof(self):
        """Test user confirmation for cleanup - EOF."""
        workspace = WorkspaceManager()
        
        with patch('builtins.input', side_effect=EOFError()):
            result = workspace._confirm_cleanup()
            
            assert result is False
    
    def test_confirm_cleanup_keyboard_interrupt(self):
        """Test user confirmation for cleanup - KeyboardInterrupt."""
        workspace = WorkspaceManager()
        
        with patch('builtins.input', side_effect=KeyboardInterrupt()):
            result = workspace._confirm_cleanup()
            
            assert result is False
    
    def test_create_timestamped_branch_success(self):
        """Test successful timestamped branch creation."""
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
        def side_effect(cmd):
            if cmd == ['add', '.']:
                return Mock(returncode=1)
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect):
            result = workspace.commit_changes("test message", "test-branch")
            
            assert result is False
    
    def test_commit_changes_commit_failure(self):
        """Test commit when commit fails."""
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = workspace.push_branch("test-branch")
            
            assert result is True
            mock_run.assert_called_once_with(['push', '-u', 'origin', 'test-branch'])
    
    def test_push_branch_failure(self):
        """Test branch push failure."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            result = workspace.push_branch("test-branch")
            
            assert result is False
    
    def test_has_changes_to_commit_unstaged(self):
        """Test change detection with unstaged changes."""
        workspace = WorkspaceManager()
        
        def side_effect(cmd):
            if cmd == ['diff', '--quiet']:
                return Mock(returncode=1)  # Unstaged changes
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect), \
             patch('builtins.print'):  # Suppress debug prints
            
            has_changes = workspace.has_changes_to_commit()
            
            assert has_changes is True
    
    def test_has_changes_to_commit_staged(self):
        """Test change detection with staged changes."""
        workspace = WorkspaceManager()
        
        def side_effect(cmd):
            if cmd == ['diff', '--quiet']:
                return Mock(returncode=0)  # No unstaged changes
            elif cmd == ['diff', '--cached', '--quiet']:
                return Mock(returncode=1)  # Staged changes
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect), \
             patch('builtins.print'):  # Suppress debug prints
            
            has_changes = workspace.has_changes_to_commit()
            
            assert has_changes is True
    
    def test_has_changes_to_commit_untracked(self):
        """Test change detection with untracked files."""
        workspace = WorkspaceManager()
        
        def side_effect(cmd):
            if cmd == ['diff', '--quiet']:
                return Mock(returncode=0)  # No unstaged changes
            elif cmd == ['diff', '--cached', '--quiet']:
                return Mock(returncode=0)  # No staged changes
            elif cmd == ['ls-files', '--others', '--exclude-standard']:
                return Mock(returncode=0, stdout="untracked.txt\n")  # Untracked files
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect), \
             patch('builtins.print'):  # Suppress debug prints
            
            has_changes = workspace.has_changes_to_commit()
            
            assert has_changes is True
    
    def test_has_changes_to_commit_none(self):
        """Test change detection with no changes."""
        workspace = WorkspaceManager()
        
        def side_effect(cmd):
            if cmd == ['diff', '--quiet']:
                return Mock(returncode=0)  # No unstaged changes
            elif cmd == ['diff', '--cached', '--quiet']:
                return Mock(returncode=0)  # No staged changes
            elif cmd == ['ls-files', '--others', '--exclude-standard']:
                return Mock(returncode=0, stdout="")  # No untracked files
            return Mock(returncode=0)
        
        with patch.object(workspace, '_run_git_command', side_effect=side_effect), \
             patch('builtins.print'):  # Suppress debug prints
            
            has_changes = workspace.has_changes_to_commit()
            
            assert has_changes is False
    
    def test_get_git_diff_with_base_branch(self):
        """Test getting git diff with base branch."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="diff content")
            
            diff = workspace.get_git_diff("main")
            
            assert diff == "diff content"
            mock_run.assert_called_once_with(['diff', 'main...HEAD'])
    
    def test_get_git_diff_no_base_branch(self):
        """Test getting git diff without base branch."""
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")
            
            diff = workspace.get_git_diff("main")
            
            assert diff == ""
    
    def test_get_commit_log_success(self):
        """Test getting commit log successfully."""
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")
            
            log = workspace.get_commit_log("main")
            
            assert log == ""
    
    def test_switch_to_branch_success(self):
        """Test successful branch switch."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = workspace.switch_to_branch("feature-branch")
            
            assert result is True
            mock_run.assert_called_once_with(['checkout', 'feature-branch'])
    
    def test_switch_to_branch_failure(self):
        """Test branch switch failure."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            result = workspace.switch_to_branch("feature-branch")
            
            assert result is False
    
    def test_branch_exists_true(self):
        """Test branch existence check when branch exists."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            exists = workspace.branch_exists("feature-branch")
            
            assert exists is True
            mock_run.assert_called_once_with(['show-ref', '--verify', '--quiet', 'refs/heads/feature-branch'])
    
    def test_branch_exists_false(self):
        """Test branch existence check when branch doesn't exist."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            exists = workspace.branch_exists("nonexistent-branch")
            
            assert exists is False
    
    def test_delete_branch_success(self):
        """Test successful branch deletion."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = workspace.delete_branch("feature-branch")
            
            assert result is True
            mock_run.assert_called_once_with(['branch', '-d', 'feature-branch'])
    
    def test_delete_branch_force(self):
        """Test force branch deletion."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = workspace.delete_branch("feature-branch", force=True)
            
            assert result is True
            mock_run.assert_called_once_with(['branch', '-D', 'feature-branch'])
    
    def test_delete_branch_failure(self):
        """Test branch deletion failure."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            result = workspace.delete_branch("feature-branch")
            
            assert result is False
    
    def test_get_remote_url_success(self):
        """Test getting remote URL successfully."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="https://github.com/user/repo.git\n")
            
            url = workspace.get_remote_url()
            
            assert url == "https://github.com/user/repo.git"
            mock_run.assert_called_once_with(['config', '--get', 'remote.origin.url'])
    
    def test_get_remote_url_failure(self):
        """Test getting remote URL when command fails."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")
            
            url = workspace.get_remote_url()
            
            assert url is None
    
    def test_is_branch_pushed_true(self):
        """Test checking if branch is pushed when it exists on remote."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            is_pushed = workspace.is_branch_pushed("feature-branch")
            
            assert is_pushed is True
            mock_run.assert_called_once_with(['show-ref', '--verify', '--quiet', 'refs/remotes/origin/feature-branch'])
    
    def test_is_branch_pushed_false(self):
        """Test checking if branch is pushed when it doesn't exist on remote."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            is_pushed = workspace.is_branch_pushed("feature-branch")
            
            assert is_pushed is False


class TestGitOperations:
    """Test git operations and environment validation."""
    
    def test_validate_git_repository(self):
        """Test validation that we're in a git repository."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        validator = EnvironmentValidator()
        
        with patch('subprocess.run') as mock_run:
            # Test successful git repository validation
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
            
            # Test failed git repository validation
            mock_run.reset_mock()
            mock_run.return_value = Mock(returncode=1, stderr="not a git repository")
            
            valid, message = validator.validate_git_repository()
            
            assert valid is False
            assert "Not a git repository" in message
    
    def test_require_claude_md_file(self, tmp_path):
        """Test that CLAUDE.md file is required."""
        from src.claude_tasker.environment_validator import EnvironmentValidator
        
        validator = EnvironmentValidator()
        
        # Test when CLAUDE.md doesn't exist
        repo_dir = tmp_path / "no_claude_md"
        repo_dir.mkdir()
        
        valid, message = validator.validate_claude_md_file(str(repo_dir))
        
        assert valid is False
        assert "CLAUDE.md not found" in message
        
        # Test when CLAUDE.md exists
        claude_md = repo_dir / "CLAUDE.md"
        claude_md.write_text("# Test CLAUDE.md\nProject instructions")
        
        valid, message = validator.validate_claude_md_file(str(repo_dir))
        
        assert valid is True
        assert "CLAUDE.md found" in message
    
    def test_get_github_repo_info(self, claude_tasker_script, mock_git_repo):
        """Test extraction of GitHub repository information."""
        with patch('subprocess.run') as mock_run:
            def git_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = git_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should not error if repo info is extracted successfully
            assert "Could not determine repository" not in result.stderr
    
    def test_workspace_hygiene_warning(self, claude_tasker_script, mock_git_repo):
        """Test workspace hygiene warnings for uncommitted changes."""
        with patch('subprocess.run') as mock_run:
            def git_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'git status --porcelain' in cmd:
                    return Mock(returncode=0, stdout="M modified_file.txt\n?? untracked_file.txt", stderr="")
                elif 'git diff --quiet' in cmd:
                    return Mock(returncode=1, stdout="", stderr="")  # Changes present
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = git_side_effect
            
            with patch('os.chdir'), patch('builtins.input', return_value='n'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should warn about uncommitted changes
            assert result.returncode != 0 or "uncommitted changes" in result.stderr
    
    def test_auto_cleanup_environment_variable(self, claude_tasker_script, mock_git_repo):
        """Test CLAUDE_TASKER_AUTO_CLEANUP environment variable."""
        with patch('subprocess.run') as mock_run, \
             patch.dict('os.environ', {'CLAUDE_TASKER_AUTO_CLEANUP': '1'}):
            
            def git_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'git reset --hard' in cmd:
                    return Mock(returncode=0, stdout="", stderr="")
                elif 'git status --porcelain' in cmd:
                    return Mock(returncode=0, stdout="", stderr="")
                elif 'git diff --quiet' in cmd:
                    return Mock(returncode=0, stdout="", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = git_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should automatically clean without prompting
            assert "git reset --hard" in str([call.args for call in mock_run.call_args_list])
    
    def test_branch_detection_main(self, claude_tasker_script, mock_git_repo):
        """Test detection of main branch."""
        with patch('subprocess.run') as mock_run:
            def git_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git show-ref --verify --quiet refs/heads/main' in cmd:
                    return Mock(returncode=0, stdout="", stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = git_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should detect main branch correctly
            assert "main" in str([call.args for call in mock_run.call_args_list])
    
    def test_branch_detection_master(self, claude_tasker_script, mock_git_repo):
        """Test detection of master branch when main doesn't exist."""
        with patch('subprocess.run') as mock_run:
            def git_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git show-ref --verify --quiet refs/heads/main' in cmd:
                    return Mock(returncode=1, stdout="", stderr="")  # main doesn't exist
                elif 'git show-ref --verify --quiet refs/heads/master' in cmd:
                    return Mock(returncode=0, stdout="", stderr="")  # master exists
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = git_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should fall back to master branch
            assert "master" in str([call.args for call in mock_run.call_args_list])
    
    def test_current_branch_detection(self, claude_tasker_script, mock_git_repo):
        """Test detection of current branch."""
        with patch('subprocess.run') as mock_run:
            def git_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git branch --show-current' in cmd:
                    return Mock(returncode=0, stdout="feature-branch", stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = git_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should detect current branch
            assert "feature-branch" in str([call.args for call in mock_run.call_args_list])
    
    def test_git_log_commit_history(self, claude_tasker_script, mock_git_repo):
        """Test retrieval of git commit history."""
        with patch('subprocess.run') as mock_run:
            def git_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git log --oneline' in cmd:
                    return Mock(returncode=0, stdout="abc123 Test commit\ndef456 Another commit", stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = git_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should retrieve commit history
            assert "git log --oneline" in str([call.args for call in mock_run.call_args_list])
    
    def test_git_status_changes_detection(self, claude_tasker_script, mock_git_repo):
        """Test detection of git status changes."""
        with patch('subprocess.run') as mock_run:
            def git_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git status --porcelain' in cmd:
                    return Mock(returncode=0, stdout="M file1.txt\nA file2.txt\nD file3.txt", stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = git_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should detect file changes
            git_status_calls = [call for call in mock_run.call_args_list 
                              if 'git status --porcelain' in str(call.args)]
            assert len(git_status_calls) > 0