"""Tests for enhanced debug logging capabilities."""

import pytest
import logging
import json
import os
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO
import sys

from src.claude_tasker.logging_config import (
    setup_logging, get_logger, get_debug_config, 
    should_log_full_content, SensitiveDataFilter
)
from src.claude_tasker.prompt_builder import PromptBuilder
from src.claude_tasker.prompt_models import TwoStageResult, LLMResult
from src.claude_tasker.workflow_logic import WorkflowLogic
from src.claude_tasker.prompt_models import LLMResult
from src.claude_tasker.github_client import IssueData, PRData


class TestLoggingConfiguration:
    """Test logging configuration enhancements."""
    
    def test_setup_logging_with_debug_options(self):
        """Test that debug logging options are properly configured."""
        config = setup_logging(
            log_level='DEBUG',
            log_prompts=True,
            log_responses=True,
            truncate_length=5000
        )
        
        assert config['log_level'] == 'DEBUG'
        assert config['log_prompts'] is True
        assert config['log_responses'] is True
        assert config['truncate_length'] == 5000
    
    def test_debug_config_from_environment(self):
        """Test reading debug config from environment variables."""
        with patch.dict(os.environ, {
            'CLAUDE_LOG_PROMPTS': 'false',
            'CLAUDE_LOG_RESPONSES': 'true',
            'CLAUDE_LOG_TRUNCATE_LENGTH': '2000',
            'CLAUDE_LOG_LEVEL': 'DEBUG'
        }):
            config = get_debug_config()
            assert config['log_prompts'] is False
            assert config['log_responses'] is True
            assert config['truncate_length'] == 2000
            assert config['log_level'] == 'DEBUG'
    
    def test_should_log_full_content_debug_enabled(self):
        """Test full content logging when DEBUG is enabled."""
        with patch.dict(os.environ, {
            'CLAUDE_LOG_PROMPTS': 'true',
            'CLAUDE_LOG_LEVEL': 'DEBUG'
        }):
            logger = logging.getLogger()
            logger.setLevel(logging.DEBUG)
            assert should_log_full_content() is True
    
    def test_should_log_full_content_info_level(self):
        """Test full content logging is disabled at INFO level."""
        with patch.dict(os.environ, {
            'CLAUDE_LOG_PROMPTS': 'true',
            'CLAUDE_LOG_LEVEL': 'INFO'
        }):
            logger = logging.getLogger()
            logger.setLevel(logging.INFO)
            assert should_log_full_content() is False
    
    def test_sensitive_data_filter(self):
        """Test that sensitive data is properly filtered."""
        filter = SensitiveDataFilter()
        
        test_cases = [
            ("password: secret123", "password=***REDACTED***"),
            ("api_key=abc123xyz", "api_key=***REDACTED***"),
            ("token: mytoken456", "token=***REDACTED***"),
            ("user@example.com", "***EMAIL***"),
            ("normal text without secrets", "normal text without secrets")
        ]
        
        for input_text, expected in test_cases:
            filtered = filter.filter(input_text)
            assert expected in filtered or filtered == expected


class TestPromptBuilderLogging:
    """Test enhanced logging in PromptBuilder."""
    
    @pytest.fixture
    def prompt_builder(self):
        """Create a PromptBuilder instance for testing."""
        return PromptBuilder()
    
    @pytest.fixture
    def mock_issue_data(self):
        """Create mock issue data."""
        return IssueData(
            number=123,
            title="Test Issue",
            body="Issue description",
            state="open",
            author="testuser",
            labels=["bug", "enhancement"],
            url="https://github.com/test/repo/issues/123"
        )
    
    @pytest.fixture
    def mock_pr_data(self):
        """Create mock PR data."""
        # Create a simple mock object with required attributes
        mock_pr = Mock()
        mock_pr.number = 456
        mock_pr.title = "Test PR"
        mock_pr.body = "PR description"
        mock_pr.author = "testuser"
        mock_pr.head_ref = "feature-branch"
        mock_pr.base_ref = "main"
        mock_pr.additions = 100
        mock_pr.deletions = 50
        mock_pr.changed_files = 5
        return mock_pr
    
    def test_generate_lyra_dev_prompt_logging(self, prompt_builder, mock_issue_data, caplog):
        """Test that Lyra-Dev prompt generation logs properly."""
        with caplog.at_level(logging.DEBUG):
            context = {
                'git_diff': 'diff content',
                'related_files': ['file1.py', 'file2.py'],
                'project_info': {'name': 'test-project'}
            }
            
            prompt = prompt_builder.generate_lyra_dev_prompt(
                mock_issue_data, 
                "CLAUDE.md content",
                context
            )
            
            # Check debug logs were created
            assert "Generating Lyra-Dev prompt for issue #123" in caplog.text
            assert "Context keys:" in caplog.text
            assert "Including git diff" in caplog.text
            assert "Including 2 related files" in caplog.text
            assert "Including project info context" in caplog.text
            assert "Generated Lyra-Dev prompt:" in caplog.text
    
    def test_generate_pr_review_prompt_logging(self, prompt_builder, mock_pr_data, caplog):
        """Test that PR review prompt generation logs properly."""
        with caplog.at_level(logging.DEBUG):
            prompt = prompt_builder.generate_pr_review_prompt(
                mock_pr_data,
                "diff content",
                "CLAUDE.md content"
            )
            
            assert "Generating PR review prompt for PR #456" in caplog.text
            assert "PR: Test PR by testuser" in caplog.text
            assert "Changes: +100/-50 lines across 5 files" in caplog.text
            assert "Generated PR review prompt:" in caplog.text
    
    def test_validate_meta_prompt_logging(self, prompt_builder, caplog):
        """Test meta-prompt validation logging."""
        with caplog.at_level(logging.DEBUG):
            # Test valid prompt
            valid_prompt = "x" * 200 + " DECONSTRUCT DIAGNOSE DEVELOP DELIVER"
            assert prompt_builder.validate_meta_prompt(valid_prompt) is True
            assert "Meta-prompt validation passed" in caplog.text
            
            # Test invalid prompt - too short
            caplog.clear()
            assert prompt_builder.validate_meta_prompt("short") is False
            assert "Validation failed: Meta-prompt too short" in caplog.text
            
            # Test invalid prompt - problematic patterns (since 4-D sections not checked in meta-prompt validation)
            caplog.clear()
            problematic_prompt = "x" * 200 + " generate another prompt please"
            assert prompt_builder.validate_meta_prompt(problematic_prompt) is False
            assert "Found problematic patterns" in caplog.text
    
    @patch('subprocess.run')
    def test_execute_llm_tool_logging(self, mock_run, prompt_builder, caplog):
        """Test LLM tool execution logging."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"result": "test response"}',
            stderr=''
        )
        
        with caplog.at_level(logging.DEBUG):
            result = prompt_builder._execute_llm_tool(
                'claude',
                'test prompt',
                execute_mode=True
            )
            
            assert "_execute_llm_tool called with tool=claude" in caplog.text
            assert "Prompt length: 11 characters" in caplog.text
            assert "FULL PROMPT CONTENT:" in caplog.text
            assert "test prompt" in caplog.text
            assert "Claude execution completed successfully" in caplog.text
    
    def test_execute_two_stage_prompt_logging(self, prompt_builder, caplog):
        """Test two-stage prompt execution logging."""
        with patch.object(prompt_builder, 'build_with_llm') as mock_llm:
            mock_llm.return_value = {'result': 'optimized prompt'}
            
            with caplog.at_level(logging.INFO):
                results = prompt_builder.execute_two_stage_prompt(
                    task_type="test_task",
                    task_data={'key': 'value'},
                    claude_md_content="CLAUDE.md",
                    prompt_only=True
                )
                
                assert "Starting two-stage prompt execution for task type: test_task" in caplog.text
                assert "Stage 1: Generating meta-prompt" in caplog.text
                assert "Stage 2: Generating optimized prompt" in caplog.text
                assert "Skipping Stage 3: Prompt-only mode enabled" in caplog.text
                assert "Two-stage prompt execution completed successfully" in caplog.text


class TestWorkflowLogicLogging:
    """Test enhanced logging in WorkflowLogic."""
    
    @pytest.fixture
    def workflow_logic(self):
        """Create a WorkflowLogic instance for testing."""
        with patch('src.claude_tasker.workflow_logic.GitHubClient'):
            with patch('src.claude_tasker.workflow_logic.WorkspaceManager'):
                return WorkflowLogic()
    
    def test_validate_environment_logging(self, workflow_logic, caplog):
        """Test environment validation logging."""
        with patch.object(workflow_logic.env_validator, 'validate_all_dependencies') as mock_validate:
            mock_validate.return_value = {'valid': True}
            
            with caplog.at_level(logging.INFO):
                valid, msg = workflow_logic.validate_environment(prompt_only=True)
                
                assert "Validating environment dependencies" in caplog.text
                assert "Environment validation passed" in caplog.text
                assert valid is True
    
    def test_process_single_issue_logging(self, workflow_logic, caplog):
        """Test single issue processing logging."""
        with patch.object(workflow_logic, 'validate_environment') as mock_env:
            mock_env.return_value = (True, "OK")
            
            with patch.object(workflow_logic.github_client, 'get_issue') as mock_get_issue:
                mock_get_issue.return_value = Mock(
                    number=123,
                    title="Test Issue",
                    body="Description",
                    state="open",
                    labels=["bug"]
                )
                
                with patch.object(workflow_logic.workspace_manager, 'validate_branch_for_issue') as mock_validate_branch:
                    mock_validate_branch.return_value = (True, "OK")
                    
                    with patch.object(workflow_logic.workspace_manager, 'smart_branch_for_issue') as mock_smart_branch:
                        mock_smart_branch.return_value = (True, "issue-123-12345", "created")
                    
                        with patch.object(workflow_logic.workspace_manager, 'workspace_hygiene') as mock_hygiene:
                            mock_hygiene.return_value = True
                            
                            with patch.object(workflow_logic.workspace_manager, 'create_timestamped_branch') as mock_create_branch:
                                mock_create_branch.return_value = (True, "issue-123-12345")
                                
                                with patch.object(workflow_logic.prompt_builder, 'execute_two_stage_prompt') as mock_prompt:
                                    mock_prompt.return_value = TwoStageResult(
                                        success=True,
                                        optimized_prompt='test prompt'
                                    )
                                    
                                    with caplog.at_level(logging.INFO):
                                        result = workflow_logic.process_single_issue(123, prompt_only=True)
                                        
                                        assert "Starting to process issue #123" in caplog.text
                                        assert "Fetching issue data for #123" in caplog.text
                                        assert "Creating timestamped branch for issue #123" in caplog.text
                                        assert "Prompt-only mode: Prompt generated for issue #123" in caplog.text
                                        assert result.success is True
    
    def test_decision_logging(self, workflow_logic, caplog):
        """Test decision-making transparency logging."""
        with patch.object(workflow_logic, 'validate_environment') as mock_env:
            mock_env.return_value = (True, "OK")
            
            with patch.object(workflow_logic.workspace_manager, 'validate_branch_for_issue') as mock_validate:
                mock_validate.return_value = (True, "Branch is valid")
                
                with patch.object(workflow_logic.github_client, 'get_issue') as mock_get_issue:
                    # Test closed issue decision
                    mock_get_issue.return_value = Mock(
                        number=123,
                        title="Test Issue", 
                        body="Description",
                        state="closed",
                        labels=[]
                    )
                    
                    with caplog.at_level(logging.INFO):
                        result = workflow_logic.process_single_issue(123)
                        
                        assert "Issue #123 is already closed" in caplog.text
                        assert result.message == "Issue #123 already closed"


class TestResponseProcessingLogging:
    """Test response processing and analysis logging."""
    
    @pytest.fixture
    def prompt_builder(self):
        """Create a PromptBuilder instance for testing."""
        return PromptBuilder()
    
    @patch('subprocess.run')
    def test_successful_response_logging(self, mock_run, prompt_builder, caplog):
        """Test logging of successful responses."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"success": true, "result": "response content"}',
            stderr=''
        )
        
        with caplog.at_level(logging.DEBUG):
            result = prompt_builder._execute_llm_tool(
                'claude',
                'test prompt',
                execute_mode=True
            )
            
            assert "FULL CLAUDE RESPONSE:" in caplog.text
            assert '{"success": true, "result": "response content"}' in caplog.text
    
    @patch('subprocess.run')
    def test_error_response_logging(self, mock_run, prompt_builder, caplog):
        """Test logging of error responses."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='error output',
            stderr='error details'
        )
        
        with caplog.at_level(logging.DEBUG):
            result = prompt_builder._execute_llm_tool(
                'claude',
                'test prompt'
            )
            
            assert "Command failed with return code 1" in caplog.text
            assert "Full stderr output:" in caplog.text
            assert "Full stdout output:" in caplog.text
    
    def test_build_with_claude_response_analysis(self, prompt_builder, caplog):
        """Test Claude response analysis logging."""
        with patch.object(prompt_builder, '_execute_llm_tool') as mock_execute:
            mock_execute.return_value = LLMResult(
                success=False,
                error='Test error message'
            )
            
            with caplog.at_level(logging.DEBUG):
                result = prompt_builder.build_with_claude('test prompt')
                
                assert "Building with Claude: execute_mode=False" in caplog.text
                assert "Claude error: Test error message" in caplog.text
                assert "Claude execution failed" in caplog.text


class TestIntegrationLogging:
    """Integration tests for complete logging flow."""
    
    def test_full_workflow_logging(self, caplog):
        """Test complete workflow with all logging enhancements."""
        # Setup logging with debug options
        setup_logging(
            log_level='DEBUG',
            log_prompts=True,
            log_responses=True,
            truncate_length=1000
        )
        
        prompt_builder = PromptBuilder()
        
        with patch.object(prompt_builder, 'build_with_llm') as mock_llm:
            mock_llm.return_value = {'result': 'optimized prompt'}
            
            with patch.object(prompt_builder, 'build_with_claude') as mock_claude:
                mock_claude.return_value = LLMResult(success=True, data={'result': 'execution result'})
                
                # Use a StringIO to capture logs
                import logging
                import io
                log_capture = io.StringIO()
                handler = logging.StreamHandler(log_capture)
                handler.setLevel(logging.INFO)
                logger = logging.getLogger('src.claude_tasker.prompt_builder')
                logger.addHandler(handler)
                
                try:
                    results = prompt_builder.execute_two_stage_prompt(
                        task_type="integration_test",
                        task_data={'test': 'data'},
                        claude_md_content="Test CLAUDE.md",
                        prompt_only=False
                    )
                    
                    log_output = log_capture.getvalue()
                    
                    # Verify all stages are logged
                    assert "Starting two-stage prompt execution" in log_output
                    assert "Stage 1: Generating meta-prompt" in log_output
                    assert "Stage 2: Generating optimized prompt" in log_output
                    assert "Stage 3: Executing optimized prompt with Claude" in log_output
                    assert results.success is True
                finally:
                    logger.removeHandler(handler)


class TestPerformanceLogging:
    """Test performance impact of logging enhancements."""
    
    def test_logging_overhead_minimal(self):
        """Test that logging overhead is minimal at INFO level."""
        import time
        setup_logging(log_level='INFO')
        prompt_builder = PromptBuilder()
        
        start = time.time()
        for _ in range(100):
            prompt_builder.generate_meta_prompt(
                "test_task",
                {'key': 'value'},
                "CLAUDE.md content"
            )
        duration = time.time() - start
        
        # Should complete 100 iterations quickly
        assert duration < 1.0  # Less than 1 second for 100 iterations
    
    def test_debug_logging_overhead(self):
        """Test debug logging overhead is acceptable."""
        import time
        setup_logging(
            log_level='DEBUG',
            log_prompts=True,
            log_responses=True
        )
        prompt_builder = PromptBuilder()
        
        prompt = "x" * 5000 + " DECONSTRUCT DIAGNOSE DEVELOP DELIVER"
        
        start = time.time()
        for _ in range(100):
            prompt_builder.validate_meta_prompt(prompt)
        duration = time.time() - start
        
        # Even with debug logging, should complete quickly
        assert duration < 2.0  # Less than 2 seconds for 100 iterations with debug logging


if __name__ == "__main__":
    pytest.main([__file__, "-v"])