# 🧪 Integration Testing Edge Cases

## 🎯 **Critical Edge Cases We Should Test**

### 1. **Network & API Failures**
```python
def test_github_api_rate_limit_handling():
    """Test behavior when GitHub API hits rate limits."""
    # Mock rate limit response from GitHub
    # Verify tool waits and retries appropriately
    
def test_github_api_timeout():
    """Test handling of GitHub API timeouts."""
    # Mock network timeouts
    # Verify graceful degradation
    
def test_claude_api_authentication_failure():
    """Test behavior when Claude CLI auth fails."""
    # Mock authentication failures
    # Verify error messages and recovery
```

### 2. **File System Edge Cases**
```python
def test_readonly_repository():
    """Test behavior in read-only repositories."""
    # Make repo read-only
    # Verify appropriate error handling
    
def test_insufficient_disk_space():
    """Test behavior when disk space is low."""
    # This could cause Claude execution to fail mid-stream
    
def test_special_characters_in_filenames():
    """Test with repos containing special characters."""
    # Unicode, spaces, emojis in filenames
    
def test_very_large_repository():
    """Test performance with large repositories."""
    # Repos with many files, large files, deep directories
```

### 3. **Git Repository States**
```python
def test_dirty_repository_state():
    """Test execution in repos with uncommitted changes."""
    # Should handle existing changes gracefully
    
def test_detached_head_state():
    """Test behavior in detached HEAD state."""
    # Common in CI environments
    
def test_merge_conflict_state():
    """Test behavior during merge conflicts."""
    # Should detect and handle appropriately
    
def test_repository_with_submodules():
    """Test repos containing git submodules."""
    # Submodules can complicate change detection
    
def test_shallow_clone_repository():
    """Test with shallow git clones."""
    # Common in CI, limited history
```

### 4. **Claude CLI Edge Cases**
```python
def test_claude_cli_version_compatibility():
    """Test with different Claude CLI versions."""
    # Different versions may have different flags
    
def test_claude_token_expiration():
    """Test behavior when Claude auth token expires."""
    # Should provide clear error messages
    
def test_claude_prompt_size_limits():
    """Test with very large prompts."""
    # May hit token limits or timeout
    
def test_claude_concurrent_execution():
    """Test multiple claude-tasker instances."""
    # File locking, race conditions
```

### 5. **Branch Management Edge Cases**
```python
def test_branch_name_conflicts():
    """Test when generated branch names already exist."""
    # issue-123-timestamp conflicts
    
def test_protected_branch_scenarios():
    """Test repos with protected main branches."""
    # Should handle push restrictions
    
def test_orphaned_branches():
    """Test cleanup of failed execution branches."""
    # Branches created but PRs never made
    
def test_stale_remote_branches():
    """Test repos with many stale remote branches."""
    # Performance and naming issues
```

### 6. **GitHub Issue/PR Edge Cases**
```python
def test_closed_issue_processing():
    """Test attempting to process closed issues."""
    # Should skip or handle appropriately
    
def test_locked_issue_processing():
    """Test processing locked issues/discussions."""
    # Can't comment on locked issues
    
def test_draft_pr_review():
    """Test reviewing draft PRs."""
    # Different behavior expected
    
def test_private_repository_access():
    """Test with private repos and limited access."""
    # Permission edge cases
```

### 7. **Error Recovery & Cleanup**
```python
def test_partial_execution_recovery():
    """Test recovery from partial execution failures."""
    # Claude starts executing but crashes mid-way
    
def test_cleanup_after_failure():
    """Test cleanup of temporary files/branches after failure."""
    # Should not leave repo in dirty state
    
def test_interrupt_signal_handling():
    """Test Ctrl+C during execution."""
    # Should cleanup gracefully
```

### 8. **Platform-Specific Issues**
```python
def test_windows_path_handling():
    """Test on Windows with different path separators."""
    # Windows vs Unix path differences
    
def test_line_ending_handling():
    """Test with mixed line endings (CRLF vs LF)."""
    # Git autocrlf settings impact
    
def test_case_sensitive_filesystems():
    """Test filename case sensitivity differences."""
    # macOS case-insensitive vs Linux case-sensitive
```

### 9. **Scale & Performance Edge Cases**
```python
def test_large_issue_description():
    """Test with very large issue descriptions."""
    # May cause prompt generation issues
    
def test_many_simultaneous_executions():
    """Test resource usage with multiple processes."""
    # Memory, file handles, API limits
    
def test_execution_timeout_handling():
    """Test when Claude execution takes very long."""
    # Should timeout gracefully
```

---

## 📊 **Most Critical Edge Cases to Implement**

### **Priority 1: High Impact, Likely to Occur**

1. **Dirty Repository State**
2. **Branch Name Conflicts**  
3. **Claude Token/Auth Issues**
4. **GitHub API Rate Limits**
5. **Partial Execution Recovery**

### **Priority 2: Medium Impact, Possible**

1. **Large Prompt Handling**
2. **Protected Branch Scenarios**
3. **Concurrent Execution**
4. **Network Timeouts**
5. **File Permission Issues**

### **Priority 3: Low Impact, Edge Cases**

1. **Platform-Specific Paths**
2. **Submodule Repositories**  
3. **Very Large Repositories**
4. **Special Character Handling**
5. **Detached HEAD States**

---

## 🧪 **Example Critical Edge Case Tests**

### 1. **Dirty Repository Handling**
```python
def test_dirty_repository_execution(self, real_git_repo):
    """Test execution in repo with uncommitted changes."""
    # Create uncommitted changes
    test_file = real_git_repo / "existing.txt" 
    test_file.write_text("uncommitted content")
    
    workspace_manager = WorkspaceManager(str(real_git_repo))
    
    # Should detect existing changes
    assert workspace_manager.has_changes_to_commit()
    
    # Execute claude-tasker
    result = workflow.process_single_issue(1, prompt_only=False)
    
    # Should handle existing changes appropriately
    # Either: stash, commit separately, or error clearly
    assert result.success or "uncommitted changes" in result.message
```

### 2. **Branch Conflict Resolution**
```python
def test_branch_name_conflict_resolution(self, real_git_repo):
    """Test when generated branch name already exists."""
    # Create branch that would conflict
    timestamp = int(time.time())
    branch_name = f"issue-7-{timestamp}"
    
    subprocess.run(['git', 'checkout', '-b', branch_name], cwd=real_git_repo)
    subprocess.run(['git', 'checkout', 'main'], cwd=real_git_repo)
    
    # Now run claude-tasker for same issue
    result = workflow.process_single_issue(7, prompt_only=False)
    
    # Should create different branch name or handle conflict
    branches = subprocess.run(
        ['git', 'branch'], cwd=real_git_repo, capture_output=True, text=True
    ).stdout
    
    # Should have created a different branch name
    assert result.success
    assert result.branch_name != branch_name
```

### 3. **Claude Auth Failure Handling**
```python
def test_claude_auth_failure_handling():
    """Test behavior when Claude CLI auth fails."""
    with patch('subprocess.run') as mock_run:
        # Mock authentication failure
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Authentication failed"
        
        result = prompt_builder._execute_llm_tool(
            'claude', 'test prompt', execute_mode=True
        )
        
        # Should return None and log error appropriately
        assert result is None
        # Should have clear error message for user
```

### 4. **GitHub Rate Limit Handling** 
```python  
def test_github_rate_limit_retry():
    """Test retry logic for GitHub API rate limits."""
    with patch.object(github_client, '_make_request') as mock_request:
        # First call hits rate limit
        mock_request.side_effect = [
            requests.exceptions.HTTPError("403 rate limit exceeded"),
            {"title": "Test Issue", "body": "Test", "labels": []}
        ]
        
        # Should retry and succeed
        issue = github_client.fetch_issue(123)
        assert issue.title == "Test Issue"
        assert mock_request.call_count == 2
```

### 5. **Partial Execution Recovery**
```python
def test_partial_execution_cleanup(self, real_git_repo):
    """Test cleanup after partial execution failure."""
    # Simulate Claude starting but crashing
    with patch('subprocess.run') as mock_run:
        def side_effect(*args, **kwargs):
            if 'claude' in args[0] and '--permission-mode' in args[0]:
                # Simulate Claude crashing mid-execution
                raise subprocess.TimeoutExpired(args[0], 180)
            return Mock(returncode=0, stdout="", stderr="")
        
        mock_run.side_effect = side_effect
        
        workspace_manager = WorkspaceManager(str(real_git_repo))
        workflow = WorkflowLogic(workspace_manager=workspace_manager)
        
        # Should fail gracefully
        result = workflow.process_single_issue(1, prompt_only=False)
        
        assert not result.success
        # Should not leave repo in dirty state
        assert not workspace_manager.has_changes_to_commit()
```

---

## 🎯 **Integration Test Strategy**

### **Test Environment Matrix**
```bash
# Different environments to test
1. Clean repo (current tests)
2. Dirty repo with uncommitted changes
3. Repo with existing feature branches  
4. Large repo (1000+ files)
5. Repo with special characters
6. Private repo (auth required)
7. Forked repo (different permissions)
```

### **Failure Mode Categories**
```bash
1. **Graceful Degradation** - Tool handles failure and reports clearly
2. **Automatic Recovery** - Tool retries and succeeds  
3. **Clean Failure** - Tool fails but leaves no artifacts
4. **User Guidance** - Tool provides actionable error messages
```

These edge cases would catch real-world failures that could occur in production environments with varied repository states, network conditions, and user configurations.