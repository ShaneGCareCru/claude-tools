"""Validation module for handoff plans with JSON Schema and semantic checks."""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from jsonschema import validate, ValidationError, Draft7Validator

from .models import Plan
from ..services.git_service import GitService
from ..services.gh_service import GhService


logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of plan validation."""
    
    def __init__(self, valid: bool = True):
        self.valid = valid
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def add_error(self, message: str):
        """Add validation error."""
        self.errors.append(message)
        self.valid = False
        
    def add_warning(self, message: str):
        """Add validation warning."""
        self.warnings.append(message)
        
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return len(self.errors) > 0 or len(self.warnings) > 0
        
    def format_report(self) -> str:
        """Format validation report."""
        report = []
        
        if self.valid:
            report.append("✅ Validation passed")
        else:
            report.append("❌ Validation failed")
            
        if self.errors:
            report.append("\n🚨 Errors:")
            for error in self.errors:
                report.append(f"  • {error}")
                
        if self.warnings:
            report.append("\n⚠️  Warnings:")
            for warning in self.warnings:
                report.append(f"  • {warning}")
                
        return '\n'.join(report)


class Validator:
    """Validates handoff plans with JSON Schema and semantic checks."""
    
    def __init__(self, 
                 git_service: Optional[GitService] = None,
                 gh_service: Optional[GhService] = None):
        """
        Initialize validator.
        
        Args:
            git_service: Git service for branch validation
            gh_service: GitHub service for issue/PR validation
        """
        self.git_service = git_service
        self.gh_service = gh_service
        self.schema = self._load_schema()
        
    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema from file."""
        schema_path = Path(__file__).parent / "schema.json"
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load schema: {e}")
            return {}
    
    def validate_json_schema(self, plan_dict: Dict[str, Any]) -> ValidationResult:
        """
        Validate plan against JSON schema.
        
        Args:
            plan_dict: Plan data as dictionary
            
        Returns:
            ValidationResult with schema validation results
        """
        result = ValidationResult()
        
        if not self.schema:
            result.add_error("Schema not loaded")
            return result
        
        try:
            validate(instance=plan_dict, schema=self.schema)
        except ValidationError as e:
            # Format validation error path
            path = " → ".join(str(p) for p in e.path) if e.path else "root"
            result.add_error(f"Schema validation failed at {path}: {e.message}")
            
        return result
    
    def validate_semantic(self, plan: Plan) -> ValidationResult:
        """
        Perform semantic validation of plan.
        
        Args:
            plan: Plan object to validate
            
        Returns:
            ValidationResult with semantic validation results
        """
        result = ValidationResult()
        
        # Validate context-specific requirements
        self._validate_context(plan, result)
        
        # Validate each action
        for i, action in enumerate(plan.actions):
            self._validate_action(action, i, result)
        
        # Validate action consistency
        self._validate_action_consistency(plan, result)
        
        return result
    
    def validate_plan_file(self, file_path: Path) -> ValidationResult:
        """
        Validate plan from file.
        
        Args:
            file_path: Path to plan JSON file
            
        Returns:
            ValidationResult with complete validation results
        """
        result = ValidationResult()
        
        # Check file exists
        if not file_path.exists():
            result.add_error(f"Plan file not found: {file_path}")
            return result
        
        # Load and parse JSON
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                plan_dict = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            result.add_error(f"Failed to load plan file: {e}")
            return result
        
        # JSON Schema validation
        schema_result = self.validate_json_schema(plan_dict)
        result.errors.extend(schema_result.errors)
        result.warnings.extend(schema_result.warnings)
        
        if not schema_result.valid:
            return result
        
        # Parse plan object
        try:
            plan = Plan.from_dict(plan_dict)
        except Exception as e:
            result.add_error(f"Failed to parse plan: {e}")
            return result
        
        # Semantic validation
        semantic_result = self.validate_semantic(plan)
        result.errors.extend(semantic_result.errors)
        result.warnings.extend(semantic_result.warnings)
        
        if not result.valid:
            result.valid = semantic_result.valid
        
        return result
    
    def validate_plan_object(self, plan: Plan) -> ValidationResult:
        """
        Validate plan object completely.
        
        Args:
            plan: Plan object to validate
            
        Returns:
            ValidationResult with complete validation results
        """
        result = ValidationResult()
        
        # Convert to dict for schema validation
        try:
            plan_dict = plan.to_dict()
        except Exception as e:
            result.add_error(f"Failed to serialize plan: {e}")
            return result
        
        # JSON Schema validation
        schema_result = self.validate_json_schema(plan_dict)
        result.errors.extend(schema_result.errors)
        result.warnings.extend(schema_result.warnings)
        
        if not schema_result.valid:
            result.valid = False
        
        # Semantic validation
        semantic_result = self.validate_semantic(plan)
        result.errors.extend(semantic_result.errors)
        result.warnings.extend(semantic_result.warnings)
        
        if not semantic_result.valid:
            result.valid = False
        
        return result
    
    def _validate_context(self, plan: Plan, result: ValidationResult):
        """Validate context-specific requirements."""
        context = plan.context
        
        # Validate issue/PR existence if services available
        if context.type.value == "issue" and context.issue_number:
            if self.gh_service:
                issue_data = self.gh_service.get_issue(context.issue_number)
                if not issue_data:
                    result.add_error(f"Issue #{context.issue_number} not found")
                elif issue_data.state == "closed":
                    result.add_warning(f"Issue #{context.issue_number} is closed")
        
        elif context.type.value == "pr" and context.pr_number:
            if self.gh_service:
                pr_data = self.gh_service.get_pr(context.pr_number)
                if not pr_data:
                    result.add_error(f"PR #{context.pr_number} not found")
        
        # Validate branch existence
        if context.branch and self.git_service:
            if not self.git_service.branch_exists(context.branch):
                result.add_warning(f"Branch '{context.branch}' does not exist")
        
        # Validate repository format
        if context.repository:
            if not re.match(r'^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$', context.repository):
                result.add_error(f"Invalid repository format: {context.repository}")
    
    def _validate_action(self, action: Any, index: int, result: ValidationResult):
        """Validate individual action."""
        action_prefix = f"Action {index + 1}"
        
        # Validate title/body lengths
        if hasattr(action, 'title'):
            title_len = len(action.title)
            if title_len > 256:
                result.add_error(f"{action_prefix}: Title too long ({title_len} > 256)")
            if title_len == 0:
                result.add_error(f"{action_prefix}: Title cannot be empty")
        
        if hasattr(action, 'body'):
            body_len = len(action.body)
            if body_len > 65536:
                result.add_error(f"{action_prefix}: Body too long ({body_len} > 65536)")
            if body_len == 0:
                result.add_error(f"{action_prefix}: Body cannot be empty")
        
        if hasattr(action, 'comment'):
            comment_len = len(action.comment)
            if comment_len > 65536:
                result.add_error(f"{action_prefix}: Comment too long ({comment_len} > 65536)")
            if comment_len == 0:
                result.add_error(f"{action_prefix}: Comment cannot be empty")
        
        # Validate branch names for PR creation
        if hasattr(action, 'head_branch'):
            if not action.head_branch:
                result.add_error(f"{action_prefix}: head_branch cannot be empty")
            elif self.git_service and not self.git_service.branch_exists(action.head_branch):
                result.add_warning(f"{action_prefix}: Branch '{action.head_branch}' does not exist")
        
        # Validate issue/PR numbers exist
        if hasattr(action, 'issue_number'):
            if self.gh_service:
                issue_data = self.gh_service.get_issue(action.issue_number)
                if not issue_data:
                    result.add_error(f"{action_prefix}: Issue #{action.issue_number} not found")
                elif issue_data.state == "closed":
                    result.add_warning(f"{action_prefix}: Issue #{action.issue_number} is closed")
        
        if hasattr(action, 'pr_number'):
            if self.gh_service:
                pr_data = self.gh_service.get_pr(action.pr_number)
                if not pr_data:
                    result.add_error(f"{action_prefix}: PR #{action.pr_number} not found")
        
        # Validate labels
        if hasattr(action, 'labels') and action.labels:
            for label in action.labels:
                if not label or len(label) > 50:
                    result.add_error(f"{action_prefix}: Invalid label '{label}'")
        
        # Validate assignees
        if hasattr(action, 'assignees') and action.assignees:
            for assignee in action.assignees:
                if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,38}[a-zA-Z0-9])?$', assignee):
                    result.add_error(f"{action_prefix}: Invalid GitHub username '{assignee}'")
    
    def _validate_action_consistency(self, plan: Plan, result: ValidationResult):
        """Validate consistency across actions."""
        # Check for duplicate issue/PR operations
        issue_numbers = set()
        pr_numbers = set()
        
        for action in plan.actions:
            if hasattr(action, 'issue_number'):
                issue_numbers.add(action.issue_number)
            if hasattr(action, 'pr_number'):
                pr_numbers.add(action.pr_number)
        
        # Ensure consistency with context
        if plan.context.issue_number and issue_numbers:
            if plan.context.issue_number not in issue_numbers:
                result.add_warning("Context issue number doesn't match any action issue numbers")
        
        if plan.context.pr_number and pr_numbers:
            if plan.context.pr_number not in pr_numbers:
                result.add_warning("Context PR number doesn't match any action PR numbers")
        
        # Check for branch consistency
        branches = set()
        for action in plan.actions:
            if hasattr(action, 'head_branch'):
                branches.add(action.head_branch)
        
        if plan.context.branch and branches:
            if plan.context.branch not in branches:
                result.add_warning("Context branch doesn't match any action branches")
        
        # Warn about multiple different branches in PR actions
        if len(branches) > 1:
            result.add_warning(f"Multiple different branches in PR actions: {sorted(branches)}")
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get schema information."""
        if not self.schema:
            return {"error": "Schema not loaded"}
        
        return {
            "schema_version": self.schema.get("$id"),
            "title": self.schema.get("title"),
            "description": self.schema.get("description"),
            "supported_actions": [
                "create_issue", "create_pr", "comment_issue", "comment_pr"
            ],
            "supported_dedupe_methods": [
                "dedupe_marker", "by_title_hash", "by_content_signature", "none"
            ]
        }