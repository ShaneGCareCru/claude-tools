# Claude Tools

A powerful collection of tools for enhancing Claude Code workflows, featuring automated GitHub issue implementation, PR reviews, and intelligent bug analysis using Claude's advanced AI capabilities.

## Overview

Claude Tools provides a sophisticated task automation system that bridges Claude Code with GitHub workflows. The flagship tool, `claude-tasker`, enables automated issue implementation, code reviews, and bug analysis while maintaining high code quality through structured methodologies.

### Key Features

- 🤖 **Automated Issue Implementation** - Transforms GitHub issues into working code with intelligent gap analysis
- 🔍 **Smart PR Reviews** - Provides detailed code reviews with actionable feedback
- 🐛 **Intelligent Bug Analysis** - Converts bug descriptions into comprehensive GitHub issues
- 🎯 **Two-Stage Execution** - Eliminates meta-prompt issues through prompt-builder → executor pattern
- 📊 **4-D Methodology** - DECONSTRUCT → DIAGNOSE → DEVELOP → DELIVER for systematic problem-solving
- ✅ **Status Verification** - Detects and prevents false completion claims
- 🔄 **Batch Processing** - Handle ranges of issues or PRs efficiently
- 🌿 **Smart Branching** - Automatic timestamped branch creation for each task
- 💬 **GitHub Integration** - Direct interaction with issues, PRs, and comments via GitHub CLI

## Installation

### Prerequisites

- **macOS** or **Linux** (bash 4.0+)
- **GitHub CLI (`gh`)** - Authenticated with your GitHub account
- **jq** - JSON processor
- **Claude CLI** - For execution mode (optional for prompt-only mode)
- **git** - Version control
- **llm** (optional) - Falls back to Claude if not available

### Quick Start

```bash
# Clone the repository
git clone https://github.com/ShaneGCareCru/claude-tools.git
cd claude-tools

# Make the script executable
chmod +x claude-tasker

# Optional: Add to PATH for global access
echo 'export PATH="$PATH:'$(pwd)'"' >> ~/.bashrc
source ~/.bashrc
```

## Usage

### Basic Commands

```bash
# Process a single GitHub issue
./claude-tasker 123

# Process a range of issues
./claude-tasker 100-110

# Review a pull request
./claude-tasker --review-pr 456

# Analyze a bug and create an issue
./claude-tasker --bug "Users report login fails after password reset"

# Interactive mode (default is headless)
./claude-tasker 123 --interactive
```

### Advanced Options

```bash
# Generate prompts without execution
./claude-tasker 123 --prompt-only

# Custom timeout between tasks (default: 10 seconds)
./claude-tasker 100-105 --timeout 30

# Dry run - skip actual execution
./claude-tasker 123 --dry-run

# Verbose logging
./claude-tasker 123 --verbose
```

## How It Works

### Architecture

Claude Tools uses a sophisticated multi-stage approach:

1. **Context Analysis** - Reads project context from `CLAUDE.md`
2. **Agent Selection** - Chooses appropriate specialized agent
3. **Meta-Prompt Generation** - Creates optimized prompts using 4-D methodology
4. **Execution** - Runs Claude with generated prompts
5. **Verification** - Validates results and handles edge cases
6. **GitHub Integration** - Updates issues, creates PRs, posts comments

### Agent System

The tool uses specialized agents stored in `.claude/agents/`:
- `github-issue-implementer` - For implementing GitHub issues
- `pr-reviewer` - For reviewing pull requests
- `bug-analyzer` - For analyzing bug reports
- Additional custom agents can be added

### Project Configuration

Projects should include a `CLAUDE.md` file in the root directory containing:
- Repository overview
- Architecture details
- Development guidelines
- Common commands
- Any project-specific instructions

## Examples

### Implementing an Issue

```bash
$ ./claude-tasker 234
[INFO] Processing issue #234: Add user authentication
[INFO] Creating branch: issue-234-20240115-143022
[INFO] Generating implementation prompt...
[SUCCESS] Implementation complete with 5 files changed
[INFO] Creating PR: "Fix #234: Add user authentication"
```

### Reviewing Multiple PRs

```bash
$ ./claude-tasker --review-pr 100-105
[RANGE] Processing PR range: 100-105
[INFO] Reviewing PR #100: Update dependencies
[SUCCESS] Review posted with 3 suggestions
...
[INFO] Completed 6 PRs in range
```

### Bug Analysis

```bash
$ ./claude-tasker --bug "API returns 500 error when filtering by date"
[INFO] Analyzing bug description...
[INFO] Searching codebase for related patterns...
[SUCCESS] Created issue #789 with detailed analysis and reproduction steps
```

## Contributing

We welcome contributions!

### Development Setup

```bash
# Fork and clone the repository
git clone https://github.com/ShaneGCareCru/claude-tools.git
cd claude-tools

# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes and test
./claude-tasker --dry-run 123

# Submit a pull request
```

### Code Style

- Use bash best practices and shellcheck compliance
- Maintain comprehensive error handling
- Add logging for significant operations
- Update documentation for new features

## Troubleshooting

### Common Issues

1. **"gh not authenticated"**
   ```bash
   gh auth login
   ```

2. **"CLAUDE.md not found"**
   - Ensure you're running from a project root with `CLAUDE.md`

3. **"Rate limit exceeded"**
   - The tool includes automatic retry with exponential backoff
   - Use `--timeout` to increase delay between operations

### Debug Mode

```bash
# Enable verbose logging
export CLAUDE_TASKER_DEBUG=1
./claude-tasker 123
```

## GitHub Actions Integration (Beta)

> ⚠️ **Beta Feature**: The following GitHub Actions integration examples are theoretical and have not been fully tested. Use with caution in production environments.

Claude Tools can be integrated into GitHub Actions workflows to automate code reviews and issue implementation. Here's how it could work:

### Automated PR Reviews

Create `.github/workflows/claude-pr-review.yml`:

```yaml
name: Claude PR Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Claude Tools
        run: |
          # Clone claude-tools to runner
          git clone https://github.com/ShaneGCareCru/claude-tools.git /tmp/claude-tools
          chmod +x /tmp/claude-tools/claude-tasker
          
      - name: Run Claude Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GH_TOKEN: ${{ github.token }}
        run: |
          cd ${{ github.workspace }}
          /tmp/claude-tools/claude-tasker --review-pr ${{ github.event.pull_request.number }}
```

### Automated Issue Implementation

Create `.github/workflows/claude-issue-implement.yml`:

```yaml
name: Claude Issue Implementation
on:
  issues:
    types: [opened, labeled]

jobs:
  implement:
    # Only run on issues labeled 'claude-implement'
    if: contains(github.event.issue.labels.*.name, 'claude-implement')
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Claude Tools
        run: |
          git clone https://github.com/ShaneGCareCru/claude-tools.git /tmp/claude-tools
          chmod +x /tmp/claude-tools/claude-tasker
          
      - name: Configure Git
        run: |
          git config --global user.name "Claude Bot"
          git config --global user.email "claude-bot@users.noreply.github.com"
          
      - name: Implement Issue
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          cd ${{ github.workspace }}
          /tmp/claude-tools/claude-tasker ${{ github.event.issue.number }}
```

### Configuration Requirements

1. **Add Anthropic API Key**: 
   - Go to Settings → Secrets → Actions
   - Add `ANTHROPIC_API_KEY` with your API key

2. **Permissions**: 
   - Ensure Actions have write permissions for PRs and issues
   - Settings → Actions → General → Workflow permissions

3. **Claude CLI Installation**:
   - The workflow would need to install Claude CLI on the runner
   - Could be done via npm, homebrew, or direct download

### Security Considerations

- **API Key Protection**: Never commit API keys; use GitHub Secrets
- **Rate Limiting**: Implement appropriate delays between API calls
- **Resource Limits**: Set timeout limits on Actions to prevent runaway costs
- **Review Output**: Always review Claude's PRs before merging
- **Selective Triggers**: Use labels or specific conditions to control when automation runs

### Potential Enhancements

- Integrate with Claude's official GitHub App (when available)
- Add cost tracking and budget limits
- Implement review approval requirements
- Add test suite execution before PR creation
- Use matrix builds for handling multiple issues/PRs

This integration would enable teams to leverage Claude's capabilities directly in their GitHub workflow, automating routine tasks while maintaining human oversight for critical decisions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for the Claude Code community
- Inspired by modern DevOps automation practices
- Uses the Lyra-Dev 4-D methodology for structured problem-solving

## Support

- 📖 [Documentation](https://github.com/ShaneGCareCru/claude-tools/wiki) - Detailed guides and documentation
- 🐛 [Issue Tracker](https://github.com/ShaneGCareCru/claude-tools/issues) - Report bugs and request features
- 💬 [Discussions](https://github.com/ShaneGCareCru/claude-tools/discussions) - Ask questions and share ideas
- 🔧 [Source Code](https://github.com/ShaneGCareCru/claude-tools) - Browse and contribute

---

Made with ❤️ by the Claude Tools community