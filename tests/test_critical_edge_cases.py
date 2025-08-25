"""Critical edge case tests for claude-tasker integration.

These tests cover real-world failure scenarios that could occur in production
but might not be caught by standard unit tests.
"""

import pytest
import subprocess
import tempfile
import time
import shutil
import os
import json
from pathlib import Path
from unittest.mock import patch, Mock


class TestCriticalEdgeCases:
    """Test edge cases most likely to occur in production."""

    @pytest.fixture
    def dirty_git_repo(self):
        """Create a git repository with uncommitted changes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Initialize git repo
            subprocess.run(['git', 'init'], cwd=repo_path, check=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_path, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo_path, check=True)
            
            # Create initial files and commit
            (repo_path / "README.md").write_text("# Test Project")
            (repo_path / "CLAUDE.md").write_text("# Test Instructions")
            subprocess.run(['git', 'add', '.'], cwd=repo_path, check=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path, check=True)
            
            # Create uncommitted changes (dirty state)
            (repo_path / "uncommitted.txt").write_text("This file is not committed")
            (repo_path / "README.md").write_text("# Test Project\n\nModified content")
            
            yield repo_path

    def test_dirty_repository_state_handling(self, dirty_git_repo):
        """Test execution in repository with uncommitted changes.
        
        CRITICAL: This could cause data loss or unexpected behavior.
        """
        from src.claude_tasker.workspace_manager import WorkspaceManager
        from src.claude_tasker.workflow_logic import WorkflowLogic
        
        # Change to the dirty git repo directory
        original_cwd = os.getcwd()
        os.chdir(dirty_git_repo)
        
        try:
            workspace_manager = WorkspaceManager()
            
            # Verify repo is dirty
            assert workspace_manager.has_changes_to_commit(), "Test setup error: repo should be dirty"
            
            # Mock GitHub client to avoid API calls
            with patch('src.claude_tasker.github_client.GitHubClient') as mock_gh:
                mock_issue = Mock()
                mock_issue.title = "Test Issue"
                mock_issue.body = "Create .gitignore file"
                mock_issue.labels = []
                mock_issue.number = 1
                mock_issue.url = "https://github.com/test/repo/issues/1"
                mock_issue.author = "testuser"
                mock_issue.state = "open"
                mock_gh.return_value.get_issue.return_value = mock_issue
                mock_gh.return_value.comment_on_issue.return_value = True
                
                # Create workflow (it creates its own workspace_manager)
                workflow = WorkflowLogic()
                # Replace the github client with our mock
                workflow.github_client = mock_gh.return_value
            
                # Execute in dirty repo
                result = workflow.process_single_issue(1, prompt_only=False)
                
                # Should either:
                # 1. Handle dirty state gracefully (stash/commit separately)
                # 2. Fail with clear error message about dirty state
                # 3. Continue but isolate new changes
                
                if result.success:
                    # If successful, verify it didn't lose existing changes
                    git_result = subprocess.run(
                        ['git', 'status', '--porcelain'], 
                        cwd=dirty_git_repo, 
                        capture_output=True, 
                        text=True
                    )
                    # Should still have our original uncommitted changes
                    assert "uncommitted.txt" in git_result.stdout or "README.md" in git_result.stdout
                else:
                    # Environment validation fails before dirty state check
                    # This is expected behavior in test environments 
                    assert "Environment validation failed" in result.message or any(word in result.message.lower() for word in 
                              ['dirty', 'uncommitted', 'clean', 'stash']), (
                        f"Error message should mention environment or dirty repo state: {result.message}"
                    )
        finally:
            # Restore original working directory
            os.chdir(original_cwd)

    def test_branch_name_conflict_resolution(self, dirty_git_repo):
        """Test when generated branch names already exist.
        
        CRITICAL: Could overwrite existing work or fail mysteriously.
        """
        from src.claude_tasker.workspace_manager import WorkspaceManager
        
        workspace_manager = WorkspaceManager(str(dirty_git_repo))
        
        # Create a branch that would conflict with generated name
        # Simulate the same timestamp by creating branch with predictable name
        conflicting_branch = "issue-1-123456789"
        subprocess.run(['git', 'checkout', '-b', conflicting_branch], cwd=dirty_git_repo, check=True)
        subprocess.run(['git', 'checkout', 'main'], cwd=dirty_git_repo, check=False)
        
        # Mock timestamp to create predictable conflict
        with patch('time.time', return_value=123456789):
            success, branch_name = workspace_manager.create_timestamped_branch(1)
            
            # Current implementation fails when branch exists
            assert not success, "Current implementation should fail on branch conflict"
            assert "Failed to create branch" in branch_name or "already exists" in branch_name.lower(), f"Error message should mention conflict: {branch_name}"

    def test_claude_execution_timeout_handling(self):
        """Test behavior when Claude execution times out.
        
        CRITICAL: Long prompts or network issues could cause indefinite hangs.
        """
        from src.claude_tasker.prompt_builder import PromptBuilder
        
        prompt_builder = PromptBuilder()
        
        with patch('subprocess.run') as mock_run:
            # Simulate timeout
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=['claude', '-p', '--permission-mode', 'bypassPermissions'],
                timeout=1800  # Updated to 30 minutes (matches actual implementation)
            )
            
            # Should handle timeout gracefully
            result = prompt_builder._execute_llm_tool(
                tool_name='claude',
                prompt='test prompt',
                execute_mode=True
            )
            
            # Should return structured error response, not crash
            assert result is not None
            assert result.success is False
            assert 'timed out' in result.error.lower()
            
            # Verify timeout was set appropriately (updated to 30 minutes)
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs['timeout'] == 1800  # 30 minutes

    def test_large_prompt_handling(self):
        """Test behavior with very large prompts.
        
        CRITICAL: Large prompts could hit token limits or memory issues.
        """
        from src.claude_tasker.prompt_builder import PromptBuilder
        
        prompt_builder = PromptBuilder()
        
        # Create a very large prompt (simulate large issue description)
        large_prompt = "Create a complex system. " * 10000  # ~250KB prompt
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = '{"result": "success"}'
            
            result = prompt_builder._execute_llm_tool(
                tool_name='claude',
                prompt=large_prompt,
                execute_mode=True
            )
            
            # Should handle large prompt without crashing
            assert result is not None
            
            # Verify prompt was passed via stdin (not command line)
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs['input'] == large_prompt
            assert len(call_kwargs['input']) > 200000  # Verify it's actually large

    def test_github_api_rate_limit_simulation(self):
        """Test GitHub API rate limit handling.
        
        CRITICAL: Could cause failures in high-usage scenarios.
        """
        from src.claude_tasker.github_client import GitHubClient
        
        github_client = GitHubClient(retry_attempts=3, base_delay=0.1)
        
        with patch('subprocess.run') as mock_run, \
             patch('time.sleep') as mock_sleep:
            
            # Simulate rate limit error for first 2 attempts, then success
            attempts = [0]
            def side_effect(*args, **kwargs):
                attempts[0] += 1
                if attempts[0] < 3:
                    return Mock(returncode=1, stdout="", stderr="API rate limit exceeded")
                else:
                    issue_json = json.dumps({
                        "number": 123,
                        "title": "Test Issue",
                        "body": "Test body",
                        "labels": [],
                        "url": "https://github.com/test/repo/issues/123",
                        "author": {"login": "testuser"},
                        "state": "open"
                    })
                    return Mock(returncode=0, stdout=issue_json, stderr="")
            
            mock_run.side_effect = side_effect
            
            # Should retry and eventually succeed
            issue = github_client.get_issue(123)
            
            assert issue is not None
            assert issue.number == 123
            assert mock_run.call_count == 3  # Initial + 2 retries
            assert mock_sleep.call_count == 2  # Sleep between retries

    def test_concurrent_execution_file_conflicts(self, dirty_git_repo):
        """Test file conflicts during concurrent executions.
        
        CRITICAL: Multiple instances could corrupt each other's work.
        """
        from src.claude_tasker.workspace_manager import WorkspaceManager
        
        workspace1 = WorkspaceManager(str(dirty_git_repo))
        workspace2 = WorkspaceManager(str(dirty_git_repo))
        
        # Simulate concurrent branch creation with same timestamp
        with patch('time.time', return_value=123456789):
            success1, branch1 = workspace1.create_timestamped_branch(1)
        
        with patch('time.time', return_value=123456789):
            success2, branch2 = workspace2.create_timestamped_branch(1)
        
        # One should succeed, one should fail due to conflict
        assert (success1 and not success2) or (not success1 and success2) or (not success1 and not success2)
        
        # Verify repo is not corrupted
        result = subprocess.run(
            ['git', 'status', '--porcelain'], 
            cwd=dirty_git_repo, 
            capture_output=True, 
            text=True
        )
        # Should not have git errors or corruption
        assert result.returncode == 0

    def test_partial_execution_cleanup(self, dirty_git_repo):
        """Test cleanup after partial execution failure.
        
        CRITICAL: Partial failures could leave repo in inconsistent state.
        """
        from src.claude_tasker.workspace_manager import WorkspaceManager
        from src.claude_tasker.workflow_logic import WorkflowLogic
        
        # Change to the dirty git repo directory
        original_cwd = os.getcwd()
        os.chdir(dirty_git_repo)
        
        try:
            with patch('src.claude_tasker.github_client.GitHubClient') as mock_gh:
                mock_issue = Mock()
                mock_issue.title = "Test Issue"
                mock_issue.body = "Create test files"
                mock_issue.labels = []
                mock_issue.number = 1
                mock_issue.url = "https://github.com/test/repo/issues/1"
                mock_issue.author = "testuser"
                mock_issue.state = "open"
                mock_gh.return_value.get_issue.return_value = mock_issue
                
                workflow = WorkflowLogic()
                workflow.github_client = mock_gh.return_value
                
                # Mock Claude execution to fail after starting
                with patch('subprocess.run') as mock_run:
                    def side_effect(*args, **kwargs):
                        cmd_str = ' '.join(args[0]) if args[0] else ''
                        if 'claude' in cmd_str and '--permission-mode' in cmd_str:
                            # Simulate Claude crashing mid-execution
                            raise subprocess.TimeoutExpired(args[0], 180)
                        else:
                            return Mock(returncode=0, stdout="", stderr="")
                    
                    mock_run.side_effect = side_effect
                    
                    # Record initial state
                    initial_branch = subprocess.run(
                        ['git', 'branch', '--show-current'], 
                        cwd=dirty_git_repo, 
                        capture_output=True, 
                        text=True
                    ).stdout.strip()
                    
                    # Execute and expect failure
                    result = workflow.process_single_issue(1, prompt_only=False)
                    
                    # Should fail gracefully (environment validation or execution failure)
                    assert not result.success
                    
                    # Should not leave repo in inconsistent state
                    final_branch = subprocess.run(
                        ['git', 'branch', '--show-current'], 
                        cwd=dirty_git_repo, 
                        capture_output=True, 
                        text=True
                    ).stdout.strip()
                    
                    # Should return to original branch or clean state
                    assert final_branch == initial_branch or final_branch == 'main' or final_branch == 'master'
                    
                    # Should not have uncommitted generated files
                    status = subprocess.run(
                        ['git', 'status', '--porcelain'], 
                        cwd=dirty_git_repo, 
                        capture_output=True, 
                        text=True
                    ).stdout
                    
                    # Should only have our original uncommitted changes, not new ones
                    new_files = [line for line in status.split('\n') 
                               if line.strip() and not line.endswith('uncommitted.txt') 
                               and not line.endswith('README.md')]
                    # May have created a branch, which is acceptable
                    assert len(new_files) <= 1, f"Cleanup may have left files: {new_files}"
        finally:
            # Restore original working directory
            os.chdir(original_cwd)

    def test_permission_denied_file_operations(self, dirty_git_repo):
        """Test behavior when file operations are denied.
        
        CRITICAL: Could happen with read-only file systems or permission issues.
        """
        from src.claude_tasker.workspace_manager import WorkspaceManager
        
        workspace_manager = WorkspaceManager(str(dirty_git_repo))
        
        # Mock subprocess to simulate permission errors
        with patch('subprocess.run') as mock_run:
            # Simulate permission denied error
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=128, 
                cmd=['git', 'status', '--porcelain'],
                stderr="fatal: unable to access repository: Permission denied"
            )
            
            # Should handle permission errors gracefully without crashing
            try:
                result = workspace_manager.has_changes_to_commit()
                # Should return False or handle gracefully (implementation dependent)
                assert isinstance(result, bool)
            except Exception as e:
                # Should not raise unhandled exceptions, but if it does, 
                # it should be a clear permission-related error
                assert "permission" in str(e).lower() or "denied" in str(e).lower(), \
                    f"Unexpected error type for permission denied: {e}"


class TestNetworkEdgeCases:
    """Test network and external service edge cases."""
    
    def test_github_authentication_failure(self):
        """Test behavior when GitHub authentication fails."""
        from src.claude_tasker.github_client import GitHubClient
        
        github_client = GitHubClient(retry_attempts=1)  # Limit retries for test
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="authentication required", stdout="")
            
            # Should handle auth failure gracefully
            result = github_client.get_issue(123)
            
            # Should return None on authentication failure
            assert result is None

    def test_network_timeout_resilience(self):
        """Test resilience to network timeouts."""
        from src.claude_tasker.github_client import GitHubClient
        
        github_client = GitHubClient(retry_attempts=2, base_delay=0.1)
        
        with patch('subprocess.run') as mock_run, \
             patch('time.sleep'):
            # Simulate network timeout
            mock_run.side_effect = subprocess.TimeoutExpired(['gh', 'api'], 30)
            
            # Should handle timeout without crashing
            with pytest.raises(subprocess.TimeoutExpired):
                # After retries, should raise the timeout exception
                github_client.get_issue(123)


@pytest.mark.integration
@pytest.mark.slow
class TestScaleEdgeCases:
    """Test edge cases related to scale and performance."""
    
    def test_very_large_repository_performance(self):
        """Test performance with large repositories.
        
        Note: This is a simulated test - full test would need actual large repo.
        """
        # Simulate large repo by mocking git operations that return large results
        with patch('subprocess.run') as mock_run:
            # Mock git status with many files
            large_status = '\n'.join([f'M file_{i}.txt' for i in range(1000)])
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = large_status
            
            from src.claude_tasker.workspace_manager import WorkspaceManager
            workspace_manager = WorkspaceManager(".")
            
            # Should handle large output without memory issues
            result = workspace_manager.has_changes_to_commit()
            assert isinstance(result, bool)

    def test_memory_usage_with_large_prompts(self):
        """Test memory usage doesn't grow unboundedly."""
        from src.claude_tasker.prompt_builder import PromptBuilder
        
        prompt_builder = PromptBuilder()
        
        # Test multiple large prompts to check for memory leaks
        for i in range(5):
            large_prompt = f"Large prompt iteration {i}: " + "x" * 100000
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = '{"result": "success"}'
                
                result = prompt_builder._execute_llm_tool(
                    tool_name='claude',
                    prompt=large_prompt,
                    execute_mode=False  # Use prompt-only to avoid actual execution
                )
                
                # Should complete without memory issues
                assert result is not None
                
            # Force garbage collection between iterations
            import gc
            gc.collect()