# Archived Bash Implementation

**Status: DEPRECATED - No longer maintained**

This directory contains the original bash implementation of claude-tasker, which has been superseded by the Python implementation (`claude-tasker-py`).

## Archived Files

- `claude-tasker` - Original bash script implementation
- `claude-agent-poc.agent` - Agent proof-of-concept script
- `claude_tasker.py` - Early Python helper script used with bash implementation
- `.claude/` - Directory containing agent definitions and settings

## Historical Context

This bash implementation was the initial version of claude-tasker, providing:
- Two-stage execution (meta-prompt generation → Claude execution)
- Agent-based architecture with specialized agents
- GitHub integration via `gh` CLI
- Lyra-Dev 4-D methodology implementation

## Migration Notice

All functionality has been migrated to the Python implementation at the repository root:
- Main executable: `claude-tasker-py`
- Source code: `src/claude_tasker/`
- Tests: `tests/`

## Why Archived?

The Python implementation provides:
- Better cross-platform compatibility
- Improved error handling and logging
- More maintainable codebase
- Comprehensive test coverage
- Enhanced performance and reliability

## Important

**DO NOT USE** these scripts for new development. They are preserved here for historical reference only.

For current usage, please refer to the main [README.md](../../README.md) and use `claude-tasker-py`.