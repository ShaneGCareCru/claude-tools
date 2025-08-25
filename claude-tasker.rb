class ClaudeTasker < Formula
  include Language::Python::Virtualenv

  desc "Context-aware wrapper for Claude Code with GitHub integration"
  homepage "https://github.com/sgleeson/claude-tools"
  url "https://github.com/sgleeson/claude-tools/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"
  head "https://github.com/sgleeson/claude-tools.git", branch: "main"

  # Dependencies
  depends_on "gh"
  depends_on "git"
  depends_on "jq"
  depends_on "python@3.11" # Requires 3.11+ for modern typing support

  # Core Python dependencies with verified SHA256 checksums
  resource "typing-extensions" do
    url "https://files.pythonhosted.org/packages/df/db/f35a00659bc03fec321ba8bce9420de607a1d37f8342eee1863174c69557/typing_extensions-4.12.2.tar.gz"
    sha256 "1a7ead55c7e559dd4dee8856e3a88b41225abfe1ce8df57b7c13915fe121ffb8"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/70/7e/fb60e6fee04d0ef8f15e4e01ff187a196fa976eb0f0ab524af4599e5754c/pydantic-2.10.4.tar.gz"
    sha256 "82f12e9723da6de4fe2ba888b5971157b3be7ad914267dea8f05f82b28254f06"
  end

  resource "pydantic-core" do
    url "https://files.pythonhosted.org/packages/fc/01/f3e5ac5e7c25833db5eb555f7b7ab24cd6f8c322d3a3ad2d67a952dc0abc/pydantic_core-2.27.2.tar.gz"
    sha256 "eb026e5a4c1fee05726072337ff51d1efb6f59090b7da90d30ea58625b1ffb39"
  end

  resource "annotated-types" do
    url "https://files.pythonhosted.org/packages/ee/67/531ea369ba64dcff5ec9c3402f9f51bf748cec26dde048a2f973a4eea7f5/annotated_types-0.7.0.tar.gz"
    sha256 "aff07c09a53a08bc8cfccb9c85b05f1aa9a2a6f23728d790723543408344ce89"
  end

  resource "python-json-logger" do
    url "https://files.pythonhosted.org/packages/e3/c4/358cd13daa1d912ef795010897a483ab2f0b41c9ea1b35235a8b2f7d15a7/python_json_logger-3.2.1.tar.gz"
    sha256 "8eb0554ea17cb75b05d2848bc14fb02fbdbd9d6972120781b974380bfa162008"
  end

  resource "colorlog" do
    url "https://files.pythonhosted.org/packages/d3/7a/359f4d5df2353f26172b3cc39ea32daa39af8de522205f512f458923e677/colorlog-6.9.0.tar.gz"
    sha256 "bfba54a1b93b94f54e1f4fe48395725a3d92fd2a4af702f6bd70946bdc0c6ac2"
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
    url "https://files.pythonhosted.org/packages/7c/2d/c3338d48ea6cc0feb8446d8e6937e1408088a72a39937982cc6111d17f84/pygments-2.19.1.tar.gz"
    sha256 "61c16d2a8576dc0649d9f39e089b5f02bcd27fba10d8fb4dcc28173f7a45151f"
  end

  def install
    # Pre-flight dependency validation
    validate_dependencies

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
           "from claude_tasker import __version__, main; assert __version__ == '1.0.0'"

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
