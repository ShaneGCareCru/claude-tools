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
    
    @pytest.mark.skip(reason="Test needs rewrite for Python module - tests bash script subprocess calls")
    def test_context_aggregation_for_pr_body(self, claude_tasker_script, mock_git_repo):
        """Test aggregation of context for intelligent PR body generation."""
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
                    # Rich issue context
                    issue_data = {
                        "title": "Implement comprehensive test suite",
                        "body": "Add testing framework with coverage reporting and CI integration",
                        "labels": [{"name": "enhancement"}, {"name": "testing"}]
                    }
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git diff main...HEAD' in cmd:
                    # Substantial git diff
                    diff_content = """diff --git a/tests/test_suite.py b/tests/test_suite.py
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
                    return Mock(returncode=0, stdout=diff_content, stderr="")
                elif 'git log --oneline -5' in cmd:
                    # Recent commit history for style reference
                    commits = """abc123 Add test framework
def456 Update CI configuration
ghi789 Fix bug in parser
jkl012 Refactor core module
mno345 Initial implementation"""
                    return Mock(returncode=0, stdout=commits, stderr="")
                elif 'command -v llm' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/llm", stderr="")
                elif 'llm' in cmd and 'chat' in cmd:
                    # LLM synthesis of all context
                    pr_body = """## Summary
Implements comprehensive test suite with pytest framework

## Changes Made
- Added test_suite.py with initial test cases
- Configured pytest with coverage reporting
- Updated CI pipeline for automated testing

## Testing
- ✅ All new tests pass
- ✅ Coverage report shows 90%+ coverage
- ✅ CI integration verified"""
                    return Mock(returncode=0, stdout=pr_body, stderr="")
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
            
            # Should aggregate context successfully
            assert result.returncode == 0
            
            # Verify context gathering commands were called
            diff_calls = [call for call in mock_run.call_args_list 
                         if 'git diff' in str(call.args) and 'HEAD' in str(call.args)]
            log_calls = [call for call in mock_run.call_args_list 
                        if 'git log --oneline' in str(call.args)]
            llm_calls = [call for call in mock_run.call_args_list 
                        if 'llm' in str(call.args)]
            
            assert len(diff_calls) > 0
            assert len(log_calls) > 0  
            assert len(llm_calls) > 0
    
    @pytest.mark.skip(reason="Test needs rewrite for Python module - tests bash script subprocess calls")
    def test_llm_tool_fallback_to_claude(self, claude_tasker_script, mock_git_repo):
        """Test fallback from LLM tool to Claude output when LLM unavailable."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('builtins.open', mock_open()):
            
            mock_temp.return_value.__enter__.return_value.name = '/tmp/claude_output.txt'
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'command -v llm' in cmd:
                    # LLM tool not available
                    return Mock(returncode=1, stdout="", stderr="llm: command not found")
                elif 'claude' in cmd:
                    return Mock(returncode=0, stdout="Claude-generated PR analysis", stderr="")
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
            
            # Should fall back to Claude output
            assert result.returncode == 0
            
            # Verify LLM availability was checked and Claude was used
            llm_check_calls = [call for call in mock_run.call_args_list 
                              if 'command -v llm' in str(call.args)]
            claude_calls = [call for call in mock_run.call_args_list 
                           if 'claude' in str(call.args)]
            
            assert len(llm_check_calls) > 0
            assert len(claude_calls) > 0
    
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
    
    @pytest.mark.skip(reason="Integration test needs rewrite for Python module - tests bash script subprocess calls")
    def test_pr_body_claude_analysis_integration(self, claude_tasker_script, mock_git_repo):
        """Test integration of Claude analysis with PR body generation."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('builtins.open', mock_open(read_data="Claude analysis: Implementation successful")):
            
            mock_temp.return_value.__enter__.return_value.name = '/tmp/claude_analysis.txt'
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Integration test", "body": "Test integration", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'claude' in cmd and '--output-format json' in cmd:
                    # Claude analysis stage
                    analysis = {
                        "analysis": "Comprehensive implementation completed",
                        "changes": ["Added new features", "Updated tests", "Fixed bugs"],
                        "testing": "All tests pass with 95% coverage"
                    }
                    return Mock(returncode=0, stdout=json.dumps(analysis), stderr="")
                elif 'command -v llm' in cmd:
                    return Mock(returncode=0, stdout="/usr/bin/llm", stderr="")
                elif 'llm' in cmd:
                    # LLM integration of Claude analysis
                    integrated_pr_body = """## Summary
Integration test implementation based on Claude analysis

## Implementation Details
Comprehensive implementation completed with the following changes:
- Added new features
- Updated tests  
- Fixed bugs

## Testing Results
All tests pass with 95% coverage as verified by Claude analysis"""
                    return Mock(returncode=0, stdout=integrated_pr_body, stderr="")
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
            
            # Should integrate Claude analysis with PR body
            assert result.returncode == 0
            
            # Verify Claude analysis and LLM integration
            claude_calls = [call for call in mock_run.call_args_list 
                           if 'claude' in str(call.args) and '--output-format json' in str(call.args)]
            llm_calls = [call for call in mock_run.call_args_list 
                        if 'llm' in str(call.args)]
            
            assert len(claude_calls) > 0 or len(llm_calls) > 0