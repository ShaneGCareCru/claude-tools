"""Main CLI interface for claude-tasker."""

import argparse
import sys
import re
import time
import os
from typing import List, Optional
from pathlib import Path

from .workflow_logic import WorkflowLogic, WorkflowResult
from src.claude_tasker.logging_config import get_logger

logger = get_logger(__name__)


def parse_issue_range(issue_arg: str) -> tuple[Optional[int], Optional[int]]:
    """Parse issue number or range (e.g., '123' or '123-125')."""
    try:
        if not issue_arg:
            return None, None
        if '-' in issue_arg:
            start_str, end_str = issue_arg.split('-', 1)
            start = int(start_str.strip())
            end = int(end_str.strip())
            if start > end:
                raise ValueError("Start issue must be <= end issue")
            return start, end
        else:
            issue_num = int(issue_arg.strip())
            return issue_num, issue_num
    except (ValueError, AttributeError, TypeError):
        return None, None


def parse_pr_range(pr_arg: str) -> tuple[Optional[int], Optional[int]]:
    """Parse PR number or range (e.g., '123' or '123-125')."""
    return parse_issue_range(pr_arg)  # Same logic as issues


def extract_pr_number(pr_url: str) -> Optional[int]:
    """Safely extract PR number from GitHub URL."""
    if pr_url is None:
        return None
    
    try:
        # Handle both full URLs and PR numbers
        # Example: https://github.com/owner/repo/pull/123
        match = re.search(r'/pull/(\d+)', pr_url)
        if match:
            return int(match.group(1))
        
        # Fallback: check if it's already just a number
        if pr_url.isdigit():
            return int(pr_url)
            
        return None
    except (ValueError, AttributeError, TypeError):
        return None


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        prog='claude-tasker',
        description='Enhanced Claude Task Runner - Context-aware wrapper for Claude Code',
        epilog="""
Examples:
  claude-tasker 123                        # Process issue #123
  claude-tasker 123-125                   # Process issues #123 through #125
  claude-tasker --review-pr 456           # Review PR #456
  claude-tasker --bug "Test failure"      # Analyze bug and create issue
  claude-tasker --feature "Add CSV export" # Analyze feature and create issue
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Positional argument for issue number/range
    parser.add_argument(
        'issue',
        nargs='?',
        help='Issue number or range (e.g., 123 or 123-125)'
    )
    
    # PR review options
    parser.add_argument(
        '--review-pr',
        metavar='PR',
        help='Review PR number or range (e.g., 456 or 456-458)'
    )
    
    # Bug analysis
    parser.add_argument(
        '--bug',
        metavar='DESCRIPTION',
        help='Analyze bug and create issue'
    )
    
    # Feature analysis
    parser.add_argument(
        '--feature',
        metavar='DESCRIPTION',
        help='Analyze feature request and create issue'
    )
    
    # Execution options
    parser.add_argument(
        '--prompt-only',
        action='store_true',
        help='Generate prompts without execution'
    )
    
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Enable interactive mode'
    )
    
    parser.add_argument(
        '--timeout',
        type=float,
        default=10.0,
        metavar='SECONDS',
        help='Delay between tasks (default: 10)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Skip actual execution (same as --prompt-only)'
    )
    
    # GitHub options
    parser.add_argument(
        '--project',
        type=int,
        metavar='NUM',
        help='GitHub project number for context'
    )
    
    # Branch management options
    parser.add_argument(
        '--branch-strategy',
        choices=['always_new', 'reuse', 'reuse_or_fail'],
        default='reuse',
        help='Branch creation strategy: always_new (create new branches), '
             'reuse (reuse existing PR branches when possible), '
             'reuse_or_fail (must reuse existing branch)'
    )
    
    parser.add_argument(
        '--no-smart-branching',
        action='store_true',
        help='Disable smart branching (always create new branches)'
    )
    
    parser.add_argument(
        '--base-branch',
        default=None,
        metavar='BRANCH',
        help='Base branch for PRs (default: auto-detect)'
    )
    
    parser.add_argument(
        '--auto-pr-review',
        action='store_true',
        help='Automatically review PRs after issue implementation'
    )
    
    # Tool selection
    parser.add_argument(
        '--coder',
        choices=['claude', 'llm'],
        default='claude',
        help='LLM tool to use (default: claude)'
    )
    
    # Version argument
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser


def validate_arguments(args: argparse.Namespace) -> Optional[str]:
    """Validate argument combinations."""
    # Must specify exactly one main action
    actions = [args.issue, args.review_pr, args.bug, args.feature]
    active_actions = [action for action in actions if action is not None]
    
    if len(active_actions) == 0:
        return "Must specify an issue number, --review-pr, --bug, or --feature"
    
    if len(active_actions) > 1:
        return "Error: Cannot specify multiple actions simultaneously"
    
    # Validate issue range format
    if args.issue:
        start, end = parse_issue_range(args.issue)
        if start is None or end is None:
            return f"Error: Invalid issue number format: {args.issue}"
    
    # Validate PR range format
    if args.review_pr:
        start, end = parse_pr_range(args.review_pr)
        if start is None or end is None:
            return f"Error: Invalid PR number format: {args.review_pr}"
    
    # Validate timeout
    if args.timeout < 0:
        return "Error: Invalid timeout value. Must be non-negative"
    
    # Validate project number
    if args.project is not None and args.project <= 0:
        return "Error: Invalid project ID. Must be a positive integer"
    
    # Validate bug description
    if args.bug is not None and not args.bug.strip():
        return "Error: Bug description cannot be empty"
    
    # Validate feature description
    if args.feature is not None and not args.feature.strip():
        return "Error: Feature description cannot be empty"
    
    # Validate base branch
    if args.base_branch and not args.base_branch.strip():
        return "Error: Base branch name cannot be empty"
    
    # Check for conflicting modes
    if args.auto_pr_review and args.prompt_only:
        return "Error: --auto-pr-review cannot be used with --prompt-only"
    
    if args.auto_pr_review and not args.issue:
        return "Error: --auto-pr-review can only be used with issue processing"
    
    # Check for interactive and prompt-only conflict
    if args.interactive and args.prompt_only:
        return "Error: --interactive and --prompt-only cannot be used together"
    
    return None


def print_results_summary(results: List[WorkflowResult]) -> None:
    """Print summary of workflow results."""
    if not results:
        return
    
    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total - successful
    
    print(f"\n📊 Summary: {successful}/{total} successful, {failed} failed")
    
    # Show failed results
    for result in results:
        if not result.success:
            logger.error(f"Issue processing failed: {result.message}")
            if result.error_details:
                logger.error(f"Error details: {result.error_details}")
            print(f"❌ {result.message}")
            if result.error_details:
                print(f"   Details: {result.error_details}")


def main() -> int:
    """Main CLI entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Validate arguments
    validation_error = validate_arguments(args)
    if validation_error:
        logger.error(f"Validation error: {validation_error}")
        print(f"Error: {validation_error}", file=sys.stderr)
        return 1
    
    # Check for CLAUDE.md (required for project context)
    if not Path("CLAUDE.md").exists():
        logger.error("CLAUDE.md not found. Must be run from project root.")
        print("Error: CLAUDE.md not found. Must be run from project root.", file=sys.stderr)
        return 1
    
    # Handle dry-run alias
    if args.dry_run:
        args.prompt_only = True
    
    # Set environment variable for smart branching
    if args.no_smart_branching:
        os.environ['CLAUDE_SMART_BRANCHING'] = 'false'
        branch_strategy = 'always_new'
    else:
        os.environ['CLAUDE_SMART_BRANCHING'] = 'true'
        branch_strategy = args.branch_strategy
    
    # Initialize workflow logic
    workflow = WorkflowLogic(
        timeout_between_tasks=args.timeout,
        interactive_mode=args.interactive,
        coder=args.coder,
        base_branch=args.base_branch,
        branch_strategy=branch_strategy
    )
    
    try:
        results = []
        
        if args.issue:
            # Process issue(s)
            start, end = parse_issue_range(args.issue)
            
            if start == end:
                # Single issue
                print(f"🔄 Processing issue #{start}...")
                result = workflow.process_single_issue(
                    start, args.prompt_only, args.project
                )
                results = [result]
            else:
                # Issue range
                print(f"🔄 Processing issues #{start} through #{end}...")
                results = workflow.process_issue_range(
                    start, end, args.prompt_only, args.project
                )
            
            # Auto PR review if requested
            if args.auto_pr_review and not args.prompt_only:
                for result in results:
                    if result.success and result.pr_url:
                        # Extract PR number from URL using safe extraction
                        pr_num = extract_pr_number(result.pr_url)
                        if pr_num:
                            print(f"🔄 Auto-reviewing PR #{pr_num}...")
                            review_result = workflow.review_pr(pr_num, False)
                            print(f"📝 PR #{pr_num}: {review_result.message}")
                        else:
                            print(f"⚠️  Could not parse PR number from {result.pr_url}")
        
        elif args.review_pr:
            # Review PR(s)
            start, end = parse_pr_range(args.review_pr)
            
            if start == end:
                # Single PR
                print(f"📝 Reviewing PR #{start}...")
                result = workflow.review_pr(start, args.prompt_only)
                results = [result]
            else:
                # PR range
                print(f"📝 Reviewing PRs #{start} through #{end}...")
                for pr_number in range(start, end + 1):
                    print(f"📝 Reviewing PR #{pr_number}...")
                    result = workflow.review_pr(pr_number, args.prompt_only)
                    results.append(result)
                    
                    print(f"✅ PR #{pr_number}: {result.message}")
                    
                    # Apply timeout between PRs (except for last one)
                    if pr_number < end and args.timeout > 0:
                        print(f"⏳ Waiting {args.timeout} seconds...")
                        time.sleep(args.timeout)
        
        elif args.bug:
            # Analyze bug
            print(f"🐛 Analyzing bug: {args.bug}")
            result = workflow.analyze_bug(args.bug, args.prompt_only)
            results = [result]
        
        elif args.feature:
            # Analyze feature
            print(f"✨ Analyzing feature: {args.feature}")
            result = workflow.analyze_feature(args.feature, args.prompt_only)
            results = [result]
        
        # Print individual results
        for result in results:
            if result.success:
                print(f"✅ {result.message}")
                if result.pr_url:
                    print(f"   PR: {result.pr_url}")
                if result.branch_name:
                    print(f"   Branch: {result.branch_name}")
            else:
                # Determine the analysis type for error message
                analysis_type = "Feature analysis" if args.feature else "Bug analysis" if args.bug else "Analysis"
                logger.error(f"{analysis_type} failed: {result.message}")
                if result.error_details:
                    logger.error(f"Error details: {result.error_details}")
                print(f"❌ {result.message}")
                if result.error_details:
                    print(f"   Details: {result.error_details}")
        
        # Print summary for multiple results
        if len(results) > 1:
            print_results_summary(results)
        
        # Return appropriate exit code
        if all(result.success for result in results):
            return 0
        else:
            return 1
    
    except KeyboardInterrupt:
        logger.warning("Operation interrupted by user")
        print("\n⚠️  Operation interrupted by user", file=sys.stderr)
        return 130  # Standard exit code for SIGINT
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())