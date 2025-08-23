# Claude-Tasker Test Suite

This directory contains comprehensive tests for the `claude-tasker-py` Python implementation, covering all features and functionality.

## Test Structure

### Core Test Files

- **`conftest.py`** - Pytest configuration and shared fixtures
- **`test_argument_parsing.py`** - Command-line argument parsing and validation
- **`test_git_operations.py`** - Git operations and workspace management  
- **`test_github_cli.py`** - GitHub CLI integrations (issues, PRs, comments)
- **`test_workflow_logic.py`** - Complex workflow logic and agent coordination
- **`test_command_flags.py`** - All command-line flags and options
- **`test_environment_validation.py`** - Environment validation and dependency checking
- **`test_integration.py`** - End-to-end integration tests

## Test Coverage

### Command-Line Flags Tested
- `--review-pr <number|range>` - PR review mode
- `--bug "description"` - Bug analysis mode
- `--project <id>` - GitHub project context
- `--prompt-only` - Generate prompts without execution
- `--timeout <seconds>` - Delay between tasks
- `--interactive` - Interactive vs headless mode
- `--auto-pr-review` - Auto-review after implementation
- `--coder <claude|codex>` - AI coder selection
- `--base-branch <branch>` - Base branch specification
- `--help` - Help documentation

### Functionality Tested
1. **Argument Parsing**
   - Single issue numbers
   - Issue ranges (e.g., 230-250)
   - PR numbers and ranges
   - Flag validation and error handling
   - Conflicting flag detection

2. **Git Operations**
   - Repository validation
   - Branch detection (main/master)
   - Workspace hygiene checks
   - Commit history retrieval
   - Status change detection

3. **GitHub CLI Integration**
   - Issue viewing and data extraction
   - PR viewing and diff retrieval
   - Comment posting
   - Project context retrieval
   - API error handling

4. **Workflow Logic**
   - Two-stage execution (meta-prompt → execution)
   - Agent-based architecture
   - Status verification protocol
   - Audit-and-implement workflow
   - Intelligent PR body generation

5. **Environment Validation**
   - Dependency checking (gh, jq, git, claude/codex)
   - GitHub remote URL validation
   - CLAUDE.md file requirement
   - TTY detection for interactive mode

6. **Integration Testing**
   - Complete workflows end-to-end
   - Range processing with timeouts
   - Error recovery and retries
   - Complex flag combinations

## Running Tests

### Prerequisites
```bash
pip install -r requirements-test.txt
```

### Run All Tests
```bash
pytest
```

### Run Specific Test Categories
```bash
# Argument parsing tests
pytest tests/test_argument_parsing.py

# Git operations tests  
pytest tests/test_git_operations.py

# GitHub CLI tests
pytest tests/test_github_cli.py

# Workflow logic tests
pytest tests/test_workflow_logic.py

# Integration tests
pytest tests/test_integration.py
```

### Coverage Report
```bash
pytest --cov=. --cov-report=html
```

## Test Strategy

### Mocking Strategy
- **subprocess.run** - Mock all shell command executions
- **File operations** - Mock file reads/writes for safety
- **Network calls** - Mock GitHub CLI API interactions
- **Time operations** - Mock sleep/delays for fast test execution

### Test Philosophy
- **Comprehensive coverage** - Test all code paths and edge cases
- **Isolated testing** - Each test is independent and doesn't affect others
- **Realistic scenarios** - Tests mirror real-world usage patterns
- **Error conditions** - Thorough testing of error handling and recovery

### Fixtures
- `mock_git_repo` - Temporary git repository with CLAUDE.md
- `mock_subprocess` - Generic subprocess mocking
- `mock_gh_cli` - GitHub CLI command mocking
- `mock_claude_cli` - Claude CLI command mocking
- `claude_tasker_script` - Path to the claude-tasker-py script

## Test Coverage Goals

The test suite aims to achieve:
- **>95% code coverage** of the bash script functionality
- **All command-line flags** tested with valid and invalid inputs
- **All error conditions** properly handled and tested
- **All external dependencies** mocked and tested
- **All workflows** tested end-to-end

## Test Benefits

These tests provide:
1. **Feature validation** - Ensure all functionality works as expected
2. **Regression testing** - Catch any functionality loss during updates
3. **Documentation** - Tests serve as executable specifications
4. **Confidence** - Comprehensive testing ensures reliability

## Contributing

When adding new tests:
1. Follow existing naming conventions
2. Use appropriate fixtures for setup
3. Mock external dependencies
4. Test both success and failure cases
5. Add docstrings explaining test purpose