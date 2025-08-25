"""
Configuration classes for TechFlow testing framework.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class QualityGates:
    """Quality gate configuration for different workflow stages."""
    
    # Bug issue requirements
    bug_required_sections: int = 8
    bug_min_acceptance_criteria: int = 3
    bug_min_section_length: int = 50
    
    # PR requirements
    pr_must_link_issue: bool = True
    pr_must_have_diff: bool = True
    pr_min_files_changed: int = 1
    pr_must_target_main: bool = True
    
    # Review requirements
    review_must_be_on_pr: bool = True
    review_min_specific_comments: int = 1
    review_max_response_time_hours: int = 24
    
    # Feedback loop requirements
    feedback_must_address_comments: bool = True
    feedback_max_iterations: int = 3


@dataclass
class ScoringConfig:
    """Scoring configuration for quality assessment."""
    
    pass_threshold: float = 3.0
    excellence_threshold: float = 4.0
    max_score: float = 5.0
    
    # Weight factors for different aspects
    completeness_weight: float = 0.3
    quality_weight: float = 0.4
    timeliness_weight: float = 0.2
    correctness_weight: float = 0.1


@dataclass
class TestConfig:
    """Main configuration for TechFlow tests."""
    
    # Execution settings
    max_retries: int = 3
    timeout_seconds: int = 900  # 15 minutes
    backoff_factor: float = 2.0
    
    # CLI settings
    cli_path: str = './claude-tasker-py'
    branch_strategy: str = 'reuse'
    interactive_mode: bool = False
    
    # Repository settings
    techflow_repo_path: Optional[str] = None
    test_branch_prefix: str = 'techflow-test'
    
    # Quality and scoring
    quality_gates: QualityGates = field(default_factory=QualityGates)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    
    # Logging and output
    log_level: str = 'INFO'
    collect_artifacts: bool = True
    save_evidence: bool = True
    evidence_dir: str = 'test-results'
    
    # Environment validation
    required_env_vars: List[str] = field(default_factory=lambda: [
        'GITHUB_TOKEN',
    ])
    
    @classmethod
    def from_environment(cls) -> 'TestConfig':
        """Create configuration from environment variables."""
        return cls(
            max_retries=int(os.getenv('TEST_MAX_RETRIES', '3')),
            timeout_seconds=int(os.getenv('TEST_TIMEOUT_SECONDS', '900')),
            backoff_factor=float(os.getenv('TEST_BACKOFF_FACTOR', '2.0')),
            cli_path=os.getenv('CLAUDE_TASKER_CLI', './claude-tasker-py'),
            branch_strategy=os.getenv('CLAUDE_BRANCH_STRATEGY', 'reuse'),
            interactive_mode=os.getenv('TEST_INTERACTIVE', 'false').lower() == 'true',
            techflow_repo_path=os.getenv('TECHFLOW_REPO_PATH'),
            log_level=os.getenv('CLAUDE_LOG_LEVEL', 'INFO'),
            evidence_dir=os.getenv('TEST_EVIDENCE_DIR', 'test-results'),
        )
    
    def validate(self) -> List[str]:
        """Validate configuration and return any errors."""
        errors = []
        
        # Check required environment variables
        for env_var in self.required_env_vars:
            if not os.getenv(env_var):
                errors.append(f"Missing required environment variable: {env_var}")
        
        # Check CLI path exists
        if not os.path.exists(self.cli_path):
            errors.append(f"CLI path does not exist: {self.cli_path}")
        
        # Validate timeout
        if self.timeout_seconds < 60:
            errors.append("Timeout must be at least 60 seconds")
        
        # Validate retry settings
        if self.max_retries < 1:
            errors.append("Max retries must be at least 1")
        
        if self.backoff_factor < 1.0:
            errors.append("Backoff factor must be at least 1.0")
        
        return errors