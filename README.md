# Claude Tools

A powerful collection of tools for enhancing Claude Code workflows, featuring automated GitHub issue implementation, PR reviews, and intelligent bug analysis using Claude's advanced AI capabilities.

## Overview

Claude Tools provides a sophisticated task automation system that bridges Claude Code with GitHub workflows. Available in both **Bash** and **Python** implementations, the flagship tool `claude-tasker` enables automated issue implementation, code reviews, and bug analysis while maintaining high code quality through structured methodologies.

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

### 🚀 Quick Install (Recommended)

**Download pre-built macOS binaries** - No Python or dependencies required!

1. Go to [GitHub Releases](https://github.com/ShaneGCareCru/claude-tools/releases)
2. Download the right binary for your Mac:
   - **Apple Silicon (M1/M2/M3)**: `claude-tasker-arm64`
   - **Intel Macs**: `claude-tasker-x86_64`
3. Make it executable and install:

```bash
chmod +x claude-tasker-*
sudo mv claude-tasker-* /usr/local/bin/claude-tasker
claude-tasker --version
```

**That's it!** See [INSTALLATION.md](./docs/development/INSTALLATION.md) for detailed instructions and troubleshooting.

### Development Installation

**Prerequisites:**
- **Python 3.11+**
- **GitHub CLI (`gh`)** - Authenticated with your GitHub account
- **jq** - JSON processor
- **git** - Version control
- **Claude CLI** - For executing prompts

```bash
# Clone and install from source
git clone https://github.com/ShaneGCareCru/claude-tools.git
cd claude-tools
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Optional: Add to PATH for global access
echo 'export PATH="$PATH:'$(pwd)'"' >> ~/.bashrc
source ~/.bashrc
```

### Implementation Choices

Claude Tools offers two implementations to suit different environments:

**Bash Implementation (`claude-tasker`)**
- Traditional shell script approach
- Minimal dependencies
- Direct system integration
- Recommended for CI/CD environments

**Python Implementation (`claude-tasker-py`)**  
- Modern object-oriented architecture
- Enhanced error handling and validation
- Comprehensive testing framework
- Better maintainability and extensibility
- Recommended for development workflows

Both implementations provide identical functionality and can be used interchangeably.

## Usage

### Basic Commands

Both implementations support identical command-line syntax:

```bash
# Process a single GitHub issue
./claude-tasker 123
./claude-tasker-py 123

# Process a range of issues  
./claude-tasker 100-110
./claude-tasker-py 100-110

# Review a pull request
./claude-tasker --review-pr 456
./claude-tasker-py --review-pr 456

# Analyze a bug and create an issue
./claude-tasker --bug "Users report login fails after password reset"
./claude-tasker-py --bug "Users report login fails after password reset"

# Interactive mode (default is headless)
./claude-tasker 123 --interactive
./claude-tasker-py 123 --interactive
```

### Advanced Options

```bash
# Generate prompts without execution
./claude-tasker 123 --prompt-only
./claude-tasker-py 123 --prompt-only

# Custom timeout between tasks (default: 10 seconds)
./claude-tasker 100-105 --timeout 30
./claude-tasker-py 100-105 --timeout 30

# Dry run - skip actual execution
./claude-tasker 123 --dry-run
./claude-tasker-py 123 --dry-run

# Verbose logging (bash only)
./claude-tasker 123 --verbose

# Choose LLM tool (Python only)
./claude-tasker-py 123 --coder claude
./claude-tasker-py 123 --coder llm
```

## How It Works

### Architecture

Claude Tools uses a sophisticated multi-stage approach across both implementations:

**Common Workflow:**
1. **Context Analysis** - Reads project context from `CLAUDE.md`
2. **Environment Validation** - Checks dependencies and repository state
3. **Task Processing** - Implements issues, reviews PRs, or analyzes bugs
4. **LLM Integration** - Uses Claude CLI or LLM tool for AI assistance  
5. **GitHub Integration** - Updates issues, creates PRs, posts comments

**Implementation Differences:**

**Bash (`claude-tasker`)**
- Single shell script with embedded functions
- Direct bash-to-CLI tool integration
- Agent-based prompt generation

**Python (`claude-tasker-py`)**
- Modular object-oriented architecture with enhanced error handling:
  - `cli.py` - Command-line interface and argument parsing with comprehensive validation
  - `workflow_logic.py` - Core orchestration, task management, and two-stage execution
  - `prompt_builder.py` - LLM prompt generation, execution, and Claude CLI integration
  - `github_client.py` - GitHub API integration with rate limiting and error recovery
  - `environment_validator.py` - Dependency validation and environment checking
  - `workspace_manager.py` - Git operations, branch management, and file system utilities
- **Two-Stage Execution**: Meta-prompt generation → Optimized prompt execution
- **Enhanced Validation**: Input validation, environment checks, and status verification
- **Error Recovery**: Automatic fallback between Claude CLI and LLM tools
- **Comprehensive Testing**: Unit tests, integration tests, and mocking support

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
$ ./claude-tasker-py 234
🔄 Processing issue #234...
✅ Issue #234: Add user authentication implementation successful
   PR: https://github.com/owner/repo/pull/456
   Branch: issue-234-1755823988
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

**Bash Implementation:**
```bash
$ ./claude-tasker --bug "API returns 500 error when filtering by date"
[INFO] Analyzing bug description...
[INFO] Searching codebase for related patterns...
[SUCCESS] Created issue #789 with detailed analysis and reproduction steps
```

**Python Implementation:**
```bash
$ ./claude-tasker-py --bug "API returns 500 error when filtering by date"
🐛 Analyzing bug: API returns 500 error when filtering by date
✅ Bug analysis completed and issue created: https://github.com/owner/repo/issues/789
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

Claude Tools can be integrated into GitHub Actions workflows to automate code reviews and issue implementation. This requires careful setup of dependencies and authentication.

### Prerequisites & Authentication

1. **GitHub Personal Access Token (PAT)**:
   - Required because the default `GITHUB_TOKEN` has limitations:
     - Cannot create PRs that trigger other workflows
     - Limited cross-repository access
     - Cannot push to protected branches
   - Create at: Settings → Developer settings → Personal access tokens
   - Required scopes: `repo`, `workflow`, `write:packages`

2. **API Keys Required**:
   - `ANTHROPIC_API_KEY` - For Claude CLI
   - `OPENAI_API_KEY` - For LLM tool (fallback when Claude CLI unavailable)

3. **Add Secrets to Repository**:
   ```
   Settings → Secrets and variables → Actions → New repository secret
   - ANTHROPIC_API_KEY
   - OPENAI_API_KEY  
   - GH_PAT (your Personal Access Token)
   ```

### Complete PR Review Workflow

Create `.github/workflows/claude-pr-review.yml`:

```yaml
name: Claude PR Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for better context
      
      - name: Validate Secrets
        run: |
          # Check all required secrets are present
          if [ -z "${{ secrets.ANTHROPIC_API_KEY }}" ]; then
            echo "❌ Error: ANTHROPIC_API_KEY secret is not set"
            exit 1
          fi
          
          if [ -z "${{ secrets.OPENAI_API_KEY }}" ]; then
            echo "❌ Error: OPENAI_API_KEY secret is not set"
            exit 1
          fi
          
          if [ -z "${{ secrets.GH_PAT }}" ]; then
            echo "❌ Error: GH_PAT secret is not set"
            exit 1
          fi
          
          echo "✅ All required secrets are configured"
          
      - name: Install Dependencies
        run: |
          # Install jq (JSON processor)
          sudo apt-get update && sudo apt-get install -y jq
          
          # Install Python and pip for LLM tool
          sudo apt-get install -y python3-pip
          
          # Install LLM tool
          pip install llm
          
          # Configure LLM with OpenAI
          llm keys set openai --key "${{ secrets.OPENAI_API_KEY }}"
          
          # Install Claude CLI via npm
          npm install -g @anthropic-ai/claude-cli
          
          # Clone claude-tools
          git clone https://github.com/ShaneGCareCru/claude-tools.git /tmp/claude-tools
          chmod +x /tmp/claude-tools/claude-tasker
          
      - name: Verify Dependencies
        run: |
          # Check all required tools are installed
          echo "Checking required dependencies..."
          
          command -v jq >/dev/null 2>&1 || { echo "❌ jq is not installed"; exit 1; }
          command -v gh >/dev/null 2>&1 || { echo "❌ gh CLI is not installed"; exit 1; }
          command -v llm >/dev/null 2>&1 || { echo "❌ llm is not installed"; exit 1; }
          command -v claude >/dev/null 2>&1 || { echo "❌ claude CLI is not installed"; exit 1; }
          command -v git >/dev/null 2>&1 || { echo "❌ git is not installed"; exit 1; }
          
          [ -x /tmp/claude-tools/claude-tasker ] || { echo "❌ claude-tasker is not executable"; exit 1; }
          
          echo "✅ All dependencies verified"
          
      - name: Configure GitHub CLI
        run: |
          # Use PAT instead of default token
          echo "${{ secrets.GH_PAT }}" | gh auth login --with-token
          
          # Verify authentication
          gh auth status || { echo "❌ GitHub CLI authentication failed"; exit 1; }
          
      - name: Run Claude Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GH_TOKEN: ${{ secrets.GH_PAT }}
        run: |
          cd ${{ github.workspace }}
          
          # Ensure CLAUDE.md exists
          if [ ! -f "CLAUDE.md" ]; then
            echo "# Project Context" > CLAUDE.md
            echo "Repository: ${{ github.repository }}" >> CLAUDE.md
          fi
          
          # Run review with timeout protection
          timeout 20m /tmp/claude-tools/claude-tasker \
            --review-pr ${{ github.event.pull_request.number }} \
            --timeout 30
```

### Complete Issue Implementation Workflow

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
    timeout-minutes: 60
    
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GH_PAT }}  # Use PAT for push access
          fetch-depth: 0
      
      - name: Validate Secrets
        run: |
          # Check all required secrets are present
          if [ -z "${{ secrets.ANTHROPIC_API_KEY }}" ]; then
            echo "❌ Error: ANTHROPIC_API_KEY secret is not set"
            echo "Please add this secret in Settings → Secrets → Actions"
            exit 1
          fi
          
          if [ -z "${{ secrets.OPENAI_API_KEY }}" ]; then
            echo "❌ Error: OPENAI_API_KEY secret is not set"
            echo "Please add this secret in Settings → Secrets → Actions"
            exit 1
          fi
          
          if [ -z "${{ secrets.GH_PAT }}" ]; then
            echo "❌ Error: GH_PAT secret is not set"
            echo "Please create a Personal Access Token with 'repo' scope"
            exit 1
          fi
          
          echo "✅ All required secrets are configured"
          
      - name: Install Dependencies
        run: |
          # System dependencies
          sudo apt-get update && sudo apt-get install -y jq python3-pip
          
          # Install and configure LLM tool
          pip install llm
          llm keys set openai --key "${{ secrets.OPENAI_API_KEY }}"
          
          # Install Claude CLI
          npm install -g @anthropic-ai/claude-cli
          
          # Setup claude-tools
          git clone https://github.com/ShaneGCareCru/claude-tools.git /tmp/claude-tools
          chmod +x /tmp/claude-tools/claude-tasker
          
      - name: Verify Dependencies
        run: |
          # Check all required tools are installed
          echo "Checking required dependencies..."
          
          command -v jq >/dev/null 2>&1 || { echo "❌ jq is not installed"; exit 1; }
          command -v gh >/dev/null 2>&1 || { echo "❌ gh CLI is not installed"; exit 1; }
          command -v llm >/dev/null 2>&1 || { echo "❌ llm is not installed"; exit 1; }
          command -v claude >/dev/null 2>&1 || { echo "❌ claude CLI is not installed"; exit 1; }
          command -v git >/dev/null 2>&1 || { echo "❌ git is not installed"; exit 1; }
          
          [ -x /tmp/claude-tools/claude-tasker ] || { echo "❌ claude-tasker is not executable"; exit 1; }
          
          # Test LLM tool configuration
          llm models list | grep -q "gpt" || { echo "❌ LLM tool not configured properly"; exit 1; }
          
          echo "✅ All dependencies verified"
          
      - name: Configure Git and GitHub
        run: |
          # Git configuration
          git config --global user.name "Claude Bot"
          git config --global user.email "claude-bot@users.noreply.github.com"
          
          # GitHub CLI with PAT
          echo "${{ secrets.GH_PAT }}" | gh auth login --with-token
          
          # Verify authentication
          gh auth status || { echo "❌ GitHub CLI authentication failed"; exit 1; }
          
      - name: Create CLAUDE.md if missing
        run: |
          if [ ! -f "CLAUDE.md" ]; then
            cat > CLAUDE.md << 'EOF'
          # Project Context for Claude
          
          Repository: ${{ github.repository }}
          
          ## Guidelines
          - Follow existing code style and conventions
          - Write comprehensive tests for new features
          - Update documentation as needed
          - Ensure all CI checks pass
          EOF
          fi
          
      - name: Implement Issue
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GH_TOKEN: ${{ secrets.GH_PAT }}
        run: |
          cd ${{ github.workspace }}
          
          # Run with timeout and error handling
          timeout 50m /tmp/claude-tools/claude-tasker \
            ${{ github.event.issue.number }} \
            --timeout 30 || {
              echo "Claude implementation failed or timed out"
              gh issue comment ${{ github.event.issue.number }} \
                --body "❌ Automated implementation failed. Please check the logs."
              exit 1
            }
            
      - name: Post Success Comment
        if: success()
        run: |
          gh issue comment ${{ github.event.issue.number }} \
            --body "✅ Automated implementation completed. Please review the generated PR."
```

### Security Considerations

1. **Secrets Management**:
   - Never log or output API keys
   - Rotate keys regularly
   - Use environment-specific keys

2. **Resource Limits**:
   - Set `timeout-minutes` on jobs
   - Use `timeout` command for long-running operations
   - Monitor Actions usage and costs

3. **Access Control**:
   - Limit PAT scopes to minimum required
   - Use workflow approval for first-time contributors
   - Require manual review before merging automated PRs

4. **Cost Management**:
   ```yaml
   # Add to workflow for cost awareness
   - name: Log API Usage Warning
     run: |
       echo "⚠️ This workflow uses paid API services (Claude & OpenAI)"
       echo "Estimated cost per run: $0.10-$0.50 depending on issue complexity"
   ```

### Troubleshooting

1. **"gh: Forbidden" errors**: Ensure PAT has correct scopes
2. **"command not found: claude"**: Claude CLI installation failed
3. **"CLAUDE.md not found"**: The workflow now creates a basic one if missing
4. **Timeout errors**: Increase `timeout-minutes` or optimize prompts

### Limitations

- Cannot work with private dependencies without additional setup
- PR creation from forks requires additional permissions
- Some GitHub API operations may hit rate limits
- Claude and OpenAI API costs can accumulate quickly

This integration enables powerful automation but requires careful configuration and monitoring to be effective and secure.

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
