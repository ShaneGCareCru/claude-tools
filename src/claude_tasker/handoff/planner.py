"""Planner module for converting structured data to handoff plans."""

import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone

from .models import (
    Plan, Context, ContextType, DedupeStrategy, DedupeMethod,
    CreateIssueAction, CreatePRAction, CommentIssueAction, CommentPRAction, Action
)
from ..services.gh_service import GhService, IssueData, PRData


logger = logging.getLogger(__name__)


class Planner:
    """Converts structured context into executable handoff plans."""
    
    def __init__(self, gh_service: Optional[GhService] = None):
        """
        Initialize planner.
        
        Args:
            gh_service: GitHub service for fetching context data
        """
        self.gh_service = gh_service
    
    def create_issue_processing_plan(self, 
                                   issue_number: int,
                                   issue_data: Optional[IssueData] = None,
                                   branch_name: Optional[str] = None) -> Optional[Plan]:
        """
        Create a plan for processing a GitHub issue.
        
        Args:
            issue_number: Issue number to process
            issue_data: Pre-fetched issue data (optional)
            branch_name: Branch name for PR creation
            
        Returns:
            Plan object or None if issue cannot be processed
        """
        # Fetch issue data if not provided
        if not issue_data and self.gh_service:
            try:
                issue_data = self.gh_service.get_issue(issue_number)
            except Exception as e:
                logger.error(f"GitHub API error while fetching issue #{issue_number}: {e}")
                return None
            
        if not issue_data:
            logger.error(f"Cannot fetch issue #{issue_number}")
            return None
        
        # Create context
        context = Context(
            type=ContextType.ISSUE,
            issue_number=issue_number,
            branch=branch_name,
            description=f"Processing issue #{issue_number}: {issue_data.title}"
        )
        
        actions = []
        
        # Add initial comment action to indicate processing started
        start_comment = self._generate_processing_start_comment(issue_data)
        actions.append(CommentIssueAction(
            issue_number=issue_number,
            comment=start_comment,
            dedupe_strategy=DedupeStrategy(
                method=DedupeMethod.BY_CONTENT_SIGNATURE,
                signature_lines=2
            )
        ))
        
        # Add PR creation action if branch is specified
        if branch_name:
            pr_title, pr_body = self._generate_pr_content(issue_data, branch_name)
            actions.append(CreatePRAction(
                title=pr_title,
                body=pr_body,
                head_branch=branch_name,
                base_branch="main",
                dedupe_strategy=DedupeStrategy(
                    method=DedupeMethod.BY_TITLE_HASH
                )
            ))
        
        # Add completion comment action
        completion_comment = self._generate_completion_comment(issue_data)
        actions.append(CommentIssueAction(
            issue_number=issue_number,
            comment=completion_comment,
            dedupe_strategy=DedupeStrategy(
                method=DedupeMethod.BY_CONTENT_SIGNATURE,
                signature_lines=3
            )
        ))
        
        return Plan(
            context=context,
            actions=actions
        )
    
    def create_pr_review_plan(self,
                            pr_number: int,
                            pr_data: Optional[PRData] = None) -> Optional[Plan]:
        """
        Create a plan for reviewing a GitHub PR.
        
        Args:
            pr_number: PR number to review
            pr_data: Pre-fetched PR data (optional)
            
        Returns:
            Plan object or None if PR cannot be processed
        """
        # Fetch PR data if not provided
        if not pr_data and self.gh_service:
            try:
                pr_data = self.gh_service.get_pr(pr_number)
            except Exception as e:
                logger.error(f"GitHub API error while fetching PR #{pr_number}: {e}")
                return None
            
        if not pr_data:
            logger.error(f"Cannot fetch PR #{pr_number}")
            return None
        
        # Create context
        context = Context(
            type=ContextType.PR,
            pr_number=pr_number,
            branch=pr_data.head_ref,
            description=f"Reviewing PR #{pr_number}: {pr_data.title}"
        )
        
        # Generate review comment
        review_comment = self._generate_pr_review_comment(pr_data)
        
        actions = [
            CommentPRAction(
                pr_number=pr_number,
                comment=review_comment,
                dedupe_strategy=DedupeStrategy(
                    method=DedupeMethod.BY_CONTENT_SIGNATURE,
                    signature_lines=3
                )
            )
        ]
        
        return Plan(
            context=context,
            actions=actions
        )
    
    def create_bug_analysis_plan(self,
                               bug_description: str,
                               create_issue: bool = True) -> Plan:
        """
        Create a plan for analyzing a bug and optionally creating an issue.
        
        Args:
            bug_description: Description of the bug
            create_issue: Whether to create an issue for the bug
            
        Returns:
            Plan object
        """
        context = Context(
            type=ContextType.BUG_ANALYSIS,
            description=f"Bug analysis: {bug_description[:100]}..."
        )
        
        actions = []
        
        if create_issue:
            issue_title = self._generate_bug_issue_title(bug_description)
            issue_body = self._generate_bug_issue_body(bug_description)
            
            actions.append(CreateIssueAction(
                title=issue_title,
                body=issue_body,
                labels=["bug", "needs-investigation"],
                dedupe_strategy=DedupeStrategy(
                    method=DedupeMethod.BY_TITLE_HASH
                )
            ))
        
        return Plan(
            context=context,
            actions=actions
        )
    
    def create_manual_plan(self,
                         actions: List[Dict[str, Any]],
                         description: Optional[str] = None) -> Plan:
        """
        Create a manual plan from action specifications.
        
        Args:
            actions: List of action dictionaries
            description: Optional description of the plan
            
        Returns:
            Plan object
        """
        context = Context(
            type=ContextType.MANUAL,
            description=description or "Manual plan execution"
        )
        
        parsed_actions = []
        for action_dict in actions:
            action = self._parse_action_dict(action_dict)
            if action:
                parsed_actions.append(action)
        
        if not parsed_actions:
            # Create a default no-op plan
            parsed_actions.append(CommentIssueAction(
                issue_number=1,
                comment="No valid actions specified",
                dedupe_strategy=DedupeStrategy(method=DedupeMethod.NONE)
            ))
        
        return Plan(
            context=context,
            actions=parsed_actions
        )
    
    def _parse_action_dict(self, action_dict: Dict[str, Any]) -> Optional[Action]:
        """Parse action dictionary into Action object."""
        action_type = action_dict.get('type')
        
        # Default dedupe strategy
        dedupe_strategy = DedupeStrategy(
            method=DedupeMethod(action_dict.get('dedupe_method', 'by_content_signature'))
        )
        
        try:
            if action_type == 'create_issue':
                return CreateIssueAction(
                    title=action_dict['title'],
                    body=action_dict['body'],
                    labels=action_dict.get('labels', []),
                    assignees=action_dict.get('assignees', []),
                    dedupe_strategy=dedupe_strategy
                )
            elif action_type == 'create_pr':
                return CreatePRAction(
                    title=action_dict['title'],
                    body=action_dict['body'],
                    head_branch=action_dict['head_branch'],
                    base_branch=action_dict.get('base_branch', 'main'),
                    draft=action_dict.get('draft', False),
                    dedupe_strategy=dedupe_strategy
                )
            elif action_type == 'comment_issue':
                return CommentIssueAction(
                    issue_number=action_dict['issue_number'],
                    comment=action_dict['comment'],
                    dedupe_strategy=dedupe_strategy
                )
            elif action_type == 'comment_pr':
                return CommentPRAction(
                    pr_number=action_dict['pr_number'],
                    comment=action_dict['comment'],
                    dedupe_strategy=dedupe_strategy
                )
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse action: {e}")
        
        return None
    
    def _generate_processing_start_comment(self, issue_data: IssueData) -> str:
        """Generate comment indicating issue processing has started."""
        return f"""🤖 **Claude Tasker Processing Started**

Starting automated processing of issue #{issue_data.number}.

**Issue:** {issue_data.title}
**Status:** In Progress
**Timestamp:** {datetime.now(timezone.utc).isoformat()}Z"""
    
    def _generate_completion_comment(self, issue_data: IssueData) -> str:
        """Generate comment indicating issue processing is complete."""
        return f"""✅ **Claude Tasker Processing Complete**

Automated processing of issue #{issue_data.number} has been completed.

**Issue:** {issue_data.title}
**Status:** Completed
**Timestamp:** {datetime.now(timezone.utc).isoformat()}Z

Please review the changes and provide feedback."""
    
    def _generate_pr_content(self, issue_data: IssueData, branch_name: str) -> tuple[str, str]:
        """Generate PR title and body from issue data."""
        title = f"Fix #{issue_data.number}: {issue_data.title}"
        
        body = f"""## Summary
Fixes #{issue_data.number}

{issue_data.body[:500] if issue_data.body else 'No description provided'}

## Changes
This PR implements the solution for the issue described above.

## Test plan
- [ ] Manual testing completed
- [ ] Automated tests pass
- [ ] Code review completed

**Branch:** `{branch_name}`"""
        
        return title, body
    
    def _generate_pr_review_comment(self, pr_data: PRData) -> str:
        """Generate PR review comment."""
        return f"""🤖 **Automated PR Review**

**PR:** #{pr_data.number} - {pr_data.title}
**Branch:** `{pr_data.head_ref}` → `{pr_data.base_ref}`
**Changes:** +{pr_data.additions}/-{pr_data.deletions} lines across {pr_data.changed_files} files

## Review Summary
This PR has been automatically analyzed. Please ensure:

- [ ] All tests are passing
- [ ] Code follows project conventions
- [ ] Documentation is updated if needed
- [ ] Breaking changes are documented

**Timestamp:** {datetime.now(timezone.utc).isoformat()}Z"""
    
    def _generate_bug_issue_title(self, bug_description: str) -> str:
        """Generate issue title from bug description."""
        # Extract first line or first 47 characters (to fit "Bug: " prefix + "..." suffix)
        first_line = bug_description.split('\n')[0]
        if len(first_line) > 47:
            title = first_line[:44] + "..."  # "Bug: " (5) + 44 + "..." (3) = 52 chars total
        else:
            title = first_line
        
        return f"Bug: {title}"
    
    def _generate_bug_issue_body(self, bug_description: str) -> str:
        """Generate issue body from bug description."""
        return f"""## Bug Report

**Description:**
{bug_description}

## Environment
- Timestamp: {datetime.now(timezone.utc).isoformat()}Z
- Reporter: Claude Tasker (automated)

## Next Steps
- [ ] Reproduce the issue
- [ ] Identify root cause
- [ ] Implement fix
- [ ] Add tests
- [ ] Update documentation if needed

**Labels:** bug, needs-investigation"""