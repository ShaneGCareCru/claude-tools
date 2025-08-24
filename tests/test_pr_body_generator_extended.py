"""Extended tests for pr_body_generator module."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.claude_tasker.pr_body_generator import PRBodyGenerator
from src.claude_tasker.github_client import IssueData


class TestPRBodyGeneratorExtended:
    """Extended tests for PRBodyGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create a PRBodyGenerator instance."""
        return PRBodyGenerator()
    
    @pytest.fixture
    def issue_data(self):
        """Create sample issue data."""
        return IssueData(
            number=42,
            title="Test Issue",
            body="Test issue body",
            labels=["bug", "enhancement"],
            url="https://github.com/test/repo/issues/42",
            author="testuser",
            state="open",
            assignee="developer",
            milestone="v1.0",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z"
        )
    
    def test_format_labels_empty(self, generator):
        """Test format_labels with empty list."""
        result = generator._format_labels([])
        assert result == "None"
    
    def test_format_labels_single(self, generator):
        """Test format_labels with single label."""
        result = generator._format_labels(["bug"])
        assert result == "`bug`"
    
    def test_format_labels_multiple(self, generator):
        """Test format_labels with multiple labels."""
        result = generator._format_labels(["bug", "enhancement", "priority"])
        assert result == "`bug`, `enhancement`, `priority`"
    
    def test_generate_test_checklist_no_diff(self, generator):
        """Test generate_test_checklist with no diff."""
        result = generator._generate_test_checklist("")
        assert "Run existing tests" in result
        assert "Verify no regressions" in result
    
    def test_generate_test_checklist_with_test_changes(self, generator):
        """Test generate_test_checklist with test file changes."""
        git_diff = """
        diff --git a/tests/test_example.py b/tests/test_example.py
        + def test_new_feature():
        +     assert True
        """
        result = generator._generate_test_checklist(git_diff)
        assert "Run new/modified tests" in result
        assert "test_example.py" in result
    
    def test_generate_test_checklist_with_src_changes(self, generator):
        """Test generate_test_checklist with source file changes."""
        git_diff = """
        diff --git a/src/module.py b/src/module.py
        + def new_function():
        +     return True
        """
        result = generator._generate_test_checklist(git_diff)
        assert "Test affected functionality" in result
        assert "module.py" in result
    
    def test_generate_test_checklist_with_config_changes(self, generator):
        """Test generate_test_checklist with config file changes."""
        git_diff = """
        diff --git a/package.json b/package.json
        + "new-dependency": "^1.0.0"
        diff --git a/requirements.txt b/requirements.txt
        + new-package==1.0.0
        """
        result = generator._generate_test_checklist(git_diff)
        assert "Verify dependency installation" in result
        assert "package.json" in result
        assert "requirements.txt" in result
    
    def test_generate_pr_body_minimal(self, generator):
        """Test generate_pr_body with minimal data."""
        issue_data = IssueData(
            number=1,
            title="Fix bug",
            body="",
            labels=[],
            url="https://github.com/test/repo/issues/1",
            author="testuser",
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        
        result = generator.generate_pr_body(
            issue_data=issue_data,
            git_diff="",
            branch_name="fix-1",
            commit_log=""
        )
        
        assert "Fixes #1" in result
        assert "Fix bug" in result
        assert "## Summary" in result
        assert "## Testing" in result
    
    def test_generate_pr_body_full_data(self, generator, issue_data):
        """Test generate_pr_body with complete data."""
        git_diff = """
        diff --git a/src/main.py b/src/main.py
        + def feature():
        +     return "new"
        diff --git a/tests/test_main.py b/tests/test_main.py
        + def test_feature():
        +     assert feature() == "new"
        """
        
        commit_log = """
        abc123 Add new feature
        def456 Add tests for feature
        """
        
        result = generator.generate_pr_body(
            issue_data=issue_data,
            git_diff=git_diff,
            branch_name="issue-42-timestamp",
            commit_log=commit_log
        )
        
        assert "Fixes #42" in result
        assert "Test Issue" in result
        assert "bug" in result
        assert "enhancement" in result
        assert "v1.0" in result
        assert "developer" in result
        assert "main.py" in result
    
    def test_generate_pr_body_with_long_description(self, generator):
        """Test generate_pr_body with long issue description."""
        issue_data = IssueData(
            number=100,
            title="Complex Feature",
            body="This is a very long description. " * 50,  # Very long body
            labels=["feature"],
            url="https://github.com/test/repo/issues/100",
            author="testuser",
            state="open",
            assignee=None,
            milestone=None,
            created_at="2024-01-01",
            updated_at="2024-01-01"
        )
        
        result = generator.generate_pr_body(
            issue_data=issue_data,
            git_diff="+ changes",
            branch_name="feature-100",
            commit_log="Initial commit"
        )
        
        assert "Fixes #100" in result
        assert "..." in result  # Should be truncated
        assert len(result) < 10000  # Should not be excessively long
    
    def test_generate_pr_body_exception_handling(self, generator):
        """Test generate_pr_body with exception."""
        with patch('src.claude_tasker.pr_body_generator.logger') as mock_logger:
            # Pass None to cause exception
            result = generator.generate_pr_body(
                issue_data=None,
                git_diff="diff",
                branch_name="branch",
                commit_log="log"
            )
            
            assert result is not None
            assert "Failed to generate PR body" in result
            mock_logger.error.assert_called()
    
    def test_generate_changes_section_no_diff(self, generator):
        """Test _generate_changes_section with no diff."""
        result = generator._generate_changes_section("")
        assert "No file changes detected" in result
    
    def test_generate_changes_section_with_additions_only(self, generator):
        """Test _generate_changes_section with only additions."""
        git_diff = """
        diff --git a/new_file.py b/new_file.py
        +++ b/new_file.py
        + def new_function():
        +     pass
        + 
        + class NewClass:
        +     pass
        """
        result = generator._generate_changes_section(git_diff)
        assert "new_file.py" in result
        assert "additions" in result.lower()
    
    def test_generate_changes_section_with_deletions_only(self, generator):
        """Test _generate_changes_section with only deletions."""
        git_diff = """
        diff --git a/old_file.py b/old_file.py
        --- a/old_file.py
        - def old_function():
        -     pass
        - 
        - class OldClass:
        -     pass
        """
        result = generator._generate_changes_section(git_diff)
        assert "old_file.py" in result
    
    def test_generate_changes_section_multiple_files(self, generator):
        """Test _generate_changes_section with multiple files."""
        git_diff = """
        diff --git a/file1.py b/file1.py
        + change1
        diff --git a/file2.js b/file2.js
        + change2
        diff --git a/file3.md b/file3.md
        + change3
        """
        result = generator._generate_changes_section(git_diff)
        assert "file1.py" in result
        assert "file2.js" in result
        assert "file3.md" in result
    
    def test_extract_files_from_diff_empty(self, generator):
        """Test _extract_files_from_diff with empty diff."""
        result = generator._extract_files_from_diff("")
        assert result == []
    
    def test_extract_files_from_diff_various_formats(self, generator):
        """Test _extract_files_from_diff with various diff formats."""
        git_diff = """
        diff --git a/src/main.py b/src/main.py
        index abc123..def456 100644
        --- a/src/main.py
        +++ b/src/main.py
        diff --git a/tests/test.py b/tests/test.py
        new file mode 100644
        diff --git a/old.py b/old.py
        deleted file mode 100644
        """
        result = generator._extract_files_from_diff(git_diff)
        assert "src/main.py" in result
        assert "tests/test.py" in result
        assert "old.py" in result
    
    def test_generate_implementation_approach_empty_log(self, generator):
        """Test _generate_implementation_approach with empty commit log."""
        result = generator._generate_implementation_approach("")
        assert result == ""
    
    def test_generate_implementation_approach_with_commits(self, generator):
        """Test _generate_implementation_approach with commit messages."""
        commit_log = """
        abc123 feat: Add new feature
        def456 fix: Fix bug in feature
        ghi789 test: Add tests for feature
        jkl012 docs: Update documentation
        """
        result = generator._generate_implementation_approach(commit_log)
        assert "Implementation Approach" in result
        assert "Add new feature" in result
        assert "Fix bug" in result
        assert "Add tests" in result
        assert "Update documentation" in result
    
    def test_generate_implementation_approach_filters_automated(self, generator):
        """Test that automated commit messages are filtered."""
        commit_log = """
        abc123 Real commit message
        def456 automated implementation via agent coordination
        ghi789 Another real commit
        """
        result = generator._generate_implementation_approach(commit_log)
        assert "Real commit message" in result
        assert "Another real commit" in result
        assert "automated implementation" not in result