"""Intelligent PR body generation with template detection and context aggregation."""
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any


class PRBodyGenerator:
    """Handles intelligent PR body generation with template detection and LLM integration."""
    
    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize PR body generator.
        
        Args:
            repo_path: Path to git repository. Defaults to current directory.
        """
        self.repo_path = repo_path or Path.cwd()
        self.github_dir = self.repo_path / ".github"
    
    def detect_pr_template(self) -> Optional[str]:
        """Detect PR template files from .github directory.
        
        Returns:
            Template content if found, None otherwise.
        """
        if not self.github_dir.exists():
            return None
        
        # Priority order for template detection
        template_names = [
            "pull_request_template.md",
            "PULL_REQUEST_TEMPLATE.md",
            "pull_request_template.txt",
            "PULL_REQUEST_TEMPLATE.txt"
        ]
        
        for template_name in template_names:
            template_path = self.github_dir / template_name
            if template_path.exists():
                try:
                    return template_path.read_text(encoding='utf-8')
                except Exception:
                    continue
        
        return None
    
    def aggregate_context(self, issue_number: str) -> Dict[str, Any]:
        """Aggregate context for PR body generation.
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Dictionary containing aggregated context
        """
        context = {}
        
        try:
            # Get issue details
            result = subprocess.run(
                ["gh", "issue", "view", issue_number, "--json", "title,body,labels"],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            if result.returncode == 0:
                issue_data = json.loads(result.stdout)
                context["issue"] = issue_data
            else:
                context["issue"] = {"title": "Unknown Issue", "body": "", "labels": []}
        except Exception:
            context["issue"] = {"title": "Unknown Issue", "body": "", "labels": []}
        
        try:
            # Get git diff
            result = subprocess.run(
                ["git", "diff", "main...HEAD"],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            if result.returncode != 0:
                # Fallback to master
                result = subprocess.run(
                    ["git", "diff", "master...HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=self.repo_path
                )
            
            context["diff"] = result.stdout if result.returncode == 0 else ""
        except Exception:
            context["diff"] = ""
        
        try:
            # Get recent commits
            result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            context["commits"] = result.stdout if result.returncode == 0 else ""
        except Exception:
            context["commits"] = ""
        
        # Get PR template
        context["template"] = self.detect_pr_template()
        
        return context
    
    def generate_with_llm(self, context: Dict[str, Any]) -> str:
        """Generate PR body using LLM tool with Claude fallback.
        
        Args:
            context: Aggregated context dictionary
            
        Returns:
            Generated PR body content
        """
        # Check if LLM tool is available
        try:
            result = subprocess.run(
                ["command", "-v", "llm"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return self._generate_with_llm_tool(context)
        except Exception:
            pass
        
        # Fallback to Claude
        return self._generate_with_claude(context)
    
    def _generate_with_llm_tool(self, context: Dict[str, Any]) -> str:
        """Generate PR body using LLM tool.
        
        Args:
            context: Aggregated context dictionary
            
        Returns:
            Generated PR body content
        """
        prompt = self._build_prompt(context)
        
        try:
            # Create a temporary file for the prompt
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                temp_file = f.name
            
            # Run LLM tool
            result = subprocess.run(
                ["llm", "chat", "-f", temp_file],
                capture_output=True,
                text=True
            )
            
            # Clean up temp file
            Path(temp_file).unlink(missing_ok=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
            
        except Exception:
            pass
        
        return self._generate_fallback_body(context)
    
    def _generate_with_claude(self, context: Dict[str, Any]) -> str:
        """Generate PR body using Claude CLI.
        
        Args:
            context: Aggregated context dictionary
            
        Returns:
            Generated PR body content
        """
        prompt = self._build_prompt(context)
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                temp_file = f.name
            
            result = subprocess.run(
                ["claude", "--input", temp_file],
                capture_output=True,
                text=True
            )
            
            Path(temp_file).unlink(missing_ok=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
            
        except Exception:
            pass
        
        return self._generate_fallback_body(context)
    
    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for PR body generation.
        
        Args:
            context: Aggregated context dictionary
            
        Returns:
            Formatted prompt string
        """
        issue = context.get("issue", {})
        diff = context.get("diff", "")
        commits = context.get("commits", "")
        template = context.get("template")
        
        prompt = f"""Generate a professional PR body based on the following context:

Issue: {issue.get('title', 'Unknown')}
Description: {issue.get('body', 'No description')}
Labels: {', '.join([label.get('name', '') for label in issue.get('labels', [])])}

Recent commits:
{commits}

Git diff (truncated for size):
{diff[:5000] if len(diff) > 5000 else diff}
"""
        
        if template:
            prompt += f"\nPlease follow this template structure:\n{template}"
        
        prompt += """

Generate a concise, professional PR body that:
1. Summarizes the changes clearly
2. Highlights key implementation details
3. Notes testing status
4. Stays under 10,000 characters
5. Uses proper markdown formatting
"""
        
        return prompt
    
    def _generate_fallback_body(self, context: Dict[str, Any]) -> str:
        """Generate fallback PR body when LLM tools fail.
        
        Args:
            context: Aggregated context dictionary
            
        Returns:
            Basic PR body content
        """
        issue = context.get("issue", {})
        
        body = "## Summary\n"
        body += f"Implements: {issue.get('title', 'Unknown Issue')}\n\n"
        
        if issue.get("body"):
            body += "## Description\n"
            body += f"{issue.get('body', '')}\n\n"
        
        body += "## Changes Made\n"
        body += "- Implementation completed\n"
        body += "- Tests updated\n\n"
        
        body += "## Testing\n"
        body += "- [ ] Tests pass\n"
        body += "- [ ] Manual testing completed\n"
        
        return body
    
    def generate_pr_body(self, issue_number: str) -> str:
        """Main method to generate PR body.
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Generated PR body content
        """
        context = self.aggregate_context(issue_number)
        return self.generate_with_llm(context)