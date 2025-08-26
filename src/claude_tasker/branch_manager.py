"""Intelligent branch management with reuse capabilities."""

import os
import re
import time
import json
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from src.claude_tasker.logging_config import get_logger
from src.claude_tasker.services.git_service import GitService
from src.claude_tasker.services.gh_service import GhService

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
    
    def __init__(self, 
                 git_service: GitService,
                 gh_service: GhService,
                 strategy: BranchStrategy = BranchStrategy.REUSE_WHEN_POSSIBLE):
        """Initialize branch manager with specified strategy and services."""
        self.git_service = git_service
        self.gh_service = gh_service
        self.strategy = strategy
        self.repo_owner = None
        self.repo_name = None
        self._init_repo_info()
    
    def _init_repo_info(self):
        """Initialize repository information from git remote."""
        try:
            result = self.git_service.remote("get-url", "origin")
            if result.success:
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
        
        # Get current branch
        current_branch = self.git_service.current_branch() or ""
        
        # Get local branches
        local_result = self.git_service.branch(list_all=False)
        
        # Get remote branches 
        remote_result = self.git_service.branch(list_all=True)
        
        # Parse local branches
        if local_result.success:
            for line in local_result.stdout.strip().split('\n'):
                if line and pattern in line:
                    branch_name = line.strip().lstrip('* ')
                    if branch_name:
                        branches.append(self._analyze_branch(branch_name, current_branch))
        
        # Parse remote branches
        if remote_result.success:
            for line in remote_result.stdout.strip().split('\n'):
                if line and pattern in line:
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
        info.exists_remotely = self.git_service.branch_exists(branch_name, remote=True)
        
        # Check for uncommitted changes if it's the current branch
        if info.is_current:
            info.has_uncommitted_changes = not self.git_service.is_clean()
        
        return info
    
    def find_existing_pr_for_issue(self, issue_number: int) -> Optional[Dict[str, Any]]:
        """Find existing open PR for an issue using gh CLI."""
        if not self.repo_owner or not self.repo_name:
            logger.warning("Repository info not available, cannot check for PRs")
            return None
        
        try:
            # Get all open PRs and filter for this issue
            prs = self.gh_service.list_prs(state="open")
            
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
        fetch_result = self.git_service.fetch("origin")
        
        # Check if branch exists locally
        branch_exists_locally = self.git_service.branch_exists(branch_name, remote=False)
        
        if branch_exists_locally:
            # Branch exists locally, just checkout
            checkout_result = self.git_service.checkout(branch_name)
            
            if checkout_result.success:
                # Pull latest changes
                pull_result = self.git_service.pull("origin", branch_name)
                
                if not pull_result.success:
                    logger.warning(f"Could not pull latest changes: {pull_result.stderr}")
                
                return True, f"Checked out existing local branch '{branch_name}'"
            else:
                return False, f"Failed to checkout local branch: {checkout_result.stderr}"
        else:
            # Branch doesn't exist locally, create from remote
            checkout_result = self.git_service.checkout(f"origin/{branch_name}", create=True)
            
            if checkout_result.success:
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
        checkout_base = self.git_service.checkout(base_branch)
        
        if not checkout_base.success:
            # Try to create base branch from origin
            checkout_base = self.git_service.checkout(f"origin/{base_branch}", create=True)
            
            if not checkout_base.success:
                return False, "", f"Failed to checkout base branch '{base_branch}': {checkout_base.stderr}"
        
        # Pull latest changes
        pull_result = self.git_service.pull("origin", base_branch)
        
        # Create new branch
        create_result = self.git_service.checkout(branch_name, create=True)
        
        if create_result.success:
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
                delete_local = self.git_service.branch(name=branch.name, delete=True, force_delete=True)
                
                if delete_local.success:
                    logger.debug(f"Deleted local branch '{branch.name}'")
                else:
                    logger.warning(f"Could not delete local branch: {delete_local.stderr}")
            
            # Delete remote branch
            if branch.exists_remotely:
                delete_remote = self.git_service.push("origin", f":{branch.name}")
                
                if delete_remote.success:
                    logger.debug(f"Deleted remote branch '{branch.name}'")
                    deleted_count += 1
                else:
                    logger.warning(f"Could not delete remote branch: {delete_remote.stderr}")
        
        logger.info(f"Cleaned up {deleted_count} old branches for issue #{issue_number}")
        return deleted_count