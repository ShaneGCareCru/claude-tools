"""Extended CLI tests for improved coverage."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import tempfile
import os
import argparse

from src.claude_tasker.cli import (
    parse_issue_range,
    parse_pr_range,
    extract_pr_number,
    create_argument_parser,
    validate_arguments,
    print_results_summary,
    main
)
from src.claude_tasker.workflow_logic import WorkflowResult


class TestParseIssueRange:
    """Test issue range parsing with edge cases."""
    
    def test_parse_single_issue(self):
        """Test parsing single issue number."""
        start, end = parse_issue_range("42")
        assert start == 42
        assert end == 42
    
    def test_parse_issue_range(self):
        """Test parsing issue range."""
        start, end = parse_issue_range("10-20")
        assert start == 10
        assert end == 20
    
    def test_parse_issue_range_with_spaces(self):
        """Test parsing issue range with spaces."""
        start, end = parse_issue_range(" 5 - 15 ")
        assert start == 5
        assert end == 15
    
    def test_parse_invalid_range_start_greater_than_end(self):
        """Test invalid range where start > end."""
        start, end = parse_issue_range("20-10")
        assert start is None
        assert end is None
    
    def test_parse_invalid_format(self):
        """Test invalid issue format."""
        start, end = parse_issue_range("not-a-number")
        assert start is None
        assert end is None
    
    def test_parse_empty_string(self):
        """Test empty string."""
        start, end = parse_issue_range("")
        assert start is None
        assert end is None
    
    def test_parse_multiple_dashes(self):
        """Test string with multiple dashes."""
        # Multiple dashes result in invalid format
        start, end = parse_issue_range("1-2-3")
        assert start is None
        assert end is None


class TestParsePRRange:
    """Test PR range parsing."""
    
    def test_parse_pr_range_delegates_to_issue_range(self):
        """Test that PR range parsing uses same logic as issue range."""
        start, end = parse_pr_range("100-200")
        assert start == 100
        assert end == 200


class TestExtractPRNumber:
    """Test PR number extraction from URLs."""
    
    def test_extract_from_github_url(self):
        """Test extracting PR number from GitHub URL."""
        pr_num = extract_pr_number("https://github.com/owner/repo/pull/123")
        assert pr_num == 123
    
    def test_extract_from_partial_url(self):
        """Test extracting from partial URL."""
        pr_num = extract_pr_number("/pull/456")
        assert pr_num == 456
    
    def test_extract_from_number_string(self):
        """Test extracting from plain number string."""
        pr_num = extract_pr_number("789")
        assert pr_num == 789
    
    def test_extract_invalid_url(self):
        """Test invalid URL returns None."""
        pr_num = extract_pr_number("not-a-url")
        assert pr_num is None
    
    def test_extract_url_without_pr(self):
        """Test URL without PR number."""
        pr_num = extract_pr_number("https://github.com/owner/repo")
        assert pr_num is None
    
    def test_extract_with_exception(self):
        """Test handling of exceptions."""
        # extract_pr_number should handle None by checking if pr_url is None first
        pr_num = extract_pr_number(None)
        assert pr_num is None


class TestValidateArguments:
    """Test argument validation."""
    
    def test_validate_no_action(self):
        """Test validation when no action specified."""
        args = Mock(issue=None, bug=None, review_pr=None, feature=None, timeout=10)
        result = validate_arguments(args)
        assert result == "Must specify an issue number, --review-pr, --bug, or --feature"
    
    def test_validate_multiple_actions(self):
        """Test validation when multiple actions specified."""
        args = Mock(issue='42', bug='bug desc', review_pr=None, feature=None, timeout=10)
        result = validate_arguments(args)
        assert result == "Error: Cannot specify multiple actions simultaneously"
    
    def test_validate_invalid_issue_format(self):
        """Test validation with invalid issue format."""
        args = Mock(issue='invalid', bug=None, review_pr=None, feature=None, timeout=10)
        with patch('src.claude_tasker.cli.parse_issue_range', return_value=(None, None)):
            result = validate_arguments(args)
            assert "Invalid issue number format" in result
    
    def test_validate_invalid_pr_format(self):
        """Test validation with invalid PR format."""
        args = Mock(issue=None, bug=None, review_pr='invalid', feature=None, timeout=10)
        with patch('src.claude_tasker.cli.parse_pr_range', return_value=(None, None)):
            result = validate_arguments(args)
            assert "Invalid PR number format" in result
    
    def test_validate_negative_timeout(self):
        """Test validation with negative timeout."""
        args = Mock(issue='42', bug=None, review_pr=None, feature=None, timeout=-1)
        result = validate_arguments(args)
        assert "Invalid timeout value" in result
    
    def test_validate_success(self):
        """Test successful validation."""
        args = Mock(
            issue='42', bug=None, review_pr=None, feature=None, timeout=10,
            project=None, base_branch=None, auto_pr_review=False, 
            prompt_only=False
        )
        with patch('src.claude_tasker.cli.parse_issue_range', return_value=(42, 42)):
            result = validate_arguments(args)
            assert result is None  # None means success


class TestCreateArgumentParser:
    """Test argument parser creation."""
    
    def test_create_parser(self):
        """Test that parser is created correctly."""
        parser = create_argument_parser()
        assert isinstance(parser, argparse.ArgumentParser)
        
        # Test parsing issue number
        args = parser.parse_args(['42'])
        assert args.issue == '42'
    
    def test_parse_with_bug(self):
        """Test parsing with bug description."""
        parser = create_argument_parser()
        args = parser.parse_args(['--bug', 'Something is broken'])
        assert args.bug == 'Something is broken'
    
    def test_parse_with_review_pr(self):
        """Test parsing with PR review."""
        parser = create_argument_parser()
        args = parser.parse_args(['--review-pr', '123'])
        assert args.review_pr == '123'
    
    def test_parse_with_all_flags(self):
        """Test parsing with all optional flags."""
        parser = create_argument_parser()
        args = parser.parse_args([
            '42',
            '--interactive',
            '--prompt-only',
            '--dry-run',
            '--timeout', '30',
            '--coder', 'llm'
        ])
        assert args.issue == '42'
        assert args.interactive is True
        assert args.prompt_only is True
        assert args.dry_run is True
        assert args.timeout == 30
        assert args.coder == 'llm'


class TestPrintResultsSummary:
    """Test results summary printing."""
    
    def test_print_empty_results(self):
        """Test printing empty results."""
        with patch('builtins.print') as mock_print:
            print_results_summary([])
            # Empty results should not print anything
            mock_print.assert_not_called()
    
    def test_print_single_success(self):
        """Test printing single successful result."""
        result = WorkflowResult(
            success=True,
            message="Issue processed",
            issue_number=42
        )
        with patch('builtins.print') as mock_print:
            print_results_summary([result])
            # Verify summary was printed with correct format
            calls = [str(call) for call in mock_print.call_args_list]
            assert any("Summary" in str(call) or "successful" in str(call) for call in calls)
    
    def test_print_mixed_results(self):
        """Test printing mixed success/failure results."""
        results = [
            WorkflowResult(success=True, message="Success", issue_number=1),
            WorkflowResult(success=False, message="Failed", issue_number=2, error_details="Test error"),
            WorkflowResult(success=True, message="Success", issue_number=3, pr_url="http://pr.url")
        ]
        with patch('builtins.print') as mock_print:
            print_results_summary(results)
            calls = [str(call) for call in mock_print.call_args_list]
            # Should show summary and failure
            assert any("Summary" in str(call) or "successful" in str(call) or "failed" in str(call) for call in calls)
            assert any("Failed" in str(call) or "❌" in str(call) for call in calls)


class TestMainFunction:
    """Test main function with various scenarios."""
    
    @patch('src.claude_tasker.cli.create_argument_parser')
    @patch('src.claude_tasker.cli.WorkflowLogic')
    def test_main_no_action_specified(self, mock_workflow, mock_parser):
        """Test main with no action specified."""
        mock_args = Mock(issue=None, bug=None, review_pr=None)
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_parser.return_value = mock_parser_instance
        
        with patch('src.claude_tasker.cli.validate_arguments', return_value="Must specify an issue number, --review-pr, or --bug"):
            with patch('src.claude_tasker.cli.logger') as mock_logger:
                result = main()
                assert result == 1
                assert mock_logger.error.called
    
    @patch('src.claude_tasker.cli.create_argument_parser')
    @patch('src.claude_tasker.cli.Path')
    @patch('src.claude_tasker.cli.WorkflowLogic')
    def test_main_invalid_coder_path(self, mock_workflow, mock_path, mock_parser):
        """Test main with missing CLAUDE.md."""
        mock_args = Mock(
            issue='42', bug=None, review_pr=None, coder='claude', timeout=10,
            project=None, base_branch=None, auto_pr_review=False, prompt_only=False,
            interactive=False, dry_run=False
        )
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_parser.return_value = mock_parser_instance
        
        # Simulate missing CLAUDE.md
        mock_path.return_value.exists.return_value = False
        
        with patch('src.claude_tasker.cli.validate_arguments', return_value=None):
            with patch('src.claude_tasker.cli.logger') as mock_logger:
                with patch('builtins.print'):
                    result = main()
                    assert result == 1
                    mock_logger.error.assert_called()
    
    @patch('src.claude_tasker.cli.create_argument_parser')
    @patch('src.claude_tasker.cli.Path')
    @patch('src.claude_tasker.cli.WorkflowLogic')
    def test_main_environment_validation_failure(self, mock_workflow, mock_path, mock_parser):
        """Test main with workflow error."""
        mock_args = Mock(
            issue='42', bug=None, review_pr=None, coder='claude', timeout=10,
            project=None, base_branch=None, auto_pr_review=False, prompt_only=False,
            interactive=False, dry_run=False
        )
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_parser.return_value = mock_parser_instance
        
        # Simulate CLAUDE.md exists
        mock_path.return_value.exists.return_value = True
        
        # Simulate workflow failure
        mock_workflow_instance = Mock()
        mock_workflow_instance.process_single_issue.side_effect = Exception("Workflow error")
        mock_workflow.return_value = mock_workflow_instance
        
        with patch('src.claude_tasker.cli.validate_arguments', return_value=None):
            with patch('src.claude_tasker.cli.parse_issue_range', return_value=(42, 42)):
                with patch('src.claude_tasker.cli.logger') as mock_logger:
                    with patch('builtins.print'):
                        result = main()
                        assert result == 1
    
    @patch('src.claude_tasker.cli.create_argument_parser')
    @patch('src.claude_tasker.cli.Path')
    @patch('src.claude_tasker.cli.WorkflowLogic')
    def test_main_process_issue_success(self, mock_workflow_class, mock_path, mock_parser):
        """Test successful issue processing."""
        mock_args = Mock(
            issue='42', bug=None, review_pr=None, coder='claude',
            interactive=False, prompt_only=False, dry_run=False, timeout=10,
            project=None, base_branch=None, auto_pr_review=False
        )
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_parser.return_value = mock_parser_instance
        
        # Simulate CLAUDE.md exists
        mock_path.return_value.exists.return_value = True
        
        mock_workflow = Mock()
        mock_result = WorkflowResult(success=True, message="Success", issue_number=42)
        mock_workflow.process_single_issue.return_value = mock_result
        mock_workflow_class.return_value = mock_workflow
        
        with patch('src.claude_tasker.cli.validate_arguments', return_value=None):
            with patch('src.claude_tasker.cli.parse_issue_range', return_value=(42, 42)):
                with patch('builtins.print'):
                    result = main()
                    assert result == 0
                    mock_workflow.process_single_issue.assert_called_once_with(42, False, None)
    
    @patch('src.claude_tasker.cli.create_argument_parser')
    @patch('src.claude_tasker.cli.Path')
    @patch('src.claude_tasker.cli.WorkflowLogic')
    def test_main_process_issue_range(self, mock_workflow_class, mock_path, mock_parser):
        """Test processing issue range."""
        mock_args = Mock(
            issue='10-12', bug=None, review_pr=None, coder='claude',
            interactive=False, prompt_only=False, dry_run=False, timeout=10,
            project=None, base_branch=None, auto_pr_review=False
        )
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_parser.return_value = mock_parser_instance
        
        # Simulate CLAUDE.md exists
        mock_path.return_value.exists.return_value = True
        
        mock_workflow = Mock()
        mock_results = [
            WorkflowResult(success=True, message="Success", issue_number=10),
            WorkflowResult(success=True, message="Success", issue_number=11),
            WorkflowResult(success=True, message="Success", issue_number=12)
        ]
        mock_workflow.process_issue_range.return_value = mock_results
        mock_workflow_class.return_value = mock_workflow
        
        with patch('src.claude_tasker.cli.validate_arguments', return_value=None):
            with patch('src.claude_tasker.cli.parse_issue_range', return_value=(10, 12)):
                with patch('builtins.print'):
                    result = main()
                    assert result == 0
                    mock_workflow.process_issue_range.assert_called_once_with(10, 12, False, None)
    
    @patch('src.claude_tasker.cli.create_argument_parser')
    @patch('src.claude_tasker.cli.Path')
    @patch('src.claude_tasker.cli.WorkflowLogic')
    def test_main_keyboard_interrupt(self, mock_workflow_class, mock_path, mock_parser):
        """Test handling keyboard interrupt."""
        mock_args = Mock(
            issue='42', bug=None, review_pr=None, coder='claude', timeout=10,
            project=None, base_branch=None, auto_pr_review=False, prompt_only=False,
            interactive=False, dry_run=False
        )
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_parser.return_value = mock_parser_instance
        
        # Simulate CLAUDE.md exists
        mock_path.return_value.exists.return_value = True
        
        mock_workflow = Mock()
        mock_workflow.process_single_issue.side_effect = KeyboardInterrupt()
        mock_workflow_class.return_value = mock_workflow
        
        with patch('src.claude_tasker.cli.validate_arguments', return_value=None):
            with patch('src.claude_tasker.cli.parse_issue_range', return_value=(42, 42)):
                with patch('src.claude_tasker.cli.logger') as mock_logger:
                    with patch('builtins.print'):
                        result = main()
                        assert result == 130
                        mock_logger.warning.assert_called_with("Operation interrupted by user")