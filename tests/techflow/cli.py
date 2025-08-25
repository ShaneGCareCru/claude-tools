"""
Command-line interface for TechFlow test framework.

This module provides a CLI interface for running TechFlow tests,
making it easy to execute tests from the command line or CI/CD systems.
"""

import argparse
import logging
import sys
from pathlib import Path
import json

from .test_runner import TechFlowTestRunner
from .config import TestConfig


def setup_logging(level: str) -> None:
    """Setup logging configuration."""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='TechFlow Demo Self-Testing Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full test cycle with default settings
  python -m tests.techflow.cli

  # Run with custom bug description
  python -m tests.techflow.cli --bug "Custom bug description"

  # Run with increased timeout and retries
  python -m tests.techflow.cli --timeout 1800 --max-retries 5

  # Run with custom CLI path
  python -m tests.techflow.cli --cli-path ./my-claude-tasker

  # Generate report only (no execution)
  python -m tests.techflow.cli --report-only --run-id abc123

Environment Variables:
  GITHUB_TOKEN          GitHub API token (required)
  CLAUDE_LOG_LEVEL      Log level (default: INFO)
  CLAUDE_BRANCH_STRATEGY Branch strategy (default: reuse)
  TEST_MAX_RETRIES      Maximum retries (default: 3)
  TEST_TIMEOUT_SECONDS  Timeout in seconds (default: 900)
        """
    )
    
    # Execution options
    parser.add_argument(
        '--bug', 
        type=str,
        help='Custom bug description (if not provided, a test bug will be generated)'
    )
    
    parser.add_argument(
        '--cli-path',
        type=str,
        default='./claude-tasker-py',
        help='Path to claude-tasker CLI (default: ./claude-tasker-py)'
    )
    
    parser.add_argument(
        '--branch-strategy',
        type=str,
        choices=['reuse', 'always_new'],
        default='reuse',
        help='Branch creation strategy (default: reuse)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=900,
        help='Timeout in seconds (default: 900)'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum number of retries (default: 3)'
    )
    
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir',
        type=str,
        default='test-results',
        help='Directory for test results (default: test-results)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Log level (default: INFO)'
    )
    
    parser.add_argument(
        '--no-evidence',
        action='store_true',
        help='Skip evidence collection'
    )
    
    # Report-only mode
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Generate report for existing run (requires --run-id)'
    )
    
    parser.add_argument(
        '--run-id',
        type=str,
        help='Run ID for report generation'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        if args.report_only:
            if not args.run_id:
                logger.error("--run-id is required when using --report-only")
                return 1
            
            return generate_report_only(args, logger)
        else:
            return run_test_cycle(args, logger)
            
    except KeyboardInterrupt:
        logger.info("Test execution interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug("", exc_info=True)
        return 1


def run_test_cycle(args, logger) -> int:
    """Run the complete test cycle."""
    logger.info("Starting TechFlow test execution")
    
    # Create configuration
    config = TestConfig(
        cli_path=args.cli_path,
        branch_strategy=args.branch_strategy,
        timeout_seconds=args.timeout,
        max_retries=args.max_retries,
        interactive_mode=args.interactive,
        evidence_dir=args.output_dir,
        save_evidence=not args.no_evidence,
        log_level=args.log_level
    )
    
    # Validate configuration
    config_errors = config.validate()
    if config_errors:
        logger.error("Configuration errors:")
        for error in config_errors:
            logger.error(f"  - {error}")
        return 1
    
    # Create and run test
    try:
        runner = TechFlowTestRunner(config)
        result = runner.run_full_cycle(args.bug)
        
        # Log results
        log_test_results(result, logger)
        
        # Return appropriate exit code
        return 0 if result.success else 1
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        logger.debug("", exc_info=True)
        return 1


def generate_report_only(args, logger) -> int:
    """Generate report for existing test run."""
    logger.info(f"Generating report for run ID: {args.run_id}")
    
    # Look for existing run data
    evidence_dir = Path(args.output_dir) / f"run-{args.run_id}"
    run_data_file = evidence_dir / "run_data.json"
    
    if not run_data_file.exists():
        logger.error(f"Run data not found: {run_data_file}")
        return 1
    
    try:
        # Load run data
        with open(run_data_file) as f:
            run_data = json.load(f)
        
        # Create config for report generation
        config = TestConfig(evidence_dir=args.output_dir)
        
        # TODO: Reconstruct TestRun from JSON data and regenerate reports
        logger.info("Report generation from existing data not yet implemented")
        logger.info(f"Run data found at: {run_data_file}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        return 1


def log_test_results(test_run, logger) -> None:
    """Log test execution results."""
    if test_run.success:
        logger.info(f"✅ Test PASSED - Quality Score: {test_run.quality_score:.1f}/5.0")
    else:
        logger.error(f"❌ Test FAILED - Quality Score: {test_run.quality_score:.1f}/5.0")
    
    logger.info(f"Duration: {test_run.duration:.1f}s")
    logger.info(f"Retries: {test_run.retry_count}")
    logger.info(f"Artifacts: {len(test_run.artifacts)}")
    
    if test_run.issue_num:
        logger.info(f"Issue: #{test_run.issue_num}")
    if test_run.pr_num:
        logger.info(f"PR: #{test_run.pr_num}")
    if test_run.branch_name:
        logger.info(f"Branch: {test_run.branch_name}")
    
    if test_run.failures:
        logger.error(f"Failures ({len(test_run.failures)}):")
        for failure in test_run.failures:
            logger.error(f"  - {failure.stage}: {failure.message}")
    
    if test_run.evidence_path:
        logger.info(f"Evidence: {test_run.evidence_path}")


if __name__ == '__main__':
    sys.exit(main())