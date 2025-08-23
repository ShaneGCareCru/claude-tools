"""Core workflow orchestration module for claude-tasker."""

import time
import os
from typing import List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from .environment_validator import EnvironmentValidator
from .github_client import GitHubClient
from .workspace_manager import WorkspaceManager
from .prompt_builder import PromptBuilder
from .pr_body_generator import PRBodyGenerator


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    success: bool
    message: str
    issue_number: Optional[int] = None
    pr_url: Optional[str] = None
    branch_name: Optional[str] = None
    error_details: Optional[str] = None


class WorkflowLogic:
    """Core workflow orchestration for claude-tasker operations."""
    
    def __init__(self, 
                 timeout_between_tasks: float = 10.0,
                 interactive_mode: bool = None,
                 coder: str = "claude",
                 base_branch: str = None):
        self.timeout_between_tasks = timeout_between_tasks
        self.interactive_mode = interactive_mode if interactive_mode is not None else os.isatty(0)
        self.coder = coder
        
        # Initialize components
        self.env_validator = EnvironmentValidator()
        self.github_client = GitHubClient()
        self.workspace_manager = WorkspaceManager()
        self.prompt_builder = PromptBuilder()
        self.pr_body_generator = PRBodyGenerator()
        
        # Detect the default branch if not specified
        if base_branch is None:
            self.base_branch = self._detect_default_branch()
        else:
            self.base_branch = base_branch
        
        # Load project context
        self.claude_md_content = self._load_claude_md()
    
    def _detect_default_branch(self) -> str:
        """Detect the repository's default branch."""
        # Try to get from GitHub API first
        default_branch = self.github_client.get_default_branch()
        if default_branch:
            return default_branch
        
        # Fall back to workspace manager detection
        return self.workspace_manager.detect_main_branch()
    
    def _load_claude_md(self) -> str:
        """Load CLAUDE.md content for project context."""
        claude_md_path = Path("CLAUDE.md")
        if claude_md_path.exists():
            try:
                return claude_md_path.read_text(encoding='utf-8')
            except Exception:
                return ""
        return ""
    
    def validate_environment(self, prompt_only: bool = False) -> Tuple[bool, str]:
        """Validate environment before execution."""
        validation_results = self.env_validator.validate_all_dependencies(prompt_only=prompt_only)
        
        if not validation_results['valid']:
            report = self.env_validator.format_validation_report(validation_results)
            return False, report
        
        return True, "Environment validation passed"
    
    def process_single_issue(self, issue_number: int, prompt_only: bool = False,
                           project_number: Optional[int] = None) -> WorkflowResult:
        """Process a single GitHub issue using the audit-and-implement workflow."""
        try:
            # Validate environment
            env_valid, env_msg = self.validate_environment(prompt_only)
            if not env_valid:
                return WorkflowResult(
                    success=False,
                    message="Environment validation failed",
                    error_details=env_msg
                )
            
            # Fetch issue data
            issue_data = self.github_client.get_issue(issue_number)
            if not issue_data:
                return WorkflowResult(
                    success=False,
                    message=f"Failed to fetch issue #{issue_number}",
                    issue_number=issue_number
                )
            
            # Check if issue is already closed
            if issue_data.state.lower() == 'closed':
                return WorkflowResult(
                    success=True,
                    message=f"Issue #{issue_number} already closed",
                    issue_number=issue_number
                )
            
            # Get project context if specified
            project_context = {}
            if project_number:
                project_info = self.github_client.get_project_info(project_number)
                if project_info:
                    project_context['project_info'] = project_info
            
            # Perform workspace hygiene
            if not self.workspace_manager.workspace_hygiene():
                return WorkflowResult(
                    success=False,
                    message="Workspace hygiene failed or cancelled by user",
                    issue_number=issue_number
                )
            
            # Create timestamped branch
            branch_created, branch_name = self.workspace_manager.create_timestamped_branch(
                issue_number, self.base_branch
            )
            if not branch_created:
                return WorkflowResult(
                    success=False,
                    message=f"Failed to create branch: {branch_name}",
                    issue_number=issue_number
                )
            
            # Generate and execute prompt using two-stage execution
            task_data = {
                'issue_number': issue_number,
                'issue_title': issue_data.title,
                'issue_body': issue_data.body,
                'issue_labels': issue_data.labels,
                'branch_name': branch_name
            }
            
            prompt_result = self.prompt_builder.execute_two_stage_prompt(
                task_type="issue_implementation",
                task_data=task_data,
                claude_md_content=self.claude_md_content,
                prompt_only=prompt_only
            )
            
            if not prompt_result['success']:
                return WorkflowResult(
                    success=False,
                    message="Prompt generation failed",
                    issue_number=issue_number,
                    branch_name=branch_name,
                    error_details=prompt_result.get('error')
                )
            
            # If prompt-only mode, return success
            if prompt_only:
                return WorkflowResult(
                    success=True,
                    message=f"Prompt generated for issue #{issue_number}",
                    issue_number=issue_number,
                    branch_name=branch_name
                )
            
            # Check if there are changes to commit
            print("[DEBUG] Checking for git changes after Claude execution")
            has_changes = self.workspace_manager.has_changes_to_commit()
            print(f"[DEBUG] Git has changes: {has_changes}")
            
            if has_changes:
                # Commit changes
                commit_msg = "automated implementation via agent coordination"
                if not self.workspace_manager.commit_changes(commit_msg, branch_name):
                    return WorkflowResult(
                        success=False,
                        message="Failed to commit changes",
                        issue_number=issue_number,
                        branch_name=branch_name
                    )
                
                # Push branch
                if not self.workspace_manager.push_branch(branch_name):
                    return WorkflowResult(
                        success=False,
                        message="Failed to push branch",
                        issue_number=issue_number,
                        branch_name=branch_name
                    )
                
                # Generate PR body
                git_diff = self.workspace_manager.get_git_diff(self.base_branch)
                commit_log = self.workspace_manager.get_commit_log(self.base_branch)
                
                pr_body = self.pr_body_generator.generate_pr_body(
                    issue_data, git_diff, branch_name, commit_log
                )
                
                # Create PR
                pr_title = f"Fix #{issue_number}: {issue_data.title}"
                pr_url = self.github_client.create_pr(
                    title=pr_title,
                    body=pr_body,
                    head=branch_name,
                    base=self.base_branch
                )
                
                if pr_url:
                    # Comment on issue with audit results and PR link
                    audit_comment = f"""## 🤖 Automated Implementation Complete

**Audit Results:**
- Issue analysis completed using Lyra-Dev 4-D methodology
- Implementation gaps identified and addressed
- Code changes committed to branch `{branch_name}`

**Pull Request:** {pr_url}

The implementation has been completed and is ready for review.

🤖 Generated via agent coordination with [Claude Code](https://claude.ai/code)"""
                    
                    self.github_client.comment_on_issue(issue_number, audit_comment)
                    
                    return WorkflowResult(
                        success=True,
                        message=f"Issue #{issue_number} implemented successfully",
                        issue_number=issue_number,
                        pr_url=pr_url,
                        branch_name=branch_name
                    )
                else:
                    return WorkflowResult(
                        success=False,
                        message="Failed to create PR",
                        issue_number=issue_number,
                        branch_name=branch_name
                    )
            else:
                # No changes made - issue might already be complete
                # Comment on issue explaining the situation
                no_changes_comment = """## 🤖 Automated Analysis Complete

**Audit Results:**
- Issue was analyzed using Lyra-Dev 4-D methodology
- No implementation gaps were identified
- Issue appears to already be complete or no code changes are required

The issue has been reviewed and no further action is needed at this time.

🤖 Generated via agent coordination with [Claude Code](https://claude.ai/code)"""
                
                self.github_client.comment_on_issue(issue_number, no_changes_comment)
                
                return WorkflowResult(
                    success=True,
                    message=f"Issue #{issue_number} already complete - no changes needed",
                    issue_number=issue_number,
                    branch_name=branch_name
                )
        
        except Exception as e:
            return WorkflowResult(
                success=False,
                message=f"Unexpected error processing issue #{issue_number}",
                issue_number=issue_number,
                error_details=str(e)
            )
    
    def process_issue_range(self, start_issue: int, end_issue: int, 
                           prompt_only: bool = False,
                           project_number: Optional[int] = None) -> List[WorkflowResult]:
        """Process a range of GitHub issues."""
        results = []
        
        for issue_number in range(start_issue, end_issue + 1):
            print(f"\n🔄 Processing issue #{issue_number}...")
            
            result = self.process_single_issue(
                issue_number, prompt_only, project_number
            )
            results.append(result)
            
            print(f"✅ Issue #{issue_number}: {result.message}")
            
            # Apply timeout between issues (except for last one)
            if issue_number < end_issue and self.timeout_between_tasks > 0:
                print(f"⏳ Waiting {self.timeout_between_tasks} seconds...")
                time.sleep(self.timeout_between_tasks)
        
        return results
    
    def review_pr(self, pr_number: int, prompt_only: bool = False) -> WorkflowResult:
        """Conduct comprehensive PR review."""
        try:
            # Validate environment
            env_valid, env_msg = self.validate_environment(prompt_only)
            if not env_valid:
                return WorkflowResult(
                    success=False,
                    message="Environment validation failed",
                    error_details=env_msg
                )
            
            # Fetch PR data
            pr_data = self.github_client.get_pr(pr_number)
            if not pr_data:
                return WorkflowResult(
                    success=False,
                    message=f"Failed to fetch PR #{pr_number}"
                )
            
            # Get PR diff
            pr_diff = self.github_client.get_pr_diff(pr_number)
            if not pr_diff:
                return WorkflowResult(
                    success=False,
                    message=f"Failed to fetch diff for PR #{pr_number}"
                )
            
            # Generate review prompt
            review_prompt = self.prompt_builder.generate_pr_review_prompt(
                pr_data, pr_diff, self.claude_md_content
            )
            
            # Execute review (using claude directly for reviews)
            review_result = self.prompt_builder.build_with_claude(review_prompt)
            
            if not review_result:
                return WorkflowResult(
                    success=False,
                    message=f"Failed to generate review for PR #{pr_number}"
                )
            
            # If not prompt-only, post review comment
            if not prompt_only:
                review_comment = f"""## 🤖 Automated Code Review

{review_result.get('response', 'Review completed')}

---
🤖 Generated via automated review with [Claude Code](https://claude.ai/code)"""
                
                if self.github_client.comment_on_pr(pr_number, review_comment):
                    return WorkflowResult(
                        success=True,
                        message=f"PR #{pr_number} reviewed successfully"
                    )
                else:
                    return WorkflowResult(
                        success=False,
                        message=f"Failed to post review comment on PR #{pr_number}"
                    )
            else:
                return WorkflowResult(
                    success=True,
                    message=f"Review generated for PR #{pr_number}"
                )
        
        except Exception as e:
            return WorkflowResult(
                success=False,
                message=f"Unexpected error reviewing PR #{pr_number}",
                error_details=str(e)
            )
    
    def analyze_bug(self, bug_description: str, prompt_only: bool = False) -> WorkflowResult:
        """Analyze bug and create GitHub issue."""
        try:
            # Validate environment
            env_valid, env_msg = self.validate_environment(prompt_only)
            if not env_valid:
                return WorkflowResult(
                    success=False,
                    message="Environment validation failed",
                    error_details=env_msg
                )
            
            # Gather context
            context = {
                'recent_commits': self.workspace_manager.get_commit_log(self.base_branch, 5),
                'git_diff': self.workspace_manager.get_git_diff()
            }
            
            # Generate bug analysis prompt
            analysis_prompt = self.prompt_builder.generate_bug_analysis_prompt(
                bug_description, self.claude_md_content, context
            )
            
            # Execute analysis - try Claude first, then fallback to LLM
            analysis_result = self.prompt_builder.build_with_claude(analysis_prompt)
            
            if not analysis_result:
                # Fallback to LLM tool
                analysis_result = self.prompt_builder.build_with_llm(analysis_prompt)
                
            if not analysis_result:
                return WorkflowResult(
                    success=False,
                    message="Failed to analyze bug"
                )
            
            # If not prompt-only, create GitHub issue
            if not prompt_only:
                issue_title = f"Bug: {bug_description[:50]}..."
                issue_body = analysis_result.get('result', analysis_result.get('optimized_prompt', bug_description))
                
                issue_url = self.github_client.create_issue(
                    title=issue_title,
                    body=issue_body,
                    labels=['bug']
                )
                
                if issue_url:
                    return WorkflowResult(
                        success=True,
                        message=f"Bug analysis completed and issue created: {issue_url}"
                    )
                else:
                    return WorkflowResult(
                        success=False,
                        message="Failed to create GitHub issue"
                    )
            else:
                return WorkflowResult(
                    success=True,
                    message="Bug analysis completed"
                )
        
        except Exception as e:
            return WorkflowResult(
                success=False,
                message="Unexpected error during bug analysis",
                error_details=str(e)
            )