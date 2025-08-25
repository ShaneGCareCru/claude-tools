"""Workspace and Git management module for claude-tasker."""

import subprocess
import os
import time
from typing import Tuple, Optional, List
from pathlib import Path
from src.claude_tasker.logging_config import get_logger
from src.claude_tasker.branch_manager import BranchManager, BranchStrategy

logger = get_logger(__name__)


class WorkspaceManager:
    """Manages workspace hygiene, Git operations, and branch management."""
    
    def __init__(self, cwd: str = ".", branch_strategy: str = "reuse"):
        """Initialize workspace manager.
        
        Args:
            cwd: Current working directory
            branch_strategy: Branch strategy - "always_new", "reuse", or "reuse_or_fail"
        """
        self.cwd = Path(cwd).resolve()
        self.interactive_mode = self._is_interactive()
        
        # Initialize branch manager with specified strategy
        strategy_map = {
            "always_new": BranchStrategy.ALWAYS_NEW,
            "reuse": BranchStrategy.REUSE_WHEN_POSSIBLE,
            "reuse_or_fail": BranchStrategy.REUSE_OR_FAIL
        }
        strategy = strategy_map.get(branch_strategy, BranchStrategy.REUSE_WHEN_POSSIBLE)
        self.branch_manager = BranchManager(strategy)
    
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
        # Check if workspace is already clean
        if self.is_working_directory_clean():
            # Workspace is already clean, no need to do anything
            return True
        
        # Only prompt if there are actual changes and we're in interactive mode
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
            print("Workspace has changes. Choose an option:")
            print("  1. Clean workspace (reset --hard && clean -fd)")
            print("  2. Stash changes and continue")
            print("  3. Cancel operation")
            response = input("Your choice [1/2/3]: ").strip()
            
            if response == '1':
                # User wants to clean workspace
                return True
            elif response == '2':
                # User wants to stash changes
                return self._stash_changes()
            else:
                # User wants to cancel
                return False
        except (EOFError, KeyboardInterrupt):
            return False
    
    def _stash_changes(self) -> bool:
        """Stash current changes with a descriptive message."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        stash_message = f"claude-tasker auto-stash at {timestamp}"
        
        # Stash all changes including untracked files
        result = self._run_git_command(['stash', 'push', '-u', '-m', stash_message])
        if result.returncode != 0:
            logger.error(f"Failed to stash changes: {result.stderr}")
            print(f"Failed to stash changes: {result.stderr}")
            return False
        
        logger.info(f"Changes stashed successfully: {stash_message}")
        print(f"Changes stashed successfully: {stash_message}")
        print("You can restore them later with: git stash pop")
        return True
    
    def smart_branch_for_issue(self, issue_number: int, base_branch: str = None) -> Tuple[bool, str, str]:
        """Intelligently reuse existing branch or create new one for issue.
        
        Returns:
            Tuple of (success, branch_name, action) where action is "reused", "created", or "switched"
        """
        if base_branch is None:
            base_branch = self.detect_main_branch()
        
        logger.info(f"Smart branch selection for issue #{issue_number}")
        
        # Use branch manager for intelligent reuse
        success, branch_name, action = self.branch_manager.reuse_or_create_branch(
            issue_number, base_branch
        )
        
        if success:
            logger.info(f"Branch '{branch_name}' {action} for issue #{issue_number}")
            
            # Optional: Clean up old branches if we created a new one
            if action == "created" and os.getenv('CLAUDE_CLEANUP_OLD_BRANCHES', 'false').lower() == 'true':
                deleted_count = self.branch_manager.cleanup_old_issue_branches(
                    issue_number, 
                    keep_count=int(os.getenv('CLAUDE_KEEP_BRANCHES', '3'))
                )
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old branches")
        
        return success, branch_name, action
    
    def create_timestamped_branch(self, issue_number: int, base_branch: str = None) -> Tuple[bool, str]:
        """Create a new timestamped branch for issue processing."""
        if base_branch is None:
            base_branch = self.detect_main_branch()
        
        # Generate timestamped branch name
        timestamp = str(int(time.time()))
        branch_name = f"issue-{issue_number}-{timestamp}"
        
        logger.info(f"Creating branch '{branch_name}' for issue #{issue_number}")
        
        # Validation: Ensure issue number in branch name matches expected issue
        if issue_number <= 0:
            logger.error(f"Invalid issue number: {issue_number}")
            return False, f"Invalid issue number: {issue_number}"
        
        # First, fetch to ensure we have the latest remote branches
        result = self._run_git_command(['fetch', 'origin'])
        if result.returncode != 0:
            # Continue even if fetch fails (might be offline)
            pass
        
        # Check if base branch exists locally
        result = self._run_git_command(['show-ref', '--verify', '--quiet', f'refs/heads/{base_branch}'])
        if result.returncode != 0:
            # Base branch doesn't exist locally, try to create it from origin
            result = self._run_git_command(['checkout', '-b', base_branch, f'origin/{base_branch}'])
            if result.returncode != 0:
                # If that fails, just create the branch locally
                result = self._run_git_command(['checkout', '-b', base_branch])
                if result.returncode != 0:
                    return False, f"Failed to create base branch {base_branch}: {result.stderr}"
        else:
            # Switch to base branch
            result = self._run_git_command(['checkout', base_branch])
            if result.returncode != 0:
                return False, f"Failed to checkout {base_branch}: {result.stderr}"
        
        # Pull latest changes if possible
        result = self._run_git_command(['pull', 'origin', base_branch])
        if result.returncode != 0:
            # Continue even if pull fails (might be offline or no upstream)
            pass
        
        # Create and checkout new branch
        result = self._run_git_command(['checkout', '-b', branch_name])
        if result.returncode != 0:
            return False, f"Failed to create branch {branch_name}: {result.stderr}"
        
        return True, branch_name
    
    def validate_branch_for_issue(self, issue_number: int) -> Tuple[bool, str]:
        """Validate that current branch corresponds to the expected issue number."""
        current_branch = self.get_current_branch()
        if not current_branch:
            return False, "Could not determine current branch"
        
        # Parse issue number from branch name (format: issue-{number}-{timestamp})
        if current_branch.startswith('issue-'):
            try:
                # Extract issue number from branch name
                parts = current_branch.split('-')
                if len(parts) >= 2:
                    branch_issue_number = int(parts[1])
                    if branch_issue_number != issue_number:
                        logger.warning(f"Branch '{current_branch}' indicates issue #{branch_issue_number} but processing issue #{issue_number}")
                        suggestion = f"Consider switching to main branch first: git checkout main"
                        return False, f"Branch mismatch: branch '{current_branch}' suggests issue #{branch_issue_number}, but processing issue #{issue_number}. {suggestion}"
                    return True, f"Branch '{current_branch}' correctly matches issue #{issue_number}"
                else:
                    logger.warning(f"Branch '{current_branch}' has unexpected format")
                    return False, f"Branch '{current_branch}' has unexpected naming format"
            except ValueError:
                logger.warning(f"Could not parse issue number from branch '{current_branch}'")
                return False, f"Could not parse issue number from branch '{current_branch}'"
        else:
            # Not an issue branch, which might be intentional (e.g., main branch work)
            logger.info(f"Working on non-issue branch '{current_branch}' for issue #{issue_number}")
            return True, f"Working on branch '{current_branch}' (not an issue-specific branch)"
        
        return True, "Branch validation passed"
    
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
        logger.debug("Checking for git changes...")
        
        # Use git status --porcelain for a more reliable check
        result = self._run_git_command(['status', '--porcelain'])
        logger.debug(f"Git status --porcelain check: return code {result.returncode}")
        
        if result.returncode != 0:
            logger.debug(f"Git status command failed: {result.stderr}")
            # Fall back to checking individual types of changes
            
            # Check for unstaged changes
            result = self._run_git_command(['diff', '--quiet', 'HEAD'])
            logger.debug(f"Unstaged changes check (git diff --quiet HEAD): return code {result.returncode}")
            if result.returncode != 0:
                # Double-check with actual diff output
                diff_result = self._run_git_command(['diff', 'HEAD'])
                if diff_result.stdout.strip():
                    logger.debug("Found unstaged changes")
                    return True
            
            # Check for staged changes
            result = self._run_git_command(['diff', '--cached', '--quiet'])
            logger.debug(f"Staged changes check (git diff --cached --quiet): return code {result.returncode}")
            if result.returncode != 0:
                # Double-check with actual diff output
                diff_result = self._run_git_command(['diff', '--cached'])
                if diff_result.stdout.strip():
                    logger.debug("Found staged changes")
                    return True
            
            # Check for untracked files
            result = self._run_git_command(['ls-files', '--others', '--exclude-standard'])
            untracked = result.stdout.strip() if result.returncode == 0 else ""
            logger.debug(f"Untracked files check: {len(untracked)} chars of output")
            if untracked:
                logger.debug(f"Found untracked files: {untracked[:200]}...")
                return True
        else:
            # git status --porcelain succeeded, check its output
            output = result.stdout.strip()
            logger.debug(f"Git status output length: {len(output)} chars")
            if output:
                logger.debug(f"Git status shows changes:\n{output[:500]}...")
                return True
            else:
                logger.debug("Git status shows no changes")
        
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
    
    def has_changes(self) -> bool:
        """Check if there are any uncommitted changes in the workspace."""
        result = self._run_git_command(['status', '--porcelain'])
        if result.returncode != 0:
            return False
        return bool(result.stdout.strip())
    
    def cleanup_old_branches(self, days: int = 30) -> bool:
        """Clean up old local branches that have been merged."""
        try:
            # Get list of merged branches
            result = self._run_git_command(['branch', '--merged'])
            if result.returncode != 0:
                return False
            
            branches = result.stdout.strip().split('\n')
            cleaned_count = 0
            
            for branch in branches:
                branch = branch.strip().replace('*', '').strip()
                # Skip main/master branches
                if branch in ['main', 'master', 'develop']:
                    continue
                
                # Delete the branch
                result = self._run_git_command(['branch', '-d', branch])
                if result.returncode == 0:
                    cleaned_count += 1
                    logger.info(f"Deleted merged branch: {branch}")
            
            logger.info(f"Cleaned up {cleaned_count} old branches")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up branches: {e}")
            return False