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
from .prompt_models import PromptContext, ExecutionOptions
from .pr_body_generator import PRBodyGenerator
from src.claude_tasker.logging_config import get_logger

logger = get_logger(__name__)


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
                 base_branch: str = None,
                 branch_strategy: str = "reuse"):
        self.timeout_between_tasks = timeout_between_tasks
        self.interactive_mode = interactive_mode if interactive_mode is not None else os.isatty(0)
        self.coder = coder
        self.branch_strategy = branch_strategy
        
        # Initialize components
        self.env_validator = EnvironmentValidator()
        self.github_client = GitHubClient()
        self.workspace_manager = WorkspaceManager(branch_strategy=branch_strategy)
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
        logger.info("Validating environment dependencies")
        logger.debug(f"Prompt-only mode: {prompt_only}")
        
        validation_results = self.env_validator.validate_all_dependencies(prompt_only=prompt_only)
        
        logger.debug(f"Validation results: {validation_results}")
        
        if not validation_results['valid']:
            report = self.env_validator.format_validation_report(validation_results)
            logger.error(f"Environment validation failed: {report}")
            return False, report
        
        logger.info("Environment validation passed")
        return True, "Environment validation passed"
    
    def process_single_issue(self, issue_number: int, prompt_only: bool = False,
                           project_number: Optional[int] = None) -> WorkflowResult:
        """Process a single GitHub issue using the audit-and-implement workflow."""
        logger.info(f"Starting to process issue #{issue_number}")
        logger.debug(f"Options: prompt_only={prompt_only}, project_number={project_number}")
        
        try:
            # Validate environment
            logger.debug("Decision: Validating environment before processing")
            env_valid, env_msg = self.validate_environment(prompt_only)
            if not env_valid:
                logger.error(f"Environment validation failed for issue #{issue_number}")
                return WorkflowResult(
                    success=False,
                    message="Environment validation failed",
                    error_details=env_msg
                )
            
            # Fetch issue data
            logger.info(f"Fetching issue data for #{issue_number}")
            issue_data = self.github_client.get_issue(issue_number)
            if not issue_data:
                logger.error(f"Failed to fetch issue #{issue_number}")
                return WorkflowResult(
                    success=False,
                    message=f"Failed to fetch issue #{issue_number}",
                    issue_number=issue_number
                )
            
            logger.debug(f"Issue #{issue_number}: {issue_data.title}")
            logger.debug(f"Issue state: {issue_data.state}")
            logger.debug(f"Issue labels: {issue_data.labels}")
            
            # Validate that we're on the correct branch for this issue
            logger.debug("Decision: Validating branch matches issue number")
            branch_valid, branch_msg = self.workspace_manager.validate_branch_for_issue(issue_number)
            if not branch_valid:
                logger.warning(f"Branch validation failed: {branch_msg}")
                logger.debug(f"Decision: Continuing despite branch mismatch (warning only)")
                print(f"⚠️  Warning: {branch_msg}")
                # Don't fail hard, but warn the user about the mismatch
            
            # Check if issue is already closed
            if issue_data.state.lower() == 'closed':
                logger.info(f"Issue #{issue_number} is already closed")
                logger.debug("Decision: Skipping closed issue")
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
            logger.debug("Decision: Performing workspace hygiene before processing")
            if not self.workspace_manager.workspace_hygiene():
                logger.error("Workspace hygiene failed or was cancelled")
                return WorkflowResult(
                    success=False,
                    message="Workspace hygiene failed or cancelled by user",
                    issue_number=issue_number
                )
            logger.debug("Workspace hygiene completed successfully")
            
            # Smart branch selection - reuse existing or create new
            use_smart_branching = os.getenv('CLAUDE_SMART_BRANCHING', 'true').lower() == 'true'
            
            if use_smart_branching:
                logger.info(f"Using smart branch selection for issue #{issue_number}")
                logger.debug(f"Base branch: {self.base_branch}")
                branch_success, branch_name, action = self.workspace_manager.smart_branch_for_issue(
                    issue_number, self.base_branch
                )
                
                if branch_success:
                    if action == "reused":
                        logger.info(f"♻️  Reusing existing branch: {branch_name}")
                        print(f"♻️  Reusing existing branch: {branch_name}")
                    elif action == "created":
                        logger.info(f"🌿 Created new branch: {branch_name}")
                        print(f"🌿 Created new branch: {branch_name}")
                    elif action == "switched":
                        logger.info(f"🔄 Already on branch: {branch_name}")
                        print(f"🔄 Already on branch: {branch_name}")
                else:
                    logger.error(f"Failed to setup branch: {branch_name}")
                    return WorkflowResult(
                        success=False,
                        message=f"Failed to setup branch: {branch_name}",
                        issue_number=issue_number
                    )
            else:
                # Fallback to old behavior - always create new timestamped branch
                logger.info(f"Creating timestamped branch for issue #{issue_number}")
                logger.debug(f"Base branch: {self.base_branch}")
                branch_created, branch_name = self.workspace_manager.create_timestamped_branch(
                    issue_number, self.base_branch
                )
                if not branch_created:
                    logger.error(f"Failed to create branch: {branch_name}")
                    return WorkflowResult(
                        success=False,
                        message=f"Failed to create branch: {branch_name}",
                        issue_number=issue_number
                    )
                logger.info(f"Created branch: {branch_name}")
            
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
            
            if not prompt_result.success:
                return WorkflowResult(
                    success=False,
                    message="Prompt generation failed",
                    issue_number=issue_number,
                    branch_name=branch_name,
                    error_details=prompt_result.error
                )
            
            # If prompt-only mode, return success
            if prompt_only:
                logger.info(f"Prompt-only mode: Prompt generated for issue #{issue_number}")
                logger.debug("Decision: Skipping execution due to prompt-only mode")
                return WorkflowResult(
                    success=True,
                    message=f"Prompt generated for issue #{issue_number}",
                    issue_number=issue_number,
                    branch_name=branch_name
                )
            
            # Check if there are changes to commit
            logger.info("Checking for git changes after Claude execution")
            has_changes = self.workspace_manager.has_changes_to_commit()
            logger.debug(f"Git has changes: {has_changes}")
            logger.debug(f"Decision: {('Creating PR' if has_changes else 'No changes to commit')}")
            
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
                logger.info(f"No changes made for issue #{issue_number}")
                logger.debug("Decision: Issue appears to be already complete or requires no code changes")
                
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
            logger.error(f"Unexpected error processing issue #{issue_number}: {str(e)}")
            logger.debug("Exception details:", exc_info=True)
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
            logger.info(f"Processing issue #{issue_number}...")
            print(f"\n🔄 Processing issue #{issue_number}...")
            
            result = self.process_single_issue(
                issue_number, prompt_only, project_number
            )
            results.append(result)
            
            print(f"✅ Issue #{issue_number}: {result.message}")
            
            # Apply timeout between issues (except for last one)
            if issue_number < end_issue and self.timeout_between_tasks > 0:
                logger.debug(f"Waiting {self.timeout_between_tasks} seconds between tasks")
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
            
            # If prompt-only, just display the prompt and return
            if prompt_only:
                print(f"\n{'='*60}")
                print(f"REVIEW PROMPT FOR PR #{pr_number}")
                print(f"{'='*60}")
                print(review_prompt)
                print(f"{'='*60}")
                return WorkflowResult(
                    success=True,
                    message=f"Review prompt generated for PR #{pr_number}"
                )
            
            # Execute review (using claude directly for reviews with review_mode=True)
            logger.debug(f"Generating review for PR #{pr_number}...")
            review_result = self.prompt_builder.build_with_claude(review_prompt, review_mode=True)
            
            if not review_result:
                logger.error(f"No review result returned for PR #{pr_number}")
                print(f"[ERROR] No review result returned for PR #{pr_number}")
                return WorkflowResult(
                    success=False,
                    message=f"Failed to generate review for PR #{pr_number} - no result returned"
                )
            
            # Check if the result indicates a failure
            if not review_result.success:
                error_msg = review_result.error or 'Unknown error'
                logger.error(f"Review generation failed for PR #{pr_number}: {error_msg}")
                print(f"[ERROR] Review generation failed for PR #{pr_number}: {error_msg}")
                return WorkflowResult(
                    success=False,
                    message=f"Failed to generate review for PR #{pr_number}: {error_msg}",
                    error_details=error_msg
                )
            
            if not review_result.text:
                logger.error(f"Review result missing 'text' field for PR #{pr_number}")
                logger.debug(f"Review result attributes: success={review_result.success}, data={review_result.data}, text={bool(review_result.text)}")
                print(f"[ERROR] Review result missing 'text' field for PR #{pr_number}")
                print(f"[DEBUG] Review result attributes: success={review_result.success}, data={review_result.data}, text={bool(review_result.text)}")
                return WorkflowResult(
                    success=False,
                    message=f"Failed to generate review for PR #{pr_number} - no response content"
                )
            
            # Get the actual review content
            review_content = review_result.text or 'Review completed'
            logger.debug(f"Review content length: {len(review_content)} chars")
            logger.debug(f"Review content preview: {review_content[:200]}...")
            
            # Clean up duplicate content from Claude's response
            review_content = self._deduplicate_review_content(review_content)
            logger.debug(f"After deduplication: {len(review_content)} chars")
            
            # Only add wrapper if there's actual content
            if review_content and review_content != 'Review completed':
                review_comment = f"""## 🤖 Automated Code Review

{review_content}

---
🤖 Generated via automated review with [Claude Code](https://claude.ai/code)"""
            else:
                # Fallback if no content
                review_comment = f"""## 🤖 Automated Code Review

Unable to generate detailed review. Please review the PR manually.

---
🤖 Generated via automated review with [Claude Code](https://claude.ai/code)"""
            
            logger.debug(f"Posting review comment to PR #{pr_number}...")
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
        
        except Exception as e:
            return WorkflowResult(
                success=False,
                message=f"Unexpected error reviewing PR #{pr_number}",
                error_details=str(e)
            )
    
    def _deduplicate_review_content(self, content: str) -> str:
        """Remove duplicate sections from Claude's review content."""
        if not content or len(content.strip()) < 50:
            return content
            
        lines = content.split('\n')
        if len(lines) < 10:
            return content
            
        # Look for repeated sections by finding duplicate headers or blocks
        seen_sections = set()
        deduplicated_lines = []
        current_section = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # If this looks like a header or the start of a new section
            if (line.startswith('#') or 
                line.startswith('**') and line.endswith('**') or
                (line and i > 0 and not lines[i-1].strip())):
                
                # Check if we've seen this section before
                section_key = line.lower().replace('*', '').replace('#', '').strip()
                
                if section_key and len(section_key) > 5:
                    if section_key in seen_sections:
                        # Skip duplicate section - find where it ends
                        logger.debug(f"Skipping duplicate section: {section_key[:50]}...")
                        
                        # Skip until we find the next section or end
                        i += 1
                        while i < len(lines):
                            next_line = lines[i].strip()
                            if (next_line.startswith('#') or 
                                next_line.startswith('**') and next_line.endswith('**') or
                                (next_line and i < len(lines)-1 and not lines[i+1].strip())):
                                break
                            i += 1
                        continue
                    else:
                        seen_sections.add(section_key)
            
            deduplicated_lines.append(lines[i])
            i += 1
        
        result = '\n'.join(deduplicated_lines).strip()
        
        # If we removed significant content, log it
        original_length = len(content)
        result_length = len(result)
        if original_length > result_length + 100:  # More than 100 chars removed
            logger.info(f"Deduplicated review content: {original_length} -> {result_length} chars")
            
        return result
    
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
            context = PromptContext(
                git_diff=self.workspace_manager.get_git_diff(),
                related_files=[],
                project_info={
                    'recent_commits': self.workspace_manager.get_commit_log(self.base_branch, 5)
                }
            )
            
            # Generate bug analysis prompt
            analysis_prompt = self.prompt_builder.generate_bug_analysis_prompt(
                bug_description, self.claude_md_content, context
            )
            
            # Execute analysis - try Claude first, then fallback to LLM
            analysis_result = self.prompt_builder.build_with_claude(analysis_prompt)
            
            if not analysis_result.success:
                # Fallback to LLM tool
                analysis_result = self.prompt_builder.build_with_llm(analysis_prompt)
                
            if not analysis_result.success:
                return WorkflowResult(
                    success=False,
                    message="Failed to analyze bug",
                    error_details=analysis_result.error
                )
            
            # If not prompt-only, create GitHub issue
            if not prompt_only:
                issue_title = f"Bug: {bug_description[:50]}..."
                
                # Debug: log what we got from analysis_result
                logger.debug(f"Analysis result success: {analysis_result.success}")
                logger.debug(f"Analysis result data: {analysis_result.data}")
                logger.debug(f"Analysis result text: {analysis_result.text and len(analysis_result.text)}")
                if analysis_result.text:
                    logger.debug(f"Analysis result text preview: {analysis_result.text[:200]}...")
                
                issue_body = (
                    (analysis_result.data or {}).get('result') or 
                    analysis_result.text or 
                    bug_description
                )
                
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
    
    def analyze_feature(self, feature_description: str, prompt_only: bool = False) -> WorkflowResult:
        """Analyze feature request and create GitHub issue."""
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
            context = PromptContext(
                git_diff=self.workspace_manager.get_git_diff(),
                related_files=[],
                project_info={
                    'recent_commits': self.workspace_manager.get_commit_log(self.base_branch, 5)
                }
            )
            
            # Generate feature analysis prompt
            analysis_prompt = self.prompt_builder.generate_feature_analysis_prompt(
                feature_description, self.claude_md_content, context
            )
            
            # Execute analysis - try Claude first, then fallback to LLM
            analysis_result = self.prompt_builder.build_with_claude(analysis_prompt)
            
            if not analysis_result.success:
                # Fallback to LLM tool
                analysis_result = self.prompt_builder.build_with_llm(analysis_prompt)
                
            if not analysis_result.success:
                return WorkflowResult(
                    success=False,
                    message="Failed to analyze feature request",
                    error_details=analysis_result.error
                )
            
            # If not prompt-only, create GitHub issue
            if not prompt_only:
                issue_title = f"Feature: {feature_description[:50]}..."
                
                # Debug: log what we got from analysis_result
                logger.debug(f"Analysis result success: {analysis_result.success}")
                logger.debug(f"Analysis result data: {analysis_result.data}")
                logger.debug(f"Analysis result text: {analysis_result.text and len(analysis_result.text)}")
                if analysis_result.text:
                    logger.debug(f"Analysis result text preview: {analysis_result.text[:200]}...")
                
                issue_body = (
                    (analysis_result.data or {}).get('result') or 
                    analysis_result.text or 
                    feature_description
                )
                
                issue_url = self.github_client.create_issue(
                    title=issue_title,
                    body=issue_body,
                    labels=['enhancement']
                )
                
                if issue_url:
                    return WorkflowResult(
                        success=True,
                        message=f"Feature analysis completed and issue created: {issue_url}"
                    )
                else:
                    return WorkflowResult(
                        success=False,
                        message="Failed to create GitHub issue"
                    )
            else:
                return WorkflowResult(
                    success=True,
                    message="Feature analysis completed"
                )
        
        except Exception as e:
            return WorkflowResult(
                success=False,
                message="Unexpected error during feature analysis",
                error_details=str(e)
            )