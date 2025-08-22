"""Tests for claude-tasker intelligent PR body generation functionality."""
import pytest
import subprocess
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, mock_open


class TestPRBodyGenerator:
    """Test intelligent PR body generation and template detection."""
    
    def test_pr_template_detection(self, claude_tasker_script, mock_git_repo):
        """Test detection of PR template files from .github directory."""
        # Create .github directory with PR template
        github_dir = mock_git_repo / ".github"
        github_dir.mkdir(exist_ok=True)
        
        pr_template = github_dir / "pull_request_template.md"
        pr_template.write_text("""# Pull Request Template

## Summary
Brief description of changes

## Changes Made
- [ ] Feature A
- [ ] Feature B

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass""")
        
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('builtins.open', mock_open()):
            
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test_output.txt'
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Add PR template support", "body": "Implement PR template detection", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git diff main...HEAD' in cmd or 'git diff master...HEAD' in cmd:
                    return Mock(returncode=0, stdout="diff --git a/src/file.py b/src/file.py\\n+new code", stderr="")
                elif 'git log --oneline -5' in cmd:
                    return Mock(returncode=0, stdout="abc123 Recent commit", stderr="")
                elif 'command -v llm' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/llm", stderr="")
                elif 'llm' in cmd and 'chat' in cmd:
                    return Mock(returncode=0, stdout="Generated intelligent PR body with template structure", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'), patch.dict('os.environ', {'CLAUDE_TASKER_AUTO_CLEANUP': '1'}):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should detect and use PR template
            assert result.returncode == 0
            # Template file should be accessible
            assert pr_template.exists()
    
    def test_context_aggregation_for_pr_body(self, claude_tasker_script, mock_git_repo):
        """Test aggregation of context for intelligent PR body generation."""
        from src.claude_tasker.pr_body_generator import PRBodyGenerator
        from src.claude_tasker.github_client import IssueData
        
        generator = PRBodyGenerator()
        
        # Create rich issue data
        issue_data = IssueData(
            number=123,
            title="Implement comprehensive test suite",
            body="Add testing framework with coverage reporting and CI integration",
            labels=["enhancement", "testing"],
            url="https://github.com/test/repo/issues/123",
            author="testuser",
            state="open"
        )
        
        # Substantial git diff
        git_diff = """diff --git a/tests/test_suite.py b/tests/test_suite.py
new file mode 100644
index 0000000..abc123
--- /dev/null
+++ b/tests/test_suite.py
@@ -0,0 +1,50 @@
+import pytest
+
+class TestSuite:
+    def test_example(self):
+        assert True"""
        
        branch_name = "feature/comprehensive-tests"
        commit_log = """abc123 Add test framework
def456 Update CI configuration
ghi789 Fix bug in parser
jkl012 Refactor core module
mno345 Initial implementation"""
        
        # Test context aggregation
        context = generator.aggregate_context(issue_data, git_diff, branch_name, commit_log)
        
        # Verify context structure
        assert context['issue']['number'] == 123
        assert context['issue']['title'] == "Implement comprehensive test suite"
        assert "enhancement" in context['issue']['labels']
        assert "testing" in context['issue']['labels']
        
        assert context['changes']['branch'] == branch_name
        assert context['changes']['commit_log'] == commit_log
        
        # Verify diff summary
        diff_summary = context['changes']['diff_summary']
        assert diff_summary['files_changed'] == 1
        assert 'tests/test_suite.py' in diff_summary['files']
        assert diff_summary['additions'] > 0
        
        # Verify stats
        stats = context['stats']
        assert stats['files_added'] == 1
        assert stats['lines_added'] > 0
    
    def test_llm_tool_fallback_to_claude(self, claude_tasker_script, mock_git_repo):
        """Test fallback from LLM tool to Claude output when LLM unavailable."""
        from src.claude_tasker.pr_body_generator import PRBodyGenerator
        from src.claude_tasker.github_client import IssueData
        
        generator = PRBodyGenerator()
        
        issue_data = IssueData(
            number=123,
            title="Test Issue",
            body="Test implementation",
            labels=[],
            url="https://github.com/test/repo/issues/123",
            author="testuser",
            state="open"
        )
        
        git_diff = "diff --git a/file.py b/file.py\n+new line"
        branch_name = "test-branch"
        commit_log = "abc123 Test commit"
        
        # Test context aggregation
        context = generator.aggregate_context(issue_data, git_diff, branch_name, commit_log)
        
        # Mock LLM failure, Claude success
        with patch.object(generator, 'generate_with_llm', return_value=None) as mock_llm, \
             patch.object(generator, 'generate_with_claude', return_value="Claude generated PR body") as mock_claude:
            
            result = generator.generate_pr_body(issue_data, git_diff, branch_name, commit_log)
            
            # Should fall back to Claude
            assert result == "Claude generated PR body"
            mock_llm.assert_called_once()
            mock_claude.assert_called_once()
    
    def test_pr_body_size_constraint_handling(self, claude_tasker_script, mock_git_repo):
        """Test handling of PR body size constraints (10,000 character limit)."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('builtins.open', mock_open()):
            
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test_output.txt'
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Large feature implementation", "body": "Complex feature with many components", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git diff main...HEAD' in cmd:
                    # Very large diff (simulated)
                    large_diff = "diff --git a/file.py b/file.py\n" + "+" + "x" * 50000  # Large diff
                    return Mock(returncode=0, stdout=large_diff, stderr="")
                elif 'command -v llm' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/llm", stderr="")
                elif 'llm' in cmd and 'chat' in cmd:
                    # LLM should produce concise output despite large input
                    concise_pr_body = """## Summary
Large feature implementation with 50+ files changed

## Key Changes
- Core architecture refactoring
- New API endpoints added
- Database schema updates
- Comprehensive test coverage

## Testing
- All tests pass
- Performance benchmarks met"""
                    return Mock(returncode=0, stdout=concise_pr_body, stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'), patch.dict('os.environ', {'CLAUDE_TASKER_AUTO_CLEANUP': '1'}):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should handle large context and produce concise output
            assert result.returncode == 0
    
    def test_multiple_pr_template_detection(self, claude_tasker_script, mock_git_repo):
        """Test detection of multiple PR template file formats."""
        # Create .github directory with multiple template formats
        github_dir = mock_git_repo / ".github"
        github_dir.mkdir(exist_ok=True)
        
        # Test priority: pull_request_template.md > PULL_REQUEST_TEMPLATE.md > others
        templates = [
            "pull_request_template.md",
            "PULL_REQUEST_TEMPLATE.md", 
            "pull_request_template.txt"
        ]
        
        for template_name in templates:
            template_file = github_dir / template_name
            template_file.write_text(f"# {template_name} Template\nTemplate content")
        
        with patch('subprocess.run') as mock_run:
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test templates", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'), patch.dict('os.environ', {'CLAUDE_TASKER_AUTO_CLEANUP': '1'}):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should detect template files (priority order)
            assert result.returncode == 0
            
            # Verify template files exist
            assert (github_dir / "pull_request_template.md").exists()
            assert (github_dir / "PULL_REQUEST_TEMPLATE.md").exists()
    
    def test_pr_body_claude_analysis_integration(self, claude_tasker_script, mock_git_repo):
        """Test integration of Claude analysis with PR body generation."""
        from src.claude_tasker.pr_body_generator import PRBodyGenerator
        from src.claude_tasker.github_client import IssueData
        
        generator = PRBodyGenerator()
        
        issue_data = IssueData(
            number=123,
            title="Integration test",
            body="Test integration functionality",
            labels=["feature"],
            url="https://github.com/test/repo/issues/123",
            author="testuser",
            state="open"
        )
        
        git_diff = "diff --git a/integration.py b/integration.py\n+integration code"
        branch_name = "feature/integration"
        commit_log = "abc123 Add integration feature"
        
        # Test full PR body generation pipeline
        with patch.object(generator, 'generate_with_llm', return_value="LLM generated comprehensive PR body with analysis") as mock_llm:
            
            result = generator.generate_pr_body(issue_data, git_diff, branch_name, commit_log)
            
            # Should integrate analysis successfully
            assert result == "LLM generated comprehensive PR body with analysis"
            mock_llm.assert_called_once()
            
            # Verify context was properly aggregated
            call_args = mock_llm.call_args[0]
            context = call_args[0]  # First argument to generate_with_llm is context
            
            assert context['issue']['title'] == "Integration test"
            assert context['changes']['branch'] == "feature/integration"
            assert context['stats']['files_modified'] >= 0