"""Tests for claude-tasker workspace management and git workflow functionality."""
import pytest
import subprocess
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, call

from src.claude_tasker.workspace_manager import WorkspaceManager


class TestWorkspaceManager:
    """Test workspace hygiene and git management functionality."""
    
    def test_workspace_hygiene_automatic_cleanup(self):
        """Test automatic workspace cleanup with git reset and clean."""
        workspace = WorkspaceManager()
        
        # Mock auto-cleanup environment variable
        with patch.dict(os.environ, {'CLAUDE_TASKER_AUTO_CLEANUP': '1'}), \
             patch.object(workspace, '_run_git_command') as mock_git:
            
            # Mock successful git commands
            def git_side_effect(cmd):
                if cmd == ['reset', '--hard', 'HEAD']:
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
                call(['reset', '--hard', 'HEAD']),
                call(['clean', '-fd'])
            ]
            mock_git.assert_has_calls(expected_calls)
    
    def test_interactive_cleanup_confirmation(self):
        """Test interactive cleanup confirmation when no auto-cleanup."""
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_git, \
             patch('builtins.input', return_value='y'), \
             patch.object(workspace, '_is_interactive', return_value=True):
            
            # Mock successful git commands
            def git_side_effect(cmd):
                if cmd == ['reset', '--hard', 'HEAD']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "HEAD is now at abc123", "")
                elif cmd == ['clean', '-fd']:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "Removing untracked files", "")
                else:
                    return subprocess.CompletedProcess(['git'] + cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            # Test interactive workspace hygiene
            result = workspace.workspace_hygiene(force=False)
            
            # Should succeed after user confirmation
            assert result is True
            
            # Verify git commands were called after confirmation
            expected_calls = [
                call(['reset', '--hard', 'HEAD']),
                call(['clean', '-fd'])
            ]
            mock_git.assert_has_calls(expected_calls)
    
    def test_branch_detection_main_vs_master(self):
        """Test detection of main vs master branch."""
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
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
    
    def test_workspace_status_detection(self):
        """Test detection of workspace changes requiring cleanup."""
        workspace = WorkspaceManager()
        
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
        workspace = WorkspaceManager()
        
        with patch.object(workspace, '_run_git_command') as mock_git, \
             patch.object(workspace, '_is_interactive', return_value=False):
            
            # Mock git commands
            def git_side_effect(cmd):
                if cmd == ['reset', '--hard', 'HEAD']:
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
                call(['reset', '--hard', 'HEAD']),
                call(['clean', '-fd'])
            ]
            mock_git.assert_has_calls(expected_calls)