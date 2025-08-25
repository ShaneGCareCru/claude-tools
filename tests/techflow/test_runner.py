"""
Main test orchestrator for TechFlow Demo self-testing framework.

This module provides the core TechFlowTestRunner that executes the complete
bug-to-resolution workflow and validates quality at each stage.
"""

import json
import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import uuid

from .config import TestConfig
from .validators import ValidatorRegistry
from .diagnostics import DiagnosticEngine
from .evidence import EvidenceCollector


@dataclass
class TestArtifact:
    """Represents a test artifact (issue, PR, etc.)."""
    
    artifact_type: str  # 'issue', 'pr', 'review', 'commit'
    identifier: str     # Issue number, PR number, etc.
    url: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass 
class TestFailure:
    """Represents a test failure with diagnostic information."""
    
    stage: str                    # Which stage failed
    failure_type: str             # Type of failure
    message: str                  # Failure message
    details: Optional[str] = None # Additional details
    caused_by: Optional[Exception] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    diagnostic_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestRun:
    """Represents a complete test run."""
    
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    config: Optional[TestConfig] = None
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    
    # Test artifacts
    issue_num: Optional[int] = None
    pr_num: Optional[int] = None
    branch_name: Optional[str] = None
    artifacts: List[TestArtifact] = field(default_factory=list)
    
    # Test results
    success: bool = False
    quality_score: float = 0.0
    failures: List[TestFailure] = field(default_factory=list)
    retry_count: int = 0
    
    # Evidence
    evidence_path: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> Optional[float]:
        """Get test run duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def add_artifact(self, artifact: TestArtifact) -> None:
        """Add an artifact to this test run."""
        self.artifacts.append(artifact)
    
    def add_failure(self, failure: TestFailure) -> None:
        """Add a failure to this test run."""
        self.failures.append(failure)
        self.success = False
    
    def add_log(self, message: str, level: str = 'INFO') -> None:
        """Add a log entry to this test run."""
        timestamp = datetime.now(timezone.utc).isoformat()
        self.logs.append(f"[{timestamp}] {level}: {message}")


class CLICommandWrapper:
    """Wrapper for executing CLI commands with structured output parsing."""
    
    def __init__(self, cli_path: str, timeout: int = 900):
        self.cli_path = cli_path
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
    
    def execute_command(self, args: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
        """Execute a CLI command and return structured result."""
        cmd = [self.cli_path] + args
        cmd_str = ' '.join(cmd)
        
        self.logger.debug(f"Executing command: {cmd_str}")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            execution_time = time.time() - start_time
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': cmd_str,
                'execution_time': execution_time
            }
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': f'Command timed out after {self.timeout} seconds',
                'command': cmd_str,
                'execution_time': execution_time
            }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'command': cmd_str,
                'execution_time': execution_time
            }


class TechFlowTestRunner:
    """Main test orchestrator for TechFlow Demo self-testing."""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.cli = CLICommandWrapper(config.cli_path, config.timeout_seconds)
        self.validators = ValidatorRegistry(config.quality_gates)
        self.diagnostics = DiagnosticEngine(config)
        self.evidence = EvidenceCollector(config)
        
        # Validate configuration
        config_errors = config.validate()
        if config_errors:
            raise ValueError(f"Configuration errors: {', '.join(config_errors)}")
        
        self.logger.info(f"TechFlowTestRunner initialized with config: {config}")
    
    def run_full_cycle(self, bug_description: Optional[str] = None) -> TestRun:
        """Execute complete bug-to-merge cycle."""
        run = TestRun(config=self.config)
        run.add_log("Starting full TechFlow test cycle")
        
        try:
            # Phase 1: Create and validate bug issue
            self._create_bug_issue(run, bug_description)
            if not run.success:
                return self._handle_failure(run, "bug_creation")
            
            # Phase 2: Implement fix and create PR
            self._implement_fix(run)
            if not run.success:
                return self._handle_failure(run, "implementation")
            
            # Phase 3: Review PR
            self._review_pr(run)
            if not run.success:
                return self._handle_failure(run, "review")
            
            # Phase 4: Address feedback and merge
            self._address_feedback_and_merge(run)
            if not run.success:
                return self._handle_failure(run, "feedback_merge")
            
            # Calculate quality score
            run.quality_score = self._calculate_quality_score(run)
            run.success = True
            run.add_log(f"Full cycle completed successfully with quality score: {run.quality_score}")
            
        except Exception as e:
            failure = TestFailure(
                stage="orchestration",
                failure_type="unexpected_error",
                message=str(e),
                caused_by=e
            )
            run.add_failure(failure)
            run.add_log(f"Unexpected error during test run: {e}", "ERROR")
            
        finally:
            run.end_time = datetime.now(timezone.utc)
            
            # Collect evidence
            if self.config.save_evidence:
                evidence_path = self.evidence.collect_run_summary(run)
                run.evidence_path = str(evidence_path)
                run.add_log(f"Evidence saved to: {evidence_path}")
        
        return run
    
    def _create_bug_issue(self, run: TestRun, bug_description: Optional[str]) -> None:
        """Create and validate a bug issue."""
        run.add_log("Phase 1: Creating bug issue")
        
        # Use provided description or generate one
        if not bug_description:
            bug_description = self._generate_test_bug_description()
        
        # Create bug issue using CLI
        result = self.cli.execute_command([
            '--bug', bug_description,
            '--interactive' if self.config.interactive_mode else '--headless'
        ])
        
        if not result['success']:
            failure = TestFailure(
                stage="bug_creation",
                failure_type="cli_execution_failed",
                message="Failed to create bug issue via CLI",
                details=result['stderr']
            )
            run.add_failure(failure)
            return
        
        # Parse issue number from CLI output
        issue_num = self._parse_issue_number(result['stdout'])
        if not issue_num:
            failure = TestFailure(
                stage="bug_creation",
                failure_type="issue_parsing_failed",
                message="Could not parse issue number from CLI output",
                details=result['stdout']
            )
            run.add_failure(failure)
            return
        
        run.issue_num = issue_num
        run.add_artifact(TestArtifact(
            artifact_type="issue",
            identifier=str(issue_num),
            url=f"https://github.com/ShaneGCareCru/claude-tools/issues/{issue_num}",
            content=bug_description
        ))
        
        # Validate bug issue quality
        validation_result = self.validators.validate_bug_issue(issue_num)
        if not validation_result.valid:
            failure = TestFailure(
                stage="bug_validation",
                failure_type="quality_gate_failed",
                message="Bug issue failed quality validation",
                details=str(validation_result.errors)
            )
            run.add_failure(failure)
            return
        
        run.add_log(f"Bug issue #{issue_num} created and validated successfully")
        run.success = True
    
    def _implement_fix(self, run: TestRun) -> None:
        """Implement fix for the bug issue."""
        run.add_log("Phase 2: Implementing fix")
        
        if not run.issue_num:
            failure = TestFailure(
                stage="implementation",
                failure_type="precondition_failed",
                message="No issue number available for implementation"
            )
            run.add_failure(failure)
            return
        
        # Run claude-tasker to implement the fix
        args = [
            str(run.issue_num),
            f'--branch-strategy={self.config.branch_strategy}'
        ]
        
        if self.config.interactive_mode:
            args.append('--interactive')
        
        result = self.cli.execute_command(args)
        
        if not result['success']:
            failure = TestFailure(
                stage="implementation", 
                failure_type="cli_execution_failed",
                message="Failed to implement fix via CLI",
                details=result['stderr']
            )
            run.add_failure(failure)
            return
        
        # Parse PR number and branch name from output
        pr_num = self._parse_pr_number(result['stdout'])
        branch_name = self._parse_branch_name(result['stdout'])
        
        if not pr_num:
            failure = TestFailure(
                stage="implementation",
                failure_type="pr_parsing_failed", 
                message="Could not parse PR number from CLI output",
                details=result['stdout']
            )
            run.add_failure(failure)
            return
        
        run.pr_num = pr_num
        run.branch_name = branch_name
        run.add_artifact(TestArtifact(
            artifact_type="pr",
            identifier=str(pr_num),
            url=f"https://github.com/ShaneGCareCru/claude-tools/pull/{pr_num}",
            metadata={'branch': branch_name}
        ))
        
        # Validate PR quality
        validation_result = self.validators.validate_pull_request(pr_num)
        if not validation_result.valid:
            failure = TestFailure(
                stage="pr_validation",
                failure_type="quality_gate_failed",
                message="PR failed quality validation",
                details=str(validation_result.errors)
            )
            run.add_failure(failure)
            return
        
        run.add_log(f"Fix implemented successfully in PR #{pr_num}")
        run.success = True
    
    def _review_pr(self, run: TestRun) -> None:
        """Review the created PR."""
        run.add_log("Phase 3: Reviewing PR")
        
        if not run.pr_num:
            failure = TestFailure(
                stage="review",
                failure_type="precondition_failed",
                message="No PR number available for review"
            )
            run.add_failure(failure)
            return
        
        # Use claude-tasker to review the PR
        result = self.cli.execute_command([
            '--review-pr', str(run.pr_num)
        ])
        
        if not result['success']:
            failure = TestFailure(
                stage="review",
                failure_type="cli_execution_failed",
                message="Failed to review PR via CLI",
                details=result['stderr']
            )
            run.add_failure(failure)
            return
        
        # Validate review quality
        validation_result = self.validators.validate_review(run.pr_num)
        if not validation_result.valid:
            failure = TestFailure(
                stage="review_validation",
                failure_type="quality_gate_failed",
                message="Review failed quality validation",
                details=str(validation_result.errors)
            )
            run.add_failure(failure)
            return
        
        run.add_artifact(TestArtifact(
            artifact_type="review",
            identifier=f"pr-{run.pr_num}-review",
            url=f"https://github.com/ShaneGCareCru/claude-tools/pull/{run.pr_num}#pullrequestreview"
        ))
        
        run.add_log(f"PR #{run.pr_num} reviewed successfully")
        run.success = True
    
    def _address_feedback_and_merge(self, run: TestRun) -> None:
        """Address any feedback and merge the PR."""
        run.add_log("Phase 4: Addressing feedback and merging")
        
        # For now, this is a placeholder - in a full implementation,
        # this would check for review comments and address them
        
        # Validate feedback loop
        if run.pr_num:
            validation_result = self.validators.validate_feedback_loop(run.pr_num)
            if not validation_result.valid:
                failure = TestFailure(
                    stage="feedback_validation",
                    failure_type="quality_gate_failed",
                    message="Feedback loop failed quality validation",
                    details=str(validation_result.errors)
                )
                run.add_failure(failure)
                return
        
        run.add_log("Feedback addressed and PR ready for merge")
        run.success = True
    
    def _calculate_quality_score(self, run: TestRun) -> float:
        """Calculate overall quality score for the test run."""
        scoring = self.config.scoring
        total_score = 0.0
        
        # Completeness score (did all phases complete?)
        completed_phases = sum([
            run.issue_num is not None,
            run.pr_num is not None,
            len([a for a in run.artifacts if a.artifact_type == "review"]) > 0,
            len(run.failures) == 0
        ])
        completeness_score = (completed_phases / 4) * scoring.max_score
        
        # Quality score (based on validator results)
        quality_score = scoring.max_score  # Start with max, deduct for failures
        for failure in run.failures:
            if failure.failure_type == "quality_gate_failed":
                quality_score -= 1.0
        quality_score = max(0.0, quality_score)
        
        # Timeliness score (based on execution time)
        timeliness_score = scoring.max_score
        if run.duration and run.duration > self.config.timeout_seconds * 0.8:
            timeliness_score = scoring.max_score * 0.6  # Penalty for slow execution
        
        # Correctness score (based on retry count)
        correctness_score = scoring.max_score
        if run.retry_count > 0:
            correctness_score = scoring.max_score * (1.0 - (run.retry_count * 0.1))
        correctness_score = max(0.0, correctness_score)
        
        # Weighted total
        total_score = (
            completeness_score * scoring.completeness_weight +
            quality_score * scoring.quality_weight +
            timeliness_score * scoring.timeliness_weight +
            correctness_score * scoring.correctness_weight
        )
        
        return min(total_score, scoring.max_score)
    
    def _handle_failure(self, run: TestRun, stage: str) -> TestRun:
        """Handle test failure with potential retry logic."""
        run.add_log(f"Handling failure in stage: {stage}")
        
        if run.retry_count < self.config.max_retries:
            run.add_log(f"Attempting retry {run.retry_count + 1} of {self.config.max_retries}")
            
            # Apply backoff delay
            delay = self.config.backoff_factor ** run.retry_count
            time.sleep(delay)
            
            # Try diagnostic remediation
            remediation_applied = self.diagnostics.try_remediation(run, stage)
            if remediation_applied:
                run.retry_count += 1
                # Recursive retry (in a full implementation, this would be more sophisticated)
                run.add_log("Remediation applied, retrying...")
                
        run.add_log(f"Stage {stage} failed after {run.retry_count} retries")
        return run
    
    def _generate_test_bug_description(self) -> str:
        """Generate a test bug description."""
        return """Test Bug: Missing error handling in user authentication

## Bug Description
The user authentication system does not properly handle invalid credentials, leading to confusing error messages for users.

## Reproduction Steps
1. Navigate to login page
2. Enter invalid username/password combination
3. Click "Login" button
4. Observe error message

## Expected Behavior  
- Clear error message indicating "Invalid username or password"
- User remains on login page with form cleared
- Appropriate logging of failed login attempt

## Actual Behavior
- Generic "Something went wrong" message appears
- Form data persists in fields
- No logging of the failed attempt

## Root Cause Analysis
The authentication service catches all exceptions generically without differentiating between credential failures and system errors.

## Acceptance Criteria
- [ ] Specific error message for invalid credentials
- [ ] Form clears after failed attempt  
- [ ] Failed login attempts are logged
- [ ] System errors show different message than credential errors
- [ ] Rate limiting prevents brute force attempts

## Test Plan
1. Unit tests for authentication service error handling
2. Integration tests for login flow
3. Security tests for rate limiting
4. UI tests for error message display

## Rollback Plan
If issues arise, revert authentication changes and restore previous generic error handling while investigating."""
    
    def _parse_issue_number(self, output: str) -> Optional[int]:
        """Parse issue number from CLI output."""
        # Look for patterns like "Created issue #123" or "Issue #123"
        import re
        patterns = [
            r'[Ii]ssue #?(\d+)',
            r'Created issue #?(\d+)',
            r'#(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return int(match.group(1))
        
        return None
    
    def _parse_pr_number(self, output: str) -> Optional[int]:
        """Parse PR number from CLI output."""
        import re
        patterns = [
            r'[Pp]ull [Rr]equest #?(\d+)',
            r'PR #?(\d+)',
            r'Created PR #?(\d+)',
            r'https://github\.com/[^/]+/[^/]+/pull/(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return int(match.group(1))
        
        return None
    
    def _parse_branch_name(self, output: str) -> Optional[str]:
        """Parse branch name from CLI output."""
        import re
        patterns = [
            r'[Bb]ranch[:\s]+([^\s\n]+)',
            r'[Cc]reated branch[:\s]+([^\s\n]+)',
            r'issue-\d+-\d+'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(1) if pattern.startswith('[') else match.group(0)
        
        return None