"""Integration tests for claude-tasker end-to-end functionality."""
import pytest
import subprocess
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, mock_open, call

from src.claude_tasker.workflow_logic import WorkflowLogic, WorkflowResult
from src.claude_tasker.github_client import IssueData, PRData
from src.claude_tasker.prompt_models import LLMResult, TwoStageResult


class TestIntegration:
    """Integration tests for end-to-end functionality."""
    
    def test_full_issue_workflow_prompt_only(self):
        """Test complete issue implementation workflow in prompt-only mode."""
        workflow = WorkflowLogic()
        
        # Mock all dependencies for full end-to-end test
        with patch.object(workflow, 'validate_environment') as mock_env, \
             patch.object(workflow.github_client, 'get_issue') as mock_get_issue, \
             patch.object(workflow.workspace_manager, 'workspace_hygiene') as mock_hygiene, \
             patch.object(workflow.workspace_manager, 'create_timestamped_branch') as mock_branch, \
             patch.object(workflow.prompt_builder, 'execute_two_stage_prompt') as mock_prompt:
            
            # Set up successful workflow conditions
            mock_env.return_value = (True, "Environment validation passed")
            
            issue_data = IssueData(
                number=316,
                title="Setup Python tests",
                body="Create comprehensive test suite for claude-tasker",
                labels=["enhancement"],
                url="https://github.com/test/repo/issues/316",
                author="testuser",
                state="open"
            )
            mock_get_issue.return_value = issue_data
            
            mock_hygiene.return_value = True
            mock_branch.return_value = (True, "issue-316-1234567890")
            
            mock_prompt.return_value = TwoStageResult(
                success=True,
                meta_prompt='Generated meta prompt for test implementation',
                optimized_prompt='Comprehensive test implementation prompt',
                execution_result=None  # Prompt-only mode
            )
            
            # Execute workflow
            result = workflow.process_single_issue(316, prompt_only=True)
            
            # Verify successful completion
            assert result.success is True
            assert result.issue_number == 316
            assert "generated" in result.message.lower()
            
            # Verify all components were called
            mock_env.assert_called_once()
            mock_get_issue.assert_called_once_with(316)
            mock_hygiene.assert_called_once()
            mock_branch.assert_called_once()
            mock_prompt.assert_called_once()
    
    def test_pr_review_workflow_complete(self):
        """Test complete PR review workflow."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment') as mock_env, \
             patch.object(workflow.github_client, 'get_pr') as mock_get_pr, \
             patch.object(workflow.github_client, 'get_pr_diff') as mock_get_diff, \
             patch.object(workflow.prompt_builder, 'generate_pr_review_prompt') as mock_review_prompt, \
             patch.object(workflow.prompt_builder, 'build_with_claude') as mock_build:
            
            # Set up PR review workflow conditions
            mock_env.return_value = (True, "Environment validation passed")
            
            pr_data = PRData(
                number=329,
                title="Add Python tests",
                body="This PR adds comprehensive Python tests",
                head_ref="feature-tests",
                base_ref="main",
                author="testuser",
                additions=500,
                deletions=10,
                changed_files=5,
                url="https://github.com/test/repo/pull/329"
            )
            mock_get_pr.return_value = pr_data
            
            diff_content = "diff --git a/tests/test_new.py b/tests/test_new.py\\nnew file mode 100644\\n+def test_example():\\n+    assert True"
            mock_get_diff.return_value = diff_content
            
            mock_review_prompt.return_value = "Generated PR review prompt"
            mock_build.return_value = {'response': 'Comprehensive review completed'}
            
            # Execute PR review workflow in prompt_only mode
            result = workflow.review_pr(329, prompt_only=True)
            
            # Verify successful completion
            assert result.success is True
            assert "generated" in result.message.lower()
            
            # Verify all components were called except build_with_claude (since prompt_only=True)
            mock_env.assert_called_once()
            mock_get_pr.assert_called_once_with(329)
            mock_get_diff.assert_called_once_with(329)
            mock_review_prompt.assert_called_once()
            # build_with_claude should NOT be called in prompt_only mode
            mock_build.assert_not_called()
    
    def test_bug_analysis_workflow(self):
        """Test bug analysis workflow."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment') as mock_env, \
             patch.object(workflow.workspace_manager, 'get_commit_log') as mock_commit_log, \
             patch.object(workflow.workspace_manager, 'get_git_diff') as mock_git_diff, \
             patch.object(workflow.prompt_builder, 'generate_bug_analysis_prompt') as mock_analysis_prompt, \
             patch.object(workflow.prompt_builder, 'build_with_claude') as mock_build:
            
            # Set up bug analysis workflow conditions
            mock_env.return_value = (True, "Environment validation passed")
            mock_commit_log.return_value = "abc123 Recent commit\\ndef456 Another commit"
            mock_git_diff.return_value = "diff --git a/test.py b/test.py\\n-old line\\n+new line"
            
            mock_analysis_prompt.return_value = "Generated bug analysis prompt"
            mock_build.return_value = LLMResult(
                success=True,
                text='Bug analysis completed: Intermittent test failures likely due to race conditions'
            )
            
            # Execute bug analysis workflow
            bug_description = "Tests are failing intermittently"
            result = workflow.analyze_bug(bug_description, prompt_only=True)
            
            # Verify successful completion
            assert result.success is True
            assert "analysis completed" in result.message.lower()
            
            # Verify components were called with proper context
            mock_env.assert_called_once()
            mock_analysis_prompt.assert_called_once()
            
            # Check that context was gathered
            call_args = mock_analysis_prompt.call_args[0]
            assert bug_description in call_args[0]  # bug description
            
            context_arg = mock_analysis_prompt.call_args[0][2]  # PromptContext object
            assert 'recent_commits' in context_arg.project_info
            assert context_arg.git_diff is not None
    
    def test_range_processing_with_timeout(self):
        """Test range processing with timeout between tasks."""
        workflow = WorkflowLogic(timeout_between_tasks=0.1)  # Short timeout for testing
        
        with patch.object(workflow, 'process_single_issue') as mock_process, \
             patch('time.sleep') as mock_sleep:
            
            # Mock successful issue processing for range 316-318
            def process_side_effect(issue_number, prompt_only=False, project_number=None):
                return WorkflowResult(
                    success=True,
                    message=f"Issue #{issue_number} processed successfully",
                    issue_number=issue_number
                )
            
            mock_process.side_effect = process_side_effect
            
            # Execute range processing
            results = workflow.process_issue_range(316, 318, prompt_only=True)
            
            # Verify processing results
            assert len(results) == 3  # Issues 316, 317, 318
            assert all(result.success for result in results)
            
            # Verify individual issues were processed
            expected_calls = [call(316, True, None), call(317, True, None), call(318, True, None)]
            mock_process.assert_has_calls(expected_calls)
            
            # Verify timeout was applied between issues (2 timeouts for 3 issues)
            assert mock_sleep.call_count == 2
            mock_sleep.assert_has_calls([call(0.1), call(0.1)])
    
    def test_project_context_integration(self):
        """Test integration with GitHub project context."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment') as mock_env, \
             patch.object(workflow.github_client, 'get_issue') as mock_get_issue, \
             patch.object(workflow.github_client, 'get_project_info') as mock_get_project, \
             patch.object(workflow.workspace_manager, 'workspace_hygiene') as mock_hygiene, \
             patch.object(workflow.workspace_manager, 'create_timestamped_branch') as mock_branch, \
             patch.object(workflow.prompt_builder, 'execute_two_stage_prompt') as mock_prompt:
            
            # Set up project integration conditions
            mock_env.return_value = (True, "Environment validation passed")
            
            issue_data = IssueData(
                number=316,
                title="Test Issue with Project",
                body="Test issue linked to project",
                labels=[],
                url="https://github.com/test/repo/issues/316",
                author="testuser",
                state="open"
            )
            mock_get_issue.return_value = issue_data
            
            project_info = {
                "title": "Test Project",
                "body": "Project for testing integration",
                "items": []
            }
            mock_get_project.return_value = project_info
            
            mock_hygiene.return_value = True
            mock_branch.return_value = (True, "issue-316-1234567890")
            
            mock_prompt.return_value = TwoStageResult(
                success=True,
                meta_prompt='Generated meta prompt with project context',
                optimized_prompt='Project-aware implementation prompt',
                execution_result=None
            )
            
            # Execute workflow with project context
            result = workflow.process_single_issue(316, prompt_only=True, project_number=3)
            
            # Verify successful completion with project context
            assert result.success is True
            assert result.issue_number == 316
            
            # Verify project context was fetched
            mock_get_project.assert_called_once_with(3)
            
            # Verify prompt was generated with project context
            mock_prompt.assert_called_once()
            call_args = mock_prompt.call_args
            task_data = call_args[1]['task_data']
            assert task_data['issue_number'] == 316
    
    def test_error_recovery_and_retries(self):
        """Test error recovery and retry mechanisms."""
        workflow = WorkflowLogic()
        
        # Test retry mechanism in GitHub client
        with patch('subprocess.run') as mock_run, \
             patch('time.sleep') as mock_sleep:
            
            attempt_count = 0
            
            def retry_side_effect(*args, **kwargs):
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 3:
                    # Simulate API rate limit for first 2 attempts
                    return subprocess.CompletedProcess(args[0], 1, "", "API rate limit exceeded")
                else:
                    # Success on third attempt
                    issue_json = json.dumps({
                        "number": 316,
                        "title": "Test Issue",
                        "body": "Test",
                        "labels": [],
                        "url": "https://github.com/test/repo/issues/316",
                        "author": {"login": "testuser"},
                        "state": "open"
                    })
                    return subprocess.CompletedProcess(args[0], 0, issue_json, "")
            
            mock_run.side_effect = retry_side_effect
            
            # Test issue fetching with retries
            issue_data = workflow.github_client.get_issue(316)
            
            # Should eventually succeed after retries
            assert issue_data is not None
            assert issue_data.number == 316
            assert issue_data.title == "Test Issue"
            
            # Should have attempted 3 times
            assert attempt_count == 3
            
            # Should have applied exponential backoff delays
            assert mock_sleep.call_count >= 2
    
    def test_comprehensive_flag_combination(self):
        """Test comprehensive combination of multiple workflow options."""
        # Test WorkflowLogic with various configuration options
        workflow = WorkflowLogic(
            timeout_between_tasks=30.0,
            interactive_mode=False,
            coder="claude",
            base_branch="develop"
        )
        
        # Verify configuration was applied
        assert workflow.timeout_between_tasks == 30.0
        assert workflow.interactive_mode is False
        assert workflow.coder == "claude"
        assert workflow.base_branch == "develop"
        
        # Test that components are properly initialized
        assert workflow.env_validator is not None
        assert workflow.github_client is not None
        assert workflow.workspace_manager is not None
        assert workflow.prompt_builder is not None
        assert workflow.pr_body_generator is not None
        
        # Test complex workflow with all options
        with patch.object(workflow, 'validate_environment') as mock_env, \
             patch.object(workflow.github_client, 'get_issue') as mock_get_issue, \
             patch.object(workflow.github_client, 'get_project_info') as mock_get_project, \
             patch.object(workflow.workspace_manager, 'workspace_hygiene') as mock_hygiene, \
             patch.object(workflow.workspace_manager, 'create_timestamped_branch') as mock_branch, \
             patch.object(workflow.prompt_builder, 'execute_two_stage_prompt') as mock_prompt:
            
            # Set up complex workflow conditions
            mock_env.return_value = (True, "Environment validation passed")
            
            issue_data = IssueData(
                number=316, title="Complex Test Issue", body="Test", labels=[], 
                url="https://github.com/test/repo/issues/316",
                author="testuser", state="open"
            )
            mock_get_issue.return_value = issue_data
            mock_get_project.return_value = {"title": "Test Project"}
            mock_hygiene.return_value = True
            mock_branch.return_value = (True, "issue-316-1234567890")
            mock_prompt.return_value = TwoStageResult(success=True, meta_prompt='test', optimized_prompt='test')
            
            # Execute with project context
            result = workflow.process_single_issue(316, prompt_only=True, project_number=3)
            
            # Should handle all complex options successfully
            assert result.success is True
            assert result.issue_number == 316
            
            # Verify branch creation used custom base branch
            mock_branch.assert_called_once_with(316, "develop")