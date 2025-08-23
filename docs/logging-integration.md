# Logging Integration Guide

This guide explains how to integrate the Python logging infrastructure with the claude-tasker bash script.

## Overview

The `logging_config.py` module provides a comprehensive Python logging infrastructure that can be used by Python components of the claude-tasker system. While the main claude-tasker script is written in bash, any Python utilities or agents can leverage this logging system.

## Quick Start

### Basic Usage in Python Scripts

```python
from src.claude_tasker.logging_config import setup_logging, get_logger

# Setup logging once at application start
setup_logging(
    log_level='INFO',
    log_file='claude_tasker.log',
    enable_json=True,
    sanitize_logs=True  # Redact sensitive data
)

# Get logger for your module
logger = get_logger(__name__)

# Use the logger
logger.info("Starting task processing")
logger.debug("Debug information")
logger.error("Error occurred", exc_info=True)
```

### Integration with Bash Script

To use Python logging from the bash script, create a Python wrapper:

```bash
#!/bin/bash

# Use Python script with logging
python3 -c "
from src.claude_tasker.logging_config import setup_logging, get_logger
import sys

# Setup logging based on environment
setup_logging()

logger = get_logger('claude_tasker.bash')
logger.info('Task started: ' + ' '.join(sys.argv[1:]))

# Your Python logic here
" "$@"
```

## Configuration

### Environment Variables

The logging system respects these environment variables:

- `CLAUDE_LOG_LEVEL`: Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `CLAUDE_LOG_FILE`: Path to log file
- `CLAUDE_LOG_FORMAT`: Custom log format string
- `CLAUDE_LOG_COLORS`: Enable/disable colored output (true/false)
- `CLAUDE_LOG_JSON`: Enable JSON structured logging (true/false)
- `CLAUDE_LOG_SANITIZE`: Enable sensitive data redaction (true/false)
- `CLAUDE_LOG_MAX_BYTES`: Max log file size before rotation (default: 10MB)
- `CLAUDE_LOG_BACKUP_COUNT`: Number of backup files to keep (default: 5)
- `CLAUDE_LOG_DIR`: Directory for log files (default: logs)
- `CLAUDE_AUTO_SETUP_LOGGING`: Auto-setup on import (true/false)

### Setting Environment in Bash

```bash
# In claude-tasker script
export CLAUDE_LOG_LEVEL="DEBUG"
export CLAUDE_LOG_FILE="claude_tasker.log"
export CLAUDE_LOG_JSON="true"
export CLAUDE_LOG_SANITIZE="true"

# Call Python components
python3 your_script.py
```

## Features

### 1. Structured Logging

When `enable_json=True`, logs are output as JSON for easy parsing:

```json
{
  "timestamp": "2024-01-01T12:00:00",
  "level": "INFO",
  "logger": "claude_tasker",
  "message": "Processing GitHub issue #123",
  "module": "issue_processor",
  "function": "process",
  "line": 42,
  "issue_number": 123,
  "status": "in_progress"
}
```

### 2. Sensitive Data Redaction

With `sanitize_logs=True`, sensitive information is automatically redacted:

```python
logger.info("User logged in with password=secret123")
# Output: "User logged in with password=***REDACTED***"
```

### 3. Contextual Logging

Add context to a series of log messages:

```python
from src.claude_tasker.logging_config import LogContext

with LogContext(logger, issue_id=123, user='alice') as log:
    log.info("Processing started")
    log.debug("Fetching issue details")
    # All logs within context include issue_id and user
```

### 4. Exception Logging Decorator

Automatically log exceptions from functions:

```python
from src.claude_tasker.logging_config import log_exception

@log_exception(logger, "Failed to process issue")
def process_issue(issue_number):
    # If this raises, exception is logged automatically
    api_response = fetch_issue(issue_number)
    return api_response
```

### 5. Log Rotation

Automatic rotation prevents unbounded log growth:

```python
setup_logging(
    log_file='app.log',
    max_bytes=10485760,  # 10MB
    backup_count=5       # Keep 5 backup files
)
```

## Integration Examples

### Example 1: Python Agent for Claude Tasker

```python
#!/usr/bin/env python3
"""
Python agent that can be called from claude-tasker bash script.
"""

import sys
import json
from src.claude_tasker.logging_config import setup_logging, get_logger, LogContext

def main():
    # Setup logging (respects environment variables)
    setup_logging()
    logger = get_logger('claude_tasker.agent')
    
    # Parse arguments
    task_type = sys.argv[1] if len(sys.argv) > 1 else 'unknown'
    task_data = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    
    # Process with context
    with LogContext(logger, task_type=task_type, **task_data) as log:
        log.info(f"Starting {task_type} task")
        
        try:
            # Your task logic here
            result = process_task(task_type, task_data)
            log.info(f"Task completed successfully")
            return 0
        except Exception as e:
            log.error(f"Task failed: {e}", exc_info=True)
            return 1

if __name__ == "__main__":
    sys.exit(main())
```

### Example 2: Bash Function with Python Logging

```bash
# Function in claude-tasker that uses Python logging
log_with_python() {
    local level="$1"
    local message="$2"
    shift 2
    
    python3 -c "
from src.claude_tasker.logging_config import setup_logging, get_logger
import json

setup_logging()
logger = get_logger('claude_tasker.bash')

extra_fields = json.loads('${*:-{}}') if '${*}' else {}
getattr(logger, '$level'.lower())('$message', extra={'extra_fields': extra_fields})
"
}

# Usage
log_with_python INFO "Starting GitHub issue processing" '{"issue": 123}'
log_with_python ERROR "Failed to fetch issue" '{"error": "404"}'
```

### Example 3: Mixed Bash/Python Workflow

```bash
#!/bin/bash

# claude-tasker integration example

# Setup logging environment
export CLAUDE_LOG_LEVEL="INFO"
export CLAUDE_LOG_FILE="logs/claude_tasker.log"
export CLAUDE_LOG_JSON="true"
export CLAUDE_LOG_SANITIZE="true"

# Bash logging function that also logs to Python
log_message() {
    local level="$1"
    local message="$2"
    
    # Log to bash output
    echo "[$(date)] [$level] $message"
    
    # Also log to Python logging system
    python3 -c "
from src.claude_tasker.logging_config import get_logger
logger = get_logger('claude_tasker')
logger.$(echo $level | tr '[:upper:]' '[:lower:]')('$message')
" 2>/dev/null || true
}

# Process issues
process_github_issue() {
    local issue_number="$1"
    
    log_message INFO "Processing GitHub issue #$issue_number"
    
    # Call Python script with full logging
    if python3 process_issue.py "$issue_number"; then
        log_message INFO "Successfully processed issue #$issue_number"
    else
        log_message ERROR "Failed to process issue #$issue_number"
    fi
}
```

## Best Practices

1. **Initialize Once**: Call `setup_logging()` once at application start
2. **Use Module Loggers**: Use `get_logger(__name__)` for module-specific loggers
3. **Enable Sanitization**: Always use `sanitize_logs=True` in production
4. **Set Appropriate Levels**: Use DEBUG for development, INFO or WARNING for production
5. **Use Contexts**: Leverage `LogContext` for request/transaction tracking
6. **Handle Errors Gracefully**: The logging system won't crash your application
7. **Rotate Logs**: Configure rotation to prevent disk space issues
8. **Structure Your Logs**: Use JSON format for easier parsing and analysis

## Monitoring and Analysis

### Parsing JSON Logs

```bash
# Extract all ERROR logs
jq 'select(.level == "ERROR")' < claude_tasker.log

# Get logs for specific issue
jq 'select(.issue_number == 123)' < claude_tasker.log

# Count errors by module
jq -r 'select(.level == "ERROR") | .module' < claude_tasker.log | sort | uniq -c
```

### Log Aggregation

The JSON format makes it easy to integrate with log aggregation services:

- **ELK Stack**: Direct ingestion of JSON logs
- **Splunk**: Parse JSON fields automatically
- **CloudWatch**: Send structured logs to AWS
- **Datadog**: Native JSON log support

## Troubleshooting

### Common Issues

1. **No logs appearing**: Check `CLAUDE_LOG_LEVEL` environment variable
2. **Permission denied**: Ensure log directory has write permissions
3. **Logs not rotating**: Verify `max_bytes` and `backup_count` settings
4. **Sensitive data visible**: Enable `sanitize_logs=True`
5. **Colors not working**: Check terminal support and `CLAUDE_LOG_COLORS`

### Debug Mode

Enable maximum verbosity for troubleshooting:

```bash
export CLAUDE_LOG_LEVEL="DEBUG"
export CLAUDE_LOG_COLORS="true"
export CLAUDE_LOG_JSON="false"  # Human-readable format
```

## Security Considerations

1. **File Permissions**: Logs are created with `0o600` permissions by default
2. **Sensitive Data**: Always enable sanitization in production
3. **Log Injection**: The system sanitizes log content to prevent injection
4. **Path Validation**: File paths are validated to prevent directory traversal
5. **Size Limits**: Rotation prevents resource exhaustion attacks

## Migration Guide

If you're currently using bash `echo` statements for logging:

### Before
```bash
echo "[INFO] Processing issue $issue_number"
echo "[ERROR] Failed to process: $error"
```

### After
```bash
log_with_python INFO "Processing issue" "{\"issue\": $issue_number}"
log_with_python ERROR "Failed to process" "{\"error\": \"$error\"}"
```

Benefits:
- Structured logging
- Automatic timestamps
- Log rotation
- Sensitive data redaction
- Centralized configuration
- Better analysis tools