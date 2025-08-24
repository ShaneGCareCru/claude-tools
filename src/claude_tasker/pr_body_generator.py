"""PR body generation module with template detection and context aggregation."""

import subprocess
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path
from .github_client import IssueData


class PRBodyGenerator:
    """Generates intelligent PR body content with template detection and context aggregation."""
    
    def __init__(self):
        self.max_size = 10000  # GitHub PR body size limit
        self.template_paths = [
            '.github/pull_request_template.md',
            '.github/PULL_REQUEST_TEMPLATE.md',
            '.github/pull_request_template/default.md',
            'PULL_REQUEST_TEMPLATE.md',
            'pull_request_template.md'
        ]
    
    def detect_templates(self, repo_path: str = ".") -> Optional[str]:
        """Detect PR template in repository."""
        repo_path = Path(repo_path)
        
        for template_path in self.template_paths:
            full_path = repo_path / template_path
            if full_path.exists():
                try:
                    return full_path.read_text(encoding='utf-8')
                except Exception:
                    continue
        
        return None
    
    def aggregate_context(self, issue_data: IssueData, git_diff: str, 
                         branch_name: str, commit_log: str) -> Dict[str, Any]:
        """Aggregate context for PR body generation."""
        context = {
            'issue': {
                'number': issue_data.number,
                'title': issue_data.title,
                'body': issue_data.body[:1000],  # Truncate if too long
                'labels': issue_data.labels,
                'url': issue_data.url
            },
            'changes': {
                'branch': branch_name,
                'diff_summary': self._summarize_diff(git_diff),
                'commit_log': commit_log
            },
            'stats': self._calculate_change_stats(git_diff)
        }
        
        return context
    
    def _summarize_diff(self, git_diff: str) -> Dict[str, Any]:
        """Summarize git diff changes."""
        if not git_diff:
            return {'files_changed': 0, 'summary': 'No changes'}
        
        lines = git_diff.split('\n')
        files_changed = []
        additions = 0
        deletions = 0
        
        for line in lines:
            if line.startswith('diff --git'):
                # Extract file path from diff header
                parts = line.split(' ')
                if len(parts) >= 4:
                    file_path = parts[3][2:]  # Remove 'b/' prefix
                    files_changed.append(file_path)
            elif line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1
        
        return {
            'files_changed': len(files_changed),
            'files': files_changed[:10],  # Limit to first 10 files
            'additions': additions,
            'deletions': deletions,
            'net_change': additions - deletions
        }
    
    def _calculate_change_stats(self, git_diff: str) -> Dict[str, int]:
        """Calculate detailed change statistics."""
        stats = {
            'files_added': 0,
            'files_modified': 0,
            'files_deleted': 0,
            'lines_added': 0,
            'lines_deleted': 0
        }
        
        if not git_diff:
            return stats
        
        lines = git_diff.split('\n')
        
        for line in lines:
            if line.startswith('diff --git'):
                pass  # Just tracking file boundaries
            elif line.startswith('new file mode'):
                stats['files_added'] += 1
            elif line.startswith('deleted file mode'):
                stats['files_deleted'] += 1
            elif line.startswith('+') and not line.startswith('+++'):
                stats['lines_added'] += 1
            elif line.startswith('-') and not line.startswith('---'):
                stats['lines_deleted'] += 1
        
        # Count modified files (files that are neither added nor deleted)
        total_files = len([line for line in lines if line.startswith('diff --git')])
        stats['files_modified'] = total_files - stats['files_added'] - stats['files_deleted']
        
        return stats
    
    def generate_with_llm(self, context: Dict[str, Any], template: Optional[str] = None) -> Optional[str]:
        """Generate PR body using LLM CLI tool."""
        prompt = self._build_generation_prompt(context, template)
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name
            
            result = subprocess.run([
                'llm', 'prompt', prompt_file,
                '--max-tokens', '2000'
            ], capture_output=True, text=True, check=False)
            
            Path(prompt_file).unlink()  # Clean up temp file
            
            if result.returncode == 0:
                generated_body = result.stdout.strip()
                return self._ensure_size_limit(generated_body)
            else:
                return None
                
        except (FileNotFoundError, Exception):
            return None
    
    def generate_with_claude(self, context: Dict[str, Any], template: Optional[str] = None) -> Optional[str]:
        """Generate PR body using Claude CLI tool."""
        prompt = self._build_generation_prompt(context, template)
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name
            
            result = subprocess.run([
                'claude', '--file', prompt_file,
                '--max-tokens', '2000'
            ], capture_output=True, text=True, check=False)
            
            Path(prompt_file).unlink()  # Clean up temp file
            
            if result.returncode == 0:
                generated_body = result.stdout.strip()
                return self._ensure_size_limit(generated_body)
            else:
                return None
                
        except (FileNotFoundError, Exception):
            return None
    
    def _build_generation_prompt(self, context: Dict[str, Any], template: Optional[str] = None) -> str:
        """Build prompt for PR body generation."""
        prompt_parts = [
            "Generate a comprehensive PR body for the following changes:",
            "\n## Issue Context",
            f"Issue #{context['issue']['number']}: {context['issue']['title']}",
            f"Issue Body: {context['issue']['body']}",
            f"Issue Labels: {', '.join(context['issue']['labels']) if context['issue']['labels'] else 'None'}",
        ]
        
        if context['changes']['diff_summary']:
            summary = context['changes']['diff_summary']
            prompt_parts.extend([
                "\n## Changes Summary",
                f"Branch: {context['changes']['branch']}",
                f"Files changed: {summary['files_changed']}",
                f"Lines: +{summary['additions']}/-{summary['deletions']}",
            ])
            
            if summary.get('files'):
                prompt_parts.append(f"Modified files: {', '.join(summary['files'])}")
        
        if context['changes']['commit_log']:
            prompt_parts.extend([
                "\n## Commit History",
                context['changes']['commit_log']
            ])
        
        if template:
            prompt_parts.extend([
                "\n## PR Template to Follow",
                template
            ])
        
        prompt_parts.extend([
            "\n## Instructions",
            "Create a clear, professional PR body that:",
            "1. Summarizes the changes made",
            "2. References the related issue",
            "3. Explains the approach taken",
            "4. Includes testing information if applicable",
            "5. Follows the template structure if provided",
            "6. Is concise but informative",
            "",
            "Return only the PR body content, no additional text."
        ])
        
        return "\n".join(prompt_parts)
    
    def _ensure_size_limit(self, content: str) -> str:
        """Ensure content fits within GitHub's size limits."""
        if len(content) <= self.max_size:
            return content
        
        # Truncate and add notice
        truncated = content[:self.max_size - 200]  # Leave room for notice
        truncated += f"\n\n---\n*[Content truncated to fit GitHub's {self.max_size} character limit]*"
        
        return truncated
    
    def generate_pr_body(self, issue_data: IssueData, git_diff: str, branch_name: str,
                        commit_log: str, repo_path: str = ".") -> str:
        """Generate complete PR body with template detection and context aggregation."""
        # Detect template
        template = self.detect_templates(repo_path)
        
        # Aggregate context
        context = self.aggregate_context(issue_data, git_diff, branch_name, commit_log)
        
        # Try LLM first, fallback to Claude
        pr_body = self.generate_with_llm(context, template)
        if not pr_body:
            pr_body = self.generate_with_claude(context, template)
        
        # If both fail, create a basic PR body
        if not pr_body:
            pr_body = self._create_fallback_pr_body(context, template)
        
        return pr_body
    
    def _create_fallback_pr_body(self, context: Dict[str, Any], template: Optional[str] = None) -> str:
        """Create a basic PR body when AI generation fails."""
        parts = [
            "## Summary",
            f"This PR addresses issue #{context['issue']['number']}: {context['issue']['title']}",
            "",
            "## Changes",
        ]
        
        stats = context.get('stats', {})
        if stats:
            changes = []
            if stats['files_added'] > 0:
                changes.append(f"{stats['files_added']} files added")
            if stats['files_modified'] > 0:
                changes.append(f"{stats['files_modified']} files modified")
            if stats['files_deleted'] > 0:
                changes.append(f"{stats['files_deleted']} files deleted")
            
            if changes:
                parts.append(f"- {', '.join(changes)}")
            
            parts.append(f"- {stats['lines_added']} lines added, {stats['lines_deleted']} lines deleted")
        
        parts.extend([
            "",
            "## Related Issue",
            f"Fixes #{context['issue']['number']}",
            "",
            "## Testing",
            "- [ ] Manual testing completed",
            "- [ ] Automated tests pass",
            "",
            "🤖 Generated with [Claude Code](https://claude.ai/code)"
        ])
        
        return "\n".join(parts)
    
    def _format_labels(self, labels):
        """Format labels for display in PR body."""
        if not labels:
            return "None"
        return ", ".join(f"`{label}`" for label in labels)