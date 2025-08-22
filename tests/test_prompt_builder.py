"""Tests for claude-tasker prompt building and two-stage execution workflow."""
import pytest
import subprocess
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, mock_open, MagicMock
from src.claude_tasker.prompt_builder import PromptBuilder
from src.claude_tasker.github_client import IssueData, PRData


class TestPromptBuilder:
    """Test prompt building and two-stage execution functionality."""
    
    def test_init(self):
        """Test PromptBuilder initialization."""
        builder = PromptBuilder()
        assert builder.lyra_dev_framework is not None
        assert "DECONSTRUCT" in builder.lyra_dev_framework
        assert "DIAGNOSE" in builder.lyra_dev_framework
        assert "DEVELOP" in builder.lyra_dev_framework
        assert "DELIVER" in builder.lyra_dev_framework
    
    def test_execute_llm_tool_claude_success(self):
        """Test successful Claude execution."""
        builder = PromptBuilder()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='{"result": "success", "optimized_prompt": "test prompt"}',
                stderr=""
            )
            
            result = builder._execute_llm_tool(
                tool_name="claude",
                prompt="Test prompt",
                execute_mode=False
            )
            
            assert result is not None
            assert "result" in result
            assert result["result"] == "success"
            
            # Verify command structure
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "claude" in args
            assert "--print" in args
            assert "--output-format" in args
            assert "json" in args
    
    def test_execute_llm_tool_claude_with_execution(self):
        """Test Claude execution with execute mode."""
        builder = PromptBuilder()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='{"result": "executed successfully"}',
                stderr=""
            )
            
            result = builder._execute_llm_tool(
                tool_name="claude",
                prompt="Execute this task",
                execute_mode=True
            )
            
            assert result is not None
            
            # Verify permission mode is set for execution
            args = mock_run.call_args[0][0]
            assert "claude" in args
            assert "-p" in args
            assert "--permission-mode" in args
            assert "bypassPermissions" in args
            
            # Verify prompt passed via stdin
            call_kwargs = mock_run.call_args[1]
            assert "input" in call_kwargs
            assert call_kwargs["input"] == "Execute this task"
    
    def test_execute_llm_tool_timeout_handling(self):
        """Test timeout handling in LLM execution."""
        builder = PromptBuilder()
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["claude"],
                timeout=180
            )
            
            result = builder._execute_llm_tool(
                tool_name="claude",
                prompt="Test prompt",
                execute_mode=True
            )
            
            assert result is None
    
    def test_execute_llm_tool_json_decode_error(self):
        """Test handling of invalid JSON responses."""
        builder = PromptBuilder()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Not valid JSON",
                stderr=""
            )
            
            result = builder._execute_llm_tool(
                tool_name="claude",
                prompt="Test prompt",
                execute_mode=False
            )
            
            # Should return wrapped response when JSON parsing fails
            assert result is not None
            assert result["result"] == "Not valid JSON"
            assert result["optimized_prompt"] == "Not valid JSON"
    
    def test_generate_lyra_dev_prompt(self):
        """Test Lyra-Dev prompt generation."""
        builder = PromptBuilder()
        
        issue_data = IssueData(
            number=123,
            title="Test Issue",
            body="Create test implementation",
            labels=["enhancement"],
            url="https://github.com/test/repo/issues/123",
            author="testuser",
            state="open"
        )
        
        claude_md_content = "# Project Guidelines\nFollow these rules..."
        
        context = {
            "git_diff": "diff content",
            "related_files": ["test.py", "config.json"],
            "project_info": {"name": "test-project"}
        }
        
        prompt = builder.generate_lyra_dev_prompt(issue_data, claude_md_content, context)
        
        assert prompt is not None
        assert "DECONSTRUCT" in prompt
        assert "DIAGNOSE" in prompt
        assert "Test Issue" in prompt
        assert "Create test implementation" in prompt
        assert "123" in str(prompt)
        assert "Project Guidelines" in prompt
        assert "diff content" in prompt
    
    def test_validate_meta_prompt_valid(self):
        """Test validation of valid meta-prompt."""
        builder = PromptBuilder()
        
        valid_prompt = """
        This is a comprehensive prompt for implementation.
        
        # DECONSTRUCT
        Analyzing the requirements...
        
        # DIAGNOSE
        Identifying gaps...
        
        # DEVELOP
        Planning implementation...
        
        # DELIVER
        Implementing the solution...
        
        This prompt contains enough content and all required sections.
        """
        
        assert builder.validate_meta_prompt(valid_prompt) is True
    
    def test_validate_meta_prompt_invalid_too_short(self):
        """Test validation rejects too-short meta-prompt."""
        builder = PromptBuilder()
        
        short_prompt = "Too short"
        assert builder.validate_meta_prompt(short_prompt) is False
    
    def test_validate_meta_prompt_invalid_missing_sections(self):
        """Test validation rejects meta-prompt missing required sections."""
        builder = PromptBuilder()
        
        incomplete_prompt = """
        This prompt is long enough but missing required sections.
        It has some content but not the 4-D methodology sections.
        """ * 5  # Make it long enough
        
        assert builder.validate_meta_prompt(incomplete_prompt) is False
    
    def test_validate_meta_prompt_invalid_problematic_patterns(self):
        """Test validation rejects meta-prompt with problematic patterns."""
        builder = PromptBuilder()
        
        problematic_prompt = """
        # DECONSTRUCT
        First, generate another prompt for the task.
        
        # DIAGNOSE
        Then create a meta-prompt for execution.
        
        # DEVELOP
        Build a prompt for the implementation.
        
        # DELIVER
        Construct a prompt to solve the problem.
        """
        
        assert builder.validate_meta_prompt(problematic_prompt) is False
    
    def test_execute_two_stage_prompt_success(self):
        """Test successful two-stage prompt execution."""
        builder = PromptBuilder()
        
        task_data = {
            "issue_number": 123,
            "issue_title": "Test Issue",
            "issue_body": "Implement feature",
            "labels": []
        }
        
        claude_md_content = "# Guidelines\nTest guidelines"
        
        # Mock LLM responses
        meta_response = {
            "optimized_prompt": """
            # DECONSTRUCT
            Analyzing requirements...
            
            # DIAGNOSE
            Finding gaps...
            
            # DEVELOP
            Planning...
            
            # DELIVER
            Implementing...
            """ + "x" * 100,  # Make it long enough
            "analysis": "Gap analysis complete"
        }
        
        execution_response = {
            "result": "Implementation completed",
            "changes": ["Added feature.py", "Updated config.json"]
        }
        
        with patch.object(builder, 'build_with_llm', return_value=meta_response), \
             patch.object(builder, 'build_with_claude') as mock_claude:
            
            mock_claude.return_value = execution_response
            
            result = builder.execute_two_stage_prompt(
                task_type="github-issue-implementer",
                task_data=task_data,
                claude_md_content=claude_md_content,
                prompt_only=False
            )
            
            assert result["success"] is True
            assert result["meta_prompt"] is not None
            assert "DECONSTRUCT" in result["optimized_prompt"]
            assert result["execution_result"] == execution_response
    
    def test_execute_two_stage_prompt_meta_failure(self):
        """Test two-stage execution when meta-prompt generation fails."""
        builder = PromptBuilder()
        
        task_data = {
            "issue_number": 123,
            "issue_title": "Test Issue",
            "issue_body": "Test",
            "labels": []
        }
        
        claude_md_content = "# Guidelines"
        
        with patch.object(builder, 'build_with_llm', return_value=None), \
             patch.object(builder, 'build_with_claude', return_value=None):
            
            result = builder.execute_two_stage_prompt(
                task_type="test-agent",
                task_data=task_data,
                claude_md_content=claude_md_content,
                prompt_only=True
            )
            
            assert result["success"] is False
            assert result["error"] == "Failed to generate optimized prompt"
    
    def test_build_with_claude(self):
        """Test direct Claude prompt building."""
        builder = PromptBuilder()
        
        with patch.object(builder, '_execute_llm_tool') as mock_execute:
            mock_execute.return_value = {"response": "Claude response"}
            
            result = builder.build_with_claude("Test prompt", execute_mode=False)
            
            assert result == {"response": "Claude response"}
            mock_execute.assert_called_once_with(
                "claude",
                "Test prompt",
                4000,
                False
            )
    
    def test_build_with_llm(self):
        """Test LLM tool prompt building."""
        builder = PromptBuilder()
        
        with patch.object(builder, '_execute_llm_tool') as mock_execute:
            mock_execute.return_value = {"response": "LLM response"}
            
            result = builder.build_with_llm("Test prompt")
            
            assert result == {"response": "LLM response"}
            mock_execute.assert_called_once_with(
                "llm",
                "Test prompt",
                4000
            )
    
    def test_generate_pr_review_prompt(self):
        """Test PR review prompt generation."""
        builder = PromptBuilder()
        
        pr_data = PRData(
            number=456,
            title="Add new feature",
            body="This PR adds a new feature",
            head_ref="feature-branch",
            base_ref="main",
            author="testuser",
            additions=100,
            deletions=20,
            changed_files=5,
            url="https://github.com/test/repo/pull/456"
        )
        
        diff_content = "diff --git a/file.py b/file.py\n+new line\n-old line"
        claude_md_content = "# Project Guidelines"
        
        prompt = builder.generate_pr_review_prompt(pr_data, diff_content, claude_md_content)
        
        assert prompt is not None
        assert "456" in prompt
        assert "Add new feature" in prompt
        assert "100" in str(prompt)  # additions
        assert "20" in str(prompt)   # deletions
        assert "diff" in prompt
        assert "Project Guidelines" in prompt
    
    def test_generate_bug_analysis_prompt(self):
        """Test bug analysis prompt generation."""
        builder = PromptBuilder()
        
        bug_description = "Tests are failing intermittently"
        claude_md_content = "# Guidelines"
        context = {
            "recent_commits": "abc123 Fix tests\ndef456 Update deps",
            "git_diff": "diff content",
            "test_output": "FAILED test_example.py::test_case"
        }
        
        prompt = builder.generate_bug_analysis_prompt(bug_description, claude_md_content, context)
        
        assert prompt is not None
        assert "Tests are failing intermittently" in prompt
        assert "Bug:" in prompt
        assert "Steps to Reproduce" in prompt
    
    def test_large_prompt_handling(self):
        """Test handling of very large prompts."""
        builder = PromptBuilder()
        
        # Create a large prompt
        large_content = "x" * 500000  # 500KB prompt
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='{"result": "handled"}',
                stderr=""
            )
            
            result = builder._execute_llm_tool(
                tool_name="claude",
                prompt=large_content,
                execute_mode=True  # Use execute mode to test stdin
            )
            
            assert result is not None
            
            # Verify prompt was passed via stdin for execute mode
            call_kwargs = mock_run.call_args[1]
            assert "input" in call_kwargs
            assert len(call_kwargs["input"]) == 500000
    
    def test_generate_meta_prompt(self):
        """Test meta-prompt generation."""
        builder = PromptBuilder()
        
        task_data = {
            "issue_number": 123,
            "issue_title": "Test Issue",
            "issue_body": "Implement feature"
        }
        
        claude_md_content = "# Project Guidelines\nFollow these conventions..."
        
        prompt = builder.generate_meta_prompt("issue-implementation", task_data, claude_md_content)
        
        assert prompt is not None
        assert "issue-implementation" in prompt
        assert "Test Issue" in prompt
        assert "Project Guidelines" in prompt
        assert "Lyra-Dev 4-D methodology" in prompt