# Claude Tools

A collection of enhanced tools for working with Claude Code in GitHub workflows.

## Claude Tasker

An enhanced Claude Task Runner that provides a context-aware wrapper for Claude Code with advanced GitHub integration capabilities.

### Features

- **Two-stage Claude execution**: prompt-builder → executor (eliminates meta-prompt issues)
- **Lyra-Dev 4-D methodology** for optimized prompt generation
- **Status verification protocol** to detect false completion claims
- **AUDIT-AND-IMPLEMENT workflow**: Claude audits and fixes gaps in one run
- **Smart PR creation**: only when actual code changes are made
- **Graceful handling** of "already complete" cases (auto-closes, no unnecessary PRs)
- **Range processing**: Handle single tasks or ranges (e.g., 230-250)
- **Automatic branch creation** for each task
- **Configurable timeout** between tasks for API rate limiting
- **Interactive or headless mode** support
- **Project-aware prompts** using CLAUDE.md context
- **Gap analysis**: focuses on actual missing pieces, not claimed completions
- **Robust retry logic** with exponential backoff for API limits
- **Bug report analysis**: Intelligent codebase analysis to create detailed GitHub issues from bug descriptions

### Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd claude-tools
   ```

2. Make the script executable:
   ```bash
   chmod +x claude-tasker
   ```

3. Optionally, add to your PATH for global access:
   ```bash
   # Add to your ~/.bashrc or ~/.zshrc
   export PATH="$PATH:/path/to/claude-tools"
   ```

### Requirements

- **GitHub CLI (`gh`)** - For GitHub API interactions
- **jq** - JSON processor for parsing API responses
- **claude** - Claude Code CLI (not required for prompt-only mode)
- **git** - Version control
- **CLAUDE.md** - Must exist in the project directory
- **Git repository** with GitHub remote configured

### Usage

#### Issue Processing
```bash
# Audit and implement a single task
claude-tasker <issue_number> [options]

# Audit and implement a range of tasks
claude-tasker <start_issue>-<end_issue> [options]
```

#### PR Review
```bash
# Review a single PR (read-only analysis)
claude-tasker --review-pr <pr_number> [options]

# Review a range of PRs (read-only analysis)
claude-tasker --review-pr <start_pr>-<end_pr> [options]
```

#### Bug Report
```bash
# Analyze bug description and create detailed GitHub issue
claude-tasker --bug "<bug_description>" [options]
```

### Workflow

#### For Issues:
1. **Meta-prompt generation** → optimized prompt creation
2. **Audit phase** → identify actual gaps and missing implementations
3. **Implementation** → fix identified gaps
4. **Comment** → provide transparency on audit results
5. **PR creation** → only if actual code changes were made

#### For PR Reviews:
1. **Direct prompt** → review analysis
2. **Comment generation** → `gh pr comment` (no branches/PRs/separate comments)

#### For Bug Reports:
1. **Codebase analysis** → search for relevant code patterns and potential causes
2. **Gap analysis** → identify likely root causes based on code examination
3. **Issue creation** → generate comprehensive GitHub issue with structured bug report
4. **Labeling** → apply appropriate labels for priority, severity, and area

### Environment Setup

The script must be run from a directory containing:
- `CLAUDE.md` - Project context file
- A git repository with GitHub remote configured

### Dependencies Check

The script automatically validates that all required tools are installed and the environment is properly configured before execution.

### Error Handling

- Robust retry logic with exponential backoff for API rate limits
- Graceful handling of edge cases (already completed tasks, etc.)
- Comprehensive logging with color-coded output levels (INFO, SUCCESS, WARNING, ERROR, RANGE)

### Contributing

This tool is designed to work with Claude Code and GitHub workflows. Ensure any modifications maintain compatibility with the existing GitHub API integration and Claude Code CLI.

### License

[Add your license information here]