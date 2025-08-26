"""GitHub CLI and REST API service wrapper."""
import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from .command_executor import CommandExecutor, CommandResult


@dataclass
class IssueData:
    """Data structure for GitHub issue information."""
    number: int
    title: str
    body: str
    labels: List[str]
    url: str
    author: str
    state: str
    assignee: Optional[str] = None
    milestone: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class PRData:
    """Data structure for GitHub PR information."""
    number: int
    title: str
    body: str
    head_ref: str
    base_ref: str
    author: str
    additions: int
    deletions: int
    changed_files: int
    url: str


class GitHubError:
    """GitHub CLI error codes and patterns."""
    RATE_LIMIT = 'API rate limit exceeded'
    AUTH_FAILED = 'authentication failed'
    NOT_FOUND = 'not found'
    
    @classmethod
    def is_rate_limit(cls, stderr: str) -> bool:
        """Check if error is rate limit related."""
        if not stderr:
            return False
        rate_limit_patterns = [
            'API rate limit exceeded',
            'rate limit',
            'X-RateLimit-Remaining: 0'
        ]
        stderr_lower = stderr.lower()
        return any(pattern.lower() in stderr_lower for pattern in rate_limit_patterns)


class GhService:
    """Service for GitHub CLI and REST API operations using CommandExecutor."""
    
    def __init__(self, 
                 command_executor: CommandExecutor,
                 prefer_rest: bool = False,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize GhService.
        
        Args:
            command_executor: CommandExecutor instance for running gh commands
            prefer_rest: Whether to prefer REST API over CLI when available
            logger: Logger instance
        """
        self.executor = command_executor
        self.prefer_rest = prefer_rest
        self.logger = logger or logging.getLogger(__name__)
        
        # Hidden operation ID/marker for idempotency
        self.op_marker = "<!-- claude-tasker-op -->"
    
    def _run_gh_command(self, cmd: List[str], **kwargs) -> CommandResult:
        """Execute GitHub CLI command with retry logic."""
        return self.executor.execute(['gh'] + cmd, **kwargs)
    
    def _add_op_marker(self, content: str, op_id: Optional[str] = None) -> str:
        """Add operation marker to content for idempotency."""
        if op_id:
            marker = f"{self.op_marker}-{op_id}"
        else:
            marker = self.op_marker
        return f"{content}\n\n{marker}"
    
    def _has_op_marker(self, content: str, op_id: Optional[str] = None) -> bool:
        """Check if content has operation marker."""
        if op_id:
            marker = f"{self.op_marker}-{op_id}"
        else:
            marker = self.op_marker
        return marker in content
    
    def get_issue(self, issue_number: int) -> Optional[IssueData]:
        """Fetch issue data from GitHub."""
        cmd = [
            'issue', 'view', str(issue_number),
            '--json', 'number,title,body,labels,url,author,state'
        ]
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to fetch issue #{issue_number}: {result.stderr}")
            return None
        
        try:
            data = json.loads(result.stdout)
            return IssueData(
                number=data['number'],
                title=data['title'],
                body=data.get('body') or '',
                labels=[label['name'] for label in data.get('labels', [])],
                url=data['url'],
                author=data['author']['login'],
                state=data['state']
            )
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to parse issue data: {e}")
            return None
    
    def get_pr(self, pr_number: int) -> Optional[PRData]:
        """Fetch PR data from GitHub."""
        cmd = [
            'pr', 'view', str(pr_number),
            '--json', 'number,title,body,headRefName,baseRefName,author,additions,deletions,changedFiles,url'
        ]
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to fetch PR #{pr_number}: {result.stderr}")
            return None
        
        try:
            data = json.loads(result.stdout)
            return PRData(
                number=data['number'],
                title=data['title'], 
                body=data.get('body') or '',
                head_ref=data['headRefName'],
                base_ref=data['baseRefName'],
                author=data['author']['login'],
                additions=data.get('additions', 0),
                deletions=data.get('deletions', 0),
                changed_files=data.get('changedFiles', 0),
                url=data['url']
            )
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to parse PR data: {e}")
            return None
    
    def get_pr_diff(self, pr_number: int) -> Optional[str]:
        """Get PR diff content."""
        cmd = ['pr', 'diff', str(pr_number)]
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to get PR diff #{pr_number}: {result.stderr}")
            return None
        
        return result.stdout
    
    def get_pr_files(self, pr_number: int) -> List[str]:
        """Get list of files changed in PR."""
        cmd = ['pr', 'view', str(pr_number), '--json', 'files']
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to get PR files #{pr_number}: {result.stderr}")
            return []
        
        try:
            data = json.loads(result.stdout)
            return [file_info['path'] for file_info in data.get('files', [])]
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to parse PR files: {e}")
            return []
    
    def comment_on_issue(self, issue_number: int, comment: str, op_id: Optional[str] = None) -> bool:
        """Add comment to GitHub issue with deduplication check and idempotency marker."""
        # Add operation marker for idempotency
        marked_comment = self._add_op_marker(comment, op_id)
        
        # Check for existing comments to prevent duplicates
        existing_comments = self.get_issue_comments(issue_number)
        
        # Check if comment with this operation ID already exists
        if op_id:
            for existing_comment in existing_comments:
                existing_body = existing_comment.get('body', '')
                if self._has_op_marker(existing_body, op_id):
                    self.logger.info(f"Skipping duplicate comment on issue #{issue_number} (op_id: {op_id})")
                    return True
        
        # Extract first few lines of the new comment for comparison
        comment_lines = comment.strip().split('\n')
        comment_signature = '\n'.join(comment_lines[:3]).strip() if comment_lines else comment.strip()
        
        # Check if a similar comment already exists
        for existing_comment in existing_comments:
            existing_body = existing_comment.get('body', '')
            existing_lines = existing_body.strip().split('\n')
            existing_signature = '\n'.join(existing_lines[:3]).strip() if existing_lines else existing_body.strip()
            
            # If the signature matches, it's likely a duplicate
            if comment_signature == existing_signature and len(comment_signature) > 10:
                self.logger.info(f"Skipping duplicate comment on issue #{issue_number}")
                return True
        
        cmd = ['issue', 'comment', str(issue_number), '--body', marked_comment]
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to comment on issue #{issue_number}: {result.stderr}")
            return False
        
        self.logger.info(f"Successfully posted comment to issue #{issue_number}")
        return True
    
    def comment_on_pr(self, pr_number: int, comment: str, op_id: Optional[str] = None) -> bool:
        """Add comment to GitHub PR with deduplication check and idempotency marker."""
        # Add operation marker for idempotency
        marked_comment = self._add_op_marker(comment, op_id)
        
        # Check for existing comments to prevent duplicates
        existing_comments = self.get_pr_comments(pr_number)
        
        # Check if comment with this operation ID already exists
        if op_id:
            for existing_comment in existing_comments:
                existing_body = existing_comment.get('body', '')
                if self._has_op_marker(existing_body, op_id):
                    self.logger.info(f"Skipping duplicate comment on PR #{pr_number} (op_id: {op_id})")
                    return True
        
        # Extract first few lines of the new comment for comparison
        comment_lines = comment.strip().split('\n')
        comment_signature = '\n'.join(comment_lines[:3]).strip() if comment_lines else comment.strip()
        
        # Check if a similar comment already exists
        for existing_comment in existing_comments:
            existing_body = existing_comment.get('body', '')
            existing_lines = existing_body.strip().split('\n')
            existing_signature = '\n'.join(existing_lines[:3]).strip() if existing_lines else existing_body.strip()
            
            # If the signature matches, it's likely a duplicate
            if comment_signature == existing_signature and len(comment_signature) > 10:
                self.logger.info(f"Skipping duplicate comment on PR #{pr_number}")
                return True
        
        cmd = ['pr', 'comment', str(pr_number), '--body', marked_comment]
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to comment on PR #{pr_number}: {result.stderr}")
            return False
        
        self.logger.info(f"Successfully posted comment to PR #{pr_number}")
        return True
    
    def create_pr(self, title: str, body: str, head: str, base: str = "main", op_id: Optional[str] = None) -> Optional[str]:
        """Create a new PR and return its URL with idempotency marker."""
        # Add operation marker for idempotency
        marked_body = self._add_op_marker(body, op_id)
        
        cmd = [
            'pr', 'create',
            '--title', title,
            '--body', marked_body,
            '--head', head,
            '--base', base
        ]
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to create PR: {result.stderr}")
            return None
        
        # Extract PR URL from output
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if 'https://github.com' in line and '/pull/' in line:
                url = line.strip()
                self.logger.info(f"Successfully created PR: {url}")
                return url
        
        return None
    
    def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None, op_id: Optional[str] = None) -> Optional[str]:
        """Create a new issue and return its URL with idempotency marker."""
        # Add operation marker for idempotency
        marked_body = self._add_op_marker(body, op_id)
        
        cmd = ['issue', 'create', '--title', title, '--body', marked_body]
        
        if labels:
            cmd.extend(['--label', ','.join(labels)])
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to create issue: {result.stderr}")
            return None
        
        # Extract issue URL from output
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if 'https://github.com' in line and '/issues/' in line:
                url = line.strip()
                self.logger.info(f"Successfully created issue: {url}")
                return url
        
        return None
    
    def get_default_branch(self) -> Optional[str]:
        """Get the repository's default branch name."""
        cmd = ['repo', 'view', '--json', 'defaultBranchRef']
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to get default branch: {result.stderr}")
            return None
        
        try:
            data = json.loads(result.stdout)
            return data.get('defaultBranchRef', {}).get('name')
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse default branch data: {e}")
            return None
    
    def get_project_info(self, project_number: int) -> Optional[Dict[str, Any]]:
        """Get project information."""
        cmd = ['project', 'view', str(project_number), '--json', 'title,body']
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to get project info #{project_number}: {result.stderr}")
            return None
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse project info: {e}")
            return None
    
    def get_issue_comments(self, issue_number: int) -> List[Dict[str, Any]]:
        """Get comments on an issue."""
        cmd = ['api', f'repos/{{owner}}/{{repo}}/issues/{issue_number}/comments']
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to get issue comments #{issue_number}: {result.stderr}")
            return []
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse issue comments: {e}")
            return []
    
    def get_pr_comments(self, pr_number: int) -> List[Dict[str, Any]]:
        """Get comments on a PR."""
        cmd = ['api', f'repos/{{owner}}/{{repo}}/pulls/{pr_number}/comments']
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to get PR comments #{pr_number}: {result.stderr}")
            return []
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse PR comments: {e}")
            return []
    
    def check_pr_status(self, pr_number: int) -> Dict[str, Any]:
        """Check PR status including checks and reviews."""
        cmd = ['pr', 'view', str(pr_number), '--json', 'statusCheckRollup,reviewDecision']
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to get PR status #{pr_number}: {result.stderr}")
            return {}
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse PR status: {e}")
            return {}
    
    def get_repo_info(self) -> Optional[Dict[str, Any]]:
        """Get repository information."""
        cmd = ['repo', 'view', '--json', 'name,owner,description,url,isPrivate,defaultBranchRef']
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to get repo info: {result.stderr}")
            return None
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse repo info: {e}")
            return None
    
    def list_issues(self, state: str = "open", limit: int = 30) -> List[Dict[str, Any]]:
        """List repository issues."""
        cmd = ['issue', 'list', '--state', state, '--limit', str(limit), '--json', 'number,title,labels,url,author,state']
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to list issues: {result.stderr}")
            return []
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse issues list: {e}")
            return []
    
    def list_prs(self, state: str = "open", limit: int = 30) -> List[Dict[str, Any]]:
        """List repository PRs."""
        cmd = ['pr', 'list', '--state', state, '--limit', str(limit), '--json', 'number,title,headRefName,baseRefName,author,url']
        
        result = self._run_gh_command(cmd)
        if not result.success:
            self.logger.error(f"Failed to list PRs: {result.stderr}")
            return []
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse PRs list: {e}")
            return []