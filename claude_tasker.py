#!/usr/bin/env python3
"""Claude Tasker - Python implementation for argument parsing and environment validation."""

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class Arguments:
    """Structured arguments object."""
    
    # Core modes
    issue_numbers: Optional[List[int]] = None
    review_pr_numbers: Optional[List[int]] = None
    bug_description: Optional[str] = None
    
    # Flags
    project_id: Optional[str] = None
    timeout: int = 10
    coder: str = "claude"
    base_branch: Optional[str] = None
    prompt_only: bool = False
    interactive: bool = False
    auto_pr_review: bool = False
    help_requested: bool = False


class ArgumentParser:
    """Parse and validate claude-tasker command-line arguments."""
    
    def parse(self, args: List[str]) -> Arguments:
        """Parse command-line arguments and return structured Arguments object."""
        arguments = Arguments()
        i = 0
        
        while i < len(args):
            arg = args[i]
            
            if arg == "--help":
                arguments.help_requested = True
                return arguments
            elif arg == "--review-pr":
                if i + 1 >= len(args):
                    raise ValueError("--review-pr requires a PR number or range")
                i += 1
                pr_arg = args[i]
                arguments.review_pr_numbers = self._parse_numbers(pr_arg)
            elif arg == "--bug":
                if i + 1 >= len(args):
                    raise ValueError("--bug requires a description")
                i += 1
                bug_desc = args[i]
                if not bug_desc.strip():
                    raise ValueError("--bug requires a description")
                arguments.bug_description = bug_desc
            elif arg == "--project":
                if i + 1 >= len(args):
                    raise ValueError("--project requires a project ID")
                i += 1
                project_id = args[i]
                if not project_id.strip() or not project_id.replace('-', '').replace('_', '').isalnum():
                    raise ValueError("--project requires a project ID")
                arguments.project_id = project_id
            elif arg == "--timeout":
                if i + 1 >= len(args):
                    raise ValueError("--timeout requires a number of seconds")
                i += 1
                timeout_str = args[i]
                try:
                    arguments.timeout = int(timeout_str)
                except ValueError:
                    raise ValueError("--timeout requires a number of seconds")
            elif arg == "--coder":
                if i + 1 >= len(args):
                    raise ValueError("--coder requires either 'claude' or 'codex'")
                i += 1
                coder = args[i]
                if coder not in ["claude", "codex"]:
                    raise ValueError("--coder requires either 'claude' or 'codex'")
                arguments.coder = coder
            elif arg == "--base-branch":
                if i + 1 >= len(args):
                    raise ValueError("--base-branch requires a branch name")
                i += 1
                branch = args[i]
                if not branch.strip():
                    raise ValueError("--base-branch requires a branch name")
                arguments.base_branch = branch
            elif arg == "--prompt-only":
                arguments.prompt_only = True
            elif arg == "--interactive":
                arguments.interactive = True
            elif arg == "--auto-pr-review":
                arguments.auto_pr_review = True
            elif arg.startswith("-"):
                raise ValueError(f"Invalid argument: {arg} (expected: number, range, --review-pr, or --bug)")
            else:
                # Should be issue number or range
                if self._is_number_or_range(arg):
                    arguments.issue_numbers = self._parse_numbers(arg)
                else:
                    raise ValueError(f"Invalid argument: {arg} (expected: number, range, --review-pr, or --bug)")
            
            i += 1
        
        return arguments
    
    def validate_arguments(self, args: Arguments) -> None:
        """Validate argument combinations and constraints."""
        # Count active modes
        modes = 0
        if args.issue_numbers:
            modes += 1
        if args.review_pr_numbers:
            modes += 1
        if args.bug_description:
            modes += 1
        
        # Check for conflicting modes
        if modes > 1:
            if args.review_pr_numbers and args.issue_numbers:
                raise ValueError("Cannot specify both --review-pr and issue number/range")
            elif args.bug_description and (args.issue_numbers or args.review_pr_numbers):
                if args.issue_numbers:
                    raise ValueError("Cannot specify both issue number/range and other modes")
                else:
                    raise ValueError("Cannot specify both --bug and --review-pr")
        
        # Check auto-pr-review restrictions
        if args.auto_pr_review:
            if args.review_pr_numbers or args.bug_description:
                raise ValueError("--auto-pr-review can only be used with issue implementation")
        
        # Check interactive/prompt-only conflict
        if args.prompt_only and args.interactive:
            raise ValueError("Cannot use --prompt-only and --interactive together")
    
    def _is_number_or_range(self, arg: str) -> bool:
        """Check if argument is a number or range."""
        if arg.isdigit():
            return True
        if "-" in arg and len(arg.split("-")) == 2:
            parts = arg.split("-")
            return parts[0].isdigit() and parts[1].isdigit()
        return False
    
    def _parse_numbers(self, arg: str) -> List[int]:
        """Parse number or range into list of integers."""
        if arg.isdigit():
            return [int(arg)]
        elif "-" in arg:
            parts = arg.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start, end = int(parts[0]), int(parts[1])
                return list(range(start, end + 1))
        
        raise ValueError(f"Invalid number or range: {arg}")


class EnvironmentValidator:
    """Validate environment and check dependencies."""
    
    def check_dependencies(self, prompt_only: bool = False) -> None:
        """Check all required tools are available."""
        missing_tools = []
        
        # Always required tools
        required_tools = [
            ("gh", "GitHub CLI"),
            ("jq", "JSON processor"), 
            ("git", "Git version control")
        ]
        
        # Add coder tool if not in prompt-only mode
        if not prompt_only:
            required_tools.append(("claude", "Claude CLI"))
        
        for tool, description in required_tools:
            if not self._command_exists(tool):
                missing_tools.append(f"{tool} ({description})")
        
        if missing_tools:
            error_msg = "Missing required tools:\n" + "\n".join(missing_tools)
            raise RuntimeError(error_msg)
    
    def validate_environment(self) -> None:
        """Validate git repo and CLAUDE.md existence."""
        # Check if we're in a git repository
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError:
            raise RuntimeError("Not in a git repository")
        
        # Check if CLAUDE.md exists
        if not os.path.exists("CLAUDE.md"):
            raise RuntimeError("CLAUDE.md file not found")
    
    def get_repo_info(self) -> Tuple[str, str]:
        """Extract GitHub repo owner and name from git config."""
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                check=True
            )
            
            remote_url = result.stdout.strip()
            
            # Parse GitHub URL (both HTTPS and SSH formats)
            github_pattern = r"(?:https://github\.com/|git@github\.com:)([^/]+)/([^/.]+)(?:\.git)?$"
            match = re.match(github_pattern, remote_url)
            
            if not match:
                raise RuntimeError(f"Remote URL is not a GitHub repository: {remote_url}")
            
            owner, repo = match.groups()
            return owner, repo
            
        except subprocess.CalledProcessError:
            raise RuntimeError("Could not determine repository information")
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            subprocess.run(
                ["command", "-v", command],
                capture_output=True,
                check=True,
                shell=True
            )
            return True
        except subprocess.CalledProcessError:
            return False


def main():
    """Main entry point for Python implementation."""
    parser = ArgumentParser()
    validator = EnvironmentValidator()
    
    try:
        # Parse arguments
        args = parser.parse(sys.argv[1:])
        
        # Handle help
        if args.help_requested:
            print("Usage: python claude-tasker.py [ISSUE_NUMBER|RANGE] [OPTIONS]")
            print("Options:")
            print("  --review-pr NUMBER/RANGE  Review pull request(s)")
            print("  --bug DESCRIPTION         Analyze bug and create issue")
            print("  --project ID              Specify project ID")
            print("  --timeout SECONDS         Set timeout between tasks")
            print("  --coder TOOL              Use 'claude' or 'codex'")
            print("  --base-branch BRANCH      Base branch for PRs")
            print("  --prompt-only             Generate prompts only")
            print("  --interactive             Interactive mode")
            print("  --auto-pr-review          Auto review PRs")
            print("  --help                    Show this help")
            return 0
        
        # Validate arguments
        parser.validate_arguments(args)
        
        # Check dependencies
        validator.check_dependencies(args.prompt_only)
        
        # Validate environment
        validator.validate_environment()
        
        # Get repo info
        owner, repo = validator.get_repo_info()
        
        print(f"Successfully validated arguments and environment for {owner}/{repo}")
        return 0
        
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())