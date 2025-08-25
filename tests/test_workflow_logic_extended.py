"""Extended tests for workflow_logic module to improve coverage."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import tempfile
import os

from src.claude_tasker.workflow_logic import WorkflowLogic, WorkflowResult
from src.claude_tasker.github_client import IssueData
from src.claude_tasker.prompt_models import TwoStageResult, LLMResult


class TestWorkflowLogicExtended:
    """Extended tests for WorkflowLogic class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for WorkflowLogic."""
        mock_github = Mock()
        mock_workspace = Mock()
        mock_prompt_builder = Mock()
        mock_pr_generator = Mock()
        mock_env_validator = Mock()
        
        return {
            'github_client': mock_github,
            'workspace_manager': mock_workspace,
            'prompt_builder': mock_prompt_builder,
            'pr_body_generator': mock_pr_generator,
            'env_validator': mock_env_validator
        }
    
    @pytest.fixture
    def workflow(self, mock_dependencies):
        """Create WorkflowLogic instance with mocked dependencies."""
        with patch('src.claude_tasker.workflow_logic.GitHubClient', return_value=mock_dependencies['github_client']), \
             patch('src.claude_tasker.workflow_logic.WorkspaceManager', return_value=mock_dependencies['workspace_manager']), \
             patch('src.claude_tasker.workflow_logic.PromptBuilder', return_value=mock_dependencies['prompt_builder']), \
             patch('src.claude_tasker.workflow_logic.PRBodyGenerator', return_value=mock_dependencies['pr_body_generator']), \
             patch('src.claude_tasker.workflow_logic.EnvironmentValidator', return_value=mock_dependencies['env_validator']), \
             patch('src.claude_tasker.workflow_logic.Path'):
            # Mock the _detect_default_branch and _load_claude_md methods
            mock_dependencies['github_client'].get_default_branch.return_value = 'main'
            workflow = WorkflowLogic(base_branch='main')
            return workflow
    
    def test_process_issue_github_fetch_failure(self, workflow, mock_dependencies):
        """Test process_single_issue when GitHub fetch fails."""
        mock_dependencies['github_client'].get_issue.return_value = None
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        
        result = workflow.process_single_issue(42, prompt_only=False)
        
        assert result.success is False
        assert "Failed to fetch issue" in result.message
        assert result.issue_number == 42
    
    def test_process_issue_workspace_preparation_failure(self, workflow, mock_dependencies):
        """Test process_issue when workspace preparation fails."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            url="https://github.com/test/repo/issues/42",
            author="testuser",
            state="open"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].validate_branch_for_issue.return_value = (True, "Valid branch")
        mock_dependencies['workspace_manager'].workspace_hygiene.return_value = False
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.process_single_issue(42, prompt_only=False)
        
        assert result.success is False
        assert "Workspace hygiene failed" in result.message
    
    def test_process_issue_prompt_generation_failure(self, workflow, mock_dependencies):
        """Test process_issue when prompt generation fails."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            url="https://github.com/test/repo/issues/42",
            author="testuser",
            state="open"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].validate_branch_for_issue.return_value = (True, "Valid branch")
        mock_dependencies['workspace_manager'].workspace_hygiene.return_value = True
        mock_dependencies['workspace_manager'].create_timestamped_branch.return_value = (True, "issue-42-123456")
        mock_dependencies['workspace_manager'].get_branch_and_status.return_value = ("main", True)
        mock_dependencies['prompt_builder'].execute_two_stage_prompt.return_value = TwoStageResult(success=False, error='Prompt failed')
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.process_single_issue(42, prompt_only=False)
        
        assert result.success is False
        assert "Prompt generation failed" in result.message
    
    def test_process_issue_prompt_only_mode(self, workflow, mock_dependencies):
        """Test process_issue in prompt-only mode."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            url="https://github.com/test/repo/issues/42",
            author="testuser",
            state="open"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].validate_branch_for_issue.return_value = (True, "Valid branch")
        mock_dependencies['workspace_manager'].workspace_hygiene.return_value = True
        mock_dependencies['workspace_manager'].create_timestamped_branch.return_value = (True, "issue-42-123456")
        mock_dependencies['workspace_manager'].get_branch_and_status.return_value = ("main", True)
        mock_dependencies['prompt_builder'].execute_two_stage_prompt.return_value = TwoStageResult(success=True, optimized_prompt='Test prompt')
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        
        result = workflow.process_single_issue(42, prompt_only=True)
        
        assert result.success is True
        assert "Prompt generated" in result.message
    
    def test_process_issue_dry_run_mode(self, workflow, mock_dependencies):
        """Test process_issue with no changes to commit."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            url="https://github.com/test/repo/issues/42",
            author="testuser",
            state="open"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].validate_branch_for_issue.return_value = (True, "Valid branch")
        mock_dependencies['workspace_manager'].workspace_hygiene.return_value = True
        mock_dependencies['workspace_manager'].create_timestamped_branch.return_value = (True, "issue-42-123456")
        mock_dependencies['workspace_manager'].get_branch_and_status.return_value = ("main", True)
        mock_dependencies['prompt_builder'].execute_two_stage_prompt.return_value = TwoStageResult(success=True, optimized_prompt='Test prompt')
        mock_dependencies['workspace_manager'].has_changes_to_commit.return_value = False
        mock_dependencies['github_client'].comment_on_issue.return_value = True
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.process_single_issue(42, prompt_only=False)
        
        assert result.success is True
        assert "already complete" in result.message
    
    def test_process_issue_claude_execution_failure(self, workflow, mock_dependencies):
        """Test process_issue when Claude execution fails."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            url="https://github.com/test/repo/issues/42",
            author="testuser",
            state="open"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].validate_branch_for_issue.return_value = (True, "Valid branch")
        mock_dependencies['workspace_manager'].workspace_hygiene.return_value = True
        mock_dependencies['workspace_manager'].create_timestamped_branch.return_value = (True, "issue-42-123456")
        mock_dependencies['workspace_manager'].get_branch_and_status.return_value = ("main", True)
        mock_dependencies['prompt_builder'].execute_two_stage_prompt.return_value = TwoStageResult(success=False, error='Claude execution failed')
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.process_single_issue(42, prompt_only=False)
        
        assert result.success is False
        assert "Prompt generation failed" in result.message
    
    def test_process_issue_commit_failure(self, workflow, mock_dependencies):
        """Test process_issue when git commit fails."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            url="https://github.com/test/repo/issues/42",
            author="testuser",
            state="open"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].validate_branch_for_issue.return_value = (True, "Valid branch")
        mock_dependencies['workspace_manager'].workspace_hygiene.return_value = True
        mock_dependencies['workspace_manager'].create_timestamped_branch.return_value = (True, "issue-42-123456")
        mock_dependencies['workspace_manager'].get_branch_and_status.return_value = ("main", True)
        mock_dependencies['prompt_builder'].execute_two_stage_prompt.return_value = TwoStageResult(success=True, optimized_prompt='Test prompt')
        mock_dependencies['workspace_manager'].has_changes_to_commit.return_value = True
        mock_dependencies['workspace_manager'].commit_changes.return_value = False
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.process_single_issue(42, prompt_only=False)
        
        assert result.success is False
        assert "Failed to commit changes" in result.message
    
    def test_process_issue_push_failure(self, workflow, mock_dependencies):
        """Test process_issue when git push fails."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            url="https://github.com/test/repo/issues/42",
            author="testuser",
            state="open"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].validate_branch_for_issue.return_value = (True, "Valid branch")
        mock_dependencies['workspace_manager'].workspace_hygiene.return_value = True
        mock_dependencies['workspace_manager'].create_timestamped_branch.return_value = (True, "issue-42-123456")
        mock_dependencies['workspace_manager'].get_branch_and_status.return_value = ("main", True)
        mock_dependencies['prompt_builder'].execute_two_stage_prompt.return_value = TwoStageResult(success=True, optimized_prompt='Test prompt')
        mock_dependencies['workspace_manager'].has_changes_to_commit.return_value = True
        mock_dependencies['workspace_manager'].commit_changes.return_value = True
        mock_dependencies['workspace_manager'].push_branch.return_value = False
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.process_single_issue(42, prompt_only=False)
        
        assert result.success is False
        assert "Failed to push branch" in result.message
    
    def test_process_issue_pr_creation_failure(self, workflow, mock_dependencies):
        """Test process_issue when PR creation fails."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            url="https://github.com/test/repo/issues/42",
            author="testuser",
            state="open"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].validate_branch_for_issue.return_value = (True, "Valid branch")
        mock_dependencies['workspace_manager'].workspace_hygiene.return_value = True
        mock_dependencies['workspace_manager'].create_timestamped_branch.return_value = (True, "issue-42-123456")
        mock_dependencies['workspace_manager'].get_branch_and_status.return_value = ("main", True)
        mock_dependencies['prompt_builder'].execute_two_stage_prompt.return_value = TwoStageResult(success=True, optimized_prompt='Test prompt')
        mock_dependencies['workspace_manager'].has_changes_to_commit.return_value = True
        mock_dependencies['workspace_manager'].commit_changes.return_value = True
        mock_dependencies['workspace_manager'].push_branch.return_value = True
        mock_dependencies['workspace_manager'].get_git_diff.return_value = "diff content"
        mock_dependencies['workspace_manager'].get_commit_log.return_value = "commit log"
        mock_dependencies['pr_body_generator'].generate_pr_body.return_value = "PR body"
        mock_dependencies['github_client'].create_pr.return_value = None
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.process_single_issue(42, prompt_only=False)
        
        assert result.success is False
        assert "Failed to create PR" in result.message
    
    
    def test_analyze_bug_prompt_generation_failure(self, workflow, mock_dependencies):
        """Test analyze_bug when prompt generation fails."""
        mock_dependencies['workspace_manager'].get_commit_log.return_value = "commit log"
        mock_dependencies['workspace_manager'].get_git_diff.return_value = "git diff"
        mock_dependencies['prompt_builder'].generate_bug_analysis_prompt.return_value = "Bug analysis prompt"
        mock_dependencies['prompt_builder'].build_with_claude.return_value = LLMResult(success=False, error='Build failed')
        mock_dependencies['prompt_builder'].build_with_llm.return_value = LLMResult(success=False, error='Build failed')
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.analyze_bug("Something is broken", prompt_only=False)
        
        assert result.success is False
        assert "Failed to analyze bug" in result.message
    
    def test_analyze_bug_prompt_only_mode(self, workflow, mock_dependencies):
        """Test analyze_bug in prompt-only mode."""
        mock_dependencies['workspace_manager'].get_commit_log.return_value = "commit log"
        mock_dependencies['workspace_manager'].get_git_diff.return_value = "git diff"
        mock_dependencies['prompt_builder'].generate_bug_analysis_prompt.return_value = "Bug prompt"
        mock_dependencies['prompt_builder'].build_with_claude.return_value = LLMResult(success=True, text='Analysis complete')
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        
        result = workflow.analyze_bug("Something is broken", prompt_only=True)
        
        assert result.success is True
        assert "Bug analysis completed" in result.message
    
    def test_analyze_bug_claude_execution_failure(self, workflow, mock_dependencies):
        """Test analyze_bug when Claude execution fails."""
        mock_dependencies['workspace_manager'].get_commit_log.return_value = "commit log"
        mock_dependencies['workspace_manager'].get_git_diff.return_value = "git diff"
        mock_dependencies['prompt_builder'].generate_bug_analysis_prompt.return_value = "Bug prompt"
        mock_dependencies['prompt_builder'].build_with_claude.return_value = LLMResult(success=False, error='Build failed')
        mock_dependencies['prompt_builder'].build_with_llm.return_value = LLMResult(success=False, error='Build failed')
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.analyze_bug("Something is broken", prompt_only=False)
        
        assert result.success is False
        assert "Failed to analyze bug" in result.message
    
    def test_analyze_bug_issue_creation_failure(self, workflow, mock_dependencies):
        """Test analyze_bug when issue creation fails."""
        mock_dependencies['workspace_manager'].get_commit_log.return_value = "commit log"
        mock_dependencies['workspace_manager'].get_git_diff.return_value = "git diff"
        mock_dependencies['prompt_builder'].generate_bug_analysis_prompt.return_value = "Bug prompt"
        mock_dependencies['prompt_builder'].build_with_claude.return_value = LLMResult(success=True, text='Analysis complete')
        mock_dependencies['prompt_builder'].build_with_llm.return_value = LLMResult(success=True, text='Analysis complete')
        mock_dependencies['github_client'].create_issue.return_value = None
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.analyze_bug("Something is broken", prompt_only=False)
        
        assert result.success is False
        assert "Failed to create GitHub issue" in result.message
    
    def test_review_pr_github_fetch_failure(self, workflow, mock_dependencies):
        """Test review_pr when GitHub fetch fails."""
        mock_dependencies['github_client'].get_pr.return_value = None
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.review_pr(123, prompt_only=False)
        
        assert result.success is False
        assert "Failed to fetch PR" in result.message
    
    def test_review_pr_prompt_generation_failure(self, workflow, mock_dependencies):
        """Test review_pr when PR diff fetch fails."""
        pr_data = Mock()
        mock_dependencies['github_client'].get_pr.return_value = pr_data
        mock_dependencies['github_client'].get_pr_diff.return_value = None
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.review_pr(123, prompt_only=False)
        
        assert result.success is False
        assert "Failed to fetch diff" in result.message
    
    def test_review_pr_prompt_only_mode(self, workflow, mock_dependencies):
        """Test review_pr in prompt-only mode."""
        pr_data = Mock()
        mock_dependencies['github_client'].get_pr.return_value = pr_data
        mock_dependencies['github_client'].get_pr_diff.return_value = "diff content"
        mock_dependencies['prompt_builder'].generate_pr_review_prompt.return_value = "Review prompt"
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        
        with patch('builtins.print') as mock_print:
            result = workflow.review_pr(123, prompt_only=True)
        
        assert result.success is True
        assert "Review prompt generated" in result.message
        mock_print.assert_called()
    
    def test_review_pr_claude_execution_failure(self, workflow, mock_dependencies):
        """Test review_pr when Claude execution fails."""
        pr_data = Mock()
        mock_dependencies['github_client'].get_pr.return_value = pr_data
        mock_dependencies['github_client'].get_pr_diff.return_value = "diff content"
        mock_dependencies['prompt_builder'].generate_pr_review_prompt.return_value = "Review prompt"
        mock_dependencies['prompt_builder'].build_with_claude.return_value = None
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.review_pr(123, prompt_only=False)
        
        assert result.success is False
        assert "Failed to generate review" in result.message
    
    def test_review_pr_comment_posting_failure(self, workflow, mock_dependencies):
        """Test review_pr when comment posting fails."""
        pr_data = Mock()
        mock_dependencies['github_client'].get_pr.return_value = pr_data
        mock_dependencies['github_client'].get_pr_diff.return_value = "diff content"
        mock_dependencies['prompt_builder'].generate_pr_review_prompt.return_value = "Review prompt"
        mock_dependencies['prompt_builder'].build_with_claude.return_value = LLMResult(
            success=True,
            text='Review complete'
        )
        mock_dependencies['github_client'].comment_on_pr.return_value = False
        
        mock_dependencies['env_validator'].validate_all_dependencies.return_value = {'valid': True}
        result = workflow.review_pr(123, prompt_only=False)
        
        assert result.success is False
        assert "Failed to post review comment" in result.message