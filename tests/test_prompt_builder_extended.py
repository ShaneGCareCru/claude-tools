"""Extended tests for prompt_builder module to improve coverage."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import subprocess
import tempfile
from pathlib import Path

from src.claude_tasker.prompt_builder import PromptBuilder
from src.claude_tasker.github_client import IssueData, PRData


class TestPromptBuilderExtended:
    """Extended tests for PromptBuilder class."""
    
    @pytest.fixture
    def prompt_builder(self):
        """Create a PromptBuilder instance."""
        return PromptBuilder()
    
    def test_generate_bug_analysis_prompt(self, prompt_builder):
        """Test generate_bug_analysis_prompt."""
        bug_description = "Application crashes on startup"
        claude_md_content = "Project context"
        
        result = prompt_builder.generate_bug_analysis_prompt(bug_description, claude_md_content)
        
        assert result is not None
        assert isinstance(result, str)
        assert bug_description in result
    
    def test_generate_pr_review_prompt(self, prompt_builder):
        """Test generate_pr_review_prompt."""
        pr_data = PRData(
            number=123,
            title="Fix bug",
            body="This PR fixes a bug",
            head_ref="fix-branch",
            base_ref="main",
            author="testuser",
            additions=10,
            deletions=5,
            changed_files=2,
            url="https://github.com/test/repo/pull/123"
        )
        pr_diff = "diff content"
        
        result = prompt_builder.generate_pr_review_prompt(pr_data, pr_diff, claude_md_content)
        
        assert result is not None
        assert isinstance(result, str)
        assert pr_data.title in result
    
    def test_generate_lyra_dev_prompt(self, prompt_builder):
        """Test generate_lyra_dev_prompt."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            url="https://github.com/test/repo/issues/42",
            author="testuser",
            state="open"
        )
        claude_md_content = "Project context"
        
        context = {
            'git_diff': 'diff content',
            'related_files': ['file1.py', 'file2.py']
        }
        result = prompt_builder.generate_lyra_dev_prompt(issue_data, claude_md_content, context)
        
        assert result is not None
        assert isinstance(result, str)
        assert issue_data.title in result
    
    def test_build_with_llm(self, prompt_builder):
        """Test build_with_llm method."""
        prompt = "Test prompt"
        
        mock_result = Mock(returncode=0, stdout="LLM Success", stderr="")
        
        with patch('subprocess.run', return_value=mock_result):
            result = prompt_builder.build_with_llm(prompt)
        
        assert result is not None
        assert result['result'] == "LLM Success"
    
    def test_build_with_llm_failure(self, prompt_builder):
        """Test build_with_llm with command failure."""
        prompt = "Test prompt"
        
        mock_result = Mock(returncode=1, stdout="", stderr="Error")
        
        with patch('subprocess.run', return_value=mock_result):
            result = prompt_builder.build_with_llm(prompt)
        
        assert result is not None
        assert result['success'] is False
        assert 'error' in result
    
    def test_build_with_claude(self, prompt_builder):
        """Test build_with_claude method."""
        prompt = "Test prompt"
        
        mock_result = Mock(returncode=0, stdout="Claude Success", stderr="")
        
        with patch('subprocess.run', return_value=mock_result):
            result = prompt_builder.build_with_claude(prompt)
        
        assert result is not None
        assert result['result'] == "Claude Success"
    
    def test_build_with_claude_execute_mode(self, prompt_builder):
        """Test build_with_claude in execute mode."""
        prompt = "Test prompt"
        
        mock_result = Mock(returncode=0, stdout="Claude Success", stderr="")
        
        with patch('subprocess.run', return_value=mock_result):
            result = prompt_builder.build_with_claude(prompt, execute_mode=True)
        
        assert result is not None
        assert result['result'] == "Claude Success"
    
    def test_build_with_claude_review_mode(self, prompt_builder):
        """Test build_with_claude in review mode."""
        prompt = "Test prompt"
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test.txt'
            
            mock_result = Mock(returncode=0, stdout="Review Success", stderr="")
            
            with patch('subprocess.run', return_value=mock_result):
                result = prompt_builder.build_with_claude(prompt, review_mode=True)
        
        assert result is not None
        assert result['success'] is True
        assert result['response'] == "Review Success"
    
    def test_build_with_claude_timeout(self, prompt_builder):
        """Test build_with_claude with timeout."""
        prompt = "Test prompt"
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 30)):
            result = prompt_builder.build_with_claude(prompt)
        
        assert result is not None
        assert result['success'] is False
        assert 'timed out' in result['error'].lower()
    
    def test_validate_meta_prompt(self, prompt_builder):
        """Test validate_meta_prompt method."""
        valid_prompt = "This is a valid prompt\nWith multiple lines"
        
        result = prompt_builder.validate_meta_prompt(valid_prompt)
        assert result is True
        
        # Test with empty prompt
        result = prompt_builder.validate_meta_prompt("")
        assert result is False
        
        # Test with None
        result = prompt_builder.validate_meta_prompt(None)
        assert result is False
    
    def test_generate_meta_prompt(self, prompt_builder):
        """Test generate_meta_prompt method."""
        task_type = "issue_implementation"
        task_data = {
            'issue_number': 42,
            'issue_title': 'Test Issue',
            'issue_body': 'Test body'
        }
        claude_md_content = "Project context"
        
        result = prompt_builder.generate_meta_prompt(task_type, task_data, claude_md_content)
        
        assert result is not None
        assert isinstance(result, str)
        assert task_type in result
        assert "Project context" in result
    
    def test_execute_two_stage_prompt(self, prompt_builder):
        """Test execute_two_stage_prompt method."""
        task_type = "issue_implementation"
        task_data = {
            'issue_number': 42,
            'issue_title': 'Test Issue',
            'issue_body': 'Test body'
        }
        claude_md_content = "Project context"
        
        # Mock the build_with_llm to return optimized prompt
        with patch.object(prompt_builder, 'build_with_llm') as mock_llm:
            mock_llm.return_value = {
                'result': 'Generated optimized prompt\n\n# DECONSTRUCT\nAnalyzing...\n\n# DIAGNOSE\nFinding gaps...\n\n# DEVELOP\nPlanning...\n\n# DELIVER\nImplementing...',
                'optimized_prompt': 'Generated optimized prompt\n\n# DECONSTRUCT\nAnalyzing...\n\n# DIAGNOSE\nFinding gaps...\n\n# DEVELOP\nPlanning...\n\n# DELIVER\nImplementing...'
            }
            
            # Mock build_with_claude to return success for execution
            with patch.object(prompt_builder, 'build_with_claude') as mock_build:
                mock_build.return_value = {
                    'result': 'Execution complete'
                }
                
                result = prompt_builder.execute_two_stage_prompt(
                    task_type, task_data, claude_md_content, prompt_only=False
                )
        
        assert result is not None
        assert result['success'] is True
    
    def test_execute_two_stage_prompt_prompt_only(self, prompt_builder):
        """Test execute_two_stage_prompt in prompt-only mode."""
        task_type = "issue_implementation"
        task_data = {
            'issue_number': 42,
            'issue_title': 'Test Issue',
            'issue_body': 'Test body'
        }
        claude_md_content = "Project context"
        
        # Mock the build_with_llm to return optimized prompt
        with patch.object(prompt_builder, 'build_with_llm') as mock_llm:
            mock_llm.return_value = {
                'result': 'Generated optimized prompt\n\n# DECONSTRUCT\nAnalyzing...\n\n# DIAGNOSE\nFinding gaps...\n\n# DEVELOP\nPlanning...\n\n# DELIVER\nImplementing...',
                'optimized_prompt': 'Generated optimized prompt\n\n# DECONSTRUCT\nAnalyzing...\n\n# DIAGNOSE\nFinding gaps...\n\n# DEVELOP\nPlanning...\n\n# DELIVER\nImplementing...'
            }
            
            result = prompt_builder.execute_two_stage_prompt(
                task_type, task_data, claude_md_content, prompt_only=True
            )
        
        assert result is not None
        assert result['success'] is True
    
    def test_execute_two_stage_prompt_meta_prompt_failure(self, prompt_builder):
        """Test execute_two_stage_prompt when optimized prompt generation fails."""
        task_type = "issue_implementation"
        task_data = {
            'issue_number': 42,
            'issue_title': 'Test Issue',
            'issue_body': 'Test body'
        }
        claude_md_content = "Project context"
        
        # Mock both LLM tools to fail
        with patch.object(prompt_builder, 'build_with_llm', return_value=None), \
             patch.object(prompt_builder, 'build_with_claude', return_value=None):
            
            result = prompt_builder.execute_two_stage_prompt(
                task_type, task_data, claude_md_content, prompt_only=False
            )
        
        assert result is not None
        assert result['success'] is False
        assert 'error' in result
    
    def test_execute_two_stage_prompt_execution_failure(self, prompt_builder):
        """Test execute_two_stage_prompt when execution fails."""
        task_type = "issue_implementation"
        task_data = {
            'issue_number': 42,
            'issue_title': 'Test Issue',
            'issue_body': 'Test body'
        }
        claude_md_content = "Project context"
        
        # Mock the build_with_llm to succeed with optimized prompt
        with patch.object(prompt_builder, 'build_with_llm') as mock_llm:
            mock_llm.return_value = {
                'result': 'Generated optimized prompt\n\n# DECONSTRUCT\nAnalyzing...\n\n# DIAGNOSE\nFinding gaps...\n\n# DEVELOP\nPlanning...\n\n# DELIVER\nImplementing...',
                'optimized_prompt': 'Generated optimized prompt\n\n# DECONSTRUCT\nAnalyzing...\n\n# DIAGNOSE\nFinding gaps...\n\n# DEVELOP\nPlanning...\n\n# DELIVER\nImplementing...'
            }
            
            # Mock build_with_claude execution to return None (failure)
            with patch.object(prompt_builder, 'build_with_claude', return_value=None):
                
                result = prompt_builder.execute_two_stage_prompt(
                    task_type, task_data, claude_md_content, prompt_only=False
                )
        
        assert result is not None
        assert result['success'] is False
        assert 'error' in result