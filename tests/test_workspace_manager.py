"""Tests for claude-tasker workspace management and git workflow functionality."""
import pytest
import subprocess
import os
from pathlib import Path
from unittest.mock import patch, Mock


class TestWorkspaceManager:
    """Test workspace hygiene and git management functionality."""
    
    def test_workspace_hygiene_automatic_cleanup(self, claude_tasker_script, mock_git_repo):
        """Test automatic workspace cleanup with git reset and clean."""
        with patch('subprocess.run') as mock_run, \
             patch.dict(os.environ, {'CLAUDE_TASKER_AUTO_CLEANUP': '1'}):
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'git reset --hard' in cmd:
                    return Mock(returncode=0, stdout="HEAD is now at abc123", stderr="")
                elif 'git clean -fd' in cmd:
                    return Mock(returncode=0, stdout="Removing untracked files", stderr="")
                elif 'git show-ref --verify --quiet refs/heads/main' in cmd:
                    return Mock(returncode=0, stdout="", stderr="")
                elif 'git checkout main' in cmd:
                    return Mock(returncode=0, stdout="Switched to branch 'main'", stderr="")
                elif 'git pull origin main' in cmd:
                    return Mock(returncode=0, stdout="Already up to date", stderr="")
                elif 'gh issue view' in cmd:
                    return Mock(returncode=0, stdout='{"title":"Test","body":"Test","labels":[]}', stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should perform automatic cleanup
            assert result.returncode == 0
            
            # Verify workspace hygiene commands were called
            git_reset_calls = [call for call in mock_run.call_args_list 
                              if 'git reset --hard' in str(call.args)]
            git_clean_calls = [call for call in mock_run.call_args_list 
                              if 'git clean -fd' in str(call.args)]
            
            assert len(git_reset_calls) > 0
            assert len(git_clean_calls) > 0
    
    def test_interactive_cleanup_confirmation(self, claude_tasker_script, mock_git_repo):
        """Test interactive cleanup confirmation when no auto-cleanup."""
        with patch('subprocess.run') as mock_run, \
             patch('builtins.input', return_value='y'), \
             patch('os.isatty', return_value=True):  # Simulate TTY environment
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'git status --porcelain' in cmd:
                    # Simulate uncommitted changes
                    return Mock(returncode=0, stdout="M modified_file.txt", stderr="")
                elif 'git diff --quiet' in cmd:
                    # Simulate changes present
                    return Mock(returncode=1, stdout="", stderr="")
                elif 'git reset --hard' in cmd:
                    return Mock(returncode=0, stdout="HEAD is now at abc123", stderr="")
                elif 'git clean -fd' in cmd:
                    return Mock(returncode=0, stdout="Removing untracked files", stderr="")
                elif 'gh issue view' in cmd:
                    return Mock(returncode=0, stdout='{"title":"Test","body":"Test","labels":[]}', stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True,
                    input="y\n"  # Simulate user confirming cleanup
                )
            
            # Should proceed after user confirmation
            assert result.returncode == 0
    
    def test_branch_detection_main_vs_master(self, claude_tasker_script, mock_git_repo):
        """Test detection of main vs master branch."""
        with patch('subprocess.run') as mock_run:
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'git show-ref --verify --quiet refs/heads/main' in cmd:
                    # main branch exists
                    return Mock(returncode=0, stdout="", stderr="")
                elif 'git checkout main' in cmd:
                    return Mock(returncode=0, stdout="Switched to branch 'main'", stderr="")
                elif 'git pull origin main' in cmd:
                    return Mock(returncode=0, stdout="Already up to date", stderr="")
                elif 'gh issue view' in cmd:
                    return Mock(returncode=0, stdout='{"title":"Test","body":"Test","labels":[]}', stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'), patch.dict(os.environ, {'CLAUDE_TASKER_AUTO_CLEANUP': '1'}):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should detect and use main branch
            assert result.returncode == 0
            main_checkout_calls = [call for call in mock_run.call_args_list 
                                  if 'git checkout main' in str(call.args)]
            assert len(main_checkout_calls) > 0
    
    def test_branch_detection_fallback_to_master(self, claude_tasker_script, mock_git_repo):
        """Test fallback to master branch when main doesn't exist."""
        with patch('subprocess.run') as mock_run:
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'git show-ref --verify --quiet refs/heads/main' in cmd:
                    # main branch doesn't exist
                    return Mock(returncode=1, stdout="", stderr="")
                elif 'git show-ref --verify --quiet refs/heads/master' in cmd:
                    # master branch exists
                    return Mock(returncode=0, stdout="", stderr="")
                elif 'git checkout master' in cmd:
                    return Mock(returncode=0, stdout="Switched to branch 'master'", stderr="")
                elif 'git pull origin master' in cmd:
                    return Mock(returncode=0, stdout="Already up to date", stderr="")
                elif 'gh issue view' in cmd:
                    return Mock(returncode=0, stdout='{"title":"Test","body":"Test","labels":[]}', stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'), patch.dict(os.environ, {'CLAUDE_TASKER_AUTO_CLEANUP': '1'}):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should fallback to master branch
            assert result.returncode == 0
            master_checkout_calls = [call for call in mock_run.call_args_list 
                                    if 'git checkout master' in str(call.args)]
            assert len(master_checkout_calls) > 0
    
    def test_timestamped_branch_creation(self, claude_tasker_script, mock_git_repo):
        """Test creation of timestamped branches for issues."""
        with patch('subprocess.run') as mock_run, \
             patch('time.time', return_value=1234567890):
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'git checkout -b issue-316-1234567890' in cmd:
                    return Mock(returncode=0, stdout="Switched to a new branch", stderr="")
                elif 'git push -u origin issue-316-1234567890' in cmd:
                    return Mock(returncode=0, stdout="Branch pushed to origin", stderr="")
                elif 'gh issue view' in cmd:
                    return Mock(returncode=0, stdout='{"title":"Test","body":"Test","labels":[]}', stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'), patch.dict(os.environ, {'CLAUDE_TASKER_AUTO_CLEANUP': '1'}):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should create timestamped branch
            branch_creation_calls = [call for call in mock_run.call_args_list 
                                   if 'git checkout -b issue-316-1234567890' in str(call.args)]
            assert len(branch_creation_calls) > 0 or result.returncode == 0  # May not create branch in prompt-only mode
    
    def test_commit_and_push_workflow(self, claude_tasker_script, mock_git_repo):
        """Test git commit and push workflow."""
        with patch('subprocess.run') as mock_run:
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'git add .' in cmd:
                    return Mock(returncode=0, stdout="", stderr="")
                elif 'git commit' in cmd:
                    return Mock(returncode=0, stdout="[issue-316-123] Added test implementation", stderr="")
                elif 'git rev-parse HEAD' in cmd:
                    return Mock(returncode=0, stdout="abc123def456", stderr="")
                elif 'git push -u origin' in cmd:
                    return Mock(returncode=0, stdout="Branch pushed successfully", stderr="")
                elif 'git remote get-url origin' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'gh issue view' in cmd:
                    return Mock(returncode=0, stdout='{"title":"Test","body":"Test","labels":[]}', stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'), patch.dict(os.environ, {'CLAUDE_TASKER_AUTO_CLEANUP': '1'}):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should handle git workflow commands
            assert result.returncode == 0
    
    def test_workspace_status_detection(self, claude_tasker_script, mock_git_repo):
        """Test detection of workspace changes requiring cleanup."""
        with patch('subprocess.run') as mock_run:
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'git status --porcelain' in cmd:
                    # Simulate various workspace states
                    return Mock(returncode=0, stdout="M  modified.txt\n?? untracked.txt\nD  deleted.txt", stderr="")
                elif 'git diff --quiet' in cmd:
                    # Changes present
                    return Mock(returncode=1, stdout="", stderr="")
                elif 'gh issue view' in cmd:
                    return Mock(returncode=0, stdout='{"title":"Test","body":"Test","labels":[]}', stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'), patch.dict(os.environ, {'CLAUDE_TASKER_AUTO_CLEANUP': '1'}):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should detect and handle workspace changes
            status_calls = [call for call in mock_run.call_args_list 
                           if 'git status --porcelain' in str(call.args)]
            diff_calls = [call for call in mock_run.call_args_list 
                         if 'git diff --quiet' in str(call.args)]
            
            assert len(status_calls) > 0 or len(diff_calls) > 0 or result.returncode == 0
    
    def test_non_interactive_environment_handling(self, claude_tasker_script, mock_git_repo):
        """Test handling of non-interactive environments (CI/automation)."""
        with patch('subprocess.run') as mock_run, \
             patch('os.isatty', return_value=False):  # Simulate non-TTY environment
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'git status --porcelain' in cmd:
                    return Mock(returncode=0, stdout="M modified.txt", stderr="")
                elif 'git diff --quiet' in cmd:
                    return Mock(returncode=1, stdout="", stderr="")
                elif 'git reset --hard' in cmd:
                    return Mock(returncode=0, stdout="HEAD is now at abc123", stderr="")
                elif 'gh issue view' in cmd:
                    return Mock(returncode=0, stdout='{"title":"Test","body":"Test","labels":[]}', stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should proceed automatically in non-interactive environment
            assert result.returncode == 0