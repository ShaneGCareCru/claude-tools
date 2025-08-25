# Installing Claude Tasker via Homebrew

This guide explains how to install `claude-tasker` using Homebrew on macOS and Linux.

## Prerequisites

1. **Homebrew**: Install from [brew.sh](https://brew.sh) if not already installed
2. **Claude CLI**: Install from [Anthropic's documentation](https://docs.anthropic.com/en/docs/claude-code)
3. **GitHub Authentication**: Run `gh auth login` or set `GITHUB_TOKEN` environment variable

## Installation Methods

### Method 1: From GitHub Release (Recommended for Users)

Once the formula is published to a tap:

```bash
# Add the tap (if published to a custom tap)
brew tap sgleeson/claude-tools

# Install claude-tasker
brew install claude-tasker
```

### Method 2: Local Formula Installation (For Development/Testing)

If you have cloned the repository locally:

```bash
# Navigate to the repository
cd /path/to/claude-tools

# Install using the local formula
brew install --build-from-source ./claude-tasker.rb
```

### Method 3: Direct from URL

```bash
# Install directly from the raw formula URL
brew install https://raw.githubusercontent.com/sgleeson/claude-tools/main/claude-tasker.rb
```

## Post-Installation Setup

1. **Verify Installation**:
   ```bash
   claude-tasker --version
   ```

2. **Configure Claude CLI**:
   ```bash
   # If not already configured
   claude auth login
   ```

3. **Configure GitHub Access**:
   ```bash
   # Option 1: Use GitHub CLI
   gh auth login
   
   # Option 2: Use environment variable
   export GITHUB_TOKEN="your-github-token"
   ```

## Usage Examples

```bash
# Process a single GitHub issue
claude-tasker 123

# Process multiple issues
claude-tasker 100-110

# Review a pull request
claude-tasker --review-pr 456

# Analyze a bug and create an issue
claude-tasker --bug "Users cannot login after password reset"

# Interactive mode
claude-tasker 123 --interactive
```

## Updating

```bash
# Update to the latest version
brew upgrade claude-tasker
```

## Uninstalling

```bash
# Remove claude-tasker
brew uninstall claude-tasker
```

## Troubleshooting

### Common Issues

1. **Python Dependencies Error**:
   ```bash
   # Reinstall with verbose output
   brew reinstall claude-tasker --verbose --debug
   ```

2. **Missing Claude CLI**:
   - Install from: https://docs.anthropic.com/en/docs/claude-code
   - Verify with: `which claude`

3. **GitHub Authentication Failed**:
   ```bash
   # Check GitHub CLI status
   gh auth status
   
   # Re-authenticate if needed
   gh auth login
   ```

4. **Permission Errors**:
   ```bash
   # Fix Homebrew permissions
   sudo chown -R $(whoami) $(brew --prefix)/*
   ```

### Dependency Verification

Check that all dependencies are installed:

```bash
# Check Python
python3 --version  # Should be 3.11+

# Check GitHub CLI
gh --version

# Check jq
jq --version

# Check git
git --version

# Check Claude CLI
claude --version
```

## Formula Details

The Homebrew formula:
- Installs Python 3.11+ if not present
- Creates an isolated Python virtual environment
- Installs all Python dependencies (pydantic, rich, etc.)
- Sets up the `claude-tasker` command in your PATH
- Manages updates through Homebrew's standard mechanisms

## Development

To modify the formula for local testing:

1. Edit `claude-tasker.rb`
2. Test installation:
   ```bash
   brew uninstall claude-tasker 2>/dev/null || true
   brew install --build-from-source ./claude-tasker.rb
   ```
3. Run audit checks:
   ```bash
   brew audit --strict claude-tasker
   ```
4. Test the formula:
   ```bash
   brew test claude-tasker
   ```

## Support

For issues related to:
- **Claude Tasker**: Open an issue at [GitHub Issues](https://github.com/sgleeson/claude-tools/issues)
- **Homebrew Formula**: Check the formula file or open a PR with fixes
- **Claude CLI**: Refer to [Anthropic's documentation](https://docs.anthropic.com/en/docs/claude-code)