"""Tests for claude-tasker git operations and workspace management."""
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, Mock, call


@pytest.mark.skip(reason="Git operations tests need to be updated for Python module - currently test bash script behavior")
class TestGitOperations:
    """Test git operations and workspace management."""
    
    def test_validate_git_repository(self, claude_tasker_script, mock_git_repo):
        """Test validation that we're in a git repository."""
        with patch('subprocess.run') as mock_run:
            # Mock git rev-parse to fail (not a git repo)
            mock_run.return_value = Mock(returncode=1, stderr="not a git repository")
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            assert result.returncode != 0
            assert "not a git repository" in result.stderr or "git repository" in result.stderr
    
    def test_require_claude_md_file(self, claude_tasker_script, tmp_path):
        """Test that CLAUDE.md file is required."""
        repo_dir = tmp_path / "no_claude_md"
        repo_dir.mkdir()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=".git", stderr="")
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True
                )
            
            assert result.returncode != 0
            assert "CLAUDE.md" in result.stderr
    
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