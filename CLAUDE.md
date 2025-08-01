# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a collection of enhanced tools for working with Claude Code in GitHub workflows, with the primary tool being `claude-tasker` - an advanced task runner that provides context-aware wrapper for Claude Code with GitHub integration.

## Key Architecture

### Claude Tasker
- **Two-stage execution**: Meta-prompt generation → Claude execution (eliminates meta-prompt issues)
- **Agent-based architecture**: Uses specialized agents in `.claude/agents/` for different task types
- **Lyra-Dev 4-D methodology**: DECONSTRUCT → DIAGNOSE → DEVELOP → DELIVER
- **GitHub integration**: Direct interaction with issues, PRs, and comments via `gh` CLI
- **Status verification protocol**: Detects false completion claims
- **AUDIT-AND-IMPLEMENT workflow**: Audits gaps before implementation

### File Structure
- `claude-tasker`: Main bash script with agent coordination logic
- `.claude/agents/`: Directory containing specialized agent definitions (auto-created if missing)
- `test-repo/mixologist/`: Example FastAPI application for testing

## Common Commands

### Running Claude Tasker
```bash
# Process single GitHub issue
./claude-tasker <issue_number>

# Process range of issues
./claude-tasker <start>-<end>

# Review PR (read-only)
./claude-tasker --review-pr <pr_number>

# Analyze bug and create issue
./claude-tasker --bug "<description>"

# Interactive mode (default is headless)
./claude-tasker <issue_number> --interactive
```

### Script Options
- `--interactive`: Enable interactive mode
- `--prompt-only`: Generate prompts without execution
- `--timeout <seconds>`: Set delay between tasks (default: 10)
- `--dry-run`: Skip actual execution

## Development Guidelines

### Required Dependencies
- `gh` - GitHub CLI (required for API interactions)
- `jq` - JSON processor
- `claude` - Claude Code CLI (not required for prompt-only mode)
- `git` - Version control
- `llm` - Optional, falls back to Claude if not available

### Git Workflow
- Always creates timestamped branches: `issue-<number>-<timestamp>`
- Commits with standardized messages: `🤖 <branch>: automated <mode> via agent coordination`
- Only creates PRs when actual code changes are made
- Gracefully handles "already complete" cases

### Agent System
- Agents are stored in `.claude/agents/` as markdown files
- Each agent has specialized capabilities (e.g., `github-issue-implementer`, `pr-reviewer`)
- Agents follow the 4-D methodology for structured problem-solving
- Script auto-creates essential agents if missing

### Error Handling
- Exponential backoff for API rate limits
- Comprehensive logging with color-coded levels
- Validation of environment before execution
- Graceful degradation when tools are missing