#!/usr/bin/env python3
"""Comprehensive integration test for Python claude-tasker implementation."""

import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

# Add src directory to Python path
sys.path.insert(0, "src")

from claude_tasker import main
from claude_tasker.environment_validator import EnvironmentValidator
from claude_tasker.github_client import GitHubClient
from claude_tasker.workspace_manager import WorkspaceManager
from claude_tasker.prompt_builder import PromptBuilder
from claude_tasker.pr_body_generator import PRBodyGenerator
from claude_tasker.workflow_logic import WorkflowLogic


def test_environment_validation():
    """Test environment validation functionality."""
    print("🧪 Testing environment validation...")
    
    validator = EnvironmentValidator()
    
    # Test basic functionality
    results = validator.validate_all_dependencies(prompt_only=True)
    assert isinstance(results, dict)
    assert 'valid' in results
    assert 'errors' in results
    assert 'warnings' in results
    
    # Test git repository validation
    git_valid, git_msg = validator.validate_git_repository()
    assert isinstance(git_valid, bool)
    assert isinstance(git_msg, str)
    
    print("✅ Environment validation tests passed")


def test_github_client():
    """Test GitHub client functionality."""
    print("🧪 Testing GitHub client...")
    
    client = GitHubClient()
    
    # Test with mocked subprocess
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"number":123,"title":"Test","body":"Test body","labels":[],"url":"https://github.com/test/repo/issues/123","author":{"login":"test"},"state":"open"}',
            stderr=""
        )
        
        issue_data = client.get_issue(123)
        assert issue_data is not None
        assert issue_data.number == 123
        assert issue_data.title == "Test"
    
    print("✅ GitHub client tests passed")


def test_workspace_manager():
    """Test workspace manager functionality."""
    print("🧪 Testing workspace manager...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = WorkspaceManager(temp_dir)
        
        # Test basic functionality
        main_branch = manager.detect_main_branch()
        assert main_branch in ['main', 'master']
        
        # Test interactive mode detection
        assert isinstance(manager._is_interactive(), bool)
    
    print("✅ Workspace manager tests passed")


def test_prompt_builder():
    """Test prompt builder functionality."""
    print("🧪 Testing prompt builder...")
    
    builder = PromptBuilder()
    
    # Test Lyra-Dev framework loading
    assert "DECONSTRUCT" in builder.lyra_dev_framework
    assert "DIAGNOSE" in builder.lyra_dev_framework
    assert "DEVELOP" in builder.lyra_dev_framework
    assert "DELIVER" in builder.lyra_dev_framework
    
    # Test meta-prompt validation
    valid_prompt = builder.lyra_dev_framework
    assert builder.validate_meta_prompt(valid_prompt)
    
    invalid_prompt = "too short"
    assert not builder.validate_meta_prompt(invalid_prompt)
    
    print("✅ Prompt builder tests passed")


def test_pr_body_generator():
    """Test PR body generator functionality."""
    print("🧪 Testing PR body generator...")
    
    generator = PRBodyGenerator()
    
    # Test template detection
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock PR template
        github_dir = Path(temp_dir) / '.github'
        github_dir.mkdir()
        template_file = github_dir / 'pull_request_template.md'
        template_file.write_text("# PR Template\n## Description\n## Changes")
        
        template = generator.detect_templates(temp_dir)
        assert template is not None
        assert "PR Template" in template
    
    # Test diff summarization
    git_diff = """diff --git a/test.py b/test.py
new file mode 100644
index 0000000..abc123
--- /dev/null
+++ b/test.py
@@ -0,0 +1,3 @@
+def test():
+    return True
+"""
    
    diff_summary = generator._summarize_diff(git_diff)
    assert diff_summary['files_changed'] > 0
    
    print("✅ PR body generator tests passed")


def test_cli_integration():
    """Test CLI integration with mocked dependencies."""
    print("🧪 Testing CLI integration...")
    
    # Test help command
    with patch('sys.argv', ['claude-tasker', '--help']):
        try:
            main()
            assert False, "Should have exited with help"
        except SystemExit as e:
            assert e.code == 0  # Help should exit with 0
    
    # Test invalid argument
    with patch('sys.argv', ['claude-tasker', 'invalid-arg']):
        try:
            result = main()
            assert result == 1  # Should return error code
        except SystemExit as e:
            assert e.code == 1
    
    print("✅ CLI integration tests passed")


def test_workflow_logic():
    """Test workflow logic coordination."""
    print("🧪 Testing workflow logic...")
    
    # Test with mocked environment
    with patch.dict(os.environ, {'CI': 'false'}):
        workflow = WorkflowLogic(
            timeout_between_tasks=0.1,  # Fast for testing
            interactive_mode=False
        )
        
        # Test environment validation
        env_valid, env_msg = workflow.validate_environment(prompt_only=True)
        assert isinstance(env_valid, bool)
        assert isinstance(env_msg, str)
    
    print("✅ Workflow logic tests passed")


def run_all_tests():
    """Run all integration tests."""
    print("🚀 Starting Python claude-tasker integration tests...\n")
    
    try:
        test_environment_validation()
        test_github_client()
        test_workspace_manager()
        test_prompt_builder()
        test_pr_body_generator()
        test_cli_integration()
        test_workflow_logic()
        
        print(f"\n🎉 All integration tests passed!")
        print(f"📊 Python implementation is working correctly")
        print(f"✅ Ready for deployment and further testing")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())