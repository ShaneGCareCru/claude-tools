"""Workspace and Git management module for claude-tasker."""

import subprocess
import os
import time
from typing import Tuple, Optional, List
from pathlib import Path


class WorkspaceManager:
    """Manages workspace hygiene, Git operations, and branch management."""
    
    def __init__(self, cwd: str = "."):
        self.cwd = Path(cwd).resolve()
        self.interactive_mode = self._is_interactive()
    
    def _is_interactive(self) -> bool:
        """Determine if running in interactive mode."""
        return (
            os.isatty(0) and  # stdin is a terminal
            os.environ.get('CI') != 'true' and  # not in CI
            os.environ.get('GITHUB_ACTIONS') != 'true'  # not in GitHub Actions
        )
    
    def _run_git_command(self, cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Execute git command with proper error handling."""
        try:
            return subprocess.run(
                ['git'] + cmd,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=False,
                **kwargs
            )
        except Exception as e:
            return subprocess.CompletedProcess(
                args=['git'] + cmd,
                returncode=1,
                stdout="",
                stderr=str(e)
            )
    
    def detect_main_branch(self) -> str:
        """Detect the main branch (main, master, or default)."""
        # Check current branch first
        result = self._run_git_command(['branch', '--show-current'])
        if result.returncode == 0 and result.stdout.strip():
            current_branch = result.stdout.strip()
            
            # If already on main or master, return it
            if current_branch in ['main', 'master']:
                return current_branch
        
        # Check for main branch
        result = self._run_git_command(['show-ref', '--verify', '--quiet', 'refs/heads/main'])
        if result.returncode == 0:
            return 'main'
        
        # Check for master branch
        result = self._run_git_command(['show-ref', '--verify', '--quiet', 'refs/heads/master'])
        if result.returncode == 0:
            return 'master'
        
        # Default to main
        return 'main'
    
    def get_current_branch(self) -> Optional[str]:
        """Get the current Git branch name."""
        result = self._run_git_command(['branch', '--show-current'])
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    
    def is_working_directory_clean(self) -> bool:
        """Check if working directory has no uncommitted changes."""
        result = self._run_git_command(['status', '--porcelain'])
        return result.returncode == 0 and not result.stdout.strip()
    
    def workspace_hygiene(self, force: bool = False) -> bool:
        """Perform workspace hygiene (reset and clean)."""
        if not force and self.interactive_mode:
            if not self._confirm_cleanup():
                return False
        
        # Hard reset to HEAD
        result = self._run_git_command(['reset', '--hard', 'HEAD'])
        if result.returncode != 0:
            return False
        
        # Clean untracked files and directories
        result = self._run_git_command(['clean', '-fd'])
        if result.returncode != 0:
            return False
        
        return True
    
    def _confirm_cleanup(self) -> bool:
        """Ask user to confirm workspace cleanup in interactive mode."""
        try:
            response = input("Workspace has changes. Clean workspace (reset --hard && clean -fd)? [y/N]: ")
            return response.lower().startswith('y')
        except (EOFError, KeyboardInterrupt):
            return False
    
    def create_timestamped_branch(self, issue_number: int, base_branch: str = None) -> Tuple[bool, str]:
        """Create a new timestamped branch for issue processing."""
        if base_branch is None:
            base_branch = self.detect_main_branch()
        
        # Generate timestamped branch name
        timestamp = str(int(time.time()))
        branch_name = f"issue-{issue_number}-{timestamp}"
        
        # Switch to base branch
        result = self._run_git_command(['checkout', base_branch])
        if result.returncode != 0:
            return False, f"Failed to checkout {base_branch}: {result.stderr}"
        
        # Pull latest changes
        result = self._run_git_command(['pull', 'origin', base_branch])
        if result.returncode != 0:
            # Continue even if pull fails (might be offline or no upstream)
            pass
        
        # Create and checkout new branch
        result = self._run_git_command(['checkout', '-b', branch_name])
        if result.returncode != 0:
            return False, f"Failed to create branch {branch_name}: {result.stderr}"
        
        return True, branch_name
    
    def commit_changes(self, message: str, branch_name: str) -> bool:
        """Stage and commit all changes."""
        # Add all changes
        result = self._run_git_command(['add', '.'])
        if result.returncode != 0:
            return False
        
        # Check if there are changes to commit
        result = self._run_git_command(['diff', '--cached', '--quiet'])
        if result.returncode == 0:
            # No changes to commit
            return True
        
        # Create commit with standardized message
        commit_msg = f"🤖 {branch_name}: {message}\n\n🤖 Generated with [Claude Code](https://claude.ai/code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        
        result = self._run_git_command(['commit', '-m', commit_msg])
        return result.returncode == 0
    
    def push_branch(self, branch_name: str) -> bool:
        """Push branch to origin with upstream tracking."""
        result = self._run_git_command(['push', '-u', 'origin', branch_name])
        return result.returncode == 0
    
    def has_changes_to_commit(self) -> bool:
        """Check if there are staged or unstaged changes."""
        # Check for unstaged changes
        result = self._run_git_command(['diff', '--quiet'])
        if result.returncode != 0:
            return True
        
        # Check for staged changes
        result = self._run_git_command(['diff', '--cached', '--quiet'])
        if result.returncode != 0:
            return True
        
        # Check for untracked files
        result = self._run_git_command(['ls-files', '--others', '--exclude-standard'])
        if result.returncode == 0 and result.stdout.strip():
            return True
        
        return False
    
    def get_git_diff(self, base_branch: str = None) -> str:
        """Get git diff output for current changes."""
        if base_branch:
            result = self._run_git_command(['diff', f'{base_branch}...HEAD'])
        else:
            # Get all changes (staged and unstaged)
            result1 = self._run_git_command(['diff', 'HEAD'])
            result2 = self._run_git_command(['diff', '--cached'])
            
            if result1.returncode == 0 and result2.returncode == 0:
                return result1.stdout + result2.stdout
        
        if result.returncode == 0:
            return result.stdout
        return ""
    
    def get_commit_log(self, base_branch: str, limit: int = 10) -> str:
        """Get commit log from base branch to current HEAD."""
        result = self._run_git_command([
            'log', f'{base_branch}..HEAD',
            '--oneline', f'--max-count={limit}'
        ])
        
        if result.returncode == 0:
            return result.stdout
        return ""
    
    def switch_to_branch(self, branch_name: str) -> bool:
        """Switch to specified branch."""
        result = self._run_git_command(['checkout', branch_name])
        return result.returncode == 0
    
    def branch_exists(self, branch_name: str) -> bool:
        """Check if branch exists locally."""
        result = self._run_git_command(['show-ref', '--verify', '--quiet', f'refs/heads/{branch_name}'])
        return result.returncode == 0
    
    def delete_branch(self, branch_name: str, force: bool = False) -> bool:
        """Delete a local branch."""
        flag = '-D' if force else '-d'
        result = self._run_git_command(['branch', flag, branch_name])
        return result.returncode == 0
    
    def get_remote_url(self) -> Optional[str]:
        """Get the remote origin URL."""
        result = self._run_git_command(['config', '--get', 'remote.origin.url'])
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    
    def is_branch_pushed(self, branch_name: str) -> bool:
        """Check if branch exists on remote."""
        result = self._run_git_command(['show-ref', '--verify', '--quiet', f'refs/remotes/origin/{branch_name}'])
        return result.returncode == 0