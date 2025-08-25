class ClaudeTasker < Formula
  include Language::Python::Virtualenv

  desc "Context-aware wrapper for Claude Code with GitHub integration"
  homepage "https://github.com/sgleeson/claude-tools"
  url "https://github.com/sgleeson/claude-tools.git", 
      tag: "v1.0.0", revision: "c39bc61d3f5e088b9e939e6a8cfe40d931fa5258"
  version "1.0.0"
  license "MIT"
  head "https://github.com/sgleeson/claude-tools.git", branch: "main"

  depends_on "python@3.11"
  depends_on "gh"
  depends_on "jq"
  depends_on "git"

  resource "typing-extensions" do
    url "https://files.pythonhosted.org/packages/df/db/f35a00659bc03fec321ba8bce9420de607a1d37f8342eee1863174c69557/typing_extensions-4.12.2.tar.gz"
    sha256 "1a7ead55c7e559dd4dee8856e3a88b41225abfe1ce8df57b7c13915fe121ffb8"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/df/e4/ba44652d562cbf0bf320e0f3810206149c8a4e99cdbf66da82e97ab53a15/pydantic-2.10.4.tar.gz"
    sha256 "82f12d6f4738ecb5b35b01ad57bb29233bfe405e15314d5e86e805785521ba41"
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
    url "https://files.pythonhosted.org/packages/3e/25/a1eb8dcf0bf6240b3be82508eebe67f5ac088241e5e42327ad8a72dc7a4e/python_json_logger-3.2.1.tar.gz"
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
    url "https://files.pythonhosted.org/packages/7c/82/91aaac5f025e86e49c373b3a8dcd4d3064a2c2cd2d0f17ad9586f5a19e14/pygments-2.19.1.tar.gz"
    sha256 "61c16d2a8576dc0649d9f39e089b5f02bcd27fba10d8fb4dcc28173f7a45151f"
  end

  def install
    virtualenv_install_with_resources

    # Create wrapper script that sets up the environment
    (bin/"claude-tasker").write <<~EOS
      #!/bin/bash
      export PYTHONPATH="#{libexec}/lib/python#{Language::Python.major_minor_version("python3")}/site-packages:$PYTHONPATH"
      exec "#{libexec}/bin/python3" "#{libexec}/claude-tasker-py" "$@"
    EOS
    
    # Install the main script and source code
    libexec.install "claude-tasker-py"
    libexec.install "src"
    
    # Make the wrapper executable
    chmod 0755, bin/"claude-tasker"
  end

  def post_install
    ohai "Claude Tasker has been installed successfully!"
    opoo "Make sure you have the 'claude' CLI installed and configured."
    opoo "You can install it from: https://docs.anthropic.com/en/docs/claude-code"
    
    if ENV["GITHUB_TOKEN"].nil?
      opoo "No GITHUB_TOKEN found in environment."
      opoo "Run: export GITHUB_TOKEN='your-token' or use 'gh auth login'"
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
    # Test version output
    assert_match "1.0.0", shell_output("#{bin}/claude-tasker --version 2>&1", 1)
    
    # Test Python import
    system libexec/"bin/python", "-c", "from claude_tasker import __version__; print(__version__)"
    
    # Test that dependencies are available
    %w[gh jq git].each do |dep|
      assert_predicate Formula[dep], :any_version_installed?
    end
  end
end