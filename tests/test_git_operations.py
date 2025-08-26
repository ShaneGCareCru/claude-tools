"""Tests for claude-tasker git operations and workspace management."""
import pytest
import subprocess
import os
import time
from pathlib import Path
from unittest.mock import patch, Mock, call, MagicMock
from src.claude_tasker.workspace_manager import WorkspaceManager
from src.claude_tasker.services.command_executor import CommandExecutor, CommandResult, CommandErrorType
from src.claude_tasker.services.git_service import GitService


def create_mock_git_service_with_executor():
    """Helper to create properly structured GitService mock with executor."""
    mock_executor = Mock(spec=CommandExecutor)
    mock_git_service = Mock(spec=GitService)
    mock_git_service.executor = mock_executor
    
    # Configure mock executor to return proper CommandResult objects
    result = CommandResult(
        returncode=0,
        stdout="",
        stderr="",
        command="test command",
        execution_time=1.0,
        error_type=CommandErrorType.SUCCESS,
        attempts=1,
        success=True
    )
    mock_executor.execute.return_value = result
    return mock_executor, mock_git_service


class TestWorkspaceManager:
    """Test WorkspaceManager class directly."""
    
    def test_init(self):
        """Test WorkspaceManager initialization."""
        mock_executor, mock_git_service = create_mock_git_service_with_executor()
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        assert workspace.cwd == Path(".").resolve()
        assert hasattr(workspace, 'interactive_mode')
    
    def test_init_with_custom_cwd(self, tmp_path):
        """Test WorkspaceManager initialization with custom directory."""
        mock_executor, mock_git_service = create_mock_git_service_with_executor()
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
            mock_executor, mock_git_service = create_mock_git_service_with_executor()
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
            mock_executor, mock_git_service = create_mock_git_service_with_executor()
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
            mock_executor, mock_git_service = create_mock_git_service_with_executor()
            workspace = WorkspaceManager(
                command_executor=mock_executor,
                git_service=mock_git_service,
                gh_service=Mock()
            )
            assert workspace.interactive_mode is False
    
    def test_run_git_command_success(self):
        """Test successful git command execution."""
        mock_executor, mock_git_service = create_mock_git_service_with_executor()
        
        # Configure mock to return success result
        result = CommandResult(
            returncode=0,
            stdout="output",
            stderr="",
            command=["git", "status"],
            execution_time=1.0,
            error_type=CommandErrorType.SUCCESS,
            attempts=1,
            success=True
        )
        mock_executor.execute.return_value = result
        
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        result = workspace._run_git_command(['status'])
        
        assert result.returncode == 0
        assert result.stdout == "output"
    
    def test_run_git_command_failure(self):
        """Test git command execution failure."""
        mock_executor, mock_git_service = create_mock_git_service_with_executor()
        
        # Configure mock to return failure result
        result = CommandResult(
            returncode=1,
            stdout="",
            stderr="error",
            command=["git", "invalid-command"],
            execution_time=1.0,
            error_type=CommandErrorType.GENERAL_ERROR,
            attempts=1,
            success=False
        )
        mock_executor.execute.return_value = result
        
        workspace = WorkspaceManager(
            command_executor=mock_executor,
            git_service=mock_git_service,
            gh_service=Mock()
        )
        
        result = workspace._run_git_command(['invalid-command'])
        
        assert result.returncode == 1
        assert result.stderr == "error"
    
    def test_detect_main_branch_current_main(self):
        """Test main branch detection when already on main."""
        mock_executor, mock_git_service = create_mock_git_service_with_executor()
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
    
    def test_get_current_branch_success(self):
        """Test getting current branch successfully."""
        mock_executor, mock_git_service = create_mock_git_service_with_executor()
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
    
    def test_workspace_hygiene_force(self):
        """Test workspace hygiene with force flag."""
        mock_executor, mock_git_service = create_mock_git_service_with_executor()
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
    
    def test_commit_changes_success(self):
        """Test successful commit creation."""
        mock_executor, mock_git_service = create_mock_git_service_with_executor()
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


