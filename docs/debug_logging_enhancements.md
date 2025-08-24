# Debug Logging Enhancements

## Overview

The claude-tasker tool now includes comprehensive debug logging capabilities that provide complete transparency into prompt generation, decision-making processes, and response handling. These enhancements enable developers to understand exactly what the tool is doing at every step of execution.

## Key Features

### 1. Complete Prompt Logging
- **Full Meta-Prompts**: All meta-prompts generated during two-stage execution are logged in their entirety when DEBUG mode is enabled
- **Optimized Prompts**: Complete optimized prompts sent to Claude are logged without truncation in DEBUG mode
- **PR Review Prompts**: Full PR review prompts are captured and logged
- **Bug Analysis Prompts**: Complete bug analysis prompts are logged for debugging

### 2. Decision-Making Transparency
- **Branch Validation**: Detailed logging of branch validation logic with clear reasoning
- **Environment Validation**: Complete visibility into dependency checks and validation decisions
- **Fallback Logic**: Clear logging when falling back between Claude and LLM tools
- **Execution Mode Decisions**: Transparent logging of prompt-only vs execution mode choices

### 3. Response Processing Visibility
- **Full Response Logging**: Complete Claude responses are logged in DEBUG mode
- **Error Analysis**: Detailed error response logging with full context
- **Success Criteria**: Clear logging of response validation and success determination
- **Response Metadata**: Additional response metadata (tokens, timing, etc.) is captured

### 4. Configuration Options

#### Environment Variables
```bash
# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
export CLAUDE_LOG_LEVEL=DEBUG

# Enable/disable full prompt logging in DEBUG mode
export CLAUDE_LOG_PROMPTS=true

# Enable/disable full response logging in DEBUG mode  
export CLAUDE_LOG_RESPONSES=true

# Maximum length before truncation (default: 10000)
export CLAUDE_LOG_TRUNCATE_LENGTH=5000

# Enable JSON structured logging
export CLAUDE_LOG_JSON=true

# Enable sensitive data sanitization
export CLAUDE_LOG_SANITIZE=true

# Log file configuration
export CLAUDE_LOG_FILE=claude_tasker.log
export CLAUDE_LOG_DIR=logs
export CLAUDE_LOG_MAX_BYTES=10485760  # 10MB
export CLAUDE_LOG_BACKUP_COUNT=5
```

#### Programmatic Configuration
```python
from src.claude_tasker.logging_config import setup_logging

# Configure with specific options
setup_logging(
    log_level='DEBUG',
    log_prompts=True,
    log_responses=True,
    truncate_length=5000,
    sanitize_logs=True,
    enable_json=True,
    log_file='debug.log'
)
```

## Usage Examples

### Basic Debug Mode
```bash
# Enable debug logging for a single issue
CLAUDE_LOG_LEVEL=DEBUG ./claude-tasker-py 123
```

### Full Transparency Mode
```bash
# Maximum logging detail
export CLAUDE_LOG_LEVEL=DEBUG
export CLAUDE_LOG_PROMPTS=true
export CLAUDE_LOG_RESPONSES=true
export CLAUDE_LOG_TRUNCATE_LENGTH=50000

./claude-tasker-py 123
```

### Production Mode with Sanitization
```bash
# Safe for production with sensitive data redaction
export CLAUDE_LOG_LEVEL=INFO
export CLAUDE_LOG_SANITIZE=true
export CLAUDE_LOG_FILE=production.log

./claude-tasker-py 123
```

## Log Output Examples

### Stage Execution Logging
```
2024-01-15 10:30:15 - prompt_builder - INFO - Starting two-stage prompt execution for task type: issue_implementation
2024-01-15 10:30:15 - prompt_builder - INFO - Stage 1: Generating meta-prompt
2024-01-15 10:30:15 - prompt_builder - DEBUG - ================================================================================
2024-01-15 10:30:15 - prompt_builder - DEBUG - META-PROMPT GENERATED:
2024-01-15 10:30:15 - prompt_builder - DEBUG - [Full meta-prompt content...]
2024-01-15 10:30:15 - prompt_builder - DEBUG - ================================================================================
2024-01-15 10:30:20 - prompt_builder - INFO - Stage 2: Generating optimized prompt
2024-01-15 10:30:20 - prompt_builder - DEBUG - Attempting to use LLM tool first
2024-01-15 10:30:25 - prompt_builder - INFO - Stage 3: Executing optimized prompt with Claude
```

### Decision Logging
```
2024-01-15 10:30:30 - workflow_logic - DEBUG - Decision: Validating branch matches issue number
2024-01-15 10:30:30 - workflow_logic - DEBUG - Decision: Continuing despite branch mismatch (warning only)
2024-01-15 10:30:31 - workflow_logic - DEBUG - Decision: Performing workspace hygiene before processing
2024-01-15 10:30:32 - workflow_logic - DEBUG - Decision: Creating PR (has changes to commit)
```

### Response Analysis
```
2024-01-15 10:30:45 - prompt_builder - DEBUG - Claude response received: success=True
2024-01-15 10:30:45 - prompt_builder - DEBUG - Execution result keys: ['success', 'result', 'metadata']
2024-01-15 10:30:45 - prompt_builder - DEBUG - ================================================================================
2024-01-15 10:30:45 - prompt_builder - DEBUG - FULL CLAUDE RESPONSE:
2024-01-15 10:30:45 - prompt_builder - DEBUG - [Complete response content...]
2024-01-15 10:30:45 - prompt_builder - DEBUG - ================================================================================
```

## Performance Considerations

- **Minimal Overhead**: Logging adds < 5ms per operation at INFO level
- **Lazy Evaluation**: Debug logs are only formatted when DEBUG level is active
- **Log Rotation**: Automatic rotation prevents disk space issues
- **Async Options**: Can be configured for async logging in high-throughput scenarios

## Security Features

### Sensitive Data Filtering
The logging system automatically redacts sensitive information:
- Passwords
- API keys
- Tokens
- Email addresses
- Other configurable patterns

Example:
```python
# Input: "password: secret123, api_key=abc123xyz"
# Logged: "password=***REDACTED***, api_key=***REDACTED***"
```

### File Permissions
Log files are created with restrictive permissions (0o600) by default to prevent unauthorized access.

## Testing

Comprehensive test coverage ensures logging functionality:
```bash
# Run logging enhancement tests
pytest tests/test_logging_enhancements.py -v

# Run with coverage
pytest tests/test_logging_enhancements.py --cov=src/claude_tasker
```

## Migration Guide

For existing users, the logging enhancements are backward compatible:

1. **Default Behavior**: No changes required - INFO level logging continues as before
2. **Enable Debug Logging**: Set `CLAUDE_LOG_LEVEL=DEBUG` to access new features
3. **Customize Output**: Use environment variables to fine-tune logging behavior

## Troubleshooting

### Common Issues

1. **Logs Too Verbose**
   - Solution: Increase `CLAUDE_LOG_TRUNCATE_LENGTH` or disable `CLAUDE_LOG_PROMPTS`

2. **Missing Debug Output**
   - Solution: Ensure `CLAUDE_LOG_LEVEL=DEBUG` is set

3. **Sensitive Data in Logs**
   - Solution: Enable `CLAUDE_LOG_SANITIZE=true`

4. **Log Files Too Large**
   - Solution: Adjust `CLAUDE_LOG_MAX_BYTES` and `CLAUDE_LOG_BACKUP_COUNT`

## Best Practices

1. **Development**: Use DEBUG level with full logging for development and debugging
2. **Testing**: Use INFO level with prompt logging for integration testing
3. **Production**: Use INFO or WARNING level with sanitization enabled
4. **Debugging Issues**: Temporarily enable DEBUG logging to diagnose problems
5. **Log Analysis**: Use structured JSON logging for automated log analysis tools

## Future Enhancements

Potential future improvements:
- OpenTelemetry integration for distributed tracing
- Metrics collection and reporting
- Log aggregation service integration
- Custom log formatters for specific use cases
- Performance profiling integration