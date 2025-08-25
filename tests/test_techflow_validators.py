"""
Comprehensive tests for TechFlow validators.

This module tests all validator components to ensure proper quality gate
enforcement across the entire workflow.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from tests.techflow.config import QualityGates
from tests.techflow.validators import (
    ValidatorRegistry, ValidationResult,
    BugIssueValidator, PullRequestValidator,
    ReviewValidator, FeedbackValidator
)


class TestValidationResult:
    """Test ValidationResult class."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation and defaults."""
        result = ValidationResult(valid=True, score=4.5)
        
        assert result.valid is True
        assert result.score == 4.5
        assert result.errors == []
        assert result.warnings == []
        assert result.details == {}
    
    def test_validation_result_add_error(self):
        """Test adding errors to validation result."""
        result = ValidationResult(valid=True)
        
        result.add_error("Test error")
        
        assert result.valid is False  # Should become False when error added
        assert "Test error" in result.errors
    
    def test_validation_result_add_warning(self):
        """Test adding warnings to validation result."""
        result = ValidationResult(valid=True)
        
        result.add_warning("Test warning")
        
        assert result.valid is True  # Should remain True for warnings
        assert "Test warning" in result.warnings
    
    def test_validation_result_add_detail(self):
        """Test adding details to validation result."""
        result = ValidationResult(valid=True)
        
        result.add_detail("key1", "value1")
        result.add_detail("key2", 123)
        
        assert result.details["key1"] == "value1"
        assert result.details["key2"] == 123


class TestValidatorRegistry:
    """Test ValidatorRegistry class."""
    
    def test_validator_registry_creation(self):
        """Test ValidatorRegistry initialization."""
        quality_gates = QualityGates()
        registry = ValidatorRegistry(quality_gates)
        
        assert registry.quality_gates == quality_gates
        assert registry.bug_validator is not None
        assert registry.pr_validator is not None
        assert registry.review_validator is not None
        assert registry.feedback_validator is not None
    
    @patch('tests.techflow.validators.bug_issue.BugIssueValidator.validate')
    def test_validate_bug_issue(self, mock_validate):
        """Test bug issue validation through registry."""
        quality_gates = QualityGates()
        registry = ValidatorRegistry(quality_gates)
        
        mock_result = ValidationResult(valid=True, score=4.0)
        mock_validate.return_value = mock_result
        
        result = registry.validate_bug_issue(123)
        
        mock_validate.assert_called_once_with(123)
        assert result == mock_result
    
    @patch('tests.techflow.validators.pull_request.PullRequestValidator.validate')
    def test_validate_pull_request(self, mock_validate):
        """Test PR validation through registry."""
        quality_gates = QualityGates()
        registry = ValidatorRegistry(quality_gates)
        
        mock_result = ValidationResult(valid=True, score=3.5)
        mock_validate.return_value = mock_result
        
        result = registry.validate_pull_request(456)
        
        mock_validate.assert_called_once_with(456)
        assert result == mock_result


class TestBugIssueValidator:
    """Test BugIssueValidator class."""
    
    def test_bug_issue_validator_creation(self):
        """Test BugIssueValidator initialization."""
        quality_gates = QualityGates()
        validator = BugIssueValidator(quality_gates)
        
        assert validator.quality_gates == quality_gates
        assert len(validator.REQUIRED_SECTIONS) == 8
        assert "Bug Description" in validator.REQUIRED_SECTIONS
        assert "Acceptance Criteria" in validator.REQUIRED_SECTIONS
    
    @patch('subprocess.run')
    def test_get_issue_data_success(self, mock_run):
        """Test successful issue data retrieval."""
        quality_gates = QualityGates()
        validator = BugIssueValidator(quality_gates)
        
        # Mock successful gh CLI response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'title': 'Test Bug Issue',
            'body': 'Bug description here',
            'state': 'open',
            'labels': [{'name': 'bug'}]
        })
        mock_run.return_value = mock_result
        
        data = validator._get_issue_data(123)
        
        assert data['title'] == 'Test Bug Issue'
        assert data['body'] == 'Bug description here'
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_get_issue_data_failure(self, mock_run):
        """Test issue data retrieval failure."""
        quality_gates = QualityGates()
        validator = BugIssueValidator(quality_gates)
        
        # Mock failed gh CLI response
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Issue not found"
        mock_run.return_value = mock_result
        
        data = validator._get_issue_data(123)
        
        assert data == {}
        mock_run.assert_called_once()
    
    def test_validate_required_sections_all_present(self):
        """Test validation when all required sections are present."""
        quality_gates = QualityGates()
        validator = BugIssueValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        issue_body = """
        ## Bug Description
        This is a test bug.
        
        ## Reproduction Steps
        1. Step 1
        2. Step 2
        
        ## Expected Behavior
        Should work correctly.
        
        ## Actual Behavior
        Does not work.
        
        ## Root Cause Analysis
        The cause is XYZ.
        
        ## Acceptance Criteria
        - [ ] Fix should work
        - [ ] Tests should pass
        - [ ] Documentation updated
        
        ## Test Plan
        Test approach here.
        
        ## Rollback Plan
        Rollback steps here.
        """
        
        validator._validate_required_sections(issue_body, result)
        
        assert result.valid is True
        assert len(result.errors) == 0
        assert len(result.details['found_sections']) == 8
        assert len(result.details['missing_sections']) == 0
    
    def test_validate_required_sections_missing(self):
        """Test validation when required sections are missing."""
        quality_gates = QualityGates()
        validator = BugIssueValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        issue_body = """
        ## Bug Description
        This is a test bug.
        
        ## Reproduction Steps
        1. Step 1
        2. Step 2
        """
        
        validator._validate_required_sections(issue_body, result)
        
        assert result.valid is False
        assert len(result.errors) > 0
        assert "Missing required sections" in result.errors[0]
        assert len(result.details['missing_sections']) > 0
    
    def test_validate_acceptance_criteria_sufficient(self):
        """Test acceptance criteria validation with sufficient criteria."""
        quality_gates = QualityGates(bug_min_acceptance_criteria=3)
        validator = BugIssueValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        issue_body = """
        ## Acceptance Criteria
        - [ ] First criteria
        - [ ] Second criteria  
        - [ ] Third criteria
        - [ ] Fourth criteria
        """
        
        validator._validate_acceptance_criteria(issue_body, result)
        
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.details['acceptance_criteria_count'] >= 3
    
    def test_validate_acceptance_criteria_insufficient(self):
        """Test acceptance criteria validation with insufficient criteria."""
        quality_gates = QualityGates(bug_min_acceptance_criteria=5)
        validator = BugIssueValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        issue_body = """
        ## Acceptance Criteria
        - [ ] First criteria
        - [ ] Second criteria
        """
        
        validator._validate_acceptance_criteria(issue_body, result)
        
        assert len(result.errors) > 0
        assert "Need at least 5 acceptance criteria" in result.errors[0]
        assert result.details['acceptance_criteria_count'] < 5
    
    def test_validate_title_quality_good(self):
        """Test title validation with good title."""
        quality_gates = QualityGates()
        validator = BugIssueValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        validator._validate_title_quality("Bug: User authentication fails with invalid credentials", result)
        
        assert len(result.errors) == 0
        # Should have minimal warnings for a good title
    
    def test_validate_title_quality_poor(self):
        """Test title validation with poor title."""
        quality_gates = QualityGates()
        validator = BugIssueValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        validator._validate_title_quality("Fix", result)
        
        assert len(result.warnings) > 0
        assert result.score < 5.0  # Should be penalized


class TestPullRequestValidator:
    """Test PullRequestValidator class."""
    
    def test_pr_validator_creation(self):
        """Test PullRequestValidator initialization."""
        quality_gates = QualityGates()
        validator = PullRequestValidator(quality_gates)
        
        assert validator.quality_gates == quality_gates
    
    @patch('subprocess.run')
    def test_get_pr_data_success(self, mock_run):
        """Test successful PR data retrieval."""
        quality_gates = QualityGates()
        validator = PullRequestValidator(quality_gates)
        
        # Mock successful gh CLI response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'title': 'Fix bug #123',
            'body': 'Fixes issue #123 by updating authentication',
            'baseRefName': 'main',
            'headRefName': 'issue-123-fix',
            'state': 'open',
            'number': 456,
            'url': 'https://github.com/test/repo/pull/456'
        })
        mock_run.return_value = mock_result
        
        data = validator._get_pr_data(456)
        
        assert data['title'] == 'Fix bug #123'
        assert data['baseRefName'] == 'main'
        assert data['headRefName'] == 'issue-123-fix'
        mock_run.assert_called_once()
    
    def test_validate_issue_link_present(self):
        """Test issue link validation when link is present."""
        quality_gates = QualityGates()
        validator = PullRequestValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        pr_data = {
            'title': 'Fix authentication bug',
            'body': 'This PR fixes #123 by updating the auth logic.'
        }
        
        validator._validate_issue_link(pr_data, result)
        
        assert result.valid is True
        assert len(result.errors) == 0
        assert '123' in result.details['linked_issues']
    
    def test_validate_issue_link_missing(self):
        """Test issue link validation when link is missing."""
        quality_gates = QualityGates()
        validator = PullRequestValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        pr_data = {
            'title': 'Fix authentication bug',
            'body': 'This PR updates the auth logic.'
        }
        
        validator._validate_issue_link(pr_data, result)
        
        assert len(result.errors) > 0
        assert "does not reference any issues" in result.errors[0]
        assert len(result.details['linked_issues']) == 0
    
    @patch('subprocess.run')
    def test_validate_has_changes_with_files(self, mock_run):
        """Test change validation when PR has file changes."""
        quality_gates = QualityGates()
        validator = PullRequestValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        # Mock gh CLI response with changed files
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "src/auth.py\ntests/test_auth.py\nREADME.md"
        mock_run.return_value = mock_result
        
        validator._validate_has_changes(456, result)
        
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.details['files_changed_count'] == 3
        assert 'src/auth.py' in result.details['changed_files']
    
    @patch('subprocess.run')
    def test_validate_has_changes_no_files(self, mock_run):
        """Test change validation when PR has no file changes."""
        quality_gates = QualityGates()
        validator = PullRequestValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        # Mock gh CLI response with no changed files
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        
        validator._validate_has_changes(456, result)
        
        assert len(result.errors) > 0
        assert "PR has no file changes" in result.errors[0]
        assert result.details['files_changed_count'] == 0
    
    def test_validate_target_branch_correct(self):
        """Test target branch validation when targeting main."""
        quality_gates = QualityGates()
        validator = PullRequestValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        pr_data = {
            'baseRefName': 'main',
            'headRefName': 'feature-branch'
        }
        
        validator._validate_target_branch(pr_data, result)
        
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.details['base_branch'] == 'main'
        assert result.details['head_branch'] == 'feature-branch'
    
    def test_validate_target_branch_incorrect(self):
        """Test target branch validation when not targeting main."""
        quality_gates = QualityGates()
        validator = PullRequestValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        pr_data = {
            'baseRefName': 'develop',
            'headRefName': 'feature-branch'
        }
        
        validator._validate_target_branch(pr_data, result)
        
        assert len(result.errors) > 0
        assert "targets 'develop' instead of 'main'" in result.errors[0]


class TestReviewValidator:
    """Test ReviewValidator class."""
    
    def test_review_validator_creation(self):
        """Test ReviewValidator initialization."""
        quality_gates = QualityGates()
        validator = ReviewValidator(quality_gates)
        
        assert validator.quality_gates == quality_gates
    
    @patch('subprocess.run')
    def test_get_pr_reviews_success(self, mock_run):
        """Test successful PR review retrieval."""
        quality_gates = QualityGates()
        validator = ReviewValidator(quality_gates)
        
        # Mock successful gh API response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {
                'id': 123,
                'state': 'APPROVED',
                'body': 'LGTM! Great work on the authentication fix.',
                'submitted_at': '2023-12-01T10:00:00Z'
            },
            {
                'id': 124,
                'state': 'CHANGES_REQUESTED',
                'body': 'Please add unit tests for the new authentication method.',
                'submitted_at': '2023-12-01T09:00:00Z'
            }
        ])
        mock_run.return_value = mock_result
        
        reviews = validator._get_pr_reviews(456)
        
        assert len(reviews) == 2
        assert reviews[0]['state'] == 'APPROVED'
        assert reviews[1]['state'] == 'CHANGES_REQUESTED'
        mock_run.assert_called_once()
    
    def test_validate_review_placement_valid(self):
        """Test review placement validation with valid reviews."""
        quality_gates = QualityGates()
        validator = ReviewValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        reviews = [
            {'state': 'APPROVED', 'body': 'Looks good'},
            {'state': 'CHANGES_REQUESTED', 'body': 'Needs tests'}
        ]
        
        validator._validate_review_placement(reviews, result)
        
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.details['valid_reviews'] == 2
    
    def test_validate_review_placement_invalid(self):
        """Test review placement validation with no valid reviews."""
        quality_gates = QualityGates()
        validator = ReviewValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        reviews = [
            {'state': 'UNKNOWN', 'body': 'Invalid review state'}
        ]
        
        validator._validate_review_placement(reviews, result)
        
        assert len(result.errors) > 0
        assert "No valid PR reviews found" in result.errors[0]
        assert result.details['valid_reviews'] == 0
    
    def test_validate_review_quality_specific_comments(self):
        """Test review quality validation with specific comments."""
        quality_gates = QualityGates(review_min_specific_comments=1)
        validator = ReviewValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        reviews = [
            {
                'body': 'The authenticate function should handle edge cases better. Consider adding validation for empty passwords.'
            },
            {
                'body': 'Please update the login method to use the new authentication class.'
            }
        ]
        
        validator._validate_review_quality(reviews, result)
        
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.details['specific_comments'] >= 1
        assert result.details['actionable_comments'] >= 1
    
    def test_validate_review_quality_insufficient_comments(self):
        """Test review quality validation with insufficient specific comments."""
        quality_gates = QualityGates(review_min_specific_comments=5)
        validator = ReviewValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        reviews = [
            {'body': 'LGTM'},
            {'body': 'Looks good to me'}
        ]
        
        validator._validate_review_quality(reviews, result)
        
        assert len(result.errors) > 0
        assert "Need at least 5 specific comments" in result.errors[0]
        assert result.details['specific_comments'] < 5


class TestFeedbackValidator:
    """Test FeedbackValidator class."""
    
    def test_feedback_validator_creation(self):
        """Test FeedbackValidator initialization."""
        quality_gates = QualityGates()
        validator = FeedbackValidator(quality_gates)
        
        assert validator.quality_gates == quality_gates
    
    def test_validate_feedback_addressed_with_commits(self):
        """Test feedback validation when changes were addressed with commits."""
        quality_gates = QualityGates()
        validator = FeedbackValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        # Mock change request followed by addressing commit
        reviews = [
            {
                'state': 'CHANGES_REQUESTED',
                'submitted_at': '2023-12-01T09:00:00Z'
            }
        ]
        
        commits = [
            {
                'commit': {
                    'message': 'Initial implementation',
                    'author': {'date': '2023-12-01T08:00:00Z'}
                }
            },
            {
                'commit': {
                    'message': 'Fix authentication issues based on review feedback',
                    'author': {'date': '2023-12-01T10:00:00Z'}
                }
            }
        ]
        
        validator._validate_feedback_addressed(reviews, commits, result)
        
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.details['commits_after_reviews'] == 1
        assert result.details['addressing_commits'] == 1
    
    def test_validate_feedback_addressed_no_commits(self):
        """Test feedback validation when changes were requested but not addressed."""
        quality_gates = QualityGates()
        validator = FeedbackValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        # Mock change request with no follow-up commits
        reviews = [
            {
                'state': 'CHANGES_REQUESTED',
                'submitted_at': '2023-12-01T09:00:00Z'
            }
        ]
        
        commits = [
            {
                'commit': {
                    'message': 'Initial implementation',
                    'author': {'date': '2023-12-01T08:00:00Z'}
                }
            }
        ]
        
        validator._validate_feedback_addressed(reviews, commits, result)
        
        assert len(result.errors) > 0
        assert "Changes were requested but no commits were made" in result.errors[0]
        assert result.details['commits_after_reviews'] == 0
    
    def test_validate_iteration_count_reasonable(self):
        """Test iteration count validation with reasonable iterations."""
        quality_gates = QualityGates(feedback_max_iterations=3)
        validator = FeedbackValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        reviews = [
            {'state': 'CHANGES_REQUESTED'},
            {'state': 'APPROVED'}
        ]
        
        commits = [
            {'commit': {'message': 'Initial'}},
            {'commit': {'message': 'Fix 1'}},
            {'commit': {'message': 'Fix 2'}}
        ]
        
        validator._validate_iteration_count(reviews, commits, result)
        
        assert result.valid is True
        assert len(result.warnings) == 0
        assert result.details['review_rounds'] == 2
    
    def test_validate_iteration_count_excessive(self):
        """Test iteration count validation with excessive iterations."""
        quality_gates = QualityGates(feedback_max_iterations=2)
        validator = FeedbackValidator(quality_gates)
        result = ValidationResult(valid=True, score=5.0)
        
        reviews = [
            {'state': 'CHANGES_REQUESTED'},
            {'state': 'CHANGES_REQUESTED'},
            {'state': 'CHANGES_REQUESTED'},
            {'state': 'APPROVED'}
        ]
        
        commits = []
        
        validator._validate_iteration_count(reviews, commits, result)
        
        assert len(result.warnings) > 0
        assert "Too many feedback iterations" in result.warnings[0]
        assert result.details['review_rounds'] == 4