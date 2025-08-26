class ClaudeTasker < Formula
  include Language::Python::Virtualenv

  desc "Context-aware wrapper for Claude Code with GitHub integration"
  homepage "https://github.com/ShaneGCareCru/claude-tools"
  url "https://github.com/ShaneGCareCru/claude-tools/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "f847de908b8215401c931ec935a350dc386852abc3dd425a6e9292cf399c493a"
  license "MIT"
  head "https://github.com/ShaneGCareCru/claude-tools.git", branch: "main"

  # Dependencies
  depends_on "gh"
  depends_on "git"
  depends_on "jq"
  depends_on "python@3.11" # Requires 3.11+ for modern typing support

  # Python dependencies - using latest stable versions
  resource "typing-extensions" do
    url "https://files.pythonhosted.org/packages/df/db/f35a00659bc03fec321ba8bce9420de607a1d37f8342eee1863174c69557/typing_extensions-4.12.2.tar.gz"
    sha256 "1a7ead55c7e559dd4dee8856e3a88b41225abfe1ce8df57b7c13915fe121ffb8"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/41/86/a03390cb12cf64e2a8df07c267f3eb8d5035e0f9a04bb20fb79403d2a00e/pydantic-2.10.2.tar.gz"
    sha256 "2bc2d7f17232e0841cbba4641e65ba1eb6fafb3a08de3a091ff3ce14a197c4fa"
  end

  resource "pydantic-core" do
    url "https://files.pythonhosted.org/packages/a6/9f/7de1f19b6aea45aeb441838782d68352e71bfa98ee6fa048d5041991b33e/pydantic_core-2.27.1.tar.gz"
    sha256 "62a763352879b84aa31058fc931884055fd75089cccbd9d58bb6afd01141b235"
  end

  resource "annotated-types" do
    url "https://files.pythonhosted.org/packages/ee/67/531ea369ba64dcff5ec9c3402f9f51bf748cec26dde048a2f973a4eea7f5/annotated_types-0.7.0.tar.gz"
    sha256 "aff07c09a53a08bc8cfccb9c85b05f1aa9a2a6f23728d790723543408344ce89"
  end

  resource "python-json-logger" do
    url "https://files.pythonhosted.org/packages/4f/da/95963cebfc578dabd323d7263958dfb68898617912bb09327dd30e9c8d13/python-json-logger-2.0.7.tar.gz"
    sha256 "23e7ec02d34237c5aa1e29a070193a4ea87583bb4e7f8fd06d3de8264c4b2e1c"
  end

  resource "colorlog" do
    url "https://files.pythonhosted.org/packages/db/38/2992ff192eaa7dd5a793f8b6570d6bbe887c4fbbf7e72702eb0a693a01c8/colorlog-6.8.2.tar.gz"
    sha256 "3e3e079a41feb5a1b64f978b5ea4f46040a94f11f0e8bbb8261e3dbbeca64d44"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/ab/3a/0316b28d0761c6734d6bc14e770d85506c986c85ffb239e688eeaab2c2bc/rich-13.9.4.tar.gz"
    sha256 "439594978a49a09530cff7ebc4b5c7103ef57baf48d5ea3184f21d9a2befa098"
  end

  resource "markdown-it-py" do
    url "https://files.pythonhosted.org/packages/38/71/3b932df36c1a044d397a1f92d1cf91ee0a503d91e470cbd670aa66b07ed0/markdown-it-py-3.0.0.tar.gz"
    sha256 "e3f60a94fa066dc52ec76661e37c851cb232d92f9886b15cb560aaada2df8feb"
  end

  resource "mdurl" do
    url "https://files.pythonhosted.org/packages/d6/54/cfe61301667036ec958cb99bd3efefba235e65cdeb9c84d24a8293ba1d90/mdurl-0.1.2.tar.gz"
    sha256 "bb413d29f5eea38f31dd4754dd7377d4465116fb207585f97bf925588687c1ba"
  end

  resource "pygments" do
    url "https://files.pythonhosted.org/packages/8e/62/8336eff65bcbc8e4cb5d05b55faf041285951b6e80f33e2bff20247888f31/pygments-2.18.0.tar.gz"
    sha256 "786ff802f32e91311bff3889f6e9a86e81505fe99f2735bb6d60ae0c5004f199"
  end

  def install
    # Pre-flight dependency validation
    validate_dependencies

    # Use Homebrew's standard virtualenv pattern
    virtualenv_install_with_resources

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
      export CLAUDE_TASKER_VERSION="1.0.0"

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
