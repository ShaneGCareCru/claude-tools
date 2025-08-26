"""Comprehensive integration tests for claude-tasker full workflows."""

import pytest
import subprocess
import tempfile
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
import time

from src.claude_tasker.workflow_logic import WorkflowLogic, WorkflowResult
from src.claude_tasker.github_client import IssueData, PRData
from src.claude_tasker.prompt_models import TwoStageResult, LLMResult
from src.claude_tasker.cli import main


class TestFullWorkflowIntegration(TestCase):
    """Test complete end-to-end workflows."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_issue = IssueData(
            number=123,
            title="Add user authentication",
            body="Implement JWT-based authentication system with login/logout functionality",
            labels=["enhancement", "security"],
            url="https://github.com/test/repo/issues/123",
            author="developer",
            state="open",
            assignee="team-lead",
            milestone="v2.0"
        )
        
        self.mock_pr = PRData(
            number=456,
            title="Implement user authentication",
            body="This PR adds JWT authentication as requested in #123",
            head_ref="issue-123-auth",
            base_ref="main",
            author="developer",
            additions=150,
            deletions=20,
            changed_files=8,
            url="https://github.com/test/repo/pull/456"
        )
    
    def test_complete_issue_implementation_workflow(self):
        """Test complete workflow from issue to PR creation."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.github_client, 'get_issue', return_value=self.mock_issue), \
             patch.object(workflow.workspace_manager, 'workspace_hygiene', return_value=True), \
             patch.object(workflow.workspace_manager, 'create_timestamped_branch', return_value=(True, "issue-123-1234567890")), \
             patch.object(workflow.prompt_builder, 'execute_two_stage_prompt') as mock_two_stage, \
             patch.object(workflow.workspace_manager, 'has_changes_to_commit', return_value=True), \
             patch.object(workflow.workspace_manager, 'get_git_diff', return_value="diff --git a/auth.py..."), \
             patch.object(workflow.workspace_manager, 'get_commit_log', return_value="abc123 Add auth module"), \
             patch.object(workflow.workspace_manager, 'commit_changes', return_value=True), \
             patch.object(workflow.workspace_manager, 'push_branch', return_value=True), \
             patch.object(workflow.pr_body_generator, 'generate_pr_body', return_value="## Summary\nAdded authentication"), \
             patch.object(workflow.github_client, 'create_pr', return_value="https://github.com/test/repo/pull/456"), \
             patch.object(workflow.github_client, 'comment_on_issue', return_value=True):
            
            # Mock successful two-stage execution
            mock_two_stage.return_value = TwoStageResult(
                success=True,
                meta_prompt="Generated meta prompt",
                optimized_prompt="Implementation prompt",
                execution_result={"status": "completed", "files_modified": ["auth.py", "tests/test_auth.py"]}
            )
            
            result = workflow.process_single_issue(123, prompt_only=False)
            
            # Verify successful completion
            assert result.success is True
            assert result.issue_number == 123
            assert result.pr_url == "https://github.com/test/repo/pull/456"
            assert result.branch_name == "issue-123-1234567890"
            
            # Verify all steps were executed
            mock_two_stage.assert_called_once()
            workflow.workspace_manager.workspace_hygiene.assert_called_once()
            workflow.workspace_manager.create_timestamped_branch.assert_called_once()
            workflow.workspace_manager.commit_changes.assert_called_once()
            workflow.workspace_manager.push_branch.assert_called_once()
            workflow.github_client.create_pr.assert_called_once()
            workflow.github_client.comment_on_issue.assert_called_once()
    
    def test_complete_pr_review_workflow(self):
        """Test complete PR review workflow."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.github_client, 'get_pr', return_value=self.mock_pr), \
             patch.object(workflow.github_client, 'get_pr_diff', return_value="diff --git a/auth.py..."), \
             patch.object(workflow.github_client, 'get_pr_files', return_value=["auth.py", "tests/test_auth.py"]), \
             patch.object(workflow.prompt_builder, 'build_pr_review_prompt', return_value="Review prompt"), \
             patch.object(workflow.prompt_builder, '_execute_review_with_claude') as mock_review, \
             patch.object(workflow.github_client, 'comment_on_pr', return_value=True):
            
            # Mock successful review execution
            mock_review.return_value = LLMResult(
                success=True,
                data={"review": "Comprehensive PR review", "rating": "LGTM"},
                raw_output="## Code Review\nThis PR looks great!",
                error_message=""
            )
            
            result = workflow.review_pr(456, prompt_only=False)
            
            # Verify successful completion
            assert result.success is True
            assert "review posted" in result.message.lower() or "review generated" in result.message.lower()
            
            # Verify all steps were executed
            workflow.github_client.get_pr.assert_called_once_with(456)
            workflow.github_client.get_pr_diff.assert_called_once_with(456)
            workflow.prompt_builder.build_pr_review_prompt.assert_called_once()
            mock_review.assert_called_once()
    
    def test_bug_analysis_to_issue_creation_workflow(self):
        """Test complete bug analysis and issue creation workflow."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.prompt_builder, 'build_bug_analysis_prompt', return_value="Bug analysis prompt"), \
             patch.object(workflow.prompt_builder, 'execute_llm_tool') as mock_execute, \
             patch.object(workflow.github_client, 'create_issue', return_value="https://github.com/test/repo/issues/789"):
            
            # Mock successful analysis
            mock_execute.return_value = {
                'issue_title': 'Bug: Authentication fails on mobile devices',
                'issue_body': '''## Problem Description
Users report that login fails on mobile devices with 2FA enabled.

## Steps to Reproduce
1. Open app on mobile device
2. Enter valid credentials
3. Enter 2FA code
4. Login fails with "Invalid token" error

## Expected Behavior
Login should succeed with valid 2FA token

## Actual Behavior
Login fails consistently on mobile devices

## Additional Context
- Desktop login works fine
- Affects both iOS and Android
- Started after recent security update

## Proposed Solution
- Check mobile-specific 2FA token validation
- Review token expiration timing
- Test with different mobile browsers

## Labels
- bug
- mobile
- authentication
- high-priority'''
            }
            
            result = workflow.analyze_bug(
                "Users can't login on mobile devices - 2FA token validation fails",
                prompt_only=False
            )
            
            # Verify successful completion
            assert result.success is True
            assert "issue created" in result.message.lower()
            assert "https://github.com/test/repo/issues/789" in result.message
            
            # Verify all steps were executed
            workflow.prompt_builder.build_bug_analysis_prompt.assert_called_once()
            mock_execute.assert_called_once()
            workflow.github_client.create_issue.assert_called_once()
    
    def test_feature_analysis_to_issue_creation_workflow(self):
        """Test complete feature analysis and issue creation workflow."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.prompt_builder, 'build_feature_analysis_prompt', return_value="Feature analysis prompt"), \
             patch.object(workflow.prompt_builder, 'execute_llm_tool') as mock_execute, \
             patch.object(workflow.github_client, 'create_issue', return_value="https://github.com/test/repo/issues/890"):
            
            # Mock successful analysis
            mock_execute.return_value = {
                'issue_title': 'Feature: Add CSV export functionality for reports',
                'issue_body': '''## Feature Request
Add ability to export reports in CSV format for data analysis.

## User Story
As a data analyst, I want to export reports in CSV format so that I can perform further analysis in Excel or other tools.

## Acceptance Criteria
- [ ] Add "Export as CSV" button to report pages
- [ ] CSV should include all visible columns
- [ ] Handle large datasets (pagination/streaming)
- [ ] Preserve data formatting where possible
- [ ] Include proper headers
- [ ] Support date range filtering

## Technical Implementation
- Create new export service
- Add CSV generation utilities
- Update report components with export button
- Add progress indicator for large exports
- Handle memory constraints for large datasets

## Dependencies
- None identified

## Estimated Effort
Medium (1-2 sprints)

## Labels
- enhancement
- reports
- export
- medium-priority'''
            }
            
            result = workflow.analyze_feature(
                "Add CSV export functionality for all reports",
                prompt_only=False
            )
            
            # Verify successful completion
            assert result.success is True
            assert "issue created" in result.message.lower()
            assert "https://github.com/test/repo/issues/890" in result.message
            
            # Verify all steps were executed
            workflow.prompt_builder.build_feature_analysis_prompt.assert_called_once()
            mock_execute.assert_called_once()
            workflow.github_client.create_issue.assert_called_once()
    
    def test_issue_range_processing_workflow(self):
        """Test processing multiple issues in sequence."""
        workflow = WorkflowLogic(timeout_between_tasks=0.1)  # Short timeout for testing
        
        with patch.object(workflow, 'process_single_issue') as mock_process, \
             patch('time.sleep') as mock_sleep:
            
            # Mock successful processing for each issue
            def process_side_effect(issue_number, *args, **kwargs):
                return WorkflowResult(
                    success=True,
                    message=f"Issue #{issue_number} processed successfully",
                    issue_number=issue_number,
                    pr_url=f"https://github.com/test/repo/pull/{issue_number + 300}",
                    branch_name=f"issue-{issue_number}-123456789"
                )
            
            mock_process.side_effect = process_side_effect
            
            results = workflow.process_issue_range(100, 102, prompt_only=True)
            
            # Verify all issues were processed
            assert len(results) == 3
            assert all(result.success for result in results)
            assert results[0].issue_number == 100
            assert results[1].issue_number == 101
            assert results[2].issue_number == 102
            
            # Verify process_single_issue was called for each
            assert mock_process.call_count == 3
            
            # Verify timeout was applied between issues (2 sleeps for 3 issues)
            assert mock_sleep.call_count == 2
            mock_sleep.assert_called_with(0.1)
    
    def test_error_recovery_workflow(self):
        """Test workflow behavior with various error conditions."""
        workflow = WorkflowLogic()
        
        # Test environment validation failure
        with patch.object(workflow, 'validate_environment', return_value=(False, "Git not found")):
            result = workflow.process_single_issue(123)
            assert result.success is False
            assert "git not found" in result.message.lower()
        
        # Test issue not found
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.github_client, 'get_issue', return_value=None):
            result = workflow.process_single_issue(999)
            assert result.success is False
            assert "not found" in result.message.lower()
        
        # Test workspace hygiene failure
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.github_client, 'get_issue', return_value=self.mock_issue), \
             patch.object(workflow.workspace_manager, 'workspace_hygiene', return_value=False):
            result = workflow.process_single_issue(123)
            assert result.success is False
            assert "workspace hygiene" in result.message.lower()
        
        # Test branch creation failure
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.github_client, 'get_issue', return_value=self.mock_issue), \
             patch.object(workflow.workspace_manager, 'workspace_hygiene', return_value=True), \
             patch.object(workflow.workspace_manager, 'create_timestamped_branch', return_value=(False, "Branch creation failed")):
            result = workflow.process_single_issue(123)
            assert result.success is False
            assert "branch creation failed" in result.message.lower()
    
    def test_prompt_only_mode_workflow(self):
        """Test complete workflow in prompt-only mode."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.github_client, 'get_issue', return_value=self.mock_issue), \
             patch.object(workflow.workspace_manager, 'workspace_hygiene', return_value=True), \
             patch.object(workflow.workspace_manager, 'create_timestamped_branch', return_value=(True, "issue-123-1234567890")), \
             patch.object(workflow.prompt_builder, 'execute_two_stage_prompt') as mock_two_stage:
            
            # Mock successful two-stage execution in prompt-only mode
            mock_two_stage.return_value = TwoStageResult(
                success=True,
                meta_prompt="Generated meta prompt for analysis",
                optimized_prompt="Optimized implementation prompt",
                execution_result=None  # No execution in prompt-only mode
            )
            
            result = workflow.process_single_issue(123, prompt_only=True)
            
            # Verify successful completion
            assert result.success is True
            assert result.issue_number == 123
            assert "prompt generated" in result.message.lower() or "analysis completed" in result.message.lower()
            
            # Verify two-stage prompt was executed in prompt-only mode
            mock_two_stage.assert_called_once()
            call_args = mock_two_stage.call_args[1]
            assert call_args['prompt_only'] is True
    
    def test_auto_pr_review_integration(self):
        """Test automatic PR review after issue implementation."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.github_client, 'get_issue', return_value=self.mock_issue), \
             patch.object(workflow.workspace_manager, 'workspace_hygiene', return_value=True), \
             patch.object(workflow.workspace_manager, 'create_timestamped_branch', return_value=(True, "issue-123-1234567890")), \
             patch.object(workflow.prompt_builder, 'execute_two_stage_prompt') as mock_two_stage, \
             patch.object(workflow.workspace_manager, 'has_changes_to_commit', return_value=True), \
             patch.object(workflow.workspace_manager, 'get_git_diff', return_value="diff --git a/auth.py..."), \
             patch.object(workflow.workspace_manager, 'get_commit_log', return_value="abc123 Add auth module"), \
             patch.object(workflow.workspace_manager, 'commit_changes', return_value=True), \
             patch.object(workflow.workspace_manager, 'push_branch', return_value=True), \
             patch.object(workflow.pr_body_generator, 'generate_pr_body', return_value="## Summary\nAdded authentication"), \
             patch.object(workflow.github_client, 'create_pr', return_value="https://github.com/test/repo/pull/456"), \
             patch.object(workflow.github_client, 'comment_on_issue', return_value=True), \
             patch.object(workflow, 'review_pr') as mock_review:
            
            # Mock successful two-stage execution
            mock_two_stage.return_value = TwoStageResult(
                success=True,
                meta_prompt="Generated meta prompt",
                optimized_prompt="Implementation prompt",
                execution_result={"status": "completed"}
            )
            
            # Mock successful PR review
            mock_review.return_value = WorkflowResult(
                success=True,
                message="PR review completed"
            )
            
            # Process issue
            result = workflow.process_single_issue(123, prompt_only=False)
            
            # Now test auto PR review (simulating CLI behavior)
            if result.success and result.pr_url:
                # Extract PR number (456) from URL
                pr_num = 456
                review_result = workflow.review_pr(pr_num, False)
                
                assert review_result.success is True
                mock_review.assert_called_once_with(pr_num, False)


class TestCLIIntegration(TestCase):
    """Test CLI integration with full workflows."""
    
    @patch('pathlib.Path.exists', return_value=True)  # Mock CLAUDE.md exists
    @patch('src.claude_tasker.cli.WorkflowLogic')
    @patch('sys.argv', ['claude-tasker', '123'])
    def test_cli_single_issue_success(self, mock_workflow_class, mock_exists):
        """Test CLI processing single issue successfully."""
        mock_workflow = Mock()
        mock_workflow.process_single_issue.return_value = WorkflowResult(
            success=True,
            message="Issue #123 processed successfully",
            issue_number=123,
            pr_url="https://github.com/test/repo/pull/456",
            branch_name="issue-123-1234567890"
        )
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        assert exit_code == 0
        mock_workflow.process_single_issue.assert_called_once_with(123, False, None)
    
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    @patch('sys.argv', ['claude-tasker', '100-102', '--timeout', '5'])
    def test_cli_issue_range_processing(self, mock_workflow_class, mock_exists):
        """Test CLI processing issue range."""
        mock_workflow = Mock()
        mock_workflow.process_issue_range.return_value = [
            WorkflowResult(success=True, message="Issue #100 processed", issue_number=100),
            WorkflowResult(success=True, message="Issue #101 processed", issue_number=101),
            WorkflowResult(success=True, message="Issue #102 processed", issue_number=102)
        ]
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        assert exit_code == 0
        mock_workflow.process_issue_range.assert_called_once_with(100, 102, False, None)
    
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    @patch('sys.argv', ['claude-tasker', '--review-pr', '456'])
    def test_cli_pr_review(self, mock_workflow_class, mock_exists):
        """Test CLI PR review functionality."""
        mock_workflow = Mock()
        mock_workflow.review_pr.return_value = WorkflowResult(
            success=True,
            message="PR #456 reviewed successfully"
        )
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        assert exit_code == 0
        mock_workflow.review_pr.assert_called_once_with(456, False)
    
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    @patch('sys.argv', ['claude-tasker', '--bug', 'Login fails on mobile'])
    def test_cli_bug_analysis(self, mock_workflow_class, mock_exists):
        """Test CLI bug analysis functionality."""
        mock_workflow = Mock()
        mock_workflow.analyze_bug.return_value = WorkflowResult(
            success=True,
            message="Bug analysis completed and issue created: https://github.com/test/repo/issues/789"
        )
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        assert exit_code == 0
        mock_workflow.analyze_bug.assert_called_once_with('Login fails on mobile', False)
    
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    @patch('sys.argv', ['claude-tasker', '--feature', 'Add CSV export'])
    def test_cli_feature_analysis(self, mock_workflow_class, mock_exists):
        """Test CLI feature analysis functionality."""
        mock_workflow = Mock()
        mock_workflow.analyze_feature.return_value = WorkflowResult(
            success=True,
            message="Feature analysis completed and issue created: https://github.com/test/repo/issues/890"
        )
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        assert exit_code == 0
        mock_workflow.analyze_feature.assert_called_once_with('Add CSV export', False)
    
    @patch('pathlib.Path.exists', return_value=False)
    def test_cli_missing_claude_md(self, mock_exists):
        """Test CLI behavior when CLAUDE.md is missing."""
        with patch('sys.argv', ['claude-tasker', '123']):
            exit_code = main()
            
            assert exit_code == 1


class TestPerformanceAndStressIntegration(TestCase):
    """Test performance and stress scenarios."""
    
    def test_large_issue_range_performance(self):
        """Test processing large range of issues efficiently."""
        workflow = WorkflowLogic(timeout_between_tasks=0.01)  # Very short timeout for testing
        
        with patch.object(workflow, 'process_single_issue') as mock_process, \
             patch('time.sleep') as mock_sleep:
            
            # Mock fast successful processing
            mock_process.return_value = WorkflowResult(
                success=True,
                message="Issue processed",
                issue_number=1
            )
            
            start_time = time.time()
            results = workflow.process_issue_range(1, 10, prompt_only=True)
            end_time = time.time()
            
            # Should complete quickly
            assert end_time - start_time < 5.0  # Should take less than 5 seconds
            assert len(results) == 10
            assert all(result.success for result in results)
            assert mock_process.call_count == 10
            assert mock_sleep.call_count == 9  # n-1 sleeps for n issues
    
    def test_error_resilience_in_range_processing(self):
        """Test that range processing continues despite individual failures."""
        workflow = WorkflowLogic(timeout_between_tasks=0.01)
        
        with patch.object(workflow, 'process_single_issue') as mock_process, \
             patch('time.sleep'):
            
            # Mock mixed success/failure results
            def process_side_effect(issue_number, *args, **kwargs):
                if issue_number % 2 == 0:
                    return WorkflowResult(success=False, message=f"Issue #{issue_number} failed", issue_number=issue_number)
                else:
                    return WorkflowResult(success=True, message=f"Issue #{issue_number} succeeded", issue_number=issue_number)
            
            mock_process.side_effect = process_side_effect
            
            results = workflow.process_issue_range(1, 5, prompt_only=True)
            
            # Should process all issues despite some failures
            assert len(results) == 5
            assert mock_process.call_count == 5
            
            # Check mixed results
            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]
            
            assert len(successful) == 3  # Issues 1, 3, 5
            assert len(failed) == 2     # Issues 2, 4
    
    def test_memory_efficiency_with_large_prompts(self):
        """Test memory efficiency when handling large prompts and responses."""
        workflow = WorkflowLogic()
        
        # Create large mock issue
        large_issue = IssueData(
            number=123,
            title="Large Issue",
            body="x" * 10000,  # 10KB body
            labels=["large"] * 100,  # Many labels
            url="https://github.com/test/repo/issues/123",
            author="developer",
            state="open"
        )
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.github_client, 'get_issue', return_value=large_issue), \
             patch.object(workflow.workspace_manager, 'workspace_hygiene', return_value=True), \
             patch.object(workflow.workspace_manager, 'create_timestamped_branch', return_value=(True, "issue-123-1234567890")), \
             patch.object(workflow.prompt_builder, 'execute_two_stage_prompt') as mock_two_stage:
            
            # Mock execution with large response
            mock_two_stage.return_value = TwoStageResult(
                success=True,
                meta_prompt="y" * 5000,  # Large meta prompt
                optimized_prompt="z" * 10000,  # Large optimized prompt
                execution_result={"large_result": "a" * 20000}  # Large result
            )
            
            result = workflow.process_single_issue(123, prompt_only=True)
            
            # Should handle large data gracefully
            assert result.success is True
            mock_two_stage.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])