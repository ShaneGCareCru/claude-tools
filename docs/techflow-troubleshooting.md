# TechFlow Framework Troubleshooting Guide

This guide provides solutions to common issues encountered when using the TechFlow Demo Self-Testing Framework.

## Quick Diagnosis Commands

```bash
# Check framework health
python -c "from tests.techflow import TechFlowTestRunner, TestConfig; print('✅ Framework imports working')"

# Validate configuration
python -c "
from tests.techflow.config import TestConfig
config = TestConfig()
errors = config.validate()
print(f'Configuration errors: {len(errors)}')
for error in errors: print(f'  - {error}')
"

# Test CLI availability
python -m tests.techflow.cli --help
```

## Common Issues & Solutions

### 1. Authentication Errors

#### Symptom
```
ERROR - Configuration errors:
ERROR -   - Missing required environment variable: GITHUB_TOKEN
```

#### Diagnosis
```bash
# Check if token is set
echo ${GITHUB_TOKEN:-"NOT SET"}

# Check token format
echo $GITHUB_TOKEN | cut -c1-8
# Should output: ghp_ or github_pat_
```

#### Solutions
```bash
# Set GitHub token (classic)
export GITHUB_TOKEN="ghp_your_token_here"

# Or use fine-grained token
export GITHUB_TOKEN="github_pat_your_token_here"

# Verify token works
gh auth status
```

#### Prevention
- Generate tokens with appropriate scopes (repo, workflow)
- Store securely in environment or CI secrets
- Regularly rotate tokens for security

### 2. CLI Execution Timeouts

#### Symptom
```
ERROR - Command timed out after 900 seconds
```

#### Diagnosis
```bash
# Check system resources
top -l 1 | head -5

# Test CLI directly
./claude-tasker-py --help

# Check for stuck processes
ps aux | grep claude-tasker
```

#### Solutions
```bash
# Increase timeout
python -m tests.techflow.cli --timeout 1800  # 30 minutes

# Set environment variable
export TEST_TIMEOUT_SECONDS=1800

# Kill stuck processes
pkill -f claude-tasker
```

#### Prevention
- Monitor system resources before running tests
- Use appropriate timeouts for your environment
- Clean up processes between test runs

### 3. Quality Gate Failures

#### Symptom
```
ERROR - Bug issue failed quality validation
ERROR - Missing required sections: ['Root Cause Analysis', 'Test Plan']
```

#### Diagnosis
```bash
# Enable debug logging
CLAUDE_LOG_LEVEL=DEBUG python -m tests.techflow.cli

# Check generated content
cat test-results/run-*/artifacts/issue_*.json | jq '.content'

# Validate specific issue manually
python -c "
from tests.techflow.validators import BugIssueValidator
from tests.techflow.config import QualityGates
validator = BugIssueValidator(QualityGates())
result = validator._generate_test_bug_description()
print(result)
"
```

#### Solutions
```bash
# Use custom bug description
python -m tests.techflow.cli --bug "$(cat custom-bug-description.txt)"

# Adjust quality gates
python -c "
from tests.techflow.config import TestConfig, QualityGates
config = TestConfig()
config.quality_gates.bug_required_sections = 6  # Lower requirement
"

# Check prompt templates
grep -r "Bug Description\|Acceptance Criteria" tests/techflow/
```

#### Prevention
- Use comprehensive bug description templates
- Validate bug descriptions before using them
- Configure quality gates appropriate for your use case

### 4. Branch Management Issues

#### Symptom
```
ERROR - Branch 'issue-1-12345' indicates issue #1 but processing issue #2
WARNING - Branch validation failed
```

#### Diagnosis
```bash
# Check current branch
git branch --show-current

# List all branches
git branch -a | grep issue-

# Check branch strategy
echo ${CLAUDE_BRANCH_STRATEGY:-"default: reuse"}
```

#### Solutions
```bash
# Use always_new strategy
python -m tests.techflow.cli --branch-strategy always_new

# Clean up old branches
git branch -D $(git branch | grep issue- | head -5)

# Force branch creation
export CLAUDE_BRANCH_STRATEGY=always_new
```

#### Prevention
- Use consistent branch naming conventions
- Clean up stale branches regularly
- Choose appropriate branch strategy for your workflow

### 5. Rate Limiting Issues

#### Symptom
```
ERROR - API rate limit exceeded
ERROR - Too many requests in the last hour
```

#### Diagnosis
```bash
# Check API rate limit status
gh api rate_limit

# Check recent API usage
gh api /user | jq '.login'
```

#### Solutions
```bash
# Wait for rate limit reset
python -c "import time; time.sleep(3600)"  # 1 hour

# Use different token
export GITHUB_TOKEN="your_secondary_token"

# Reduce request frequency
python -m tests.techflow.cli --timeout 1800 --max-retries 1
```

#### Prevention
- Monitor API usage with multiple repositories
- Use dedicated tokens for testing
- Implement request caching where possible

### 6. Import/Module Errors

#### Symptom
```
ModuleNotFoundError: No module named 'tests.techflow'
```

#### Diagnosis
```bash
# Check Python path
python -c "import sys; print('\\n'.join(sys.path))"

# Check if module exists
ls -la tests/techflow/

# Test basic import
python -c "import tests.techflow"
```

#### Solutions
```bash
# Run from project root
cd /path/to/claude-tools

# Add to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Install in development mode
pip install -e .
```

#### Prevention
- Always run from project root directory
- Set up proper Python environment
- Use virtual environments consistently

### 7. GitHub CLI Issues

#### Symptom
```
ERROR - GitHub CLI not found or not working properly
```

#### Diagnosis
```bash
# Check if gh CLI is installed
which gh

# Check gh version
gh --version

# Test gh authentication
gh auth status
```

#### Solutions
```bash
# Install GitHub CLI (macOS)
brew install gh

# Install GitHub CLI (Ubuntu)
sudo apt install gh

# Authenticate
gh auth login
```

#### Prevention
- Include gh CLI in your environment setup
- Verify authentication before running tests
- Keep gh CLI updated

## Advanced Troubleshooting

### Enable Debug Logging

```bash
# Maximum verbosity
export CLAUDE_LOG_LEVEL=DEBUG
export CLAUDE_LOG_PROMPTS=true
export CLAUDE_LOG_RESPONSES=true
export CLAUDE_LOG_DECISIONS=true

python -m tests.techflow.cli --log-level DEBUG
```

### Analyze Test Results

```bash
# Find recent test results
find test-results -name "run_data.json" -type f | head -5

# Extract key information
cat test-results/run-*/run_data.json | jq '{
  success: .success,
  quality_score: .quality_score,
  duration: .duration,
  failures: .failures | length
}'

# Check failure patterns
grep -h "ERROR\|FAILURE" test-results/run-*/test_run.log | sort | uniq -c
```

### Performance Analysis

```bash
# Check execution times
grep "Duration:" test-results/run-*/test_run.log

# Monitor system resources during execution
# (Run in separate terminal)
while true; do
  echo "$(date): CPU=$(top -l 1 | grep "CPU usage" | awk '{print $3}'), Memory=$(top -l 1 | grep PhysMem | awk '{print $2}')"
  sleep 10
done
```

### Log Analysis Patterns

```bash
# Authentication issues
grep -i "auth\|token\|unauthorized\|forbidden" test-results/run-*/test_run.log

# Rate limiting
grep -i "rate.limit\|too.many\|quota" test-results/run-*/test_run.log

# Quality gate failures
grep -i "validation.*failed\|quality.*gate\|missing.*section" test-results/run-*/test_run.log

# Timeout issues
grep -i "timeout\|timed.out\|exceeded.*time" test-results/run-*/test_run.log

# Branch issues
grep -i "branch\|checkout\|merge\|conflict" test-results/run-*/test_run.log
```

## Environment-Specific Issues

### macOS

```bash
# Fix permission issues
chmod +x ./claude-tasker-py

# Use Homebrew for dependencies
brew install gh jq

# Check Python version
python3 --version  # Use python3 explicitly
```

### Ubuntu/Linux

```bash
# Install required packages
sudo apt update
sudo apt install python3-pip git curl jq

# Install GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install gh
```

### Windows (WSL)

```bash
# Use Windows Subsystem for Linux
wsl --install

# In WSL, follow Ubuntu instructions
# Ensure proper line endings
git config --global core.autocrlf input
```

### CI/CD Environments

```bash
# GitHub Actions debugging
echo "::debug::TechFlow test starting"
env | grep -E "(GITHUB|CLAUDE|TEST)_" | sort

# Set up proper permissions
chmod +x ./claude-tasker-py
export GITHUB_TOKEN="${{ secrets.GITHUB_TOKEN }}"
```

## Recovery Procedures

### Clean Slate Recovery

```bash
# Complete environment reset
cd /path/to/claude-tools

# Clean up test artifacts
rm -rf test-results/
rm -rf .pytest_cache/
rm -rf __pycache__/

# Reset git state
git status
git clean -fd  # If needed

# Reinstall dependencies
pip uninstall -r requirements.txt -y
pip install -r requirements.txt

# Test basic functionality
python -m tests.techflow.cli --help
```

### Partial Recovery

```bash
# Reset only test results
rm -rf test-results/run-*

# Clean Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -exec rm -rf {} +

# Restart from clean state
python -m tests.techflow.cli
```

## Preventive Measures

### Pre-run Checklist

```bash
#!/bin/bash
# pre-run-check.sh

echo "TechFlow Pre-run Health Check"
echo "=============================="

# 1. Check Python
python3 --version || echo "❌ Python not found"

# 2. Check dependencies
python -c "import tests.techflow" && echo "✅ TechFlow imports" || echo "❌ Import failed"

# 3. Check GitHub token
[ -n "$GITHUB_TOKEN" ] && echo "✅ GitHub token set" || echo "❌ No GitHub token"

# 4. Check GitHub CLI
gh --version >/dev/null 2>&1 && echo "✅ GitHub CLI available" || echo "❌ GitHub CLI missing"

# 5. Check claude-tasker CLI
./claude-tasker-py --help >/dev/null 2>&1 && echo "✅ Claude Tasker CLI works" || echo "❌ Claude Tasker CLI issue"

# 6. Check git status
[ -z "$(git status --porcelain)" ] && echo "✅ Git working tree clean" || echo "⚠️  Uncommitted changes"

echo "=============================="
echo "Health check complete"
```

### Monitoring Setup

```bash
# Set up log monitoring
tail -f test-results/run-*/test_run.log &

# Monitor resource usage
watch -n 5 'top -l 1 | head -10'

# Set up alerts for long-running tests
timeout 1800 python -m tests.techflow.cli || echo "Test exceeded 30 minutes"
```

## Getting Help

### Information to Collect

Before reporting issues, collect:

1. **System information**:
   ```bash
   python -c "
   import platform, sys
   print(f'OS: {platform.system()} {platform.release()}')
   print(f'Python: {sys.version}')
   "
   ```

2. **Framework version**:
   ```bash
   python -c "from tests.techflow import __version__; print(__version__)"
   ```

3. **Configuration**:
   ```bash
   python -c "
   from tests.techflow.config import TestConfig
   config = TestConfig.from_environment()
   print(f'CLI Path: {config.cli_path}')
   print(f'Timeout: {config.timeout_seconds}')
   print(f'Strategy: {config.branch_strategy}')
   "
   ```

4. **Recent logs**:
   ```bash
   find test-results -name "test_run.log" -exec tail -20 {} \;
   ```

### Support Channels

1. **Check existing documentation**
2. **Search GitHub issues**
3. **Create detailed bug report with collected information**
4. **Include reproducible test case**

---

*This troubleshooting guide is maintained as part of the TechFlow Framework. Please contribute improvements and additional solutions.*