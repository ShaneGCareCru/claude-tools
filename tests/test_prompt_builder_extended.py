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
    
    def test_build_bug_analysis_prompt_with_exception(self, prompt_builder):
        """Test build_bug_analysis_prompt with exception."""
        with patch('src.claude_tasker.prompt_builder.logger') as mock_logger:
            # Force an exception by passing None
            result = prompt_builder.build_bug_analysis_prompt(None)
            
            assert result is None
            mock_logger.error.assert_called()
    
    def test_build_pr_review_prompt_with_exception(self, prompt_builder):
        """Test build_pr_review_prompt with exception."""
        # Create PR data that will cause an exception
        pr_data = None
        
        with patch('src.claude_tasker.prompt_builder.logger') as mock_logger:
            result = prompt_builder.build_pr_review_prompt(pr_data)
            
            assert result is None
            mock_logger.error.assert_called()
    
    def test_execute_claude_with_prompt_interactive_mode(self, prompt_builder):
        """Test execute_claude_with_prompt in interactive mode."""
        prompt = "Test prompt"
        args = Mock(interactive=True, coder='claude')
        
        mock_result = Mock(returncode=0, stdout="Success", stderr="")
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_file = Mock()
                mock_file.name = '/tmp/test.txt'
                mock_temp.return_value.__enter__.return_value = mock_file
                
                with patch('pathlib.Path.unlink') as mock_unlink:
                    result = prompt_builder.execute_claude_with_prompt(prompt, args)
        
        assert result is not None
        assert result['success'] is True
        assert result['response'] == "Success"
        
        # Verify interactive flag was used
        call_args = mock_run.call_args[0][0]
        assert '--permission-mode' not in call_args  # Interactive mode doesn't use permission mode
    
    def test_execute_claude_with_prompt_llm_coder(self, prompt_builder):
        """Test execute_claude_with_prompt with llm coder."""
        prompt = "Test prompt"
        args = Mock(interactive=False, coder='llm')
        
        mock_result = Mock(returncode=0, stdout="LLM Success", stderr="")
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_file = Mock()
                mock_file.name = '/tmp/test.txt'
                mock_temp.return_value.__enter__.return_value = mock_file
                
                with patch('pathlib.Path.unlink') as mock_unlink:
                    result = prompt_builder.execute_claude_with_prompt(prompt, args)
        
        assert result is not None
        assert result['success'] is True
        assert result['response'] == "LLM Success"
        
        # Verify llm command was used
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == 'llm'
    
    def test_execute_claude_with_prompt_command_failure(self, prompt_builder):
        """Test execute_claude_with_prompt when command fails."""
        prompt = "Test prompt"
        args = Mock(interactive=False, coder='claude')
        
        mock_result = Mock(returncode=1, stdout="", stderr="Error occurred")
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_file = Mock()
                mock_file.name = '/tmp/test.txt'
                mock_temp.return_value.__enter__.return_value = mock_file
                
                with patch('pathlib.Path.unlink') as mock_unlink:
                    with patch('src.claude_tasker.prompt_builder.logger') as mock_logger:
                        result = prompt_builder.execute_claude_with_prompt(prompt, args)
        
        assert result is None
        mock_logger.error.assert_called()
    
    def test_execute_claude_with_prompt_timeout(self, prompt_builder):
        """Test execute_claude_with_prompt with timeout."""
        prompt = "Test prompt"
        args = Mock(interactive=False, coder='claude')
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 300)):
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_file = Mock()
                mock_file.name = '/tmp/test.txt'
                mock_temp.return_value.__enter__.return_value = mock_file
                
                with patch('pathlib.Path.unlink') as mock_unlink:
                    with patch('src.claude_tasker.prompt_builder.logger') as mock_logger:
                        result = prompt_builder.execute_claude_with_prompt(prompt, args)
        
        assert result is None
        mock_logger.error.assert_called_with("Claude command timed out after 5 minutes")
    
    def test_execute_claude_with_prompt_generic_exception(self, prompt_builder):
        """Test execute_claude_with_prompt with generic exception."""
        prompt = "Test prompt"
        args = Mock(interactive=False, coder='claude')
        
        with patch('subprocess.run', side_effect=Exception("Unexpected error")):
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_file = Mock()
                mock_file.name = '/tmp/test.txt'
                mock_temp.return_value.__enter__.return_value = mock_file
                
                with patch('pathlib.Path.unlink') as mock_unlink:
                    with patch('src.claude_tasker.prompt_builder.logger') as mock_logger:
                        result = prompt_builder.execute_claude_with_prompt(prompt, args)
        
        assert result is None
        mock_logger.error.assert_called()
    
    def test_execute_claude_review_success(self, prompt_builder):
        """Test execute_claude_review with successful execution."""
        prompt = "Review prompt"
        
        mock_result = Mock(returncode=0, stdout="Review output", stderr="")
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_file = Mock()
                mock_file.name = '/tmp/review.txt'
                mock_temp.return_value.__enter__.return_value = mock_file
                
                with patch('pathlib.Path.unlink') as mock_unlink:
                    result = prompt_builder.execute_claude_review(prompt)
        
        assert result is not None
        assert result['success'] is True
        assert result['response'] == "Review output"
        
        # Verify command includes review-specific settings
        call_args = mock_run.call_args[0][0]
        assert 'claude' in call_args
        assert '--permission-mode' in call_args
        assert 'bypassPermissions' in call_args
    
    def test_execute_claude_review_command_failure(self, prompt_builder):
        """Test execute_claude_review when command fails."""
        prompt = "Review prompt"
        
        mock_result = Mock(returncode=1, stdout="", stderr="Review error")
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_file = Mock()
                mock_file.name = '/tmp/review.txt'
                mock_temp.return_value.__enter__.return_value = mock_file
                
                with patch('pathlib.Path.unlink') as mock_unlink:
                    with patch('src.claude_tasker.prompt_builder.logger') as mock_logger:
                        result = prompt_builder.execute_claude_review(prompt)
        
        assert result is None
        mock_logger.error.assert_called()
    
    def test_execute_claude_review_timeout(self, prompt_builder):
        """Test execute_claude_review with timeout."""
        prompt = "Review prompt"
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 1200)):
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_file = Mock()
                mock_file.name = '/tmp/review.txt'
                mock_temp.return_value.__enter__.return_value = mock_file
                
                with patch('pathlib.Path.unlink') as mock_unlink:
                    with patch('src.claude_tasker.prompt_builder.logger') as mock_logger:
                        result = prompt_builder.execute_claude_review(prompt)
        
        assert result is None
        mock_logger.error.assert_called_with("Claude review command timed out")
    
    def test_execute_claude_review_generic_exception(self, prompt_builder):
        """Test execute_claude_review with generic exception."""
        prompt = "Review prompt"
        
        with patch('subprocess.run', side_effect=Exception("Review exception")):
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_file = Mock()
                mock_file.name = '/tmp/review.txt'
                mock_temp.return_value.__enter__.return_value = mock_file
                
                with patch('pathlib.Path.unlink') as mock_unlink:
                    with patch('src.claude_tasker.prompt_builder.logger') as mock_logger:
                        result = prompt_builder.execute_claude_review(prompt)
        
        assert result is None
        mock_logger.error.assert_called()
    
    def test_build_audit_prompt_with_context_files(self, prompt_builder):
        """Test build_audit_prompt with context files."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body with context",
            labels=["bug"],
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        
        # Mock file reading
        with patch('builtins.open', mock_open(read_data="File content")):
            with patch('os.path.exists', return_value=True):
                with patch('os.path.isfile', return_value=True):
                    prompt = prompt_builder.build_audit_prompt(issue_data)
        
        assert prompt is not None
        assert "Test Issue" in prompt
        assert "DECONSTRUCT" in prompt
    
    def test_build_implementation_prompt_with_audit_results(self, prompt_builder):
        """Test build_implementation_prompt with audit results."""
        issue_data = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["enhancement"],
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        
        audit_results = "Audit found these issues:\n- Issue 1\n- Issue 2"
        
        prompt = prompt_builder.build_implementation_prompt(issue_data, audit_results)
        
        assert prompt is not None
        assert "Test Issue" in prompt
        assert "IMPLEMENT" in prompt
        assert audit_results in prompt
    
    def test_build_pr_review_prompt_with_full_data(self, prompt_builder):
        """Test build_pr_review_prompt with complete PR data."""
        pr_data = PRData(
            number=123,
            title="Test PR",
            body="PR description",
            state="open",
            head_branch="feature-branch",
            base_branch="main",
            diff="+ Added line\n- Removed line",
            commits=[
                {'sha': 'abc123', 'message': 'First commit'},
                {'sha': 'def456', 'message': 'Second commit'}
            ],
            files_changed=['file1.py', 'file2.py'],
            additions=50,
            deletions=10,
            changed_files_count=2,
            review_comments=[],
            labels=["review"],
            assignee="developer",
            milestone="v1.0",
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        
        prompt = prompt_builder.build_pr_review_prompt(pr_data)
        
        assert prompt is not None
        assert "Test PR" in prompt
        assert "Review the following Pull Request" in prompt
        assert "feature-branch" in prompt
        assert "main" in prompt
    
    def test_execute_claude_with_prompt_cleanup_on_exception(self, prompt_builder):
        """Test that temp file is cleaned up even on exception."""
        prompt = "Test prompt"
        args = Mock(interactive=False, coder='claude')
        
        temp_file_path = '/tmp/test_file.txt'
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_file = Mock()
            mock_file.name = temp_file_path
            mock_temp.return_value.__enter__.return_value = mock_file
            
            with patch('subprocess.run', side_effect=Exception("Test exception")):
                with patch('pathlib.Path.unlink') as mock_unlink:
                    with patch('src.claude_tasker.prompt_builder.logger'):
                        result = prompt_builder.execute_claude_with_prompt(prompt, args)
            
            # Verify cleanup was called
            mock_unlink.assert_called_once()
            assert result is None
    
    def test_execute_claude_review_cleanup_on_exception(self, prompt_builder):
        """Test that temp file is cleaned up in review even on exception."""
        prompt = "Review prompt"
        
        temp_file_path = '/tmp/review_file.txt'
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_file = Mock()
            mock_file.name = temp_file_path
            mock_temp.return_value.__enter__.return_value = mock_file
            
            with patch('subprocess.run', side_effect=Exception("Review exception")):
                with patch('pathlib.Path.unlink') as mock_unlink:
                    with patch('src.claude_tasker.prompt_builder.logger'):
                        result = prompt_builder.execute_claude_review(prompt)
            
            # Verify cleanup was called
            mock_unlink.assert_called_once()
            assert result is None