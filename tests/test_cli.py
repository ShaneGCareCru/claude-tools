"""Comprehensive unit tests for CLI module."""

import sys
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
import argparse
import pytest

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


class TestParseIssueRange(TestCase):
    """Test issue range parsing functionality."""
    
    def test_parse_single_issue(self):
        """Test parsing single issue number."""
        start, end = parse_issue_range("123")
        self.assertEqual(start, 123)
        self.assertEqual(end, 123)
    
    def test_parse_issue_range(self):
        """Test parsing issue range."""
        start, end = parse_issue_range("123-456")
        self.assertEqual(start, 123)
        self.assertEqual(end, 456)
    
    def test_parse_issue_range_with_spaces(self):
        """Test parsing issue range with spaces."""
        start, end = parse_issue_range(" 10 - 20 ")
        self.assertEqual(start, 10)
        self.assertEqual(end, 20)
    
    def test_parse_invalid_range_start_greater_than_end(self):
        """Test parsing invalid range where start > end."""
        start, end = parse_issue_range("456-123")
        self.assertIsNone(start)
        self.assertIsNone(end)
    
    def test_parse_invalid_format(self):
        """Test parsing invalid format."""
        start, end = parse_issue_range("abc")
        self.assertIsNone(start)
        self.assertIsNone(end)
    
    def test_parse_empty_string(self):
        """Test parsing empty string."""
        start, end = parse_issue_range("")
        self.assertIsNone(start)
        self.assertIsNone(end)
    
    def test_parse_multiple_dashes(self):
        """Test parsing with multiple dashes."""
        start, end = parse_issue_range("1-2-3")
        # Should fail due to invalid format (can't parse "2-3" as int)
        self.assertIsNone(start)
        self.assertIsNone(end)
    
    def test_parse_negative_numbers(self):
        """Test parsing negative numbers."""
        start, end = parse_issue_range("-5")
        self.assertIsNone(start)
        self.assertIsNone(end)
    
    def test_parse_float_numbers(self):
        """Test parsing float numbers."""
        start, end = parse_issue_range("1.5")
        self.assertIsNone(start)
        self.assertIsNone(end)
    
    def test_parse_none_input(self):
        """Test parsing None input."""
        start, end = parse_issue_range(None)
        self.assertIsNone(start)
        self.assertIsNone(end)


class TestParsePRRange(TestCase):
    """Test PR range parsing functionality."""
    
    def test_parse_pr_range_delegates_to_issue_range(self):
        """Test that parse_pr_range delegates to parse_issue_range."""
        with patch('src.claude_tasker.cli.parse_issue_range') as mock_parse:
            mock_parse.return_value = (1, 5)
            result = parse_pr_range("1-5")
            mock_parse.assert_called_once_with("1-5")
            self.assertEqual(result, (1, 5))


class TestExtractPRNumber(TestCase):
    """Test PR number extraction functionality."""
    
    def test_extract_from_github_url(self):
        """Test extracting PR number from full GitHub URL."""
        pr_num = extract_pr_number("https://github.com/owner/repo/pull/123")
        self.assertEqual(pr_num, 123)
    
    def test_extract_from_partial_url(self):
        """Test extracting PR number from partial URL."""
        pr_num = extract_pr_number("/pull/456")
        self.assertEqual(pr_num, 456)
    
    def test_extract_from_number_string(self):
        """Test extracting PR number from plain number string."""
        pr_num = extract_pr_number("789")
        self.assertEqual(pr_num, 789)
    
    def test_extract_invalid_url(self):
        """Test extracting from invalid URL."""
        pr_num = extract_pr_number("https://github.com/owner/repo/issues/123")
        self.assertIsNone(pr_num)
    
    def test_extract_url_without_pr(self):
        """Test extracting from URL without PR number."""
        pr_num = extract_pr_number("https://github.com/owner/repo")
        self.assertIsNone(pr_num)
    
    def test_extract_none_input(self):
        """Test extracting from None input."""
        pr_num = extract_pr_number(None)
        self.assertIsNone(pr_num)
    
    def test_extract_empty_string(self):
        """Test extracting from empty string."""
        pr_num = extract_pr_number("")
        self.assertIsNone(pr_num)
    
    def test_extract_non_numeric(self):
        """Test extracting from non-numeric string."""
        pr_num = extract_pr_number("abc")
        self.assertIsNone(pr_num)
    
    def test_extract_with_exception(self):
        """Test extraction with exception handling."""
        # Pass an invalid type that will cause an exception
        # This tests the except (ValueError, AttributeError) clause
        pr_num = extract_pr_number(123)  # int instead of string
        self.assertIsNone(pr_num)


class TestCreateArgumentParser(TestCase):
    """Test argument parser creation."""
    
    def test_create_parser(self):
        """Test creating argument parser."""
        parser = create_argument_parser()
        self.assertIsInstance(parser, argparse.ArgumentParser)
        self.assertEqual(parser.prog, 'claude-tasker')
    
    def test_parse_with_issue(self):
        """Test parsing with issue argument."""
        parser = create_argument_parser()
        args = parser.parse_args(['123'])
        self.assertEqual(args.issue, '123')
        self.assertIsNone(args.review_pr)
        self.assertIsNone(args.bug)
        self.assertIsNone(args.feature)
    
    def test_parse_with_issue_range(self):
        """Test parsing with issue range."""
        parser = create_argument_parser()
        args = parser.parse_args(['123-456'])
        self.assertEqual(args.issue, '123-456')
    
    def test_parse_with_review_pr(self):
        """Test parsing with review-pr flag."""
        parser = create_argument_parser()
        args = parser.parse_args(['--review-pr', '789'])
        self.assertIsNone(args.issue)
        self.assertEqual(args.review_pr, '789')
    
    def test_parse_with_bug(self):
        """Test parsing with bug flag."""
        parser = create_argument_parser()
        args = parser.parse_args(['--bug', 'Test failure in auth module'])
        self.assertIsNone(args.issue)
        self.assertEqual(args.bug, 'Test failure in auth module')
    
    def test_parse_with_feature(self):
        """Test parsing with feature flag."""
        parser = create_argument_parser()
        args = parser.parse_args(['--feature', 'Add CSV export'])
        self.assertIsNone(args.issue)
        self.assertEqual(args.feature, 'Add CSV export')
    
    def test_parse_with_all_flags(self):
        """Test parsing with multiple flags."""
        parser = create_argument_parser()
        args = parser.parse_args([
            '123',
            '--interactive',
            '--prompt-only',
            '--timeout', '30',
            '--project', '5',
            '--branch-strategy', 'always_new',
            '--base-branch', 'develop',
            '--coder', 'llm'
        ])
        self.assertEqual(args.issue, '123')
        self.assertTrue(args.interactive)
        self.assertTrue(args.prompt_only)
        self.assertEqual(args.timeout, 30.0)
        self.assertEqual(args.project, 5)
        self.assertEqual(args.branch_strategy, 'always_new')
        self.assertEqual(args.base_branch, 'develop')
        self.assertEqual(args.coder, 'llm')
    
    def test_parse_dry_run(self):
        """Test parsing with dry-run flag."""
        parser = create_argument_parser()
        args = parser.parse_args(['123', '--dry-run'])
        self.assertTrue(args.dry_run)
    
    def test_parse_no_smart_branching(self):
        """Test parsing with no-smart-branching flag."""
        parser = create_argument_parser()
        args = parser.parse_args(['123', '--no-smart-branching'])
        self.assertTrue(args.no_smart_branching)
    
    def test_parse_auto_pr_review(self):
        """Test parsing with auto-pr-review flag."""
        parser = create_argument_parser()
        args = parser.parse_args(['123', '--auto-pr-review'])
        self.assertTrue(args.auto_pr_review)
    
    def test_default_values(self):
        """Test default values for optional arguments."""
        parser = create_argument_parser()
        args = parser.parse_args(['123'])
        self.assertFalse(args.interactive)
        self.assertFalse(args.prompt_only)
        self.assertFalse(args.dry_run)
        self.assertFalse(args.auto_pr_review)
        self.assertFalse(args.no_smart_branching)
        self.assertEqual(args.timeout, 10.0)
        self.assertEqual(args.coder, 'claude')
        self.assertEqual(args.branch_strategy, 'reuse')
        self.assertIsNone(args.project)
        self.assertIsNone(args.base_branch)


class TestValidateArguments(TestCase):
    """Test argument validation."""
    
    def test_validate_no_action(self):
        """Test validation with no action specified."""
        args = Mock(issue=None, review_pr=None, bug=None, feature=None)
        error = validate_arguments(args)
        self.assertIsNotNone(error)
        self.assertIn("Must specify", error)
    
    def test_validate_multiple_actions(self):
        """Test validation with multiple actions."""
        args = Mock(issue='123', review_pr='456', bug=None, feature=None)
        error = validate_arguments(args)
        self.assertIsNotNone(error)
        self.assertIn("multiple actions", error)
    
    def test_validate_invalid_issue_format(self):
        """Test validation with invalid issue format."""
        args = Mock(issue='abc', review_pr=None, bug=None, feature=None)
        error = validate_arguments(args)
        self.assertIsNotNone(error)
        self.assertIn("Invalid issue number format", error)
    
    def test_validate_invalid_pr_format(self):
        """Test validation with invalid PR format."""
        args = Mock(issue=None, review_pr='xyz', bug=None, feature=None)
        error = validate_arguments(args)
        self.assertIsNotNone(error)
        self.assertIn("Invalid PR number format", error)
    
    def test_validate_negative_timeout(self):
        """Test validation with negative timeout."""
        args = Mock(
            issue='123', review_pr=None, bug=None, feature=None,
            timeout=-5, project=None, base_branch=None,
            auto_pr_review=False, prompt_only=False, interactive=False
        )
        error = validate_arguments(args)
        self.assertIsNotNone(error)
        self.assertIn("Invalid timeout", error)
    
    def test_validate_invalid_project(self):
        """Test validation with invalid project ID."""
        args = Mock(
            issue='123', review_pr=None, bug=None, feature=None,
            timeout=10, project=-1, base_branch=None,
            auto_pr_review=False, prompt_only=False, interactive=False
        )
        error = validate_arguments(args)
        self.assertIsNotNone(error)
        self.assertIn("Invalid project ID", error)
    
    def test_validate_empty_bug_description(self):
        """Test validation with empty bug description."""
        args = Mock(
            issue=None, review_pr=None, bug='  ', feature=None,
            timeout=10, project=None, base_branch=None,
            auto_pr_review=False, prompt_only=False, interactive=False
        )
        error = validate_arguments(args)
        self.assertIsNotNone(error)
        self.assertIn("Bug description cannot be empty", error)
    
    def test_validate_empty_feature_description(self):
        """Test validation with empty feature description."""
        args = Mock(
            issue=None, review_pr=None, bug=None, feature='',
            timeout=10, project=None, base_branch=None,
            auto_pr_review=False, prompt_only=False, interactive=False
        )
        error = validate_arguments(args)
        self.assertIsNotNone(error)
        self.assertIn("Feature description cannot be empty", error)
    
    def test_validate_empty_base_branch(self):
        """Test validation with empty base branch."""
        args = Mock(
            issue='123', review_pr=None, bug=None, feature=None,
            timeout=10, project=None, base_branch='  ',
            auto_pr_review=False, prompt_only=False, interactive=False
        )
        error = validate_arguments(args)
        self.assertIsNotNone(error)
        self.assertIn("Base branch name cannot be empty", error)
    
    def test_validate_auto_pr_review_with_prompt_only(self):
        """Test validation with auto-pr-review and prompt-only."""
        args = Mock(
            issue='123', review_pr=None, bug=None, feature=None,
            timeout=10, project=None, base_branch=None,
            auto_pr_review=True, prompt_only=True, interactive=False
        )
        error = validate_arguments(args)
        self.assertIsNotNone(error)
        self.assertIn("auto-pr-review cannot be used with", error)
    
    def test_validate_auto_pr_review_without_issue(self):
        """Test validation with auto-pr-review but no issue."""
        args = Mock(
            issue=None, review_pr='123', bug=None, feature=None,
            timeout=10, project=None, base_branch=None,
            auto_pr_review=True, prompt_only=False, interactive=False
        )
        error = validate_arguments(args)
        self.assertIsNotNone(error)
        self.assertIn("auto-pr-review can only be used with issue", error)
    
    def test_validate_interactive_with_prompt_only(self):
        """Test validation with interactive and prompt-only."""
        args = Mock(
            issue='123', review_pr=None, bug=None, feature=None,
            timeout=10, project=None, base_branch=None,
            auto_pr_review=False, prompt_only=True, interactive=True
        )
        error = validate_arguments(args)
        self.assertIsNotNone(error)
        self.assertIn("interactive and --prompt-only cannot", error)
    
    def test_validate_success(self):
        """Test successful validation."""
        args = Mock(
            issue='123', review_pr=None, bug=None, feature=None,
            timeout=10, project=5, base_branch='main',
            auto_pr_review=False, prompt_only=False, interactive=False
        )
        error = validate_arguments(args)
        self.assertIsNone(error)


class TestPrintResultsSummary(TestCase):
    """Test results summary printing."""
    
    def test_print_empty_results(self):
        """Test printing empty results."""
        with patch('builtins.print') as mock_print:
            print_results_summary([])
            mock_print.assert_not_called()
    
    def test_print_single_success(self):
        """Test printing single successful result."""
        result = WorkflowResult(
            success=True,
            message="Issue #123 processed successfully"
        )
        with patch('builtins.print') as mock_print:
            print_results_summary([result])
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            self.assertIn("1/1 successful", call_args)
    
    def test_print_mixed_results(self):
        """Test printing mixed success/failure results."""
        results = [
            WorkflowResult(success=True, message="Success 1"),
            WorkflowResult(
                success=False,
                message="Failed 1",
                error_details="Network error"
            ),
            WorkflowResult(success=True, message="Success 2"),
        ]
        with patch('builtins.print') as mock_print:
            print_results_summary(results)
            # Check summary line
            summary_printed = False
            failure_printed = False
            for call in mock_print.call_args_list:
                call_text = str(call[0][0])
                if "2/3 successful" in call_text:
                    summary_printed = True
                if "Failed 1" in call_text:
                    failure_printed = True
            self.assertTrue(summary_printed)
            self.assertTrue(failure_printed)
    
    def test_print_with_error_details(self):
        """Test printing results with error details."""
        result = WorkflowResult(
            success=False,
            message="Processing failed",
            error_details="Permission denied"
        )
        with patch('builtins.print') as mock_print:
            print_results_summary([result])
            # Check that error details are printed
            details_printed = False
            for call in mock_print.call_args_list:
                if "Permission denied" in str(call[0][0]):
                    details_printed = True
            self.assertTrue(details_printed)


class TestMainFunction(TestCase):
    """Test main CLI function."""
    
    @patch('sys.argv', ['claude-tasker'])
    @patch('builtins.print')
    def test_main_no_action_specified(self, mock_print):
        """Test main with no action specified."""
        exit_code = main()
        self.assertEqual(exit_code, 1)
        # Check error message was printed
        error_printed = False
        for call in mock_print.call_args_list:
            if "Must specify" in str(call):
                error_printed = True
        self.assertTrue(error_printed)
    
    @patch('sys.argv', ['claude-tasker', '123'])
    @patch('pathlib.Path.exists', return_value=False)
    @patch('builtins.print')
    def test_main_missing_claude_md(self, mock_print, mock_exists):
        """Test main with missing CLAUDE.md file."""
        exit_code = main()
        self.assertEqual(exit_code, 1)
        # Check error message was printed
        error_printed = False
        for call in mock_print.call_args_list:
            if "CLAUDE.md not found" in str(call):
                error_printed = True
        self.assertTrue(error_printed)
    
    @patch('sys.argv', ['claude-tasker', '123', '--dry-run'])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    @patch('builtins.print')
    def test_main_dry_run_sets_prompt_only(self, mock_print, mock_workflow_class, mock_exists):
        """Test that dry-run sets prompt-only mode."""
        mock_workflow = Mock()
        mock_workflow.process_single_issue.return_value = WorkflowResult(
            success=True, message="Test"
        )
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        # Verify prompt_only was set to True
        mock_workflow.process_single_issue.assert_called_once()
        call_args = mock_workflow.process_single_issue.call_args[0]
        self.assertTrue(call_args[1])  # prompt_only should be True
    
    @patch('sys.argv', ['claude-tasker', '123', '--no-smart-branching'])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    @patch('os.environ', {})
    def test_main_no_smart_branching(self, mock_workflow_class, mock_exists):
        """Test that no-smart-branching sets environment variable."""
        mock_workflow = Mock()
        mock_workflow.process_single_issue.return_value = WorkflowResult(
            success=True, message="Test"
        )
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        # Verify environment variable was set
        self.assertEqual(os.environ.get('CLAUDE_SMART_BRANCHING'), 'false')
        # Verify branch_strategy was set to always_new
        mock_workflow_class.assert_called_once()
        call_kwargs = mock_workflow_class.call_args[1]
        self.assertEqual(call_kwargs['branch_strategy'], 'always_new')
    
    @patch('sys.argv', ['claude-tasker', '123'])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    @patch('builtins.print')
    def test_main_process_single_issue_success(self, mock_print, mock_workflow_class, mock_exists):
        """Test main processing single issue successfully."""
        mock_workflow = Mock()
        mock_workflow.process_single_issue.return_value = WorkflowResult(
            success=True,
            message="Issue #123 processed",
            pr_url="https://github.com/owner/repo/pull/456",
            branch_name="issue-123"
        )
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        self.assertEqual(exit_code, 0)
        mock_workflow.process_single_issue.assert_called_once_with(123, False, None)
        # Check success message was printed
        success_printed = False
        for call in mock_print.call_args_list:
            if "Issue #123 processed" in str(call):
                success_printed = True
        self.assertTrue(success_printed)
    
    @patch('sys.argv', ['claude-tasker', '123-125'])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    @patch('builtins.print')
    def test_main_process_issue_range(self, mock_print, mock_workflow_class, mock_exists):
        """Test main processing issue range."""
        mock_workflow = Mock()
        mock_workflow.process_issue_range.return_value = [
            WorkflowResult(success=True, message="Issue #123"),
            WorkflowResult(success=True, message="Issue #124"),
            WorkflowResult(success=False, message="Issue #125 failed")
        ]
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        self.assertEqual(exit_code, 1)  # One failure
        mock_workflow.process_issue_range.assert_called_once_with(123, 125, False, None)
    
    @patch('sys.argv', ['claude-tasker', '--review-pr', '456'])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    def test_main_review_pr(self, mock_workflow_class, mock_exists):
        """Test main reviewing PR."""
        mock_workflow = Mock()
        mock_workflow.review_pr.return_value = WorkflowResult(
            success=True,
            message="PR reviewed"
        )
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        self.assertEqual(exit_code, 0)
        mock_workflow.review_pr.assert_called_once_with(456, False)
    
    @patch('sys.argv', ['claude-tasker', '--bug', 'Test failure'])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    def test_main_analyze_bug(self, mock_workflow_class, mock_exists):
        """Test main analyzing bug."""
        mock_workflow = Mock()
        mock_workflow.analyze_bug.return_value = WorkflowResult(
            success=True,
            message="Bug analyzed"
        )
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        self.assertEqual(exit_code, 0)
        mock_workflow.analyze_bug.assert_called_once_with('Test failure', False)
    
    @patch('sys.argv', ['claude-tasker', '--feature', 'Add export'])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    def test_main_analyze_feature(self, mock_workflow_class, mock_exists):
        """Test main analyzing feature."""
        mock_workflow = Mock()
        mock_workflow.analyze_feature.return_value = WorkflowResult(
            success=True,
            message="Feature analyzed"
        )
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        self.assertEqual(exit_code, 0)
        mock_workflow.analyze_feature.assert_called_once_with('Add export', False)
    
    @patch('sys.argv', ['claude-tasker', '123', '--auto-pr-review'])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    @patch('builtins.print')
    def test_main_auto_pr_review(self, mock_print, mock_workflow_class, mock_exists):
        """Test main with auto PR review."""
        mock_workflow = Mock()
        mock_workflow.process_single_issue.return_value = WorkflowResult(
            success=True,
            message="Issue processed",
            pr_url="https://github.com/owner/repo/pull/789"
        )
        mock_workflow.review_pr.return_value = WorkflowResult(
            success=True,
            message="PR reviewed"
        )
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        self.assertEqual(exit_code, 0)
        # Verify both issue processing and PR review were called
        mock_workflow.process_single_issue.assert_called_once()
        mock_workflow.review_pr.assert_called_once_with(789, False)
    
    @patch('sys.argv', ['claude-tasker', '123'])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    def test_main_keyboard_interrupt(self, mock_workflow_class, mock_exists):
        """Test main handling keyboard interrupt."""
        mock_workflow = Mock()
        mock_workflow.process_single_issue.side_effect = KeyboardInterrupt()
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        self.assertEqual(exit_code, 130)  # SIGINT exit code
    
    @patch('sys.argv', ['claude-tasker', '123'])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    @patch('builtins.print')
    def test_main_unexpected_exception(self, mock_print, mock_workflow_class, mock_exists):
        """Test main handling unexpected exception."""
        mock_workflow = Mock()
        mock_workflow.process_single_issue.side_effect = Exception("Unexpected error")
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        self.assertEqual(exit_code, 1)
        # Check error message was printed
        error_printed = False
        for call in mock_print.call_args_list:
            if "Unexpected error" in str(call):
                error_printed = True
        self.assertTrue(error_printed)
    
    @patch('sys.argv', ['claude-tasker', '--review-pr', '100-102', '--timeout', '2'])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('src.claude_tasker.cli.WorkflowLogic')
    @patch('time.sleep')
    def test_main_pr_range_with_timeout(self, mock_sleep, mock_workflow_class, mock_exists):
        """Test main reviewing PR range with timeout between PRs."""
        mock_workflow = Mock()
        mock_workflow.review_pr.return_value = WorkflowResult(
            success=True,
            message="PR reviewed"
        )
        mock_workflow_class.return_value = mock_workflow
        
        exit_code = main()
        
        self.assertEqual(exit_code, 0)
        # Should review 3 PRs
        self.assertEqual(mock_workflow.review_pr.call_count, 3)
        # Should sleep twice (not after last PR)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(2.0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])