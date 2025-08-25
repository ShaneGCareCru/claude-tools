"""
Review validator for TechFlow test framework.
"""

import subprocess
import json
import logging
from datetime import datetime, timezone

from .registry import ValidationResult


class ReviewValidator:
    """Validator for PR review quality."""
    
    def __init__(self, quality_gates):
        self.quality_gates = quality_gates
        self.logger = logging.getLogger(__name__)
    
    def validate(self, pr_num: int) -> ValidationResult:
        """Validate PR review quality."""
        result = ValidationResult(valid=True, score=5.0)
        
        try:
            # Get review data via GitHub CLI
            reviews = self._get_pr_reviews(pr_num)
            if not reviews:
                result.add_error(f"No reviews found for PR #{pr_num}")
                return result
            
            result.add_detail('review_count', len(reviews))
            
            # Validate review placement (on PR, not issue)
            if self.quality_gates.review_must_be_on_pr:
                self._validate_review_placement(reviews, result)
            
            # Validate review specificity and quality
            self._validate_review_quality(reviews, result)
            
            # Validate response time
            self._validate_response_time(reviews, pr_num, result)
            
            # Calculate final score
            self._calculate_score(result)
            
        except Exception as e:
            result.add_error(f"Validation error: {str(e)}")
            self.logger.error(f"Error validating review for PR #{pr_num}: {e}")
        
        return result
    
    def _get_pr_reviews(self, pr_num: int) -> list:
        """Get PR review data from GitHub API."""
        try:
            cmd = ['gh', 'api', f'/repos/:owner/:repo/pulls/{pr_num}/reviews']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.error(f"GitHub API error: {result.stderr}")
                return []
            
            reviews = json.loads(result.stdout)
            return reviews if isinstance(reviews, list) else []
            
        except Exception as e:
            self.logger.error(f"Error getting PR reviews: {e}")
            return []
    
    def _validate_review_placement(self, reviews: list, result: ValidationResult) -> None:
        """Validate that reviews are properly placed on PR."""
        # This validation checks that we have actual PR reviews
        # (as opposed to issue comments, which would indicate improper placement)
        
        valid_reviews = [r for r in reviews if r.get('state') in ['APPROVED', 'CHANGES_REQUESTED', 'COMMENTED']]
        result.add_detail('valid_reviews', len(valid_reviews))
        
        if len(valid_reviews) == 0:
            result.add_error("No valid PR reviews found (reviews may be misplaced on issue)")
            result.score -= 2.0
    
    def _validate_review_quality(self, reviews: list, result: ValidationResult) -> None:
        """Validate quality of review comments."""
        total_comments = 0
        specific_comments = 0
        actionable_comments = 0
        
        # Quality indicators for comments
        specific_indicators = [
            'line', 'function', 'method', 'variable', 'class', 'import',
            'should', 'could', 'consider', 'suggest', 'recommend'
        ]
        
        actionable_indicators = [
            'add', 'remove', 'change', 'fix', 'update', 'refactor',
            'extract', 'rename', 'move', 'delete'
        ]
        
        for review in reviews:
            review_body = review.get('body', '')
            if review_body:
                total_comments += 1
                
                # Check for specific comments
                if any(indicator in review_body.lower() for indicator in specific_indicators):
                    specific_comments += 1
                
                # Check for actionable comments
                if any(indicator in review_body.lower() for indicator in actionable_indicators):
                    actionable_comments += 1
        
        result.add_detail('total_review_comments', total_comments)
        result.add_detail('specific_comments', specific_comments)
        result.add_detail('actionable_comments', actionable_comments)
        
        if specific_comments < self.quality_gates.review_min_specific_comments:
            result.add_error(f"Need at least {self.quality_gates.review_min_specific_comments} specific comments, found {specific_comments}")
            result.score -= 1.0
        
        if total_comments > 0:
            specificity_ratio = specific_comments / total_comments
            actionability_ratio = actionable_comments / total_comments
            
            result.add_detail('specificity_ratio', specificity_ratio)
            result.add_detail('actionability_ratio', actionability_ratio)
            
            if specificity_ratio < 0.5:
                result.add_warning("Reviews lack specificity")
                result.score -= 0.5
            
            if actionability_ratio < 0.3:
                result.add_warning("Reviews lack actionable feedback")
                result.score -= 0.3
    
    def _validate_response_time(self, reviews: list, pr_num: int, result: ValidationResult) -> None:
        """Validate review response time."""
        try:
            # Get PR creation time
            cmd = ['gh', 'pr', 'view', str(pr_num), '--json', 'createdAt']
            pr_result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if pr_result.returncode != 0:
                result.add_warning("Could not validate review response time")
                return
            
            pr_data = json.loads(pr_result.stdout)
            pr_created = datetime.fromisoformat(pr_data['createdAt'].replace('Z', '+00:00'))
            
            # Find earliest review
            earliest_review = None
            for review in reviews:
                review_time = datetime.fromisoformat(review['submitted_at'].replace('Z', '+00:00'))
                if earliest_review is None or review_time < earliest_review:
                    earliest_review = review_time
            
            if earliest_review:
                response_time_hours = (earliest_review - pr_created).total_seconds() / 3600
                result.add_detail('response_time_hours', response_time_hours)
                
                if response_time_hours > self.quality_gates.review_max_response_time_hours:
                    result.add_warning(f"Review response time too long: {response_time_hours:.1f} hours")
                    result.score -= 0.5
                else:
                    result.add_detail('timely_response', True)
            
        except Exception as e:
            result.add_warning(f"Could not validate response time: {e}")
    
    def _calculate_score(self, result: ValidationResult) -> None:
        """Calculate final validation score."""
        # Ensure score is within valid range
        result.score = max(0.0, min(5.0, result.score))
        
        # If there are errors, mark as invalid
        if result.errors:
            result.valid = False
        
        # Set validity based on score threshold
        if result.score < 3.0:
            result.valid = False