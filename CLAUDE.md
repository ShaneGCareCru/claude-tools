# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a collection of enhanced tools for working with Claude Code in GitHub workflows, with the primary tool being `claude-tasker-py` - an advanced Python-based task runner that provides context-aware wrapper for Claude Code with GitHub integration.

## Key Architecture

### Claude Tasker (Python Implementation)
- **Two-stage execution**: Meta-prompt generation → Claude execution (eliminates meta-prompt issues)
- **Modular architecture**: Object-oriented design with specialized modules for different responsibilities
- **Lyra-Dev 4-D methodology**: DECONSTRUCT → DIAGNOSE → DEVELOP → DELIVER
- **GitHub integration**: Direct interaction with issues, PRs, and comments via `gh` CLI
- **Status verification protocol**: Detects false completion claims
- **AUDIT-AND-IMPLEMENT workflow**: Audits gaps before implementation
- **Comprehensive testing**: Unit tests, integration tests, and mocking support

### File Structure
- `claude-tasker-py`: Main executable Python wrapper script
- `src/claude_tasker/`: Python package containing core implementation
  - `cli.py`: Command-line interface and argument parsing
  - `workflow_logic.py`: Core orchestration and task management
  - `prompt_builder.py`: LLM prompt generation and execution
  - `github_client.py`: GitHub API integration
  - `environment_validator.py`: Dependency validation
  - `workspace_manager.py`: Git operations and file management
  - `pr_body_generator.py`: PR description generation
  - `logging_config.py`: Logging configuration
- `tests/`: Comprehensive test suite
- `techflow-demo/`: Example React application for testing

## Common Commands

### Running Claude Tasker
```bash
# Process single GitHub issue
./claude-tasker-py <issue_number>

# Process range of issues
./claude-tasker-py <start>-<end>

# Review PR (read-only)
./claude-tasker-py --review-pr <pr_number>

# Analyze bug and create issue
./claude-tasker-py --bug "<description>"

# Interactive mode (default is headless)
./claude-tasker-py <issue_number> --interactive
```

### Script Options
- `--interactive`: Enable interactive mode
- `--prompt-only`: Generate prompts without execution
- `--timeout <seconds>`: Set delay between tasks (default: 10)
- `--dry-run`: Skip actual execution
- `--coder <claude|llm>`: Choose LLM tool (default: claude)

## Development Guidelines

### Required Dependencies
- `Python 3.7+` - Required for running the Python implementation
- `gh` - GitHub CLI (required for API interactions)
- `jq` - JSON processor
- `claude` - Claude Code CLI (primary LLM tool)
- `git` - Version control
- `llm` - Optional fallback LLM tool

### Python Package Dependencies
Install with: `pip install -r requirements.txt`
- `PyGithub` - GitHub API client
- `click` - Command-line interface creation
- `rich` - Terminal formatting and colors
- `python-dotenv` - Environment variable management

### Git Workflow
- Always creates timestamped branches: `issue-<number>-<timestamp>`
- Validates branch names match the issue being processed
- Commits with standardized messages following conventional commit format
- Only creates PRs when actual code changes are made
- Gracefully handles "already complete" cases
- Warns users when branch/issue number mismatches occur

### Testing
- Run tests with: `pytest tests/`
- Test coverage: `pytest --cov=src/claude_tasker tests/`
- Integration tests: `pytest tests/test_integration.py`

### Error Handling
- Exponential backoff for API rate limits
- Comprehensive logging with structured format
- Validation of environment before execution
- Graceful degradation when tools are missing
- Automatic fallback between Claude CLI and LLM tools

## Historical Note

A deprecated bash implementation has been archived in `archive/bash_implementation/` for historical reference. The Python implementation is the actively maintained version.