"""Environment validation module for claude-tasker."""

import subprocess
import os
from typing import List, Dict, Tuple


class EnvironmentValidator:
    """Validates environment and dependencies for claude-tasker execution."""
    
    def __init__(self):
        self.required_tools = {
            'git': 'git',
            'gh': 'gh (GitHub CLI)', 
            'jq': 'jq'
        }
        self.optional_tools = {
            'claude': 'Claude Code CLI (required for full execution)',
            'llm': 'LLM CLI tool (fallback for prompt generation)'
        }
    
    def validate_git_repository(self, path: str = ".") -> Tuple[bool, str]:
        """Validate that current directory is a git repository."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=path,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return True, "Valid git repository"
            else:
                return False, "Not a git repository"
        except FileNotFoundError:
            return False, "Git not found"
    
    def validate_github_remote(self, path: str = ".") -> Tuple[bool, str]:
        """Validate that repository has GitHub remote."""
        try:
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=path,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0 and 'github.com' in result.stdout:
                return True, f"GitHub remote: {result.stdout.strip()}"
            else:
                return False, "No GitHub remote found"
        except FileNotFoundError:
            return False, "Git not found"
    
    def check_claude_md(self, path: str = ".") -> Tuple[bool, str]:
        """Check for CLAUDE.md file existence."""
        claude_md_path = os.path.join(path, "CLAUDE.md")
        if os.path.exists(claude_md_path):
            return True, f"CLAUDE.md found at {claude_md_path}"
        else:
            return False, "CLAUDE.md not found - required for project context"
    
    def check_tool_availability(self, tool: str) -> Tuple[bool, str]:
        """Check if a specific tool is available."""
        try:
            result = subprocess.run(
                ['command', '-v', tool],
                capture_output=True,
                text=True,
                check=False,
                shell=True
            )
            if result.returncode == 0:
                return True, f"{tool} found at {result.stdout.strip()}"
            else:
                return False, f"{tool} not found"
        except Exception as e:
            return False, f"Error checking {tool}: {str(e)}"
    
    def validate_all_dependencies(self, path: str = ".", prompt_only: bool = False) -> Dict[str, any]:
        """Perform comprehensive dependency validation."""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'tool_status': {}
        }
        
        # Check git repository
        git_valid, git_msg = self.validate_git_repository(path)
        if not git_valid:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Git repository check failed: {git_msg}")
        
        # Check GitHub remote
        remote_valid, remote_msg = self.validate_github_remote(path)
        if not remote_valid:
            validation_results['valid'] = False
            validation_results['errors'].append(f"GitHub remote check failed: {remote_msg}")
        
        # Check CLAUDE.md
        claude_md_valid, claude_md_msg = self.check_claude_md(path)
        if not claude_md_valid:
            validation_results['valid'] = False
            validation_results['errors'].append(f"CLAUDE.md check failed: {claude_md_msg}")
        
        # Check required tools
        for tool, description in self.required_tools.items():
            available, status = self.check_tool_availability(tool)
            validation_results['tool_status'][tool] = {
                'available': available,
                'status': status,
                'required': True
            }
            if not available:
                validation_results['valid'] = False
                validation_results['errors'].append(f"Missing required tools: {description}")
        
        # Check optional tools (warnings only)
        for tool, description in self.optional_tools.items():
            available, status = self.check_tool_availability(tool)
            validation_results['tool_status'][tool] = {
                'available': available,
                'status': status,
                'required': False
            }
            if not available:
                if tool == 'claude' and not prompt_only:
                    validation_results['warnings'].append(
                        f"Warning: {tool} not found - {description}. Use --prompt-only flag to skip execution."
                    )
                elif tool == 'llm':
                    validation_results['warnings'].append(
                        f"Warning: {tool} not found - {description}. Will use Claude for prompt generation."
                    )
        
        return validation_results
    
    def get_missing_dependencies(self, validation_results: Dict[str, any]) -> List[str]:
        """Get list of missing required dependencies."""
        missing = []
        for tool, info in validation_results.get('tool_status', {}).items():
            if info['required'] and not info['available']:
                missing.append(tool)
        return missing
    
    def format_validation_report(self, validation_results: Dict[str, any]) -> str:
        """Format validation results into human-readable report."""
        report_lines = []
        
        if validation_results['valid']:
            report_lines.append("✅ Environment validation passed")
        else:
            report_lines.append("❌ Environment validation failed")
        
        # Show errors
        for error in validation_results['errors']:
            report_lines.append(f"  ERROR: {error}")
        
        # Show warnings
        for warning in validation_results['warnings']:
            report_lines.append(f"  WARNING: {warning}")
        
        # Show tool status
        report_lines.append("\nTool availability:")
        for tool, info in validation_results['tool_status'].items():
            status_icon = "✅" if info['available'] else "❌"
            req_text = " (required)" if info['required'] else " (optional)"
            report_lines.append(f"  {status_icon} {tool}{req_text}: {info['status']}")
        
        return "\n".join(report_lines)