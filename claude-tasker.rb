class ClaudeTasker < Formula
  include Language::Python::Virtualenv

  desc "Context-aware wrapper for Claude Code with GitHub integration"
  homepage "https://github.com/ShaneGCareCru/claude-tools"
  url "https://github.com/ShaneGCareCru/claude-tools.git",
      revision: "f2f5a2cc195ba304f1004fc8a16f4b55a2f5c639"
  version "1.0.0"
  license "MIT"
  head "https://github.com/ShaneGCareCru/claude-tools.git", branch: "main"

  # Dependencies
  depends_on "gh"
  depends_on "git"
  depends_on "jq"
  depends_on "python@3.11" # Requires 3.11+ for modern typing support

  # Python package resources will be auto-generated when creating a versioned release
  # For development, install via: pip install -r requirements.txt

  def install
    # Pre-flight dependency validation
    validate_dependencies

    # Create virtual environment and install dependencies
    venv = virtualenv_create(libexec, "python3.11")

    # Install requirements manually
    venv.pip_install_and_link buildpath, link_manpages: false
    # Install specific dependencies
    dependencies = %w[typing-extensions pydantic python-json-logger colorlog rich]
    dependencies.each do |dep|
      venv.pip_install dep
    end

    # Create robust wrapper script with error handling
    (bin/"claude-tasker").write <<~EOS
      #!/bin/bash
      set -e

      # Skip claude validation in test mode or if version/help requested
      if [[ "$CLAUDE_TASKER_TEST_MODE" == "1" ]] || [[ "$1" == "--version" ]] || [[ "$1" == "--help" ]]; then
        # Minimal validation for test/help modes
        for cmd in gh jq git; do
          if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "Error: Required command '$cmd' not found in PATH" >&2
            exit 1
          fi
        done
      else
        # Full validation for normal operation
        for cmd in claude gh jq git; do
          if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "Error: Required command '$cmd' not found in PATH" >&2
            echo "Please ensure all dependencies are installed." >&2
            exit 1
          fi
        done
      fi

      # Set up Python environment
      export PYTHONPATH="#{libexec}/lib/python#{Language::Python.major_minor_version("python3")}/site-packages:$PYTHONPATH"
      export CLAUDE_TASKER_VERSION="#{version}"

      # Execute with proper error handling
      exec "#{libexec}/bin/python3" "#{libexec}/claude-tasker-py" "$@"
    EOS

    # Install the main script and source code
    libexec.install "claude-tasker-py"
    libexec.install "src"

    # Make the wrapper executable
    chmod 0755, bin/"claude-tasker"
  end

  private

  def validate_dependencies
    # Skip Claude CLI validation in CI/test environments
    return if ENV["CI"] || ENV["HOMEBREW_GITHUB_API_TOKEN"]

    missing_deps = []

    # Check for Claude CLI availability
    unless system "command -v claude >/dev/null 2>&1"
      missing_deps << "claude CLI (install from https://docs.anthropic.com/en/docs/claude-code)"
    end

    unless missing_deps.empty?
      odie "Missing required dependencies:\n#{missing_deps.map { |dep| "  - #{dep}" }.join("\n")}"
    end
  end

  def post_install
    ohai "Claude Tasker v#{version} has been installed successfully!"

    # Validate installation
    validation_errors = []

    # Check Claude CLI
    unless system "command -v claude >/dev/null 2>&1"
      validation_errors << "Claude CLI not found. Install from: https://docs.anthropic.com/en/docs/claude-code"
    end

    # Check GitHub authentication
    unless system "gh auth status >/dev/null 2>&1" || !ENV["GITHUB_TOKEN"].nil?
      validation_errors << "GitHub authentication required. Run 'gh auth login' or set GITHUB_TOKEN"
    end

    # Test basic functionality
    unless system "#{bin}/claude-tasker --version >/dev/null 2>&1"
      validation_errors << "claude-tasker binary test failed"
    end

    if validation_errors.empty?
      ohai "✓ All dependencies validated successfully!"
      ohai "Run 'claude-tasker --help' to get started."
    else
      opoo "Installation completed with warnings:"
      validation_errors.each { |error| opoo "  - #{error}" }
    end
  end

  def caveats
    <<~EOS
      Claude Tasker has been installed as 'claude-tasker'.

      To get started:
        1. Ensure 'claude' CLI is installed and configured
        2. Authenticate with GitHub: gh auth login
        3. Run: claude-tasker --help

      Example usage:
        claude-tasker 123                    # Process GitHub issue #123
        claude-tasker 100-110                # Process issues 100-110
        claude-tasker --review-pr 456        # Review PR #456
        claude-tasker --bug "description"    # Analyze bug
    EOS
  end

  test do
    # Integration test suite
    ENV["CLAUDE_TASKER_TEST_MODE"] = "1"

    # Test version output and basic functionality
    version_output = shell_output("#{bin}/claude-tasker --version 2>&1")
    assert_match "1.0.0", version_output

    # Test help command (should work without Claude CLI in test mode)
    help_output = shell_output("#{bin}/claude-tasker --help 2>&1")
    assert_match "Context-aware wrapper", help_output

    # Test Python module imports
    system libexec/"bin/python", "-c",
           "from claude_tasker.cli import main"

    # Test core dependencies are available
    %w[gh jq git].each do |dep|
      assert_predicate Formula[dep], :any_version_installed?
    end

    # Test Python dependencies are properly installed
    %w[pydantic rich colorlog].each do |pkg|
      system libexec/"bin/python", "-c", "import #{pkg}"
    end

    # Test configuration file validation
    (testpath/"test_config.json").write('{"test": true}')
    system libexec/"bin/python", "-c",
           "import json; json.load(open('#{testpath}/test_config.json'))"
  end
end
