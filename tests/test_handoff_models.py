"""Tests for handoff models and schema validation."""

import json
import pytest
from datetime import datetime
from pydantic import ValidationError

from src.claude_tasker.handoff.models import (
    Plan, Context, ContextType, DedupeStrategy, DedupeMethod,
    CreateIssueAction, CreatePRAction, CommentIssueAction, CommentPRAction
)


class TestDedupeStrategy:
    """Test DedupeStrategy model."""
    
    def test_valid_dedupe_strategy(self):
        """Test valid dedupe strategy creation."""
        strategy = DedupeStrategy(method=DedupeMethod.BY_CONTENT_SIGNATURE)
        assert strategy.method == DedupeMethod.BY_CONTENT_SIGNATURE
        assert strategy.signature_lines == 3  # default
    
    def test_dedupe_marker_requires_marker(self):
        """Test that dedupe marker method requires marker field."""
        with pytest.raises(ValidationError, match="marker is required"):
            DedupeStrategy(method=DedupeMethod.DEDUPE_MARKER)
    
    def test_dedupe_marker_with_marker(self):
        """Test dedupe marker method with marker field."""
        strategy = DedupeStrategy(
            method=DedupeMethod.DEDUPE_MARKER,
            marker="test-marker"
        )
        assert strategy.method == DedupeMethod.DEDUPE_MARKER
        assert strategy.marker == "test-marker"
    
    def test_signature_lines_validation(self):
        """Test signature lines validation."""
        # Valid range
        strategy = DedupeStrategy(method=DedupeMethod.BY_CONTENT_SIGNATURE, signature_lines=5)
        assert strategy.signature_lines == 5
        
        # Invalid range - too low
        with pytest.raises(ValidationError):
            DedupeStrategy(method=DedupeMethod.BY_CONTENT_SIGNATURE, signature_lines=0)
        
        # Invalid range - too high
        with pytest.raises(ValidationError):
            DedupeStrategy(method=DedupeMethod.BY_CONTENT_SIGNATURE, signature_lines=11)


class TestContext:
    """Test Context model."""
    
    def test_issue_context(self):
        """Test issue context creation."""
        context = Context(
            type=ContextType.ISSUE,
            issue_number=123,
            description="Test issue context"
        )
        assert context.type == ContextType.ISSUE
        assert context.issue_number == 123
        assert context.description == "Test issue context"
    
    def test_pr_context(self):
        """Test PR context creation."""
        context = Context(
            type=ContextType.PR,
            pr_number=456,
            branch="feature-branch"
        )
        assert context.type == ContextType.PR
        assert context.pr_number == 456
        assert context.branch == "feature-branch"
    
    def test_issue_context_requires_issue_number(self):
        """Test that issue context requires issue number."""
        with pytest.raises(ValidationError, match="issue_number is required"):
            Context(type=ContextType.ISSUE)
    
    def test_pr_context_requires_pr_number(self):
        """Test that PR context requires PR number."""
        with pytest.raises(ValidationError, match="pr_number is required"):
            Context(type=ContextType.PR)
    
    def test_repository_format_validation(self):
        """Test repository format validation."""
        # Valid format
        context = Context(
            type=ContextType.MANUAL,
            repository="owner/repo"
        )
        assert context.repository == "owner/repo"
        
        # Invalid format
        with pytest.raises(ValidationError):
            Context(
                type=ContextType.MANUAL,
                repository="invalid-format"
            )


class TestActions:
    """Test action models."""
    
    def test_create_issue_action(self):
        """Test CreateIssueAction model."""
        action = CreateIssueAction(
            title="Test Issue",
            body="Test issue body",
            labels=["bug", "priority-high"],
            assignees=["testuser"],
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
        )
        assert action.type.value == "create_issue"
        assert action.title == "Test Issue"
        assert action.body == "Test issue body"
        assert action.labels == ["bug", "priority-high"]
        assert action.assignees == ["testuser"]
    
    def test_create_pr_action(self):
        """Test CreatePRAction model."""
        action = CreatePRAction(
            title="Test PR",
            body="Test PR body",
            head_branch="feature-branch",
            base_branch="main",
            draft=True,
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
        )
        assert action.type.value == "create_pr"
        assert action.title == "Test PR"
        assert action.head_branch == "feature-branch"
        assert action.base_branch == "main"
        assert action.draft is True
    
    def test_comment_issue_action(self):
        """Test CommentIssueAction model."""
        action = CommentIssueAction(
            issue_number=123,
            comment="Test comment",
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_CONTENT_SIGNATURE)
        )
        assert action.type.value == "comment_issue"
        assert action.issue_number == 123
        assert action.comment == "Test comment"
    
    def test_comment_pr_action(self):
        """Test CommentPRAction model."""
        action = CommentPRAction(
            pr_number=456,
            comment="Test PR comment",
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_CONTENT_SIGNATURE)
        )
        assert action.type.value == "comment_pr"
        assert action.pr_number == 456
        assert action.comment == "Test PR comment"
    
    def test_title_length_validation(self):
        """Test title length validation."""
        # Valid length
        action = CreateIssueAction(
            title="A" * 256,
            body="Test body",
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
        )
        assert len(action.title) == 256
        
        # Too long
        with pytest.raises(ValidationError):
            CreateIssueAction(
                title="A" * 257,
                body="Test body",
                dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
            )
        
        # Empty
        with pytest.raises(ValidationError):
            CreateIssueAction(
                title="",
                body="Test body",
                dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
            )
    
    def test_body_length_validation(self):
        """Test body length validation."""
        # Valid length
        action = CreateIssueAction(
            title="Test title",
            body="A" * 65536,
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
        )
        assert len(action.body) == 65536
        
        # Too long
        with pytest.raises(ValidationError):
            CreateIssueAction(
                title="Test title",
                body="A" * 65537,
                dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
            )
        
        # Empty
        with pytest.raises(ValidationError):
            CreateIssueAction(
                title="Test title",
                body="",
                dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
            )
    
    def test_label_validation(self):
        """Test label validation."""
        # Valid labels
        action = CreateIssueAction(
            title="Test",
            body="Test body",
            labels=["bug", "priority-high", "frontend"],
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
        )
        assert len(action.labels) == 3
        
        # Too many labels
        with pytest.raises(ValidationError):
            CreateIssueAction(
                title="Test",
                body="Test body",
                labels=["label"] * 21,  # max is 20
                dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
            )
        
        # Label too long
        with pytest.raises(ValidationError):
            CreateIssueAction(
                title="Test",
                body="Test body",
                labels=["A" * 51],  # max is 50
                dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
            )
    
    def test_assignee_validation(self):
        """Test assignee validation."""
        # Valid assignees
        action = CreateIssueAction(
            title="Test",
            body="Test body",
            assignees=["user1", "user-2", "user_3"],
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
        )
        assert len(action.assignees) == 3
        
        # Too many assignees
        with pytest.raises(ValidationError):
            CreateIssueAction(
                title="Test",
                body="Test body",
                assignees=["user"] * 11,  # max is 10
                dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
            )
        
        # Invalid username format
        with pytest.raises(ValidationError):
            CreateIssueAction(
                title="Test",
                body="Test body",
                assignees=["invalid-user-"],  # can't end with dash
                dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
            )


class TestPlan:
    """Test Plan model."""
    
    def test_basic_plan_creation(self):
        """Test basic plan creation."""
        context = Context(type=ContextType.ISSUE, issue_number=123)
        action = CommentIssueAction(
            issue_number=123,
            comment="Test comment",
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_CONTENT_SIGNATURE)
        )
        
        plan = Plan(context=context, actions=[action])
        
        assert plan.version == "1.0"
        assert isinstance(plan.timestamp, datetime)
        assert plan.op_id.startswith("op_")
        assert len(plan.op_id) == 19  # "op_" + 16 hex chars
        assert plan.context == context
        assert len(plan.actions) == 1
        assert plan.actions[0] == action
    
    def test_custom_op_id(self):
        """Test custom operation ID."""
        context = Context(type=ContextType.MANUAL)
        action = CommentIssueAction(
            issue_number=123,
            comment="Test",
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.NONE)
        )
        
        plan = Plan(
            context=context,
            actions=[action],
            op_id="custom_op_id_12345"
        )
        
        assert plan.op_id == "custom_op_id_12345"
    
    def test_op_id_validation(self):
        """Test operation ID validation."""
        context = Context(type=ContextType.MANUAL)
        action = CommentIssueAction(
            issue_number=123,
            comment="Test",
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.NONE)
        )
        
        # Too short
        with pytest.raises(ValidationError):
            Plan(context=context, actions=[action], op_id="short")
        
        # Too long
        with pytest.raises(ValidationError):
            Plan(context=context, actions=[action], op_id="a" * 65)
        
        # Invalid characters
        with pytest.raises(ValidationError):
            Plan(context=context, actions=[action], op_id="invalid@chars!")
    
    def test_empty_actions_validation(self):
        """Test that plans require at least one action."""
        context = Context(type=ContextType.MANUAL)
        
        with pytest.raises(ValidationError, match="at least 1 item"):
            Plan(context=context, actions=[])
    
    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        context = Context(type=ContextType.ISSUE, issue_number=123)
        action = CreateIssueAction(
            title="Test Issue",
            body="Test body",
            labels=["test"],
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
        )
        
        plan = Plan(context=context, actions=[action], op_id="test_op_12345")
        
        # Test to_json
        json_str = plan.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["version"] == "1.0"
        assert parsed["op_id"] == "test_op_12345"
        assert parsed["context"]["type"] == "issue"
        assert parsed["context"]["issue_number"] == 123
        assert len(parsed["actions"]) == 1
        assert parsed["actions"][0]["type"] == "create_issue"
        
        # Test from_json
        restored_plan = Plan.from_json(json_str)
        
        assert restored_plan.version == plan.version
        assert restored_plan.op_id == plan.op_id
        assert restored_plan.context.type == plan.context.type
        assert restored_plan.context.issue_number == plan.context.issue_number
        assert len(restored_plan.actions) == 1
        assert restored_plan.actions[0].type == plan.actions[0].type
    
    def test_dict_serialization(self):
        """Test dictionary serialization and deserialization."""
        context = Context(type=ContextType.PR, pr_number=456)
        action = CommentPRAction(
            pr_number=456,
            comment="Test comment",
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_CONTENT_SIGNATURE)
        )
        
        plan = Plan(context=context, actions=[action])
        
        # Test to_dict
        plan_dict = plan.to_dict()
        
        assert isinstance(plan_dict, dict)
        assert plan_dict["version"] == "1.0"
        assert plan_dict["context"]["type"] == "pr"
        assert plan_dict["context"]["pr_number"] == 456
        
        # Test from_dict
        restored_plan = Plan.from_dict(plan_dict)
        
        assert restored_plan.context.type == plan.context.type
        assert restored_plan.context.pr_number == plan.context.pr_number
        assert len(restored_plan.actions) == 1


class TestSchemaRoundTrip:
    """Test schema round-trip compatibility."""
    
    def test_comprehensive_plan_round_trip(self):
        """Test comprehensive plan with all action types."""
        context = Context(
            type=ContextType.ISSUE,
            issue_number=123,
            branch="feature-branch",
            repository="owner/repo",
            description="Test comprehensive plan"
        )
        
        actions = [
            CommentIssueAction(
                issue_number=123,
                comment="Starting work",
                dedupe_strategy=DedupeStrategy(
                    method=DedupeMethod.DEDUPE_MARKER,
                    marker="start-work"
                )
            ),
            CreatePRAction(
                title="Fix issue #123",
                body="This PR fixes the issue",
                head_branch="feature-branch",
                base_branch="main",
                draft=False,
                dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_TITLE_HASH)
            ),
            CommentPRAction(
                pr_number=789,
                comment="Please review",
                dedupe_strategy=DedupeStrategy(
                    method=DedupeMethod.BY_CONTENT_SIGNATURE,
                    signature_lines=2
                )
            ),
            CreateIssueAction(
                title="Follow-up issue",
                body="Additional work needed",
                labels=["enhancement", "follow-up"],
                assignees=["dev1", "dev2"],
                dedupe_strategy=DedupeStrategy(method=DedupeMethod.NONE)
            )
        ]
        
        original_plan = Plan(
            context=context,
            actions=actions,
            op_id="comprehensive_test"
        )
        
        # Convert to JSON and back
        json_str = original_plan.to_json()
        restored_plan = Plan.from_json(json_str)
        
        # Verify all data is preserved
        assert restored_plan.version == original_plan.version
        assert restored_plan.op_id == original_plan.op_id
        assert restored_plan.context.type == original_plan.context.type
        assert restored_plan.context.issue_number == original_plan.context.issue_number
        assert restored_plan.context.branch == original_plan.context.branch
        assert restored_plan.context.repository == original_plan.context.repository
        
        assert len(restored_plan.actions) == len(original_plan.actions)
        
        # Verify each action type is preserved
        action_types = [action.type.value if hasattr(action.type, 'value') else action.type for action in restored_plan.actions]
        assert "comment_issue" in action_types
        assert "create_pr" in action_types
        assert "comment_pr" in action_types
        assert "create_issue" in action_types
        
        # Verify specific action details
        comment_issue_action = next(a for a in restored_plan.actions if (a.type.value if hasattr(a.type, 'value') else a.type) == "comment_issue")
        assert comment_issue_action.dedupe_strategy.method == DedupeMethod.DEDUPE_MARKER
        assert comment_issue_action.dedupe_strategy.marker == "start-work"
        
        create_issue_action = next(a for a in restored_plan.actions if (a.type.value if hasattr(a.type, 'value') else a.type) == "create_issue")
        assert create_issue_action.labels == ["enhancement", "follow-up"]
        assert create_issue_action.assignees == ["dev1", "dev2"]