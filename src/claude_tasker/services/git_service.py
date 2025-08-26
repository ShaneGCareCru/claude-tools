"""Git operations service wrapper."""
import logging
from typing import List, Optional, Dict, Any
from .command_executor import CommandExecutor, CommandResult


class GitService:
    """Service for Git operations using CommandExecutor."""
    
    def __init__(self, 
                 command_executor: CommandExecutor,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize GitService.
        
        Args:
            command_executor: CommandExecutor instance for running git commands
            logger: Logger instance
        """
        self.executor = command_executor
        self.logger = logger or logging.getLogger(__name__)
    
    def status(self, cwd: Optional[str] = None, porcelain: bool = False) -> CommandResult:
        """Get git status."""
        cmd = ["git", "status"]
        if porcelain:
            cmd.append("--porcelain")
        return self.executor.execute(cmd, cwd=cwd)
    
    def add(self, files: List[str], cwd: Optional[str] = None) -> CommandResult:
        """Add files to staging area."""
        cmd = ["git", "add"] + files
        return self.executor.execute(cmd, cwd=cwd)
    
    def commit(self, message: str, cwd: Optional[str] = None, allow_empty: bool = False) -> CommandResult:
        """Create a commit."""
        cmd = ["git", "commit", "-m", message]
        if allow_empty:
            cmd.append("--allow-empty")
        return self.executor.execute(cmd, cwd=cwd)
    
    def push(self, remote: str = "origin", branch: Optional[str] = None, 
             set_upstream: bool = False, force: bool = False, cwd: Optional[str] = None) -> CommandResult:
        """Push changes to remote."""
        cmd = ["git", "push"]
        if set_upstream:
            cmd.extend(["-u", remote])
            if branch:
                cmd.append(branch)
        else:
            cmd.append(remote)
            if branch:
                cmd.append(branch)
        if force:
            cmd.append("--force")
        return self.executor.execute(cmd, cwd=cwd)
    
    def pull(self, remote: str = "origin", branch: Optional[str] = None, cwd: Optional[str] = None) -> CommandResult:
        """Pull changes from remote."""
        cmd = ["git", "pull", remote]
        if branch:
            cmd.append(branch)
        return self.executor.execute(cmd, cwd=cwd)
    
    def checkout(self, branch: str, create: bool = False, cwd: Optional[str] = None) -> CommandResult:
        """Checkout or create branch."""
        cmd = ["git", "checkout"]
        if create:
            cmd.append("-b")
        cmd.append(branch)
        return self.executor.execute(cmd, cwd=cwd)
    
    def branch(self, name: Optional[str] = None, delete: bool = False, 
               force_delete: bool = False, list_all: bool = False, cwd: Optional[str] = None) -> CommandResult:
        """Branch operations."""
        cmd = ["git", "branch"]
        if list_all:
            cmd.append("-a")
        elif delete:
            cmd.append("-D" if force_delete else "-d")
            if name:
                cmd.append(name)
        elif name:
            cmd.append(name)
        return self.executor.execute(cmd, cwd=cwd)
    
    def merge(self, branch: str, no_ff: bool = False, cwd: Optional[str] = None) -> CommandResult:
        """Merge branch."""
        cmd = ["git", "merge"]
        if no_ff:
            cmd.append("--no-ff")
        cmd.append(branch)
        return self.executor.execute(cmd, cwd=cwd)
    
    def fetch(self, remote: str = "origin", prune: bool = False, cwd: Optional[str] = None) -> CommandResult:
        """Fetch from remote."""
        cmd = ["git", "fetch", remote]
        if prune:
            cmd.append("--prune")
        return self.executor.execute(cmd, cwd=cwd)
    
    def log(self, max_count: Optional[int] = None, oneline: bool = False, 
            since: Optional[str] = None, until: Optional[str] = None, cwd: Optional[str] = None) -> CommandResult:
        """Get git log."""
        cmd = ["git", "log"]
        if max_count:
            cmd.extend(["-n", str(max_count)])
        if oneline:
            cmd.append("--oneline")
        if since:
            cmd.extend(["--since", since])
        if until:
            cmd.extend(["--until", until])
        return self.executor.execute(cmd, cwd=cwd)
    
    def diff(self, cached: bool = False, name_only: bool = False, 
             files: Optional[List[str]] = None, cwd: Optional[str] = None) -> CommandResult:
        """Get git diff."""
        cmd = ["git", "diff"]
        if cached:
            cmd.append("--cached")
        if name_only:
            cmd.append("--name-only")
        if files:
            cmd.extend(files)
        return self.executor.execute(cmd, cwd=cwd)
    
    def reset(self, mode: str = "mixed", target: Optional[str] = None, cwd: Optional[str] = None) -> CommandResult:
        """Reset git state."""
        cmd = ["git", "reset", f"--{mode}"]
        if target:
            cmd.append(target)
        return self.executor.execute(cmd, cwd=cwd)
    
    def stash(self, action: str = "push", message: Optional[str] = None, 
              include_untracked: bool = False, cwd: Optional[str] = None) -> CommandResult:
        """Stash operations."""
        cmd = ["git", "stash", action]
        if action == "push":
            if include_untracked:
                cmd.append("-u")
            if message:
                cmd.extend(["-m", message])
        return self.executor.execute(cmd, cwd=cwd)
    
    def remote(self, action: str = "show", name: Optional[str] = None, 
               url: Optional[str] = None, cwd: Optional[str] = None) -> CommandResult:
        """Remote operations."""
        cmd = ["git", "remote", action]
        if name:
            cmd.append(name)
        if url and action == "add":
            cmd.append(url)
        return self.executor.execute(cmd, cwd=cwd)
    
    def tag(self, name: Optional[str] = None, message: Optional[str] = None, 
            delete: bool = False, list_tags: bool = False, cwd: Optional[str] = None) -> CommandResult:
        """Tag operations."""
        cmd = ["git", "tag"]
        if list_tags:
            pass  # Just list tags
        elif delete and name:
            cmd.extend(["-d", name])
        elif name:
            if message:
                cmd.extend(["-a", name, "-m", message])
            else:
                cmd.append(name)
        return self.executor.execute(cmd, cwd=cwd)
    
    def clean(self, force: bool = False, directories: bool = False, 
              dry_run: bool = False, cwd: Optional[str] = None) -> CommandResult:
        """Clean working directory."""
        cmd = ["git", "clean"]
        if force:
            cmd.append("-f")
        if directories:
            cmd.append("-d")
        if dry_run:
            cmd.append("-n")
        return self.executor.execute(cmd, cwd=cwd)
    
    def rev_parse(self, ref: str, short: bool = False, cwd: Optional[str] = None) -> CommandResult:
        """Parse revision."""
        cmd = ["git", "rev-parse"]
        if short:
            cmd.append("--short")
        cmd.append(ref)
        return self.executor.execute(cmd, cwd=cwd)
    
    def show_ref(self, pattern: Optional[str] = None, heads: bool = False, 
                 tags: bool = False, cwd: Optional[str] = None) -> CommandResult:
        """Show references."""
        cmd = ["git", "show-ref"]
        if heads:
            cmd.append("--heads")
        if tags:
            cmd.append("--tags")
        if pattern:
            cmd.append(pattern)
        return self.executor.execute(cmd, cwd=cwd)
    
    def current_branch(self, cwd: Optional[str] = None) -> Optional[str]:
        """Get current branch name."""
        cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
        result = self.executor.execute(cmd, cwd=cwd)
        if result.success:
            return result.stdout.strip()
        return None
    
    def is_clean(self, cwd: Optional[str] = None) -> bool:
        """Check if working directory is clean."""
        result = self.status(cwd=cwd, porcelain=True)
        return result.success and not result.stdout.strip()
    
    def has_changes(self, cached: bool = False, cwd: Optional[str] = None) -> bool:
        """Check if there are changes to commit."""
        result = self.diff(cached=cached, cwd=cwd)
        return result.success and bool(result.stdout.strip())
    
    def branch_exists(self, branch: str, remote: bool = False, cwd: Optional[str] = None) -> bool:
        """Check if branch exists."""
        pattern = f"refs/remotes/origin/{branch}" if remote else f"refs/heads/{branch}"
        result = self.show_ref(pattern=pattern, cwd=cwd)
        return result.success and bool(result.stdout.strip())
    
    def get_remote_url(self, remote: str = "origin", cwd: Optional[str] = None) -> Optional[str]:
        """Get remote URL."""
        result = self.remote("get-url", name=remote, cwd=cwd)
        if result.success:
            return result.stdout.strip()
        return None
    
    def get_commit_hash(self, ref: str = "HEAD", short: bool = True, cwd: Optional[str] = None) -> Optional[str]:
        """Get commit hash for reference."""
        result = self.rev_parse(ref, short=short, cwd=cwd)
        if result.success:
            return result.stdout.strip()
        return None