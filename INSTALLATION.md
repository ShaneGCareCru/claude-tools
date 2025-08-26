# Installation Guide

## Quick Start: Download Pre-built Binaries

The easiest way to install claude-tasker is to download the pre-built macOS binaries from GitHub Releases.

### 1. Download the Binary

Go to the [GitHub Releases page](https://github.com/ShaneGCareCru/claude-tools/releases) and download the appropriate binary for your Mac:

- **Apple Silicon (M1/M2/M3)**: `claude-tasker-arm64`
- **Intel Macs**: `claude-tasker-x86_64`

### 2. Make it Executable and Install

```bash
# Download and make executable
chmod +x claude-tasker-*

# Move to your PATH (optional but recommended)
sudo mv claude-tasker-* /usr/local/bin/claude-tasker

# Test installation
claude-tasker --version
claude-tasker --help
```

### 3. First-time Setup

If macOS blocks the binary with a security warning:

```bash
# Remove quarantine attribute (one-time setup)
xattr -d com.apple.quarantine /usr/local/bin/claude-tasker
```

Alternatively, you can right-click the binary in Finder and select "Open" to bypass Gatekeeper.

## Development Installation

If you want to develop or modify claude-tasker, install from source:

### Prerequisites

- Python 3.11 or higher
- Git
- GitHub CLI (`gh`)
- `jq` command-line JSON processor

### Install from Source

```bash
# Clone the repository
git clone https://github.com/ShaneGCareCru/claude-tools.git
cd claude-tools

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip wheel
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Test installation
claude-tasker --version
```

### Building Your Own Binary

If you want to build your own single-file executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Build binary (safe flags for bundling compiled extensions)
pyinstaller --onefile \
  --name claude-tasker \
  --collect-all pydantic_core \
  --collect-all pydantic \
  --collect-all PyGithub \
  --collect-all click \
  --collect-all rich \
  --collect-all python_dotenv \
  --collect-all colorlog \
  --collect-all python_json_logger \
  -p src \
  -s \
  src/claude_tasker/cli.py

# Your binary will be in dist/claude-tasker
./dist/claude-tasker --help
```

## Dependencies

The pre-built binaries are self-contained and include all Python dependencies. However, you'll still need these external tools:

- **GitHub CLI (`gh`)**: For GitHub API interactions
- **Git**: For repository operations
- **Claude CLI**: For executing prompts (install separately)
- **jq**: For JSON processing

### Installing External Dependencies

```bash
# macOS with Homebrew
brew install gh git jq

# Install Claude CLI
# Follow instructions at: https://claude.ai/code
```

## Verification

After installation, verify everything works:

```bash
# Check claude-tasker
claude-tasker --version

# Check dependencies
gh --version
git --version
jq --version
claude --version
```

## Troubleshooting

### "Command not found: claude-tasker"

The binary isn't in your PATH. Either:
- Move it to `/usr/local/bin/claude-tasker`
- Add its location to your PATH: `export PATH="/path/to/claude-tasker:$PATH"`

### "Cannot be opened because the developer cannot be verified"

This is macOS Gatekeeper. Fix it with:
```bash
xattr -d com.apple.quarantine /path/to/claude-tasker-*
```

### "Import Error" or "Module Not Found"

If using the pre-built binary, this shouldn't happen. If it does:
1. Try downloading the binary again
2. Check you downloaded the right architecture (ARM vs Intel)
3. File an issue on GitHub with your macOS version and error details

### Binary Size Concerns

The self-contained binaries are ~50-80MB because they include the Python runtime and all dependencies. This is normal for PyInstaller-built applications.

## Updating

### Pre-built Binaries

1. Download the latest version from GitHub Releases
2. Replace your existing binary
3. Run `claude-tasker --version` to confirm

### Development Installation

```bash
cd claude-tools
git pull origin main
pip install -r requirements.txt  # if dependencies changed
```

## Next Steps

Once installed, see the main README for usage examples and configuration options.