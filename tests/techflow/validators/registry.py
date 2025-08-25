"""
Validator registry and base validation result classes.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    
    valid: bool
    score: float = 0.0  # 0.0 to 5.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list) 
    details: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
    
    def add_detail(self, key: str, value: Any) -> None:
        """Add a detail entry."""
        self.details[key] = value


class ValidatorRegistry:
    """Registry for all workflow stage validators."""
    
    def __init__(self, quality_gates):
        self.quality_gates = quality_gates
        self.logger = logging.getLogger(__name__)
        
        # Import validators here to avoid circular imports
        from .bug_issue import BugIssueValidator
        from .pull_request import PullRequestValidator  
        from .review import ReviewValidator
        from .feedback import FeedbackValidator
        
        # Initialize validators
        self.bug_validator = BugIssueValidator(quality_gates)
        self.pr_validator = PullRequestValidator(quality_gates)
        self.review_validator = ReviewValidator(quality_gates)
        self.feedback_validator = FeedbackValidator(quality_gates)
    
    def validate_bug_issue(self, issue_num: int) -> ValidationResult:
        """Validate a bug issue."""
        self.logger.debug(f"Validating bug issue #{issue_num}")
        return self.bug_validator.validate(issue_num)
    
    def validate_pull_request(self, pr_num: int) -> ValidationResult:
        """Validate a pull request."""
        self.logger.debug(f"Validating PR #{pr_num}")
        return self.pr_validator.validate(pr_num)
    
    def validate_review(self, pr_num: int) -> ValidationResult:
        """Validate PR review."""
        self.logger.debug(f"Validating review for PR #{pr_num}")
        return self.review_validator.validate(pr_num)
    
    def validate_feedback_loop(self, pr_num: int) -> ValidationResult:
        """Validate feedback loop."""
        self.logger.debug(f"Validating feedback loop for PR #{pr_num}")
        return self.feedback_validator.validate(pr_num)