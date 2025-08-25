# Installing Claude Tasker via Homebrew

This guide explains how to install `claude-tasker` using Homebrew on macOS and Linux.

## Prerequisites

1. **Homebrew**: Install from [brew.sh](https://brew.sh) if not already installed
2. **Claude CLI**: Install from [Anthropic's documentation](https://docs.anthropic.com/en/docs/claude-code)
3. **GitHub Authentication**: Run `gh auth login` or set `GITHUB_TOKEN` environment variable
4. **System Requirements**: macOS 10.15+ or Linux with Python 3.11+ support

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
   # Option 1: Use GitHub CLI (recommended)
   gh auth login
   
   # Option 2: Use environment variable
   export GITHUB_TOKEN="your-github-token"
   ```

4. **Validate Setup**:
   ```bash
   # The formula automatically validates dependencies
   # Check that all required tools are available
   claude-tasker --help
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
   - The formula now validates Claude CLI during installation
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

5. **Command Not Found After Installation**:
   ```bash
   # Restart shell or reload PATH
   exec $SHELL
   
   # Check if claude-tasker is in PATH
   which claude-tasker
   ```

6. **Version Compatibility Issues**:
   ```bash
   # Check minimum versions are met
   python3 --version  # Should be 3.11+
   gh --version       # Should be 2.0+
   jq --version       # Should be 1.6+
   git --version      # Should be 2.30+
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

The enhanced Homebrew formula provides:

### Installation Features
- **Dependency Validation**: Pre-flight checks for required tools
- **Version Compatibility**: Enforces minimum versions for dependencies
- **Isolated Environment**: Python virtual environment with all dependencies
- **Error Handling**: Robust error messages and validation
- **Post-Install Validation**: Automatic verification of successful installation

### Security Features
- **SHA256 Verification**: All Python packages verified with checksums
- **Minimal Permissions**: No elevated privileges required
- **Conflict Detection**: Prevents conflicts with other claude-tasker installations

### Testing & Quality
- **Integration Tests**: Comprehensive test suite for formula functionality
- **CI/CD Validation**: GitHub Actions workflow for automated testing
- **Multi-Platform Support**: Tested on multiple macOS versions

## Development

To modify the formula for local testing:

1. Edit `claude-tasker.rb`
2. Validate formula syntax:
   ```bash
   brew audit --strict --online ./claude-tasker.rb
   ```
3. Test installation:
   ```bash
   brew uninstall claude-tasker 2>/dev/null || true
   brew install --build-from-source --verbose ./claude-tasker.rb
   ```
4. Run comprehensive tests:
   ```bash
   brew test claude-tasker
   ```
5. Test uninstall/reinstall cycle:
   ```bash
   brew uninstall claude-tasker
   brew install --build-from-source ./claude-tasker.rb
   ```

### Continuous Integration

The formula includes GitHub Actions workflows that automatically:
- Test formula installation on multiple macOS versions
- Validate formula syntax and compliance
- Test HEAD version installation
- Validate documentation completeness

### Version Management

The formula uses dynamic version management:
- Release tarballs instead of Git revisions
- Automatic SHA256 checksum validation
- Support for both stable and HEAD installations

## Support

For issues related to:
- **Claude Tasker**: Open an issue at [GitHub Issues](https://github.com/sgleeson/claude-tools/issues)
- **Homebrew Formula**: Check the formula file or open a PR with fixes
- **Claude CLI**: Refer to [Anthropic's documentation](https://docs.anthropic.com/en/docs/claude-code)