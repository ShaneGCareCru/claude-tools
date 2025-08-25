"""
Feedback loop validator for TechFlow test framework.
"""

import subprocess
import json
import logging
from datetime import datetime

from .registry import ValidationResult


class FeedbackValidator:
    """Validator for feedback loop quality."""
    
    def __init__(self, quality_gates):
        self.quality_gates = quality_gates
        self.logger = logging.getLogger(__name__)
    
    def validate(self, pr_num: int) -> ValidationResult:
        """Validate feedback loop quality."""
        result = ValidationResult(valid=True, score=5.0)
        
        try:
            # Get PR reviews and commits
            reviews = self._get_pr_reviews(pr_num)
            commits = self._get_pr_commits(pr_num)
            
            result.add_detail('review_count', len(reviews))
            result.add_detail('commit_count', len(commits))
            
            # Check if feedback was addressed
            if self.quality_gates.feedback_must_address_comments:
                self._validate_feedback_addressed(reviews, commits, result)
            
            # Validate iteration count
            self._validate_iteration_count(reviews, commits, result)
            
            # Validate feedback quality
            self._validate_feedback_quality(reviews, commits, result)
            
            # Calculate final score
            self._calculate_score(result)
            
        except Exception as e:
            result.add_error(f"Validation error: {str(e)}")
            self.logger.error(f"Error validating feedback loop for PR #{pr_num}: {e}")
        
        return result
    
    def _get_pr_reviews(self, pr_num: int) -> list:
        """Get PR review data."""
        try:
            cmd = ['gh', 'api', f'/repos/:owner/:repo/pulls/{pr_num}/reviews']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return []
            
            reviews = json.loads(result.stdout)
            return reviews if isinstance(reviews, list) else []
            
        except Exception:
            return []
    
    def _get_pr_commits(self, pr_num: int) -> list:
        """Get PR commit data."""
        try:
            cmd = ['gh', 'api', f'/repos/:owner/:repo/pulls/{pr_num}/commits']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return []
            
            commits = json.loads(result.stdout)
            return commits if isinstance(commits, list) else []
            
        except Exception:
            return []
    
    def _validate_feedback_addressed(self, reviews: list, commits: list, result: ValidationResult) -> None:
        """Validate that review feedback was addressed."""
        # Find reviews requesting changes
        change_requests = [r for r in reviews if r.get('state') == 'CHANGES_REQUESTED']
        
        if not change_requests:
            result.add_detail('no_changes_requested', True)
            return
        
        result.add_detail('changes_requested_count', len(change_requests))
        
        # Check for commits after change requests
        commits_after_reviews = []
        for change_request in change_requests:
            review_time = datetime.fromisoformat(change_request['submitted_at'].replace('Z', '+00:00'))
            
            for commit in commits:
                commit_time = datetime.fromisoformat(commit['commit']['author']['date'].replace('Z', '+00:00'))
                if commit_time > review_time:
                    commits_after_reviews.append(commit)
        
        result.add_detail('commits_after_reviews', len(commits_after_reviews))
        
        if change_requests and not commits_after_reviews:
            result.add_error("Changes were requested but no commits were made to address them")
            result.score -= 2.0
        
        # Look for addressing language in commit messages
        addressing_keywords = ['fix', 'address', 'resolve', 'update', 'improve', 'refactor']
        addressing_commits = 0
        
        for commit in commits_after_reviews:
            commit_message = commit.get('commit', {}).get('message', '').lower()
            if any(keyword in commit_message for keyword in addressing_keywords):
                addressing_commits += 1
        
        result.add_detail('addressing_commits', addressing_commits)
        
        if change_requests and addressing_commits == 0:
            result.add_warning("No commit messages indicate addressing review feedback")
            result.score -= 0.5
    
    def _validate_iteration_count(self, reviews: list, commits: list, result: ValidationResult) -> None:
        """Validate number of feedback iterations."""
        # Count review rounds
        review_rounds = len([r for r in reviews if r.get('state') in ['CHANGES_REQUESTED', 'APPROVED']])
        result.add_detail('review_rounds', review_rounds)
        
        if review_rounds > self.quality_gates.feedback_max_iterations:
            result.add_warning(f"Too many feedback iterations: {review_rounds}")
            result.score -= 0.5
        
        # Excessive commits might indicate poor initial implementation
        if len(commits) > 10:
            result.add_warning(f"High commit count may indicate excessive iteration: {len(commits)}")
            result.score -= 0.3
    
    def _validate_feedback_quality(self, reviews: list, commits: list, result: ValidationResult) -> None:
        """Validate quality of the feedback loop."""
        if not reviews:
            result.add_warning("No reviews in feedback loop")
            result.score -= 1.0
            return
        
        # Check for final approval
        final_review = max(reviews, key=lambda r: r['submitted_at'])
        if final_review.get('state') != 'APPROVED':
            result.add_warning("Final review is not an approval")
            result.score -= 0.5
        else:
            result.add_detail('final_approval', True)
        
        # Validate review progression (changes requested -> approved)
        review_states = [r.get('state') for r in sorted(reviews, key=lambda r: r['submitted_at'])]
        result.add_detail('review_progression', review_states)
        
        # Good progression: CHANGES_REQUESTED followed by APPROVED
        if len(review_states) >= 2:
            has_good_progression = any(
                review_states[i] == 'CHANGES_REQUESTED' and 
                review_states[i+1] == 'APPROVED'
                for i in range(len(review_states)-1)
            )
            
            if has_good_progression:
                result.add_detail('good_review_progression', True)
            else:
                result.add_warning("Review progression could be improved")
                result.score -= 0.2
    
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