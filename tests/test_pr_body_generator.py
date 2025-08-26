"""Comprehensive unit tests for PR body generator module."""

import tempfile
import subprocess
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock, mock_open
import pytest

from src.claude_tasker.pr_body_generator import PRBodyGenerator
from src.claude_tasker.github_client import IssueData
from src.claude_tasker.services.command_executor import CommandExecutor


class TestPRBodyGenerator(TestCase):
    """Test PR body generator functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        mock_executor = Mock(spec=CommandExecutor)
        self.generator = PRBodyGenerator(mock_executor)
        self.sample_issue = IssueData(
            number=123,
            title="Add user authentication",
            body="This feature adds user authentication with JWT tokens. It includes login, logout, and user registration.",
            labels=["enhancement", "security"],
            url="https://github.com/owner/repo/issues/123",
            author="developer",
            state="open",
            assignee="team-lead",
            milestone="v2.0"
        )
        self.sample_diff = """diff --git a/src/auth.py b/src/auth.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/src/auth.py
@@ -0,0 +1,50 @@
+def login(username, password):
+    # Login implementation
+    pass
+
+def logout(token):
+    # Logout implementation
+    pass
+
diff --git a/tests/test_auth.py b/tests/test_auth.py
new file mode 100644
index 0000000..abcdefg
--- /dev/null
+++ b/tests/test_auth.py
@@ -0,0 +1,25 @@
+import unittest
+from src.auth import login, logout
+
+class TestAuth(unittest.TestCase):
+    def test_login(self):
+        pass
"""
    
    def test_initialization(self):
        """Test PRBodyGenerator initialization."""
        self.assertEqual(self.generator.max_size, 10000)
        self.assertIn('.github/pull_request_template.md', self.generator.template_paths)
        self.assertIn('PULL_REQUEST_TEMPLATE.md', self.generator.template_paths)
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    def test_detect_templates_found(self, mock_read_text, mock_exists):
        """Test template detection when template exists."""
        mock_exists.side_effect = lambda: self.call_count < 1  # First call returns True
        mock_read_text.return_value = "## PR Template\nDescription: \nTesting: "
        self.call_count = 0
        
        def side_effect():
            self.call_count += 1
            return self.call_count == 1
        
        mock_exists.side_effect = side_effect
        
        template = self.generator.detect_templates()
        
        self.assertEqual(template, "## PR Template\nDescription: \nTesting: ")
        mock_read_text.assert_called_once()
    
    @patch('pathlib.Path.exists')
    def test_detect_templates_not_found(self, mock_exists):
        """Test template detection when no template exists."""
        mock_exists.return_value = False
        
        template = self.generator.detect_templates()
        
        self.assertIsNone(template)
        # Should check all template paths
        self.assertEqual(mock_exists.call_count, len(self.generator.template_paths))
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    def test_detect_templates_read_error(self, mock_read_text, mock_exists):
        """Test template detection with read error."""
        mock_exists.return_value = True
        mock_read_text.side_effect = Exception("Read error")
        
        template = self.generator.detect_templates()
        
        self.assertIsNone(template)
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    def test_detect_templates_custom_path(self, mock_read_text, mock_exists):
        """Test template detection with custom repository path."""
        mock_exists.side_effect = lambda: self.call_count < 1
        mock_read_text.return_value = "Custom template"
        self.call_count = 0
        
        def side_effect():
            self.call_count += 1
            return self.call_count == 1
        
        mock_exists.side_effect = side_effect
        
        template = self.generator.detect_templates("/custom/repo")
        
        self.assertEqual(template, "Custom template")
    
    def test_aggregate_context(self):
        """Test context aggregation."""
        context = self.generator.aggregate_context(
            self.sample_issue,
            self.sample_diff,
            "feature-auth",
            "abc123 Add authentication\ndef456 Add tests"
        )
        
        # Test issue context
        self.assertEqual(context['issue']['number'], 123)
        self.assertEqual(context['issue']['title'], "Add user authentication")
        self.assertEqual(context['issue']['labels'], ["enhancement", "security"])
        self.assertEqual(context['issue']['assignee'], "team-lead")
        self.assertEqual(context['issue']['milestone'], "v2.0")
        
        # Test changes context
        self.assertEqual(context['changes']['branch'], "feature-auth")
        self.assertEqual(context['changes']['commit_log'], "abc123 Add authentication\ndef456 Add tests")
        
        # Test stats
        self.assertIn('files_added', context['stats'])
        self.assertIn('lines_added', context['stats'])
    
    def test_aggregate_context_long_issue_body(self):
        """Test context aggregation with long issue body."""
        long_issue = IssueData(
            number=123,
            title="Test",
            body="x" * 1500,  # Long body
            labels=[],
            url="https://example.com",
            author="user",
            state="open"
        )
        
        context = self.generator.aggregate_context(long_issue, "", "branch", "")
        
        # Should be truncated to 1000 chars + "..."
        self.assertEqual(len(context['issue']['body']), 1003)  # 1000 + "..."
        self.assertTrue(context['issue']['body'].endswith('...'))
    
    def test_summarize_diff_empty(self):
        """Test diff summarization with empty diff."""
        summary = self.generator._summarize_diff("")
        
        self.assertEqual(summary['files_changed'], 0)
        self.assertEqual(summary['files'], [])
        self.assertEqual(summary['additions'], 0)
        self.assertEqual(summary['deletions'], 0)
        self.assertEqual(summary['net_change'], 0)
        self.assertEqual(summary['summary'], 'No changes')
    
    def test_summarize_diff_with_changes(self):
        """Test diff summarization with actual changes."""
        summary = self.generator._summarize_diff(self.sample_diff)
        
        self.assertEqual(summary['files_changed'], 2)
        self.assertIn('src/auth.py', summary['files'])
        self.assertIn('tests/test_auth.py', summary['files'])
        self.assertGreater(summary['additions'], 0)
        self.assertEqual(summary['deletions'], 0)
        self.assertGreater(summary['net_change'], 0)
    
    def test_summarize_diff_with_deletions(self):
        """Test diff summarization with deletions."""
        diff_with_deletions = """diff --git a/old_file.py b/old_file.py
index 1234567..0000000
--- a/old_file.py
+++ b/old_file.py
@@ -1,5 +0,0 @@
-def old_function():
-    pass
-
-def deprecated_function():
-    return None
"""
        
        summary = self.generator._summarize_diff(diff_with_deletions)
        
        self.assertEqual(summary['files_changed'], 1)
        self.assertEqual(summary['additions'], 0)
        self.assertEqual(summary['deletions'], 5)
        self.assertEqual(summary['net_change'], -5)
    
    def test_calculate_change_stats_empty(self):
        """Test change statistics calculation with empty diff."""
        stats = self.generator._calculate_change_stats("")
        
        expected = {
            'files_added': 0,
            'files_modified': 0,
            'files_deleted': 0,
            'lines_added': 0,
            'lines_deleted': 0
        }
        self.assertEqual(stats, expected)
    
    def test_calculate_change_stats_new_files(self):
        """Test change statistics calculation with new files."""
        diff_new_file = """diff --git a/new_file.py b/new_file.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,10 @@
+def new_function():
+    pass
"""
        
        stats = self.generator._calculate_change_stats(diff_new_file)
        
        self.assertEqual(stats['files_added'], 1)
        self.assertEqual(stats['files_modified'], 0)
        self.assertEqual(stats['lines_added'], 2)  # Only content lines, not headers
    
    def test_calculate_change_stats_deleted_files(self):
        """Test change statistics calculation with deleted files."""
        diff_deleted_file = """diff --git a/old_file.py b/old_file.py
deleted file mode 100644
index 1234567..0000000
--- a/old_file.py
+++ /dev/null
@@ -1,5 +0,0 @@
-def old_function():
-    pass
"""
        
        stats = self.generator._calculate_change_stats(diff_deleted_file)
        
        self.assertEqual(stats['files_deleted'], 1)
        self.assertEqual(stats['files_modified'], 0)
        self.assertEqual(stats['lines_deleted'], 2)
    
    def test_calculate_change_stats_modified_files(self):
        """Test change statistics calculation with modified files."""
        diff_modified = """diff --git a/modified.py b/modified.py
index 1234567..abcdefg 100644
--- a/modified.py
+++ b/modified.py
@@ -1,5 +1,7 @@
 def existing_function():
-    old_line
+    new_line
+    added_line
     pass
"""
        
        stats = self.generator._calculate_change_stats(diff_modified)
        
        self.assertEqual(stats['files_modified'], 1)
        self.assertEqual(stats['files_added'], 0)
        self.assertEqual(stats['files_deleted'], 0)
        self.assertGreater(stats['lines_added'], 0)
        self.assertGreater(stats['lines_deleted'], 0)
    
    def test_build_generation_prompt_basic(self):
        """Test prompt building for LLM generation."""
        context = {
            'issue': {
                'number': 123,
                'title': 'Test Issue',
                'body': 'Test description',
                'labels': ['bug', 'high']
            },
            'changes': {
                'branch': 'fix-branch',
                'diff_summary': {
                    'files_changed': 2,
                    'files': ['file1.py', 'file2.py'],
                    'additions': 10,
                    'deletions': 5
                },
                'commit_log': 'Fix the bug\nAdd tests'
            }
        }
        
        prompt = self.generator._build_generation_prompt(context)
        
        self.assertIn('Issue #123: Test Issue', prompt)
        self.assertIn('Test description', prompt)
        self.assertIn('fix-branch', prompt)
        self.assertIn('Files changed: 2', prompt)
        self.assertIn('Lines: +10/-5', prompt)
        self.assertIn('Fix the bug', prompt)
        self.assertIn('file1.py, file2.py', prompt)
    
    def test_build_generation_prompt_with_template(self):
        """Test prompt building with template."""
        context = {
            'issue': {'number': 123, 'title': 'Test', 'body': 'Test', 'labels': []},
            'changes': {'branch': 'test', 'diff_summary': None, 'commit_log': ''}
        }
        template = "## Description\n## Testing\n## Checklist"
        
        prompt = self.generator._build_generation_prompt(context, template)
        
        self.assertIn('## Description', prompt)
        self.assertIn('## Testing', prompt)
        self.assertIn('## Checklist', prompt)
    
    def test_ensure_size_limit_within_limit(self):
        """Test size limit enforcement when within limit."""
        content = "Short content"
        result = self.generator._ensure_size_limit(content)
        
        self.assertEqual(result, content)
    
    def test_ensure_size_limit_exceeds_limit(self):
        """Test size limit enforcement when exceeding limit."""
        content = "x" * 11000  # Exceeds 10000 limit
        result = self.generator._ensure_size_limit(content)
        
        self.assertLess(len(result), self.generator.max_size)
        self.assertIn("Content truncated", result)
    
    @patch('pathlib.Path.unlink')
    def test_generate_with_llm_success(self, mock_unlink):
        """Test LLM-based generation success."""
        from src.claude_tasker.services.command_executor import CommandResult, CommandErrorType
        
        # Mock the CommandExecutor to return successful result
        mock_result = CommandResult(
            returncode=0,
            stdout="Generated PR body",
            stderr="",
            command=["llm"],
            execution_time=1.0,
            error_type=CommandErrorType.SUCCESS,
            attempts=1,
            success=True
        )
        self.generator.executor.execute.return_value = mock_result
        
        context = {
            'issue': {'number': 123, 'title': 'Test', 'body': 'Test', 'labels': []},
            'changes': {'branch': 'test', 'diff_summary': None, 'commit_log': ''}
        }
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_file = Mock()
            mock_file.name = '/tmp/test.txt'
            mock_temp.return_value.__enter__.return_value = mock_file
            
            result = self.generator.generate_with_llm(context)
            
            self.assertEqual(result, "Generated PR body")
            self.generator.executor.execute.assert_called_once()
            mock_unlink.assert_called_once()
    
    @patch('subprocess.run')
    @patch('pathlib.Path.unlink')
    def test_generate_with_llm_failure(self, mock_unlink, mock_run):
        """Test LLM-based generation failure."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error")
        
        context = {
            'issue': {'number': 123, 'title': 'Test', 'body': 'Test', 'labels': []},
            'changes': {'branch': 'test', 'diff_summary': None, 'commit_log': ''}
        }
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_file = Mock()
            mock_file.name = '/tmp/test.txt'
            mock_temp.return_value.__enter__.return_value = mock_file
            
            result = self.generator.generate_with_llm(context)
            
            self.assertIsNone(result)
    
    @patch('subprocess.run')
    def test_generate_with_llm_file_not_found(self, mock_run):
        """Test LLM-based generation with tool not found."""
        mock_run.side_effect = FileNotFoundError()
        
        context = {
            'issue': {'number': 123, 'title': 'Test', 'body': 'Test', 'labels': []},
            'changes': {'branch': 'test', 'diff_summary': None, 'commit_log': ''}
        }
        
        result = self.generator.generate_with_llm(context)
        
        self.assertIsNone(result)
    
    @patch('pathlib.Path.unlink')
    def test_generate_with_claude_success(self, mock_unlink):
        """Test Claude-based generation success."""
        from src.claude_tasker.services.command_executor import CommandResult, CommandErrorType
        
        # Mock the CommandExecutor to return successful result
        mock_result = CommandResult(
            returncode=0,
            stdout="Generated PR body",
            stderr="",
            command=["claude"],
            execution_time=1.0,
            error_type=CommandErrorType.SUCCESS,
            attempts=1,
            success=True
        )
        self.generator.executor.execute.return_value = mock_result
        
        context = {
            'issue': {'number': 123, 'title': 'Test', 'body': 'Test', 'labels': []},
            'changes': {'branch': 'test', 'diff_summary': None, 'commit_log': ''}
        }
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_file = Mock()
            mock_file.name = '/tmp/test.txt'
            mock_temp.return_value.__enter__.return_value = mock_file
            
            result = self.generator.generate_with_claude(context)
            
            self.assertEqual(result, "Generated PR body")
            self.generator.executor.execute.assert_called_once()
            # Check that claude CLI was called with correct arguments
            call_args = self.generator.executor.execute.call_args[0][0]
            self.assertIn('claude', call_args)
            self.assertIn('--file', call_args)
    
    def test_create_fallback_pr_body_basic(self):
        """Test fallback PR body creation."""
        context = {
            'issue': {
                'number': 123,
                'title': 'Test Issue',
                'body': 'Issue description',
                'labels': ['bug'],
                'assignee': 'developer',
                'milestone': 'v1.0'
            },
            'stats': {
                'files_added': 2,
                'files_modified': 1,
                'files_deleted': 0,
                'lines_added': 50,
                'lines_deleted': 10
            },
            'changes': {
                'diff_summary': {
                    'files': ['src/main.py', 'tests/test_main.py']
                }
            }
        }
        
        pr_body = self.generator._create_fallback_pr_body(context)
        
        self.assertIn("## Summary", pr_body)
        self.assertIn("issue #123: Test Issue", pr_body)
        self.assertIn("Issue description", pr_body)
        self.assertIn("2 files added", pr_body)
        self.assertIn("1 files modified", pr_body)
        self.assertIn("50 lines added, 10 lines deleted", pr_body)
        self.assertIn("src/main.py, tests/test_main.py", pr_body)
        self.assertIn("Fixes #123", pr_body)
        self.assertIn("Associated labels: bug", pr_body)
        self.assertIn("**Assignee:** developer", pr_body)
        self.assertIn("**Milestone:** v1.0", pr_body)
        self.assertIn("Generated with [Claude Code]", pr_body)
    
    def test_create_fallback_pr_body_minimal(self):
        """Test fallback PR body creation with minimal context."""
        context = {
            'issue': {
                'number': 456,
                'title': 'Simple Issue',
                'body': '',
                'labels': []
            },
            'stats': {},
            'changes': {'diff_summary': {}}
        }
        
        pr_body = self.generator._create_fallback_pr_body(context)
        
        self.assertIn("## Summary", pr_body)
        self.assertIn("issue #456: Simple Issue", pr_body)
        self.assertIn("Fixes #456", pr_body)
        self.assertNotIn("Issue Description", pr_body)  # Empty body
        self.assertNotIn("Associated labels", pr_body)  # No labels
    
    def test_format_labels_empty(self):
        """Test label formatting with empty list."""
        result = self.generator._format_labels([])
        self.assertEqual(result, "None")
        
        result = self.generator._format_labels(None)
        self.assertEqual(result, "None")
    
    def test_format_labels_with_labels(self):
        """Test label formatting with labels."""
        result = self.generator._format_labels(['bug', 'high-priority'])
        self.assertEqual(result, "`bug`, `high-priority`")
    
    def test_generate_test_checklist_no_diff(self):
        """Test test checklist generation with no diff."""
        checklist = self.generator._generate_test_checklist("")
        
        self.assertIn("Run existing tests", checklist)
        self.assertIn("Verify no regressions", checklist)
    
    def test_generate_test_checklist_with_tests(self):
        """Test test checklist generation with test files."""
        diff_with_tests = """diff --git a/tests/test_auth.py b/tests/test_auth.py
new file mode 100644
diff --git a/src/auth.py b/src/auth.py
new file mode 100644"""
        
        checklist = self.generator._generate_test_checklist(diff_with_tests)
        
        self.assertIn("Run new/modified tests", checklist)
        self.assertIn("Verify tests/test_auth.py passes", checklist)
        self.assertIn("Test affected functionality", checklist)
        self.assertIn("Test changes in src/auth.py", checklist)
    
    def test_generate_test_checklist_config_files(self):
        """Test test checklist generation with config files."""
        diff_config = """diff --git a/requirements.txt b/requirements.txt
modified
diff --git a/config.yml b/config.yml
modified"""
        
        checklist = self.generator._generate_test_checklist(diff_config)
        
        self.assertIn("Verify dependency installation", checklist)
        # Since requirements.txt is present, it goes to dependency path, not config changes
        self.assertIn("Test requirements.txt changes", checklist)
        self.assertIn("Test config.yml changes", checklist)
    
    def test_generate_changes_section_empty(self):
        """Test changes section generation with empty diff."""
        result = self.generator._generate_changes_section("")
        self.assertEqual(result, "No file changes detected")
        
        result = self.generator._generate_changes_section("   ")
        self.assertEqual(result, "No file changes detected")
    
    def test_generate_changes_section_with_changes(self):
        """Test changes section generation with changes."""
        result = self.generator._generate_changes_section(self.sample_diff)
        
        self.assertIn("Files modified:", result)
        self.assertIn("src/auth.py", result)
        self.assertIn("tests/test_auth.py", result)
        self.assertIn("additions", result)
    
    def test_extract_files_from_diff_empty(self):
        """Test file extraction from empty diff."""
        files = self.generator._extract_files_from_diff("")
        self.assertEqual(files, [])
    
    def test_extract_files_from_diff_with_files(self):
        """Test file extraction from diff with files."""
        files = self.generator._extract_files_from_diff(self.sample_diff)
        
        self.assertIn("src/auth.py", files)
        self.assertIn("tests/test_auth.py", files)
        self.assertEqual(len(files), 2)
    
    def test_generate_implementation_approach_empty(self):
        """Test implementation approach generation with empty log."""
        result = self.generator._generate_implementation_approach("")
        self.assertEqual(result, "")
        
        result = self.generator._generate_implementation_approach("   ")
        self.assertEqual(result, "")
    
    def test_generate_implementation_approach_with_commits(self):
        """Test implementation approach generation with commits."""
        commit_log = """abc123 Add user authentication
def456 Implement JWT tokens
ghi789 Add password validation"""
        
        result = self.generator._generate_implementation_approach(commit_log)
        
        self.assertIn("Implementation Approach:", result)
        self.assertIn("• Add user authentication", result)
        self.assertIn("• Implement JWT tokens", result)
        self.assertIn("• Add password validation", result)
    
    def test_generate_implementation_approach_filter_automated(self):
        """Test implementation approach filters automated commits."""
        commit_log = """abc123 Add feature
def456 automated: update dependencies
ghi789 bot: update version
jkl012 Fix bug"""
        
        result = self.generator._generate_implementation_approach(commit_log)
        
        self.assertIn("• Add feature", result)
        self.assertIn("• Fix bug", result)
        self.assertNotIn("automated", result)
        self.assertNotIn("bot:", result)
    
    @patch.object(PRBodyGenerator, 'detect_templates')
    @patch.object(PRBodyGenerator, 'generate_with_llm')
    @patch.object(PRBodyGenerator, 'generate_with_claude')
    def test_generate_pr_body_llm_success(self, mock_claude, mock_llm, mock_templates):
        """Test PR body generation with LLM success."""
        mock_templates.return_value = "Template content"
        mock_llm.return_value = "Generated PR body"
        
        result = self.generator.generate_pr_body(
            self.sample_issue,
            self.sample_diff,
            "feature-branch",
            "commit log"
        )
        
        self.assertEqual(result, "Generated PR body")
        mock_llm.assert_called_once()
        mock_claude.assert_not_called()
    
    @patch.object(PRBodyGenerator, 'detect_templates')
    @patch.object(PRBodyGenerator, 'generate_with_llm')
    @patch.object(PRBodyGenerator, 'generate_with_claude')
    def test_generate_pr_body_llm_fails_claude_success(self, mock_claude, mock_llm, mock_templates):
        """Test PR body generation with LLM failure, Claude success."""
        mock_templates.return_value = None
        mock_llm.return_value = None
        mock_claude.return_value = "Claude generated body"
        
        result = self.generator.generate_pr_body(
            self.sample_issue,
            self.sample_diff,
            "feature-branch",
            "commit log"
        )
        
        self.assertEqual(result, "Claude generated body")
        mock_llm.assert_called_once()
        mock_claude.assert_called_once()
    
    @patch.object(PRBodyGenerator, 'detect_templates')
    @patch.object(PRBodyGenerator, 'generate_with_llm')
    @patch.object(PRBodyGenerator, 'generate_with_claude')
    @patch.object(PRBodyGenerator, '_create_fallback_pr_body')
    def test_generate_pr_body_both_fail_fallback(self, mock_fallback, mock_claude, mock_llm, mock_templates):
        """Test PR body generation with both LLM and Claude failing."""
        mock_templates.return_value = None
        mock_llm.return_value = None
        mock_claude.return_value = None
        mock_fallback.return_value = "Fallback PR body"
        
        result = self.generator.generate_pr_body(
            self.sample_issue,
            self.sample_diff,
            "feature-branch",
            "commit log"
        )
        
        self.assertEqual(result, "Fallback PR body")
        mock_llm.assert_called_once()
        mock_claude.assert_called_once()
        mock_fallback.assert_called_once()
    
    @patch.object(PRBodyGenerator, 'detect_templates')
    def test_generate_pr_body_exception(self, mock_templates):
        """Test PR body generation with exception."""
        mock_templates.side_effect = Exception("Test error")
        
        result = self.generator.generate_pr_body(
            self.sample_issue,
            self.sample_diff,
            "feature-branch",
            "commit log"
        )
        
        self.assertIn("Failed to generate PR body", result)
        self.assertIn("Test error", result)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])