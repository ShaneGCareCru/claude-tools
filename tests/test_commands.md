# 🧪 Test Commands for Claude-Tasker

## Test Categories

### 1. **Unit Tests Only** (Fast, Mocked)
```bash
# Run only unit tests (existing tests that use mocks)
pytest -m "not integration and not slow"

# Run unit tests with coverage
pytest -m "not integration" --cov=src/claude_tasker --cov-report=html
```

### 2. **Integration Tests** (Slow, Real Tools)
```bash
# Run only integration tests (would have caught the bug)
pytest -m integration

# Run integration tests that require Claude CLI
pytest -m "integration and requires_claude"

# Run all integration tests with verbose output
pytest -m integration -v -s
```

### 3. **All Tests**
```bash
# Run all tests (unit + integration)
pytest

# Run all tests with coverage
pytest --cov=src/claude_tasker --cov-report=term-missing
```

### 4. **Specific Test Categories**
```bash
# Test real execution pipeline (would have caught the bug)
pytest tests/test_real_execution_integration.py::TestRealExecutionIntegration::test_real_claude_execution_creates_files

# Test git change detection accuracy
pytest tests/test_real_execution_integration.py::TestRealExecutionIntegration::test_git_change_detection_accuracy

# Test Claude CLI permission modes
pytest tests/test_real_execution_integration.py::TestRealExecutionIntegration::test_claude_cli_permission_modes
```

## Environment Setup

### Required Tools for Integration Tests
```bash
# Install required CLI tools
brew install gh      # GitHub CLI
# Claude CLI should already be installed

# Verify tools are available
claude --version
git --version  
gh --version
```

### Environment Variables
```bash
# For GitHub integration tests (optional)
export GITHUB_TOKEN=your_token_here

# For test isolation
export PYTHONPATH=/path/to/claude-tools:$PYTHONPATH
```

## Test Scenarios That Would Have Caught The Bug

### 1. **Critical Execution Test**
```bash
# This test would have FAILED with the original bug
pytest tests/test_real_execution_integration.py::TestRealExecutionIntegration::test_real_claude_execution_creates_files -v
```
**Expected with Bug:** `AssertionError: CRITICAL BUG: No git changes detected after execution`  
**Expected with Fix:** ✅ Test passes

### 2. **Execute Mode Parameter Test**  
```bash
# This test would have caught the missing execute_mode=True
pytest tests/test_real_execution_integration.py::TestExecutionModeValidation::test_execute_mode_parameter_propagation -v
```

### 3. **End-to-End Workflow Test**
```bash
# This test would have caught the broken pipeline
pytest tests/test_real_execution_integration.py::TestRealExecutionIntegration::test_end_to_end_workflow_simulation -v
```

## CI/CD Integration

### GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests
        run: pytest -m "not integration"
  
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Claude CLI
        run: npm install -g @anthropic-ai/claude-cli
      - name: Run integration tests
        run: pytest -m integration
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Test Coverage Goals
- **Unit Tests**: >95% line coverage  
- **Integration Tests**: All critical workflows tested with real tools
- **E2E Tests**: Full issue → implementation → PR workflows

## Why These Tests Matter

### The Original Bug Pattern
1. ✅ Unit tests passed (mocked execution worked)
2. ❌ Integration tests would have failed (real execution broken)
3. ❌ E2E tests would have failed (no files created)

### Test-Driven Development Enhanced
```bash
# TDD Cycle with Integration Tests
1. Write failing unit test     → pytest tests/test_unit.py
2. Write failing integration   → pytest tests/test_integration.py  
3. Implement feature           → Write code
4. Verify unit tests pass     → pytest -m "not integration"
5. Verify integration passes  → pytest -m integration
6. Refactor with confidence   → pytest
```

This approach would have caught the execution pipeline bug immediately since the integration tests would have failed when no real files were created.