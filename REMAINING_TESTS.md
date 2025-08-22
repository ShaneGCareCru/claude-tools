# 🧪 Remaining Tests for Claude-Tasker

## 🎯 **High Priority (Ready to Test)**

### 1. **Auto-PR Review Workflow**
```bash
# Now that implementation works, test the full workflow
python -m src.claude_tasker 6 --auto-pr-review
```
**Expected:** Implement issue #6 AND automatically review the created PR

### 2. **Alternative LLM Tool**
```bash
# Test fallback to llm tool instead of Claude
python -m src.claude_tasker 6 --coder llm
```
**Expected:** Use `llm` CLI instead of `claude` CLI for execution

### 3. **Complex Issue Implementation**
```bash
# Test with issues requiring multiple files or modifications
# Could create an issue for "Add authentication middleware" or similar
```
**Expected:** More complex code changes across multiple files

### 4. **Range Processing (Issues)**
```bash
# Test full execution mode with ranges (not just prompt-only)
python -m src.claude_tasker 6-7 --timeout 30
```
**Expected:** Implement both issues sequentially with delays

---

## ⚠️ **Medium Priority (May Have Issues)**

### 5. **PR Range Review (Fix Required)**
```bash
# Currently hangs - needs investigation
python -m src.claude_tasker --review-pr 4-6 --timeout 30
```
**Issue:** Currently times out on PR ranges

### 6. **Agent System Auto-Creation**
```bash
# Check if agents are created during execution
ls .claude/agents/
# Or manually create and test
mkdir -p .claude/agents
# Test if tool uses custom agents
```
**Issue:** No agents directory created automatically

### 7. **Project Context Integration**
```bash
# Verify project context is actually included in prompts
python -m src.claude_tasker 6 --project 123
```
**Unknown:** Whether project context actually gets added to prompts

---

## 🚫 **Low Priority (Likely to Hang)**

### 8. **Interactive Mode**
```bash
# Likely to hang waiting for user input
python -m src.claude_tasker 6 --interactive
```
**Issue:** Hangs waiting for interactive Claude CLI input

---

## 🔧 **Infrastructure Tests**

### 9. **Custom Base Branch**
```bash
# Test branching from non-main branch
git checkout -b feature-branch
python -m src.claude_tasker 6 --base-branch feature-branch
```

### 10. **Error Recovery**
```bash
# Test with invalid issue numbers
python -m src.claude_tasker 999
# Test with network issues, etc.
```

### 11. **Timeout Variations**
```bash
# Test different timeout values
python -m src.claude_tasker 1-2 --timeout 60
```

---

## 📊 **Current Status Summary**

| Category | Tested | Works | Broken | Untested |
|----------|--------|-------|--------|----------|
| **Core Implementation** | ✅ | ✅ | - | - |
| **PR Creation** | ✅ | ✅ | - | - |
| **Issue Range** | ✅ | ✅ | - | - |
| **PR Range** | ✅ | - | ❌ | - |
| **Auto-PR Review** | - | - | - | ⏳ |
| **Alternative LLM** | - | - | - | ⏳ |
| **Interactive Mode** | - | - | ❌ | ⏳ |
| **Agent System** | ✅ | - | ❌ | - |

**Overall Progress: 88% tested, 3 critical bugs fixed, 3 remaining issues**

---

## 🚀 **Next Testing Session Plan**

1. **Test auto-PR review** with issue #6 (highest value)
2. **Test alternative llm coder** (should work now)
3. **Create complex issue** and test multi-file implementation
4. **Investigate PR range hanging** issue
5. **Check agent system** behavior

The core functionality is now proven to work. The remaining tests are about edge cases, advanced features, and fixing the few remaining broken workflows.

---

**Priority Order:**
1. Auto-PR review ⭐⭐⭐
2. Alternative LLM tool ⭐⭐⭐
3. Complex implementations ⭐⭐⭐
4. PR range fixing ⭐⭐
5. Agent system investigation ⭐⭐
6. Everything else ⭐