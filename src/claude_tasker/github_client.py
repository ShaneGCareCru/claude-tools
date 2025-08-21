"""GitHub CLI integration module for claude-tasker."""

import subprocess
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


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


class GitHubClient:
    """GitHub CLI integration for issue and PR management."""
    
    def __init__(self, retry_attempts: int = 3, base_delay: float = 1.0):
        self.retry_attempts = retry_attempts
        self.base_delay = base_delay
    
    def _run_gh_command(self, cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Execute GitHub CLI command with retry logic."""
        for attempt in range(self.retry_attempts):
            try:
                result = subprocess.run(
                    ['gh'] + cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    **kwargs
                )
                
                # Handle rate limiting
                if result.returncode == 1 and 'API rate limit' in result.stderr:
                    if attempt < self.retry_attempts - 1:
                        delay = self.base_delay * (2 ** attempt)  # Exponential backoff
                        time.sleep(delay)
                        continue
                
                return result
                
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    raise
                time.sleep(self.base_delay * (2 ** attempt))
        
        return result
    
    def get_issue(self, issue_number: int) -> Optional[IssueData]:
        """Fetch issue data from GitHub."""
        cmd = [
            'issue', 'view', str(issue_number),
            '--json', 'number,title,body,labels,url,author,state'
        ]
        
        result = self._run_gh_command(cmd)
        if result.returncode != 0:
            return None
        
        try:
            data = json.loads(result.stdout)
            return IssueData(
                number=data['number'],
                title=data['title'],
                body=data.get('body', ''),
                labels=[label['name'] for label in data.get('labels', [])],
                url=data['url'],
                author=data['author']['login'],
                state=data['state']
            )
        except (json.JSONDecodeError, KeyError):
            return None
    
    def get_pr(self, pr_number: int) -> Optional[PRData]:
        """Fetch PR data from GitHub."""
        cmd = [
            'pr', 'view', str(pr_number),
            '--json', 'number,title,body,headRefName,baseRefName,author,additions,deletions,changedFiles,url'
        ]
        
        result = self._run_gh_command(cmd)
        if result.returncode != 0:
            return None
        
        try:
            data = json.loads(result.stdout)
            return PRData(
                number=data['number'],
                title=data['title'], 
                body=data.get('body', ''),
                head_ref=data['headRefName'],
                base_ref=data['baseRefName'],
                author=data['author']['login'],
                additions=data.get('additions', 0),
                deletions=data.get('deletions', 0),
                changed_files=data.get('changedFiles', 0),
                url=data['url']
            )
        except (json.JSONDecodeError, KeyError):
            return None
    
    def get_pr_diff(self, pr_number: int) -> Optional[str]:
        """Get PR diff content."""
        cmd = ['pr', 'diff', str(pr_number)]
        
        result = self._run_gh_command(cmd)
        if result.returncode != 0:
            return None
        
        return result.stdout
    
    def get_pr_files(self, pr_number: int) -> List[str]:
        """Get list of files changed in PR."""
        cmd = ['pr', 'view', str(pr_number), '--json', 'files']
        
        result = self._run_gh_command(cmd)
        if result.returncode != 0:
            return []
        
        try:
            data = json.loads(result.stdout)
            return [file_info['path'] for file_info in data.get('files', [])]
        except (json.JSONDecodeError, KeyError):
            return []
    
    def comment_on_issue(self, issue_number: int, comment: str) -> bool:
        """Add comment to GitHub issue."""
        cmd = ['issue', 'comment', str(issue_number), '--body', comment]
        
        result = self._run_gh_command(cmd)
        return result.returncode == 0
    
    def comment_on_pr(self, pr_number: int, comment: str) -> bool:
        """Add comment to GitHub PR."""
        cmd = ['pr', 'comment', str(pr_number), '--body', comment]
        
        result = self._run_gh_command(cmd)
        return result.returncode == 0
    
    def create_pr(self, title: str, body: str, head: str, base: str = "main") -> Optional[str]:
        """Create a new PR and return its URL."""
        cmd = [
            'pr', 'create',
            '--title', title,
            '--body', body,
            '--head', head,
            '--base', base
        ]
        
        result = self._run_gh_command(cmd)
        if result.returncode != 0:
            return None
        
        # Extract PR URL from output
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if 'https://github.com' in line and '/pull/' in line:
                return line.strip()
        
        return None
    
    def get_project_info(self, project_number: int) -> Optional[Dict[str, Any]]:
        """Get project information."""
        cmd = ['project', 'view', str(project_number), '--json', 'title,body']
        
        result = self._run_gh_command(cmd)
        if result.returncode != 0:
            return None
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
    
    def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None) -> Optional[str]:
        """Create a new issue and return its URL."""
        cmd = ['issue', 'create', '--title', title, '--body', body]
        
        if labels:
            cmd.extend(['--label', ','.join(labels)])
        
        result = self._run_gh_command(cmd)
        if result.returncode != 0:
            return None
        
        # Extract issue URL from output
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if 'https://github.com' in line and '/issues/' in line:
                return line.strip()
        
        return None
    
    def get_issue_comments(self, issue_number: int) -> List[Dict[str, Any]]:
        """Get comments on an issue."""
        cmd = ['api', f'repos/{{owner}}/{{repo}}/issues/{issue_number}/comments']
        
        result = self._run_gh_command(cmd)
        if result.returncode != 0:
            return []
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
    
    def get_pr_comments(self, pr_number: int) -> List[Dict[str, Any]]:
        """Get comments on a PR."""
        cmd = ['api', f'repos/{{owner}}/{{repo}}/pulls/{pr_number}/comments']
        
        result = self._run_gh_command(cmd)
        if result.returncode != 0:
            return []
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
    
    def check_pr_status(self, pr_number: int) -> Dict[str, Any]:
        """Check PR status including checks and reviews."""
        cmd = ['pr', 'view', str(pr_number), '--json', 'statusCheckRollup,reviewDecision']
        
        result = self._run_gh_command(cmd)
        if result.returncode != 0:
            return {}
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {}