"""PR body generation module with template detection and context aggregation."""

import tempfile
from typing import Optional, Dict, Any
from pathlib import Path
from .github_client import IssueData
from .logging_config import get_logger
from .services.command_executor import CommandExecutor

logger = get_logger(__name__)


class PRBodyGenerator:
    """Generates intelligent PR body content with template detection and context aggregation."""
    
    def __init__(self, command_executor: CommandExecutor):
        self.executor = command_executor
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
                'body': issue_data.body[:1000] + ('...' if len(issue_data.body) > 1000 else ''),  # Truncate if too long
                'labels': issue_data.labels,
                'url': issue_data.url,
                'assignee': issue_data.assignee,
                'milestone': issue_data.milestone
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
            return {
                'files_changed': 0,
                'files': [],
                'additions': 0,
                'deletions': 0,
                'net_change': 0,
                'summary': 'No changes'
            }
        
        lines = git_diff.split('\n')
        files_changed = []
        additions = 0
        deletions = 0
        
        for line in lines:
            line = line.strip()  # Remove leading/trailing whitespace
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
            line = line.strip()  # Remove leading/trailing whitespace
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
        total_files = len([line.strip() for line in lines if line.strip().startswith('diff --git')])
        stats['files_modified'] = total_files - stats['files_added'] - stats['files_deleted']
        
        return stats
    
    def generate_with_llm(self, context: Dict[str, Any], template: Optional[str] = None) -> Optional[str]:
        """Generate PR body using LLM CLI tool."""
        prompt = self._build_generation_prompt(context, template)
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name
            
            result = self.executor.execute([
                'llm', 'prompt', prompt_file,
                '--max-tokens', '2000'
            ])
            
            Path(prompt_file).unlink()  # Clean up temp file
            
            if result.success:
                generated_body = result.stdout.strip()
                return self._ensure_size_limit(generated_body)
            else:
                logger.warning(f"LLM generation failed: {result.stderr}")
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
            
            result = self.executor.execute([
                'claude', '--file', prompt_file,
                '--max-tokens', '2000'
            ])
            
            Path(prompt_file).unlink()  # Clean up temp file
            
            if result.success:
                generated_body = result.stdout.strip()
                return self._ensure_size_limit(generated_body)
            else:
                logger.warning(f"Claude generation failed: {result.stderr}")
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
            f"Issue Labels: {self._format_labels(context['issue']['labels'])}",
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
        try:
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
        
        except Exception as e:
            logger.error(f"Failed to generate PR body: {e}")
            return f"Failed to generate PR body: {str(e)}"
    
    def _create_fallback_pr_body(self, context: Dict[str, Any], template: Optional[str] = None) -> str:
        """Create a basic PR body when AI generation fails."""
        parts = [
            "## Summary",
            f"This PR addresses issue #{context['issue']['number']}: {context['issue']['title']}",
        ]
        
        # Add issue body if available and include truncation indicator
        if context['issue'].get('body'):
            parts.extend([
                "",
                "## Issue Description",
                context['issue']['body']  # This will include "..." if truncated
            ])
        
        parts.extend([
            "",
            "## Changes",
        ])
        
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
        
        # Add file names if available in diff summary
        diff_summary = context.get('changes', {}).get('diff_summary', {})
        if diff_summary.get('files'):
            parts.extend([
                "",
                "## Modified Files",
                f"- {', '.join(diff_summary['files'])}"
            ])
        
        parts.extend([
            "",
            "## Related Issue",
            f"Fixes #{context['issue']['number']}",
            ""
        ])
        
        # Add labels section
        if context['issue'].get('labels'):
            parts.extend([
                "## Labels",
                f"Associated labels: {', '.join(context['issue']['labels'])}",
                ""
            ])
        
        # Add assignee and milestone if present
        if context['issue'].get('assignee'):
            parts.append(f"**Assignee:** {context['issue']['assignee']}")
        if context['issue'].get('milestone'):
            parts.append(f"**Milestone:** {context['issue']['milestone']}")
            
        if context['issue'].get('assignee') or context['issue'].get('milestone'):
            parts.append("")
        
        parts.extend([
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
    
    def _generate_test_checklist(self, git_diff):
        """Generate test checklist based on changes."""
        if not git_diff:
            return "- [ ] Run existing tests\n- [ ] Verify no regressions"
        
        checklist_items = []
        
        # Extract file names from diff
        import re
        files_changed = re.findall(r'diff --git a/([^\s]+)', git_diff)
        
        # Check if test files were modified
        if any("test_" in f or "/tests/" in f for f in files_changed):
            checklist_items.append("- [ ] Run new/modified tests")
            test_files = [f for f in files_changed if "test_" in f or "/tests/" in f]
            for test_file in test_files:
                checklist_items.append(f"- [ ] Verify {test_file} passes")
        
        # Check if source files were modified
        src_files = [f for f in files_changed if f.endswith('.py') and 'test_' not in f]
        if src_files:
            checklist_items.append("- [ ] Test affected functionality")
            for src_file in src_files:
                checklist_items.append(f"- [ ] Test changes in {src_file}")
        
        # Check for config changes
        config_files = [f for f in files_changed if any(f.endswith(ext) for ext in ['.yml', '.yaml', '.json', '.toml', '.cfg', '.ini', '.txt'])]
        if config_files:
            # Special handling for dependency files
            if any('package.json' in f or 'requirements.txt' in f or 'poetry.lock' in f for f in config_files):
                checklist_items.append("- [ ] Verify dependency installation")
            else:
                checklist_items.append("- [ ] Verify configuration changes")
            for config_file in config_files:
                checklist_items.append(f"- [ ] Test {config_file} changes")
            
        return '\n'.join(checklist_items) if checklist_items else "- [ ] Run existing tests\n- [ ] Verify no regressions"
    
    def _generate_changes_section(self, git_diff: str) -> str:
        """Generate changes section based on git diff."""
        if not git_diff or not git_diff.strip():
            return "No file changes detected"
        
        diff_summary = self._summarize_diff(git_diff)
        changes = []
        
        if diff_summary.get('files'):
            changes.append(f"Files modified: {', '.join(diff_summary['files'])}")
        
        if diff_summary.get('additions', 0) > 0:
            changes.append(f"{diff_summary['additions']} additions")
        
        if diff_summary.get('deletions', 0) > 0:
            changes.append(f"{diff_summary['deletions']} deletions")
        
        return " • ".join(changes) if changes else "File changes detected"
    
    def _extract_files_from_diff(self, git_diff: str) -> list:
        """Extract file paths from git diff."""
        if not git_diff:
            return []
        
        files = []
        for line in git_diff.split('\n'):
            line = line.strip()
            if line.startswith('diff --git'):
                parts = line.split(' ')
                if len(parts) >= 4:
                    file_path = parts[3][2:]  # Remove 'b/' prefix
                    files.append(file_path)
        
        return files
    
    def _generate_implementation_approach(self, commit_log: str) -> str:
        """Generate implementation approach section from commit log."""
        if not commit_log or not commit_log.strip():
            return ""
        
        lines = [line.strip() for line in commit_log.strip().split('\n') if line.strip()]
        
        # Filter out automated commits
        filtered_lines = []
        automated_keywords = ['automated', 'auto-generated', 'bot:', 'dependabot', 'github-actions']
        
        for line in lines:
            if not any(keyword in line.lower() for keyword in automated_keywords):
                # Clean up commit hash prefixes
                if ' ' in line:
                    commit_msg = ' '.join(line.split(' ')[1:])  # Remove hash prefix
                    filtered_lines.append(f"• {commit_msg}")
                else:
                    filtered_lines.append(f"• {line}")
        
        if not filtered_lines:
            return ""
        
        # Include section header when there are commits
        return "Implementation Approach:\n" + '\n'.join(filtered_lines)