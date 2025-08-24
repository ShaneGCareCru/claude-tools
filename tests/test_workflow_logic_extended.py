"""Extended tests for workflow_logic module to improve coverage."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import tempfile
import os

from src.claude_tasker.workflow_logic import WorkflowLogic, WorkflowResult
from src.claude_tasker.github_client import IssueData


class TestWorkflowLogicExtended:
    """Extended tests for WorkflowLogic class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for WorkflowLogic."""
        mock_github = Mock()
        mock_workspace = Mock()
        mock_prompt_builder = Mock()
        mock_pr_generator = Mock()
        
        return {
            'github_client': mock_github,
            'workspace_manager': mock_workspace,
            'prompt_builder': mock_prompt_builder,
            'pr_body_generator': mock_pr_generator
        }
    
    @pytest.fixture
    def workflow(self, mock_dependencies):
        """Create WorkflowLogic instance with mocked dependencies."""
        return WorkflowLogic(
            github_client=mock_dependencies['github_client'],
            workspace_manager=mock_dependencies['workspace_manager'],
            prompt_builder=mock_dependencies['prompt_builder'],
            pr_body_generator=mock_dependencies['pr_body_generator'],
            base_branch='main'
        )
    
    def test_process_issue_github_fetch_failure(self, workflow, mock_dependencies):
        """Test process_issue when GitHub fetch fails."""
        mock_dependencies['github_client'].get_issue.return_value = None
        
        args = Mock(prompt_only=False, dry_run=False)
        result = workflow.process_issue(42, args)
        
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
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].prepare_workspace.return_value = None
        
        args = Mock(prompt_only=False, dry_run=False)
        result = workflow.process_issue(42, args)
        
        assert result.success is False
        assert "Failed to prepare workspace" in result.message
    
    def test_process_issue_prompt_generation_failure(self, workflow, mock_dependencies):
        """Test process_issue when prompt generation fails."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].prepare_workspace.return_value = "issue-42-branch"
        mock_dependencies['prompt_builder'].build_audit_prompt.return_value = None
        
        args = Mock(prompt_only=False, dry_run=False)
        result = workflow.process_issue(42, args)
        
        assert result.success is False
        assert "Failed to generate audit prompt" in result.message
    
    def test_process_issue_prompt_only_mode(self, workflow, mock_dependencies):
        """Test process_issue in prompt-only mode."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].prepare_workspace.return_value = "issue-42-branch"
        mock_dependencies['prompt_builder'].build_audit_prompt.return_value = "Test prompt"
        
        args = Mock(prompt_only=True, dry_run=False)
        
        with patch('builtins.print') as mock_print:
            result = workflow.process_issue(42, args)
        
        assert result.success is True
        assert "Prompt generated" in result.message
        mock_print.assert_called()
        mock_dependencies['prompt_builder'].execute_claude_with_prompt.assert_not_called()
    
    def test_process_issue_dry_run_mode(self, workflow, mock_dependencies):
        """Test process_issue in dry-run mode."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].prepare_workspace.return_value = "issue-42-branch"
        mock_dependencies['prompt_builder'].build_audit_prompt.return_value = "Test prompt"
        
        args = Mock(prompt_only=False, dry_run=True)
        result = workflow.process_issue(42, args)
        
        assert result.success is True
        assert "Dry run completed" in result.message
        mock_dependencies['prompt_builder'].execute_claude_with_prompt.assert_not_called()
    
    def test_process_issue_claude_execution_failure(self, workflow, mock_dependencies):
        """Test process_issue when Claude execution fails."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].prepare_workspace.return_value = "issue-42-branch"
        mock_dependencies['prompt_builder'].build_audit_prompt.return_value = "Test prompt"
        mock_dependencies['prompt_builder'].execute_claude_with_prompt.return_value = None
        
        args = Mock(prompt_only=False, dry_run=False, interactive=False, coder='claude')
        result = workflow.process_issue(42, args)
        
        assert result.success is False
        assert "Failed to execute Claude" in result.message
    
    def test_process_issue_implementation_prompt_failure(self, workflow, mock_dependencies):
        """Test process_issue when implementation prompt generation fails."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].prepare_workspace.return_value = "issue-42-branch"
        mock_dependencies['prompt_builder'].build_audit_prompt.return_value = "Test prompt"
        mock_dependencies['prompt_builder'].execute_claude_with_prompt.return_value = {
            'success': True,
            'response': 'Audit complete'
        }
        mock_dependencies['prompt_builder'].build_implementation_prompt.return_value = None
        
        args = Mock(prompt_only=False, dry_run=False, interactive=False, coder='claude')
        result = workflow.process_issue(42, args)
        
        assert result.success is False
        assert "Failed to generate implementation prompt" in result.message
    
    def test_process_issue_implementation_execution_failure(self, workflow, mock_dependencies):
        """Test process_issue when implementation execution fails."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].prepare_workspace.return_value = "issue-42-branch"
        mock_dependencies['prompt_builder'].build_audit_prompt.return_value = "Audit prompt"
        mock_dependencies['prompt_builder'].build_implementation_prompt.return_value = "Implementation prompt"
        
        # First call succeeds (audit), second call fails (implementation)
        mock_dependencies['prompt_builder'].execute_claude_with_prompt.side_effect = [
            {'success': True, 'response': 'Audit complete'},
            None
        ]
        
        args = Mock(prompt_only=False, dry_run=False, interactive=False, coder='claude')
        result = workflow.process_issue(42, args)
        
        assert result.success is False
        assert "Failed to execute implementation" in result.message
    
    def test_process_issue_no_changes_detected(self, workflow, mock_dependencies):
        """Test process_issue when no changes are detected."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].prepare_workspace.return_value = "issue-42-branch"
        mock_dependencies['prompt_builder'].build_audit_prompt.return_value = "Audit prompt"
        mock_dependencies['prompt_builder'].build_implementation_prompt.return_value = "Implementation prompt"
        mock_dependencies['prompt_builder'].execute_claude_with_prompt.side_effect = [
            {'success': True, 'response': 'Audit complete'},
            {'success': True, 'response': 'Implementation complete'}
        ]
        mock_dependencies['workspace_manager'].has_changes.return_value = False
        
        args = Mock(prompt_only=False, dry_run=False, interactive=False, coder='claude')
        result = workflow.process_issue(42, args)
        
        assert result.success is True
        assert "No changes detected" in result.message
        mock_dependencies['github_client'].comment_on_issue.assert_called()
    
    def test_process_issue_commit_failure(self, workflow, mock_dependencies):
        """Test process_issue when commit fails."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].prepare_workspace.return_value = "issue-42-branch"
        mock_dependencies['prompt_builder'].build_audit_prompt.return_value = "Audit prompt"
        mock_dependencies['prompt_builder'].build_implementation_prompt.return_value = "Implementation prompt"
        mock_dependencies['prompt_builder'].execute_claude_with_prompt.side_effect = [
            {'success': True, 'response': 'Audit complete'},
            {'success': True, 'response': 'Implementation complete'}
        ]
        mock_dependencies['workspace_manager'].has_changes.return_value = True
        mock_dependencies['workspace_manager'].commit_changes.return_value = False
        
        args = Mock(prompt_only=False, dry_run=False, interactive=False, coder='claude')
        result = workflow.process_issue(42, args)
        
        assert result.success is False
        assert "Failed to commit changes" in result.message
    
    def test_process_issue_push_failure(self, workflow, mock_dependencies):
        """Test process_issue when push fails."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].prepare_workspace.return_value = "issue-42-branch"
        mock_dependencies['prompt_builder'].build_audit_prompt.return_value = "Audit prompt"
        mock_dependencies['prompt_builder'].build_implementation_prompt.return_value = "Implementation prompt"
        mock_dependencies['prompt_builder'].execute_claude_with_prompt.side_effect = [
            {'success': True, 'response': 'Audit complete'},
            {'success': True, 'response': 'Implementation complete'}
        ]
        mock_dependencies['workspace_manager'].has_changes.return_value = True
        mock_dependencies['workspace_manager'].commit_changes.return_value = True
        mock_dependencies['workspace_manager'].push_branch.return_value = False
        
        args = Mock(prompt_only=False, dry_run=False, interactive=False, coder='claude')
        result = workflow.process_issue(42, args)
        
        assert result.success is False
        assert "Failed to push branch" in result.message
    
    def test_process_issue_pr_creation_failure(self, workflow, mock_dependencies):
        """Test process_issue when PR creation fails."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        mock_dependencies['github_client'].get_issue.return_value = issue_data
        mock_dependencies['workspace_manager'].prepare_workspace.return_value = "issue-42-branch"
        mock_dependencies['prompt_builder'].build_audit_prompt.return_value = "Audit prompt"
        mock_dependencies['prompt_builder'].build_implementation_prompt.return_value = "Implementation prompt"
        mock_dependencies['prompt_builder'].execute_claude_with_prompt.side_effect = [
            {'success': True, 'response': 'Audit complete'},
            {'success': True, 'response': 'Implementation complete'}
        ]
        mock_dependencies['workspace_manager'].has_changes.return_value = True
        mock_dependencies['workspace_manager'].commit_changes.return_value = True
        mock_dependencies['workspace_manager'].push_branch.return_value = True
        mock_dependencies['workspace_manager'].get_git_diff.return_value = "diff output"
        mock_dependencies['workspace_manager'].get_commit_log.return_value = "commit log"
        mock_dependencies['pr_body_generator'].generate_pr_body.return_value = "PR body"
        mock_dependencies['github_client'].create_pr.return_value = None
        
        args = Mock(prompt_only=False, dry_run=False, interactive=False, coder='claude')
        result = workflow.process_issue(42, args)
        
        assert result.success is False
        assert "Failed to create PR" in result.message
    
    def test_analyze_bug_prompt_generation_failure(self, workflow, mock_dependencies):
        """Test analyze_bug when prompt generation fails."""
        mock_dependencies['prompt_builder'].build_bug_analysis_prompt.return_value = None
        
        args = Mock(prompt_only=False, dry_run=False)
        result = workflow.analyze_bug("Something is broken", args)
        
        assert result.success is False
        assert "Failed to generate bug analysis prompt" in result.message
    
    def test_analyze_bug_prompt_only_mode(self, workflow, mock_dependencies):
        """Test analyze_bug in prompt-only mode."""
        mock_dependencies['prompt_builder'].build_bug_analysis_prompt.return_value = "Bug prompt"
        
        args = Mock(prompt_only=True)
        
        with patch('builtins.print') as mock_print:
            result = workflow.analyze_bug("Something is broken", args)
        
        assert result.success is True
        assert "Prompt generated" in result.message
        mock_print.assert_called()
    
    def test_analyze_bug_claude_execution_failure(self, workflow, mock_dependencies):
        """Test analyze_bug when Claude execution fails."""
        mock_dependencies['prompt_builder'].build_bug_analysis_prompt.return_value = "Bug prompt"
        mock_dependencies['prompt_builder'].execute_claude_with_prompt.return_value = None
        
        args = Mock(prompt_only=False, dry_run=False, interactive=False, coder='claude')
        result = workflow.analyze_bug("Something is broken", args)
        
        assert result.success is False
        assert "Failed to execute bug analysis" in result.message
    
    def test_analyze_bug_issue_creation_failure(self, workflow, mock_dependencies):
        """Test analyze_bug when issue creation fails."""
        mock_dependencies['prompt_builder'].build_bug_analysis_prompt.return_value = "Bug prompt"
        mock_dependencies['prompt_builder'].execute_claude_with_prompt.return_value = {
            'success': True,
            'response': 'Analysis complete'
        }
        mock_dependencies['github_client'].create_issue.return_value = None
        
        args = Mock(prompt_only=False, dry_run=False, interactive=False, coder='claude')
        result = workflow.analyze_bug("Something is broken", args)
        
        assert result.success is False
        assert "Failed to create GitHub issue" in result.message
    
    def test_review_pr_github_fetch_failure(self, workflow, mock_dependencies):
        """Test review_pr when GitHub fetch fails."""
        mock_dependencies['github_client'].get_pr.return_value = None
        
        args = Mock(prompt_only=False, dry_run=False)
        result = workflow.review_pr(123, args)
        
        assert result.success is False
        assert "Failed to fetch PR" in result.message
    
    def test_review_pr_prompt_generation_failure(self, workflow, mock_dependencies):
        """Test review_pr when prompt generation fails."""
        pr_data = Mock()
        mock_dependencies['github_client'].get_pr.return_value = pr_data
        mock_dependencies['prompt_builder'].build_pr_review_prompt.return_value = None
        
        args = Mock(prompt_only=False, dry_run=False)
        result = workflow.review_pr(123, args)
        
        assert result.success is False
        assert "Failed to generate PR review prompt" in result.message
    
    def test_review_pr_prompt_only_mode(self, workflow, mock_dependencies):
        """Test review_pr in prompt-only mode."""
        pr_data = Mock()
        mock_dependencies['github_client'].get_pr.return_value = pr_data
        mock_dependencies['prompt_builder'].build_pr_review_prompt.return_value = "Review prompt"
        
        args = Mock(prompt_only=True)
        
        with patch('builtins.print') as mock_print:
            result = workflow.review_pr(123, args)
        
        assert result.success is True
        assert "Prompt generated" in result.message
        mock_print.assert_called()
    
    def test_review_pr_claude_execution_failure(self, workflow, mock_dependencies):
        """Test review_pr when Claude execution fails."""
        pr_data = Mock()
        mock_dependencies['github_client'].get_pr.return_value = pr_data
        mock_dependencies['prompt_builder'].build_pr_review_prompt.return_value = "Review prompt"
        mock_dependencies['prompt_builder'].execute_claude_review.return_value = None
        
        args = Mock(prompt_only=False, dry_run=False, interactive=False, coder='claude')
        result = workflow.review_pr(123, args)
        
        assert result.success is False
        assert "Failed to generate PR review" in result.message
    
    def test_review_pr_comment_posting_failure(self, workflow, mock_dependencies):
        """Test review_pr when comment posting fails."""
        pr_data = Mock()
        mock_dependencies['github_client'].get_pr.return_value = pr_data
        mock_dependencies['prompt_builder'].build_pr_review_prompt.return_value = "Review prompt"
        mock_dependencies['prompt_builder'].execute_claude_review.return_value = {
            'success': True,
            'response': 'Review complete'
        }
        mock_dependencies['github_client'].comment_on_pr.return_value = False
        
        args = Mock(prompt_only=False, dry_run=False, interactive=False, coder='claude')
        result = workflow.review_pr(123, args)
        
        assert result.success is False
        assert "Failed to post review comment" in result.message