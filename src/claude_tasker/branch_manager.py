"""Intelligent branch management with reuse capabilities."""

import os
import re
import time
import subprocess
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from src.claude_tasker.logging_config import get_logger

logger = get_logger(__name__)


class BranchStrategy(Enum):
    """Branch creation/reuse strategies."""
    ALWAYS_NEW = "always_new"  # Always create new timestamped branches
    REUSE_WHEN_POSSIBLE = "reuse"  # Reuse existing PR branches when possible
    REUSE_OR_FAIL = "reuse_or_fail"  # Fail if can't reuse existing branch


@dataclass
class BranchInfo:
    """Information about a branch."""
    name: str
    exists_locally: bool
    exists_remotely: bool
    is_current: bool
    has_uncommitted_changes: bool
    associated_pr_number: Optional[int] = None
    issue_number: Optional[int] = None
    timestamp: Optional[str] = None


class BranchManager:
    """Manages Git branches with intelligent reuse capabilities."""
    
    def __init__(self, strategy: BranchStrategy = BranchStrategy.REUSE_WHEN_POSSIBLE):
        """Initialize branch manager with specified strategy."""
        self.strategy = strategy
        self.repo_owner = None
        self.repo_name = None
        self._init_repo_info()
    
    def _init_repo_info(self):
        """Initialize repository information from git remote."""
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # Parse owner/repo from URL
                match = re.search(r'github\.com[:/]([^/]+)/([^/.]+)', url)
                if match:
                    self.repo_owner = match.group(1)
                    self.repo_name = match.group(2).replace('.git', '')
                    logger.debug(f"Initialized repo: {self.repo_owner}/{self.repo_name}")
        except Exception as e:
            logger.warning(f"Could not determine repo info: {e}")
    
    def find_existing_branches_for_issue(self, issue_number: int) -> List[BranchInfo]:
        """Find all branches related to an issue."""
        branches = []
        
        # Pattern to match issue branches
        pattern = f"issue-{issue_number}-"
        
        # Get local branches
        local_result = subprocess.run(
            ['git', 'branch', '--list', f'*{pattern}*'],
            capture_output=True, text=True, check=False
        )
        
        # Get remote branches
        remote_result = subprocess.run(
            ['git', 'branch', '-r', '--list', f'*{pattern}*'],
            capture_output=True, text=True, check=False
        )
        
        # Get current branch
        current_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True, text=True, check=False
        )
        current_branch = current_result.stdout.strip() if current_result.returncode == 0 else ""
        
        # Parse local branches
        if local_result.returncode == 0:
            for line in local_result.stdout.strip().split('\n'):
                if line:
                    branch_name = line.strip().lstrip('* ')
                    if branch_name:
                        branches.append(self._analyze_branch(branch_name, current_branch))
        
        # Parse remote branches
        if remote_result.returncode == 0:
            for line in remote_result.stdout.strip().split('\n'):
                if line:
                    # Remote branches are prefixed with origin/
                    branch_name = line.strip().replace('origin/', '')
                    if branch_name and not any(b.name == branch_name for b in branches):
                        info = self._analyze_branch(branch_name, current_branch)
                        info.exists_locally = False
                        info.exists_remotely = True
                        branches.append(info)
        
        # Sort by timestamp (newest first)
        branches.sort(key=lambda b: b.timestamp or "0", reverse=True)
        
        return branches
    
    def _analyze_branch(self, branch_name: str, current_branch: str) -> BranchInfo:
        """Analyze a branch to extract information."""
        info = BranchInfo(
            name=branch_name,
            exists_locally=True,
            exists_remotely=False,
            is_current=(branch_name == current_branch),
            has_uncommitted_changes=False
        )
        
        # Parse issue number and timestamp from branch name
        match = re.match(r'issue-(\d+)-(\d+)', branch_name)
        if match:
            info.issue_number = int(match.group(1))
            info.timestamp = match.group(2)
        
        # Check if branch exists remotely
        remote_check = subprocess.run(
            ['git', 'ls-remote', '--heads', 'origin', branch_name],
            capture_output=True, text=True, check=False
        )
        info.exists_remotely = bool(remote_check.stdout.strip())
        
        # Check for uncommitted changes if it's the current branch
        if info.is_current:
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, check=False
            )
            info.has_uncommitted_changes = bool(status_result.stdout.strip())
        
        return info
    
    def find_existing_pr_for_issue(self, issue_number: int) -> Optional[Dict[str, Any]]:
        """Find existing open PR for an issue using gh CLI."""
        if not self.repo_owner or not self.repo_name:
            logger.warning("Repository info not available, cannot check for PRs")
            return None
        
        try:
            # Search for PRs that mention the issue in title or body
            result = subprocess.run(
                ['gh', 'pr', 'list', 
                 '--repo', f'{self.repo_owner}/{self.repo_name}',
                 '--search', f'issue #{issue_number} in:title,body',
                 '--state', 'open',
                 '--json', 'number,title,headRefName,url,isDraft'],
                capture_output=True, text=True, check=False
            )
            
            if result.returncode == 0 and result.stdout.strip():
                import json
                prs = json.loads(result.stdout)
                
                # Filter for PRs that actually reference this issue
                for pr in prs:
                    # Check if PR branch name matches issue pattern
                    if f'issue-{issue_number}-' in pr.get('headRefName', ''):
                        logger.info(f"Found existing PR #{pr['number']} for issue #{issue_number}")
                        return pr
                
                # Fallback: check PR title/body more carefully
                for pr in prs:
                    if f'#{issue_number}' in pr.get('title', '') or \
                       f'issue #{issue_number}' in pr.get('title', '').lower():
                        logger.info(f"Found existing PR #{pr['number']} for issue #{issue_number}")
                        return pr
            
        except Exception as e:
            logger.warning(f"Error checking for existing PRs: {e}")
        
        return None
    
    def reuse_or_create_branch(self, issue_number: int, base_branch: str = "main") -> Tuple[bool, str, str]:
        """
        Intelligently reuse existing branch or create new one.
        
        Returns:
            Tuple of (success, branch_name, action_taken)
            action_taken can be: "reused", "created", "switched"
        """
        logger.info(f"Branch strategy: {self.strategy.value}")
        
        # If strategy is ALWAYS_NEW, skip reuse logic
        if self.strategy == BranchStrategy.ALWAYS_NEW:
            return self._create_new_branch(issue_number, base_branch)
        
        # Check for existing PR
        existing_pr = self.find_existing_pr_for_issue(issue_number)
        
        if existing_pr:
            branch_name = existing_pr.get('headRefName')
            pr_number = existing_pr.get('number')
            
            logger.info(f"Found existing PR #{pr_number} with branch '{branch_name}'")
            
            # Try to reuse the branch
            success, message = self._checkout_branch(branch_name, base_branch)
            
            if success:
                logger.info(f"✅ Reusing existing branch '{branch_name}' from PR #{pr_number}")
                return True, branch_name, "reused"
            else:
                logger.warning(f"Could not checkout existing branch: {message}")
                
                if self.strategy == BranchStrategy.REUSE_OR_FAIL:
                    return False, "", f"Failed to reuse required branch: {message}"
                # Fall through to create new branch
        
        # Check for existing branches without PRs
        existing_branches = self.find_existing_branches_for_issue(issue_number)
        
        if existing_branches:
            # Try the most recent branch first
            for branch_info in existing_branches:
                if branch_info.is_current:
                    logger.info(f"Already on branch '{branch_info.name}' for issue #{issue_number}")
                    return True, branch_info.name, "switched"
                
                success, message = self._checkout_branch(branch_info.name, base_branch)
                if success:
                    logger.info(f"✅ Reusing existing branch '{branch_info.name}'")
                    return True, branch_info.name, "reused"
        
        # No existing branches to reuse
        if self.strategy == BranchStrategy.REUSE_OR_FAIL:
            return False, "", "No existing branch found and strategy requires reuse"
        
        # Create new timestamped branch
        return self._create_new_branch(issue_number, base_branch)
    
    def _checkout_branch(self, branch_name: str, base_branch: str) -> Tuple[bool, str]:
        """Checkout an existing branch, handling remote-only branches."""
        # First, fetch the latest from remote
        fetch_result = subprocess.run(
            ['git', 'fetch', 'origin', branch_name],
            capture_output=True, text=True, check=False
        )
        
        # Check if branch exists locally
        local_check = subprocess.run(
            ['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch_name}'],
            capture_output=True, text=True, check=False
        )
        
        if local_check.returncode == 0:
            # Branch exists locally, just checkout
            checkout_result = subprocess.run(
                ['git', 'checkout', branch_name],
                capture_output=True, text=True, check=False
            )
            
            if checkout_result.returncode == 0:
                # Pull latest changes
                pull_result = subprocess.run(
                    ['git', 'pull', 'origin', branch_name],
                    capture_output=True, text=True, check=False
                )
                
                if pull_result.returncode != 0:
                    logger.warning(f"Could not pull latest changes: {pull_result.stderr}")
                
                return True, f"Checked out existing local branch '{branch_name}'"
            else:
                return False, f"Failed to checkout local branch: {checkout_result.stderr}"
        else:
            # Branch doesn't exist locally, create from remote
            checkout_result = subprocess.run(
                ['git', 'checkout', '-b', branch_name, f'origin/{branch_name}'],
                capture_output=True, text=True, check=False
            )
            
            if checkout_result.returncode == 0:
                return True, f"Created local branch '{branch_name}' from remote"
            else:
                # Remote branch might not exist either
                return False, f"Branch not found locally or remotely: {checkout_result.stderr}"
    
    def _create_new_branch(self, issue_number: int, base_branch: str) -> Tuple[bool, str, str]:
        """Create a new timestamped branch."""
        timestamp = str(int(time.time()))
        branch_name = f"issue-{issue_number}-{timestamp}"
        
        logger.info(f"Creating new branch '{branch_name}' from '{base_branch}'")
        
        # Ensure we're on the base branch first
        checkout_base = subprocess.run(
            ['git', 'checkout', base_branch],
            capture_output=True, text=True, check=False
        )
        
        if checkout_base.returncode != 0:
            # Try to create base branch from origin
            checkout_base = subprocess.run(
                ['git', 'checkout', '-b', base_branch, f'origin/{base_branch}'],
                capture_output=True, text=True, check=False
            )
            
            if checkout_base.returncode != 0:
                return False, "", f"Failed to checkout base branch '{base_branch}': {checkout_base.stderr}"
        
        # Pull latest changes
        pull_result = subprocess.run(
            ['git', 'pull', 'origin', base_branch],
            capture_output=True, text=True, check=False
        )
        
        # Create new branch
        create_result = subprocess.run(
            ['git', 'checkout', '-b', branch_name],
            capture_output=True, text=True, check=False
        )
        
        if create_result.returncode == 0:
            logger.info(f"✅ Created new branch '{branch_name}'")
            return True, branch_name, "created"
        else:
            return False, "", f"Failed to create branch: {create_result.stderr}"
    
    def cleanup_old_issue_branches(self, issue_number: int, keep_count: int = 3) -> int:
        """
        Clean up old branches for an issue, keeping the most recent ones.
        
        Returns:
            Number of branches deleted
        """
        branches = self.find_existing_branches_for_issue(issue_number)
        
        # Filter out branches with associated PRs or uncommitted changes
        deletable = []
        for branch in branches:
            if branch.is_current or branch.has_uncommitted_changes:
                continue
            
            # Check if branch has an associated PR
            if branch.associated_pr_number:
                continue
            
            deletable.append(branch)
        
        # Keep the most recent branches
        if len(deletable) <= keep_count:
            logger.info(f"No branches to clean up (found {len(deletable)} deletable branches)")
            return 0
        
        to_delete = deletable[keep_count:]
        deleted_count = 0
        
        for branch in to_delete:
            logger.info(f"Deleting old branch '{branch.name}'")
            
            # Delete local branch
            if branch.exists_locally:
                delete_local = subprocess.run(
                    ['git', 'branch', '-D', branch.name],
                    capture_output=True, text=True, check=False
                )
                
                if delete_local.returncode == 0:
                    logger.debug(f"Deleted local branch '{branch.name}'")
                else:
                    logger.warning(f"Could not delete local branch: {delete_local.stderr}")
            
            # Delete remote branch
            if branch.exists_remotely:
                delete_remote = subprocess.run(
                    ['git', 'push', 'origin', '--delete', branch.name],
                    capture_output=True, text=True, check=False
                )
                
                if delete_remote.returncode == 0:
                    logger.debug(f"Deleted remote branch '{branch.name}'")
                    deleted_count += 1
                else:
                    logger.warning(f"Could not delete remote branch: {delete_remote.stderr}")
        
        logger.info(f"Cleaned up {deleted_count} old branches for issue #{issue_number}")
        return deleted_count