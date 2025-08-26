# 🎯 Integration Testing Edge Case Priorities

## 🚨 **CRITICAL (Must Test) - High Impact, High Probability**

### 1. **Dirty Repository State** 
```python
test_dirty_repository_state_handling()
```
**Why Critical:** Users often have uncommitted changes. Could cause data loss.
**Impact:** HIGH - Could overwrite user work
**Probability:** HIGH - Very common in development

### 2. **Branch Name Conflicts**
```python
test_branch_name_conflict_resolution()
```
**Why Critical:** Timestamp-based naming can collide in CI/automation.
**Impact:** MEDIUM - Could fail mysteriously or overwrite branches
**Probability:** HIGH - Common in CI environments

### 3. **Partial Execution Cleanup**
```python
test_partial_execution_cleanup()
```
**Why Critical:** Network issues, Ctrl+C, crashes leave repo dirty.
**Impact:** HIGH - Corrupted repository state
**Probability:** MEDIUM - Happens during development/testing

### 4. **Claude CLI Authentication/Permission Issues**
```python
test_claude_execution_timeout_handling()
test_permission_denied_file_operations()
```
**Why Critical:** Auth tokens expire, file system restrictions exist.
**Impact:** HIGH - Tool completely broken until resolved
**Probability:** HIGH - Different environments have different restrictions

---

## ⚠️ **HIGH PRIORITY - Medium Impact, Likely to Occur**

### 5. **Large Prompt Handling**
```python
test_large_prompt_handling()
```
**Why Important:** Large issue descriptions or complex repositories.
**Impact:** MEDIUM - Tool fails on complex tasks
**Probability:** MEDIUM - Happens with detailed issues

### 6. **GitHub API Rate Limits**
```python
test_github_api_rate_limit_simulation()
```
**Why Important:** Batch processing or high-usage scenarios.
**Impact:** MEDIUM - Temporary failures, but breaks automation
**Probability:** MEDIUM - Happens in CI or heavy usage

### 7. **Network Timeout Resilience**
```python
test_network_timeout_resilience()
```
**Why Important:** Poor connectivity, corporate networks, CI environments.
**Impact:** MEDIUM - Intermittent failures
**Probability:** MEDIUM - Network issues are common

---

## 📋 **MEDIUM PRIORITY - Lower Impact or Probability**

### 8. **Concurrent Execution**
```python
test_concurrent_execution_file_conflicts()
```
**Why Useful:** Multiple developers, CI parallelization.
**Impact:** LOW - Usually has workarounds
**Probability:** LOW - Most teams don't run simultaneously

### 9. **Scale Issues**
```python
test_very_large_repository_performance()
test_memory_usage_with_large_prompts()
```
**Why Useful:** Performance optimization for large projects.
**Impact:** LOW - Tool works but slowly
**Probability:** LOW - Most projects aren't huge

---

## 📊 **Implementation Recommendations**

### **Phase 1: Immediate (Ship Blockers)**
Focus on critical edge cases that could cause data loss or major failures:

```bash
# Run these tests BEFORE releasing fixes
pytest tests/test_critical_edge_cases.py::TestCriticalEdgeCases::test_dirty_repository_state_handling -v
pytest tests/test_critical_edge_cases.py::TestCriticalEdgeCases::test_branch_name_conflict_resolution -v  
pytest tests/test_critical_edge_cases.py::TestCriticalEdgeCases::test_partial_execution_cleanup -v
```

### **Phase 2: Near-term (Stability)**
Add resilience for common failure modes:

```bash
pytest tests/test_critical_edge_cases.py::TestCriticalEdgeCases::test_claude_execution_timeout_handling -v
pytest tests/test_critical_edge_cases.py::TestCriticalEdgeCases::test_large_prompt_handling -v
pytest tests/test_critical_edge_cases.py::TestNetworkEdgeCases -v
```

### **Phase 3: Long-term (Polish)**
Performance and edge platform scenarios:

```bash
pytest tests/test_critical_edge_cases.py::TestScaleEdgeCases -v
```

---

## 🔍 **Edge Cases We Discovered Are Missing**

### **From Our Bug Hunt, We Now Know To Test:**

1. **Execution Mode Validation** ✅ (We added this)
   - Parameter propagation through the call chain
   - Real vs mocked execution verification

2. **Permission Mode Handling** ✅ (We found this issue)  
   - `--permission-mode bypassPermissions` requirement
   - Claude CLI hanging on permission requests

3. **Git Change Detection Accuracy** ✅ (We tested this)
   - Untracked files detection  
   - Staged vs unstaged change differentiation

### **New Edge Cases We Should Add:**

4. **Prompt Content vs File Path Bug** ⚠️ (We fixed but didn't test)
   - Ensure LLM tool returns content, not file paths
   - Stdin vs file-based prompt passing validation

5. **Two-Stage Execution Pipeline** ⚠️ (Critical integration)
   - Meta-prompt generation works
   - Optimized prompt execution actually runs
   - Stage 1 → Stage 2 → Stage 3 flow validation

---

## 🧪 **Quick Test to Add for Our Specific Bug**

```python
def test_execute_mode_actually_calls_claude():
    """Test that execute_mode=True actually calls Claude, not just generates prompts.
    
    This is the EXACT test that would have caught our bug.
    """
    from src.claude_tasker.prompt_builder import PromptBuilder
    
    prompt_builder = PromptBuilder()
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Claude execution completed"
        
        # Test prompt-only mode
        result_prompt_only = prompt_builder.execute_two_stage_prompt(
            task_type="test",
            task_data={"prompt": "test"},
            claude_md_content="# Test",
            prompt_only=True
        )
        
        # Should NOT call Claude for execution in prompt-only mode
        claude_execution_calls = [
            call for call in mock_run.call_args_list 
            if any('claude' in str(arg) and '--permission-mode' in str(arg) 
                  for arg in call.args[0] if isinstance(arg, (str, list)))
        ]
        assert len(claude_execution_calls) == 0, "Prompt-only should not execute Claude"
        
        # Reset mock
        mock_run.reset_mock()
        
        # Test execution mode
        result_execution = prompt_builder.execute_two_stage_prompt(
            task_type="test", 
            task_data={"prompt": "test"},
            claude_md_content="# Test",
            prompt_only=False  # Should execute Claude
        )
        
        # Should call Claude for execution with proper flags
        claude_execution_calls = [
            call for call in mock_run.call_args_list 
            if any('claude' in str(arg) and '--permission-mode' in str(arg)
                  for arg in (call.args[0] if call.args else []))
        ]
        
        # This assertion would have FAILED with our original bug
        assert len(claude_execution_calls) > 0, (
            "CRITICAL BUG: execute_mode=False did not actually call Claude for execution!"
        )
        
        # Verify correct flags were used
        claude_call = claude_execution_calls[0] 
        assert '--permission-mode' in claude_call.args[0]
        assert 'bypassPermissions' in claude_call.args[0]
```

---

## 🎯 **Most Valuable Edge Cases**

Based on our debugging experience, **the most valuable edge cases to test are those that involve the boundary between our code and external tools**:

1. **Real tool integration** (Claude CLI, git, gh CLI)
2. **File system state changes** (creation, modification, deletion)  
3. **Process execution and error handling** (timeouts, failures, cleanup)
4. **Repository state management** (branches, commits, dirty state)

These are the areas where unit test mocks can't catch real-world integration failures.

The lesson: **Focus edge case testing on integration boundaries, not internal logic** - that's where the highest-value bugs hide.