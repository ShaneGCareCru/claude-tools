#!/usr/bin/env python3
"""
Demonstration of enhanced debug logging capabilities in claude-tasker.

This script showcases the comprehensive logging features including:
- Full prompt and response logging
- Decision-making transparency
- Response processing visibility
- Configurable logging options
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.claude_tasker.logging_config import setup_logging, get_logger, get_debug_config
from src.claude_tasker.prompt_builder import PromptBuilder
from src.claude_tasker.github_client import IssueData
from unittest.mock import Mock, patch


def demonstrate_logging_levels():
    """Demonstrate different logging levels and their output."""
    print("\n" + "="*80)
    print("DEMONSTRATING LOGGING LEVELS")
    print("="*80)
    
    # INFO level (default)
    print("\n1. INFO Level (Default):")
    setup_logging(log_level='INFO')
    logger = get_logger('demo')
    logger.info("This is an INFO message - minimal details")
    logger.debug("This DEBUG message won't be shown at INFO level")
    
    # DEBUG level with full content
    print("\n2. DEBUG Level with Full Content:")
    setup_logging(
        log_level='DEBUG',
        log_prompts=True,
        log_responses=True,
        truncate_length=500
    )
    logger = get_logger('demo')
    logger.info("INFO message at DEBUG level")
    logger.debug("DEBUG message with detailed information")
    
    # Show current configuration
    print("\n3. Current Debug Configuration:")
    config = get_debug_config()
    for key, value in config.items():
        print(f"   {key}: {value}")


def demonstrate_prompt_logging():
    """Demonstrate enhanced prompt generation and logging."""
    print("\n" + "="*80)
    print("DEMONSTRATING PROMPT LOGGING")
    print("="*80)
    
    # Setup debug logging
    setup_logging(
        log_level='DEBUG',
        log_prompts=True,
        log_responses=True
    )
    
    prompt_builder = PromptBuilder()
    
    # Create mock issue data
    issue_data = Mock(
        number=123,
        title="Add debug logging enhancements",
        body="Enhance the debug logging capabilities to provide complete transparency",
        state="open",
        author="demo_user",
        labels=["enhancement", "logging"]
    )
    
    context = {
        'git_diff': 'diff --git a/test.py b/test.py\n+print("hello")',
        'related_files': ['src/logging.py', 'tests/test_logging.py'],
        'project_info': {'name': 'claude-tasker', 'version': '1.0.0'}
    }
    
    print("\nGenerating Lyra-Dev prompt with full logging...")
    prompt = prompt_builder.generate_lyra_dev_prompt(
        issue_data,
        "# CLAUDE.md\nProject guidelines and conventions",
        context
    )
    
    print(f"\nGenerated prompt length: {len(prompt)} characters")
    print("Check the debug logs above for full prompt content and decision details!")


def demonstrate_two_stage_execution():
    """Demonstrate two-stage prompt execution with comprehensive logging."""
    print("\n" + "="*80)
    print("DEMONSTRATING TWO-STAGE EXECUTION LOGGING")
    print("="*80)
    
    setup_logging(
        log_level='DEBUG',
        log_prompts=True,
        log_responses=True
    )
    
    prompt_builder = PromptBuilder()
    
    # Mock the LLM tools to avoid actual API calls
    with patch.object(prompt_builder, 'build_with_llm') as mock_llm:
        mock_llm.return_value = {
            'result': 'Optimized prompt for task execution with Lyra-Dev methodology'
        }
        
        with patch.object(prompt_builder, 'build_with_claude') as mock_claude:
            mock_claude.return_value = {
                'success': True,
                'result': 'Task completed successfully'
            }
            
            print("\nExecuting two-stage prompt generation...")
            results = prompt_builder.execute_two_stage_prompt(
                task_type="debug_demo",
                task_data={'demo': 'data', 'test': 'value'},
                claude_md_content="Demo CLAUDE.md content",
                prompt_only=False
            )
            
            print(f"\nExecution result: {'SUCCESS' if results['success'] else 'FAILED'}")
            if results.get('error'):
                print(f"Error: {results['error']}")


def demonstrate_decision_logging():
    """Demonstrate decision-making transparency in workflow."""
    print("\n" + "="*80)
    print("DEMONSTRATING DECISION-MAKING TRANSPARENCY")
    print("="*80)
    
    setup_logging(log_level='DEBUG')
    
    prompt_builder = PromptBuilder()
    
    # Test meta-prompt validation with detailed logging
    print("\n1. Testing valid meta-prompt:")
    valid_prompt = "x" * 200 + " DECONSTRUCT DIAGNOSE DEVELOP DELIVER"
    is_valid = prompt_builder.validate_meta_prompt(valid_prompt)
    print(f"   Result: {'VALID' if is_valid else 'INVALID'}")
    
    print("\n2. Testing invalid meta-prompt (too short):")
    invalid_prompt = "short prompt"
    is_valid = prompt_builder.validate_meta_prompt(invalid_prompt)
    print(f"   Result: {'VALID' if is_valid else 'INVALID'}")
    
    print("\n3. Testing invalid meta-prompt (missing sections):")
    invalid_prompt = "x" * 200 + " missing required sections"
    is_valid = prompt_builder.validate_meta_prompt(invalid_prompt)
    print(f"   Result: {'VALID' if is_valid else 'INVALID'}")
    
    print("\nCheck the debug logs above for detailed validation reasoning!")


def demonstrate_response_analysis():
    """Demonstrate response processing and analysis logging."""
    print("\n" + "="*80)
    print("DEMONSTRATING RESPONSE ANALYSIS LOGGING")
    print("="*80)
    
    setup_logging(log_level='DEBUG')
    
    prompt_builder = PromptBuilder()
    
    # Mock different response scenarios
    with patch.object(prompt_builder, '_execute_llm_tool') as mock_execute:
        print("\n1. Successful response:")
        mock_execute.return_value = {
            'success': True,
            'result': 'Operation completed successfully',
            'metadata': {'tokens': 100, 'model': 'claude-3'}
        }
        result = prompt_builder.build_with_claude('test prompt')
        print(f"   Result: {result.get('success', False)}")
        
        print("\n2. Error response:")
        mock_execute.return_value = {
            'success': False,
            'error': 'Rate limit exceeded',
            'retry_after': 60
        }
        result = prompt_builder.build_with_claude('test prompt')
        print(f"   Result: {result.get('success', False)}")
        print(f"   Error: {result.get('error', 'None')}")


def demonstrate_environment_variable_config():
    """Demonstrate configuration via environment variables."""
    print("\n" + "="*80)
    print("DEMONSTRATING ENVIRONMENT VARIABLE CONFIGURATION")
    print("="*80)
    
    print("\nSetting environment variables for logging configuration...")
    
    # Set environment variables
    os.environ['CLAUDE_LOG_LEVEL'] = 'DEBUG'
    os.environ['CLAUDE_LOG_PROMPTS'] = 'true'
    os.environ['CLAUDE_LOG_RESPONSES'] = 'false'
    os.environ['CLAUDE_LOG_TRUNCATE_LENGTH'] = '1000'
    os.environ['CLAUDE_LOG_JSON'] = 'false'
    os.environ['CLAUDE_LOG_SANITIZE'] = 'true'
    
    # Setup logging with environment variables
    config = setup_logging()
    
    print("\nLogging configuration from environment:")
    print(f"   Log Level: {config['log_level']}")
    print(f"   Log Prompts: {config['log_prompts']}")
    print(f"   Log Responses: {config['log_responses']}")
    print(f"   Truncate Length: {config['truncate_length']}")
    print(f"   Sanitize Logs: {config['sanitize_logs']}")
    
    # Test sanitization
    logger = get_logger('demo')
    logger.debug("Testing sanitization: password=secret123 api_key=abc123xyz")
    print("\nCheck the debug log above - sensitive data should be redacted!")


def main():
    """Run all demonstrations."""
    print("\n" + "="*80)
    print("CLAUDE-TASKER ENHANCED DEBUG LOGGING DEMONSTRATION")
    print("="*80)
    print("\nThis demo showcases the comprehensive logging enhancements")
    print("that provide complete transparency in:")
    print("  - Prompt generation and execution")
    print("  - Decision-making processes")
    print("  - Response handling and analysis")
    print("  - Configuration options")
    
    # Run demonstrations
    demonstrate_logging_levels()
    demonstrate_prompt_logging()
    demonstrate_two_stage_execution()
    demonstrate_decision_logging()
    demonstrate_response_analysis()
    demonstrate_environment_variable_config()
    
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    print("\nKey Takeaways:")
    print("1. Use DEBUG level for full prompt/response logging")
    print("2. Configure via environment variables or function parameters")
    print("3. All decision points are logged with reasoning")
    print("4. Sensitive data can be automatically sanitized")
    print("5. Logging overhead is minimal even with DEBUG enabled")
    print("\nFor production use, set CLAUDE_LOG_LEVEL=INFO for standard logging")
    print("For debugging, set CLAUDE_LOG_LEVEL=DEBUG with CLAUDE_LOG_PROMPTS=true")


if __name__ == "__main__":
    main()