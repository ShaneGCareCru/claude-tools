# TechFlow Demo Self-Testing Framework

## Overview

The TechFlow Demo Self-Testing Framework is a comprehensive testing system designed to validate the complete bug-to-resolution workflow of the claude-tasker tool. It provides automated quality validation, diagnostic capabilities, and detailed reporting to ensure the reliability and effectiveness of our LLM-driven development process.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Quality Gates](#quality-gates)
- [Diagnostics & Remediation](#diagnostics--remediation)
- [Evidence & Reporting](#evidence--reporting)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)

## Features

### 🎯 **Automated Quality Validation**
- **Bug Issue Quality**: Validates 8 required sections, acceptance criteria, content quality
- **Pull Request Quality**: Ensures issue linking, file changes, proper targeting
- **Review Quality**: Checks placement, specificity, response times
- **Feedback Loop**: Validates comment addressing and iteration cycles

### 🔧 **Diagnostic & Remediation**
- **Intelligent Failure Analysis**: Pattern-based root cause identification
- **Automated Recovery**: Self-healing capabilities for common failures
- **Confidence Scoring**: 0.0-1.0 accuracy assessment for diagnoses
- **Remediation Strategies**: 7 built-in recovery mechanisms

### 📊 **Comprehensive Reporting**
- **Multi-format Output**: HTML, Markdown, and JSON reports
- **Quality Scoring**: 0-5 scale with weighted criteria assessment
- **Visual Dashboards**: Rich HTML reports with metrics and timelines
- **Evidence Collection**: Complete artifact and log preservation

### 🚀 **CI/CD Ready**
- **GitHub Actions Integration**: Scheduled and on-demand testing
- **Flexible Configuration**: Environment variables and CLI options
- **Failure Notifications**: Automated issue creation on test failures
- **Performance Monitoring**: Quality trends and execution metrics

## Architecture

```
TechFlow Framework
├── Core Engine (test_runner.py)
│   ├── TechFlowTestRunner - Main orchestrator
│   ├── CLICommandWrapper - Structured command execution
│   └── Test Data Models - TestRun, TestArtifact, TestFailure
│
├── Quality Validators (validators/)
│   ├── BugIssueValidator - Issue quality assessment
│   ├── PullRequestValidator - PR validation
│   ├── ReviewValidator - Review quality checks
│   └── FeedbackValidator - Feedback loop validation
│
├── Diagnostics (diagnostics/)
│   ├── DiagnosticEngine - Failure analysis orchestrator
│   ├── TriageMatrix - Pattern-based cause identification
│   └── RemediationEngine - Automated recovery strategies
│
├── Evidence System (evidence/)
│   ├── EvidenceCollector - Artifact and log collection
│   ├── ReportGenerator - Multi-format report generation
│   └── ReportTemplates - HTML/Markdown templates
│
└── CLI Interface (cli.py)
    ├── Command-line argument parsing
    ├── Configuration management
    └── Execution orchestration
```

## Installation

### Prerequisites

- **Python 3.9+**
- **GitHub CLI** (`gh` command)
- **Git**
- **Claude Tasker CLI** (`./claude-tasker-py`)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Environment Setup

```bash
export GITHUB_TOKEN="your_github_token_here"
export CLAUDE_LOG_LEVEL="INFO"  # Optional
export CLAUDE_BRANCH_STRATEGY="reuse"  # Optional
```

## Quick Start

### Basic Test Run

```bash
# Run full test cycle with defaults
python -m tests.techflow.cli

# Run with custom bug description
python -m tests.techflow.cli --bug "Test authentication bug fix"

# Run with increased timeout and retries
python -m tests.techflow.cli --timeout 1800 --max-retries 5
```

### Configuration Options

```bash
# Interactive mode
python -m tests.techflow.cli --interactive

# Custom CLI path
python -m tests.techflow.cli --cli-path ./my-claude-tasker

# Always create new branches
python -m tests.techflow.cli --branch-strategy always_new

# Skip evidence collection
python -m tests.techflow.cli --no-evidence
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub API token (**required**) | None |
| `CLAUDE_LOG_LEVEL` | Log level (DEBUG/INFO/WARNING/ERROR) | `INFO` |
| `CLAUDE_BRANCH_STRATEGY` | Branch strategy (reuse/always_new) | `reuse` |
| `TEST_MAX_RETRIES` | Maximum retry attempts | `3` |
| `TEST_TIMEOUT_SECONDS` | Test timeout in seconds | `900` |
| `TEST_BACKOFF_FACTOR` | Retry backoff multiplier | `2.0` |
| `TECHFLOW_REPO_PATH` | Path to test repository | Current directory |

### Quality Gate Configuration

```python
from tests.techflow.config import TestConfig, QualityGates

# Custom quality gates
quality_gates = QualityGates(
    bug_required_sections=8,
    bug_min_acceptance_criteria=3,
    pr_must_link_issue=True,
    review_min_specific_comments=1
)

config = TestConfig(
    timeout_seconds=1200,
    quality_gates=quality_gates
)
```

## Usage

### Command Line Interface

The framework provides a comprehensive CLI with multiple options:

```bash
python -m tests.techflow.cli [OPTIONS]

Options:
  --bug TEXT                    Custom bug description
  --cli-path TEXT               Path to claude-tasker CLI
  --branch-strategy CHOICE      Branch creation strategy
  --timeout INTEGER             Timeout in seconds
  --max-retries INTEGER         Maximum retries
  --interactive                 Interactive mode
  --output-dir TEXT             Results directory
  --log-level CHOICE            Log level
  --no-evidence                 Skip evidence collection
  --report-only                 Generate report only
  --run-id TEXT                 Run ID for report generation
```

### Python API

```python
from tests.techflow import TechFlowTestRunner, TestConfig

# Create configuration
config = TestConfig(
    cli_path='./claude-tasker-py',
    branch_strategy='reuse',
    timeout_seconds=900,
    max_retries=3
)

# Run test
runner = TechFlowTestRunner(config)
result = runner.run_full_cycle("Custom bug description")

# Check results
print(f"Success: {result.success}")
print(f"Quality Score: {result.quality_score}/5.0")
print(f"Duration: {result.duration}s")

if result.evidence_path:
    print(f"Evidence: {result.evidence_path}")
```

### Integration with Existing Code

```python
# Validate individual components
from tests.techflow.validators import ValidatorRegistry
from tests.techflow.config import QualityGates

registry = ValidatorRegistry(QualityGates())

# Validate bug issue
issue_result = registry.validate_bug_issue(123)
print(f"Issue valid: {issue_result.valid}")
print(f"Score: {issue_result.score}/5.0")

# Validate pull request
pr_result = registry.validate_pull_request(456)
print(f"PR valid: {pr_result.valid}")
```

## Quality Gates

### Bug Issue Validation

**Required Sections (8 total):**
- Bug Description
- Reproduction Steps
- Expected Behavior
- Actual Behavior
- Root Cause Analysis
- Acceptance Criteria (≥3 items)
- Test Plan
- Rollback Plan

**Quality Criteria:**
- Title descriptiveness
- Section content length (≥50 characters)
- Acceptance criteria completeness
- Overall structure and formatting

### Pull Request Validation

**Requirements:**
- Must link to an issue (`#123`, `fixes #123`, etc.)
- Must have actual file changes
- Must target `main` branch
- Must have descriptive title and body

**Quality Assessment:**
- Issue linking accuracy
- Change scope appropriateness
- Description quality and structure
- Metadata completeness

### Review Validation

**Requirements:**
- Must be on PR (not issue comments)
- Must have specific, actionable feedback
- Reasonable response time (<24 hours)
- Appropriate review state progression

**Quality Metrics:**
- Specificity ratio (specific vs generic comments)
- Actionability score (actionable feedback percentage)
- Response time efficiency
- Review progression quality

### Feedback Loop Validation

**Requirements:**
- Review comments must be addressed
- Reasonable iteration count (<3 rounds)
- Proper commit message references
- Final approval state

**Assessment Criteria:**
- Feedback addressing completeness
- Iteration efficiency
- Communication quality
- Resolution timeliness

## Diagnostics & Remediation

### Failure Analysis

The diagnostic engine uses pattern-based analysis to identify root causes:

```python
from tests.techflow.diagnostics import DiagnosticEngine, TriageMatrix

# Analyze failure
engine = DiagnosticEngine(config)
diagnosis = engine.diagnose_failure(test_run, "bug_creation")

print(f"Primary Cause: {diagnosis.primary_cause}")
print(f"Confidence: {diagnosis.confidence_score}")
print(f"Recommended Actions: {diagnosis.recommended_actions}")
```

### Common Failure Patterns

| Failure Type | Symptoms | Primary Causes | Remediation |
|-------------|----------|----------------|-------------|
| **CLI Execution Failed** | Timeout, permission denied | Environment, auth, rate limits | Increase timeout, check credentials |
| **Issue Parsing Failed** | Parse errors, format issues | Output format changes | Update parsing logic |
| **Quality Gate Failed** | Missing sections, criteria | Content generation issues | Improve prompts |
| **PR Creation Failed** | No PR created, push failures | Branch issues, permissions | Branch strategy change |

### Automated Remediation

The framework automatically applies fixes for common issues:

```python
# Automatic remediation strategies
REMEDIATION_STRATEGIES = {
    'timeout': ['increase_timeout', 'retry_with_backoff'],
    'auth_failure': ['check_github_token', 'refresh_credentials'],
    'rate_limit': ['apply_exponential_backoff', 'switch_token'],
    'branch_issues': ['create_new_branch', 'cleanup_stale_branches']
}
```

## Evidence & Reporting

### Evidence Collection

All test runs generate comprehensive evidence:

```
test-results/
├── run-{id}/
│   ├── run_data.json          # Raw test data
│   ├── artifacts/             # Generated artifacts
│   │   ├── issue_123.json
│   │   └── pr_456.json
│   ├── reports/               # Generated reports
│   │   ├── report.html
│   │   ├── summary.md
│   │   └── summary.json
│   └── test_run.log          # Execution logs
```

### Report Formats

#### HTML Reports
Rich, interactive reports with:
- Visual status indicators
- Metrics dashboard
- Timeline view
- Failure analysis
- Recommendations

#### Markdown Reports
GitHub-friendly summaries:
```markdown
# TechFlow Test Report

**Status:** ✅ PASSED  
**Quality Score:** 4.2/5.0 (Good)  
**Duration:** 180.5s

## Artifacts Created
- Issue: #123 - [View](https://github.com/repo/issues/123)
- PR: #456 - [View](https://github.com/repo/pull/456)

## Recommendations
- Test run completed successfully - no action needed
```

#### JSON Reports
Programmatic access to all data:
```json
{
  "run_id": "abc123",
  "success": true,
  "quality_score": 4.2,
  "duration": 180.5,
  "artifacts": [...],
  "failures": [...],
  "recommendations": [...]
}
```

### Quality Scoring

Quality scores (0-5 scale) are calculated using weighted criteria:

- **Completeness (30%)**: All phases completed successfully
- **Quality (40%)**: Validator results and content quality
- **Timeliness (20%)**: Execution speed and efficiency
- **Correctness (10%)**: Retry count and error frequency

```
Score ≥ 4.5: Excellent (Green)
Score ≥ 3.5: Good (Blue)
Score ≥ 2.5: Fair (Orange)
Score < 2.5: Poor (Red)
```

## CI/CD Integration

### GitHub Actions Workflow

The framework includes a comprehensive CI/CD workflow:

```yaml
# .github/workflows/techflow-tests.yml
name: TechFlow Self-Testing Framework

on:
  workflow_dispatch:     # Manual trigger
  schedule:             # Daily at 2 AM UTC
    - cron: '0 2 * * *'
  push:                 # On framework changes
    paths: ['tests/techflow/**']

jobs:
  unit-tests:           # Framework unit tests
  integration-tests:    # Integration testing
  full-workflow-test:   # End-to-end testing
  quality-analysis:     # Security & quality checks
  notify-failure:       # Automated issue creation
```

### Scheduled Testing

- **Daily Tests**: Basic validation and health checks
- **Weekly Tests**: Full workflow validation
- **On-Demand**: Manual trigger with custom parameters

### Quality Monitoring

The CI system tracks:
- Test pass rates over time
- Quality score trends
- Performance metrics
- Failure patterns

## Troubleshooting

### Common Issues

#### Authentication Failures
```bash
# Check token format
echo $GITHUB_TOKEN | cut -c1-8
# Should start with "ghp_" or "github_pat_"

# Verify permissions
gh auth status
```

#### CLI Execution Timeouts
```bash
# Increase timeout
python -m tests.techflow.cli --timeout 1800

# Check system resources
top -l 1 | grep "CPU usage"
```

#### Quality Gate Failures
```bash
# Run with debug logging
CLAUDE_LOG_LEVEL=DEBUG python -m tests.techflow.cli

# Check generated content
cat test-results/run-*/artifacts/issue_*.json | jq '.content'
```

### Debug Mode

Enable comprehensive debugging:

```bash
export CLAUDE_LOG_LEVEL=DEBUG
export CLAUDE_LOG_PROMPTS=true
export CLAUDE_LOG_RESPONSES=true

python -m tests.techflow.cli --log-level DEBUG
```

### Log Analysis

Key log patterns to look for:

```bash
# Authentication issues
grep -i "auth\|token\|unauthorized" test-results/run-*/test_run.log

# Rate limiting
grep -i "rate.limit\|too.many.requests" test-results/run-*/test_run.log

# Quality gate failures
grep -i "validation.*failed\|quality.*gate" test-results/run-*/test_run.log
```

## API Reference

### Core Classes

#### TechFlowTestRunner
```python
class TechFlowTestRunner:
    def __init__(self, config: TestConfig)
    def run_full_cycle(self, bug_description: str = None) -> TestRun
```

#### TestConfig
```python
@dataclass
class TestConfig:
    cli_path: str = './claude-tasker-py'
    branch_strategy: str = 'reuse'
    timeout_seconds: int = 900
    max_retries: int = 3
    quality_gates: QualityGates = field(default_factory=QualityGates)
```

#### ValidationResult
```python
@dataclass
class ValidationResult:
    valid: bool
    score: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
```

### Validator Registry

```python
from tests.techflow.validators import ValidatorRegistry

registry = ValidatorRegistry(quality_gates)

# Validate components
issue_result = registry.validate_bug_issue(123)
pr_result = registry.validate_pull_request(456) 
review_result = registry.validate_review(456)
feedback_result = registry.validate_feedback_loop(456)
```

### Diagnostic Engine

```python
from tests.techflow.diagnostics import DiagnosticEngine

engine = DiagnosticEngine(config)

# Diagnose failures
diagnosis = engine.diagnose_failure(test_run, "stage_name")
success = engine.try_remediation(test_run, "stage_name")
report = engine.generate_diagnostic_report(test_run)
```

### Evidence Collection

```python
from tests.techflow.evidence import EvidenceCollector

collector = EvidenceCollector(config)
evidence_path = collector.collect_run_summary(test_run)
system_info = collector.collect_system_info()
```

## Contributing

### Development Setup

1. **Clone the repository**
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Set up pre-commit hooks**: `pre-commit install`
4. **Run tests**: `python -m pytest tests/test_techflow_*.py`

### Testing

```bash
# Unit tests
python -m pytest tests/test_techflow_*.py -v

# Integration tests
GITHUB_TOKEN=your_token python -m tests.techflow.cli --help

# Coverage report
python -m pytest tests/test_techflow_*.py --cov=tests.techflow
```

### Code Style

- **PEP 8** compliance
- **Type hints** for all functions
- **Docstrings** for classes and methods
- **Comprehensive error handling**

---

## Support

For issues, questions, or contributions:

1. **Check the troubleshooting guide** above
2. **Search existing issues** on GitHub
3. **Create a new issue** with detailed information
4. **Include logs and evidence** for faster resolution

**Generated by TechFlow Framework v1.0.0**