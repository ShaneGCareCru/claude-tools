"""Tests for handoff validator."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.claude_tasker.handoff.validator import Validator, ValidationResult
from src.claude_tasker.handoff.models import (
    Plan, Context, ContextType, DedupeStrategy, DedupeMethod,
    CreateIssueAction, CommentIssueAction
)
from src.claude_tasker.services.git_service import GitService
from src.claude_tasker.services.gh_service import GhService, IssueData, PRData


class TestValidationResult:
    """Test ValidationResult class."""
    
    def test_valid_result(self):
        """Test valid result creation."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert result.has_issues() is False
    
    def test_add_error(self):
        """Test adding errors."""
        result = ValidationResult()
        result.add_error("Test error")
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0] == "Test error"
        assert result.has_issues() is True
    
    def test_add_warning(self):
        """Test adding warnings."""
        result = ValidationResult()
        result.add_warning("Test warning")
        
        assert result.valid is True
        assert len(result.warnings) == 1
        assert result.warnings[0] == "Test warning"
        assert result.has_issues() is True
    
    def test_format_report_success(self):
        """Test format report for successful validation."""
        result = ValidationResult(valid=True)
        report = result.format_report()
        assert "✅ Validation passed" in report
    
    def test_format_report_errors(self):
        """Test format report with errors."""
        result = ValidationResult()
        result.add_error("Error 1")
        result.add_error("Error 2")
        result.add_warning("Warning 1")
        
        report = result.format_report()
        assert "❌ Validation failed" in report
        assert "🚨 Errors:" in report
        assert "• Error 1" in report
        assert "• Error 2" in report
        assert "⚠️  Warnings:" in report
        assert "• Warning 1" in report


class TestValidator:
    """Test Validator class."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return Validator()
    
    @pytest.fixture
    def validator_with_services(self):
        """Create validator with mocked services."""
        git_service = Mock(spec=GitService)
        gh_service = Mock(spec=GhService)
        return Validator(git_service=git_service, gh_service=gh_service)
    
    @pytest.fixture
    def valid_plan(self):
        """Create a valid plan for testing."""
        context = Context(type=ContextType.ISSUE, issue_number=123)
        action = CommentIssueAction(
            issue_number=123,
            comment="Test comment",
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_CONTENT_SIGNATURE)
        )
        return Plan(context=context, actions=[action], op_id="test_op_12345")
    
    def test_schema_loading(self, validator):
        """Test that schema is loaded correctly."""
        assert validator.schema is not None
        assert validator.schema.get("$id") is not None
        assert "properties" in validator.schema
    
    def test_valid_json_schema(self, validator, valid_plan):
        """Test JSON schema validation with valid plan."""
        plan_dict = valid_plan.to_dict()
        result = validator.validate_json_schema(plan_dict)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_invalid_json_schema_missing_required(self, validator):
        """Test JSON schema validation with missing required fields."""
        invalid_plan = {
            "version": "1.0",
            # Missing required fields: timestamp, op_id, context, actions
        }
        
        result = validator.validate_json_schema(invalid_plan)
        
        assert result.valid is False
        assert len(result.errors) > 0
        assert any("required" in error.lower() for error in result.errors)
    
    def test_invalid_json_schema_wrong_version(self, validator):
        """Test JSON schema validation with wrong version."""
        invalid_plan = {
            "version": "2.0",  # Only 1.0 is allowed
            "timestamp": "2024-01-01T00:00:00Z",
            "op_id": "test_op_12345",
            "context": {"type": "manual"},
            "actions": [{
                "type": "comment_issue",
                "issue_number": 123,
                "comment": "Test",
                "dedupe_strategy": {"method": "none"}
            }]
        }
        
        result = validator.validate_json_schema(invalid_plan)
        
        assert result.valid is False
        assert len(result.errors) > 0
    
    def test_semantic_validation_success(self, validator, valid_plan):
        """Test successful semantic validation."""
        result = validator.validate_semantic(valid_plan)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_semantic_validation_with_github_service(self, validator_with_services, valid_plan):
        """Test semantic validation with GitHub service."""
        # Mock issue exists and is open
        issue_data = IssueData(
            number=123, title="Test", body="Test body", labels=[],
            url="https://example.com", author="test", state="open"
        )
        validator_with_services.gh_service.get_issue.return_value = issue_data
        
        result = validator_with_services.validate_semantic(valid_plan)
        
        assert result.valid is True
        validator_with_services.gh_service.get_issue.assert_called_with(123)
    
    def test_semantic_validation_closed_issue(self, validator_with_services, valid_plan):
        """Test semantic validation with closed issue."""
        # Mock issue exists but is closed
        issue_data = IssueData(
            number=123, title="Test", body="Test body", labels=[],
            url="https://example.com", author="test", state="closed"
        )
        validator_with_services.gh_service.get_issue.return_value = issue_data
        
        result = validator_with_services.validate_semantic(valid_plan)
        
        # Should still be valid but with warning
        assert result.valid is True
        assert len(result.warnings) == 1
        assert "closed" in result.warnings[0].lower()
    
    def test_semantic_validation_missing_issue(self, validator_with_services, valid_plan):
        """Test semantic validation with missing issue."""
        # Mock issue not found
        validator_with_services.gh_service.get_issue.return_value = None
        
        result = validator_with_services.validate_semantic(valid_plan)
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert "not found" in result.errors[0]
    
    def test_semantic_validation_branch_check(self, validator_with_services):
        """Test semantic validation with branch checking."""
        context = Context(type=ContextType.ISSUE, issue_number=123, branch="feature-branch")
        action = CommentIssueAction(
            issue_number=123,
            comment="Test",
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.NONE)
        )
        plan = Plan(context=context, actions=[action])
        
        # Mock branch doesn't exist
        validator_with_services.git_service.branch_exists.return_value = False
        
        result = validator_with_services.validate_semantic(plan)
        
        assert result.valid is True  # Warning, not error
        assert len(result.warnings) == 1
        assert "does not exist" in result.warnings[0]
        validator_with_services.git_service.branch_exists.assert_called_with("feature-branch")
    
    def test_action_validation_title_length(self, validator):
        """Test action validation for title length."""
        context = Context(type=ContextType.MANUAL)
        
        # Title too long
        action = CreateIssueAction(
            title="A" * 300,  # Too long
            body="Test body",
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.NONE)
        )
        plan = Plan(context=context, actions=[action])
        
        result = validator.validate_semantic(plan)
        
        assert result.valid is False
        assert any("too long" in error for error in result.errors)
    
    def test_action_validation_empty_comment(self, validator):
        """Test action validation for empty comment."""
        context = Context(type=ContextType.MANUAL)
        action = CommentIssueAction(
            issue_number=123,
            comment="",  # Empty comment
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.NONE)
        )
        plan = Plan(context=context, actions=[action])
        
        result = validator.validate_semantic(plan)
        
        assert result.valid is False
        assert any("cannot be empty" in error for error in result.errors)
    
    def test_action_validation_invalid_assignee(self, validator):
        """Test action validation for invalid assignee."""
        context = Context(type=ContextType.MANUAL)
        action = CreateIssueAction(
            title="Test",
            body="Test body",
            assignees=["invalid-username-"],  # Invalid format
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.NONE)
        )
        plan = Plan(context=context, actions=[action])
        
        result = validator.validate_semantic(plan)
        
        assert result.valid is False
        assert any("Invalid GitHub username" in error for error in result.errors)
    
    def test_action_consistency_validation(self, validator):
        """Test action consistency validation."""
        context = Context(type=ContextType.ISSUE, issue_number=123, branch="main")
        
        # Action references different issue and branch
        action = CommentIssueAction(
            issue_number=456,  # Different issue
            comment="Test",
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.NONE)
        )
        plan = Plan(context=context, actions=[action])
        
        result = validator.validate_semantic(plan)
        
        assert result.valid is True  # Valid but with warnings
        assert len(result.warnings) > 0
        assert any("doesn't match" in warning for warning in result.warnings)
    
    def test_validate_plan_file_not_found(self, validator):
        """Test validating non-existent plan file."""
        result = validator.validate_plan_file(Path("non-existent.json"))
        
        assert result.valid is False
        assert any("not found" in error for error in result.errors)
    
    def test_validate_plan_file_invalid_json(self, validator):
        """Test validating plan file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            f.flush()
            
            result = validator.validate_plan_file(Path(f.name))
            
            assert result.valid is False
            assert any("Failed to load" in error for error in result.errors)
            
            # Clean up
            Path(f.name).unlink()
    
    def test_validate_plan_file_success(self, validator, valid_plan):
        """Test successful plan file validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(valid_plan.to_json())
            f.flush()
            
            result = validator.validate_plan_file(Path(f.name))
            
            assert result.valid is True
            assert len(result.errors) == 0
            
            # Clean up
            Path(f.name).unlink()
    
    def test_validate_plan_object_success(self, validator, valid_plan):
        """Test successful plan object validation."""
        result = validator.validate_plan_object(valid_plan)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_validate_plan_object_serialization_error(self, validator):
        """Test plan object validation with serialization error."""
        # Create a mock plan that fails serialization
        mock_plan = Mock()
        mock_plan.to_dict.side_effect = Exception("Serialization failed")
        
        result = validator.validate_plan_object(mock_plan)
        
        assert result.valid is False
        assert any("Failed to serialize" in error for error in result.errors)
    
    def test_get_schema_info(self, validator):
        """Test schema info retrieval."""
        info = validator.get_schema_info()
        
        assert isinstance(info, dict)
        assert "supported_actions" in info
        assert "supported_dedupe_methods" in info
        assert "create_issue" in info["supported_actions"]
        assert "dedupe_marker" in info["supported_dedupe_methods"]


class TestValidatorIntegration:
    """Integration tests for validator with real JSON schema."""
    
    def test_full_validation_pipeline(self):
        """Test complete validation pipeline."""
        # Create a comprehensive plan
        context = Context(
            type=ContextType.ISSUE,
            issue_number=123,
            branch="feature-branch",
            repository="owner/repo"
        )
        
        actions = [
            CommentIssueAction(
                issue_number=123,
                comment="Starting work on this issue",
                dedupe_strategy=DedupeStrategy(
                    method=DedupeMethod.DEDUPE_MARKER,
                    marker="start-work-123"
                )
            ),
            CreateIssueAction(
                title="Follow-up issue",
                body="This is a follow-up issue that needs to be addressed",
                labels=["enhancement", "follow-up"],
                assignees=["developer1"],
                dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
            )
        ]
        
        plan = Plan(
            context=context,
            actions=actions,
            op_id="integration_test_123"
        )
        
        validator = Validator()
        
        # Test complete validation
        result = validator.validate_plan_object(plan)
        
        # Should pass JSON schema validation
        assert result.valid is True
        
        # Should have some warnings about missing services
        # (since we don't have real GitHub/Git services)
        # But no errors
        assert len(result.errors) == 0
    
    def test_schema_compliance_edge_cases(self):
        """Test schema compliance with edge cases."""
        validator = Validator()
        
        # Test minimum valid plan
        minimal_plan_dict = {
            "version": "1.0",
            "timestamp": "2024-01-01T00:00:00Z",
            "op_id": "minimal_test",
            "context": {
                "type": "manual"
            },
            "actions": [{
                "type": "comment_issue",
                "issue_number": 1,
                "comment": "Test",
                "dedupe_strategy": {
                    "method": "none"
                }
            }]
        }
        
        result = validator.validate_json_schema(minimal_plan_dict)
        assert result.valid is True
        
        # Test with all optional fields
        maximal_plan_dict = {
            "version": "1.0",
            "timestamp": "2024-01-01T00:00:00Z",
            "op_id": "maximal_test_12345",
            "context": {
                "type": "issue",
                "issue_number": 123,
                "pr_number": None,
                "branch": "feature-branch",
                "repository": "owner/repo",
                "description": "Maximal test plan"
            },
            "actions": [{
                "type": "create_issue",
                "title": "Test Issue",
                "body": "Test issue body",
                "labels": ["bug", "high-priority"],
                "assignees": ["dev1", "dev2"],
                "dedupe_strategy": {
                    "method": "by_content_signature",
                    "signature_lines": 5
                }
            }]
        }
        
        result = validator.validate_json_schema(maximal_plan_dict)
        assert result.valid is True