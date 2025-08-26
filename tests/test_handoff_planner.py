"""Tests for handoff planner."""

from unittest.mock import Mock, patch
from datetime import datetime

import pytest

from src.claude_tasker.handoff.planner import Planner
from src.claude_tasker.handoff.models import (
    ContextType, DedupeMethod, CreateIssueAction, CreatePRAction,
    CommentIssueAction, CommentPRAction
)
from src.claude_tasker.services.gh_service import GhService, IssueData, PRData


class TestPlanner:
    """Test Planner class."""
    
    @pytest.fixture
    def mock_gh_service(self):
        """Create mock GitHub service."""
        return Mock(spec=GhService)
    
    @pytest.fixture
    def planner(self, mock_gh_service):
        """Create planner with mock service."""
        return Planner(gh_service=mock_gh_service)
    
    @pytest.fixture
    def sample_issue_data(self):
        """Create sample issue data."""
        return IssueData(
            number=123,
            title="Test Issue",
            body="This is a test issue that needs to be fixed",
            labels=["bug", "priority-high"],
            url="https://github.com/owner/repo/issues/123",
            author="testuser",
            state="open"
        )
    
    @pytest.fixture
    def sample_pr_data(self):
        """Create sample PR data."""
        return PRData(
            number=456,
            title="Fix test issue",
            body="This PR fixes the test issue",
            head_ref="feature-branch",
            base_ref="main",
            author="developer",
            additions=50,
            deletions=10,
            changed_files=3,
            url="https://github.com/owner/repo/pull/456"
        )
    
    def test_create_issue_processing_plan_success(self, planner, mock_gh_service, sample_issue_data):
        """Test successful issue processing plan creation."""
        mock_gh_service.get_issue.return_value = sample_issue_data
        
        plan = planner.create_issue_processing_plan(
            issue_number=123,
            branch_name="feature-branch"
        )
        
        assert plan is not None
        assert plan.context.type == ContextType.ISSUE
        assert plan.context.issue_number == 123
        assert plan.context.branch == "feature-branch"
        assert "Processing issue #123" in plan.context.description
        
        # Should have 3 actions: start comment, create PR, completion comment
        assert len(plan.actions) == 3
        
        # Check action types
        action_types = [action.type.value for action in plan.actions]
        assert "comment_issue" in action_types
        assert "create_pr" in action_types
        
        # Verify start comment
        start_comment = next(a for a in plan.actions if a.type.value == "comment_issue" and "Processing Started" in a.comment)
        assert start_comment.issue_number == 123
        assert start_comment.dedupe_strategy.method == DedupeMethod.BY_CONTENT_SIGNATURE
        
        # Verify PR creation
        pr_action = next(a for a in plan.actions if a.type.value == "create_pr")
        assert "Fix issue #123" in pr_action.title
        assert pr_action.head_branch == "feature-branch"
        assert pr_action.base_branch == "main"
        assert pr_action.dedupe_strategy.method == DedupeMethod.BY_TITLE_HASH
        
        # Verify completion comment
        completion_comment = next(a for a in plan.actions if a.type.value == "comment_issue" and "Processing Complete" in a.comment)
        assert completion_comment.issue_number == 123
    
    def test_create_issue_processing_plan_no_branch(self, planner, mock_gh_service, sample_issue_data):
        """Test issue processing plan without branch (no PR creation)."""
        mock_gh_service.get_issue.return_value = sample_issue_data
        
        plan = planner.create_issue_processing_plan(issue_number=123)
        
        assert plan is not None
        assert len(plan.actions) == 2  # Only start and completion comments
        
        action_types = [action.type.value for action in plan.actions]
        assert "comment_issue" in action_types
        assert "create_pr" not in action_types
    
    def test_create_issue_processing_plan_with_provided_data(self, planner, sample_issue_data):
        """Test issue processing plan with pre-provided issue data."""
        plan = planner.create_issue_processing_plan(
            issue_number=123,
            issue_data=sample_issue_data,
            branch_name="feature-branch"
        )
        
        assert plan is not None
        assert plan.context.issue_number == 123
        # Should not call gh_service since data was provided
        assert not hasattr(planner.gh_service, 'get_issue') or not planner.gh_service.get_issue.called
    
    def test_create_issue_processing_plan_missing_issue(self, planner, mock_gh_service):
        """Test issue processing plan when issue doesn't exist."""
        mock_gh_service.get_issue.return_value = None
        
        plan = planner.create_issue_processing_plan(issue_number=999)
        
        assert plan is None
        mock_gh_service.get_issue.assert_called_with(999)
    
    def test_create_pr_review_plan_success(self, planner, mock_gh_service, sample_pr_data):
        """Test successful PR review plan creation."""
        mock_gh_service.get_pr.return_value = sample_pr_data
        
        plan = planner.create_pr_review_plan(pr_number=456)
        
        assert plan is not None
        assert plan.context.type == ContextType.PR
        assert plan.context.pr_number == 456
        assert plan.context.branch == "feature-branch"
        assert "Reviewing PR #456" in plan.context.description
        
        # Should have 1 action: review comment
        assert len(plan.actions) == 1
        
        review_action = plan.actions[0]
        assert review_action.type.value == "comment_pr"
        assert review_action.pr_number == 456
        assert "Automated PR Review" in review_action.comment
        assert review_action.dedupe_strategy.method == DedupeMethod.BY_CONTENT_SIGNATURE
    
    def test_create_pr_review_plan_with_provided_data(self, planner, sample_pr_data):
        """Test PR review plan with pre-provided PR data."""
        plan = planner.create_pr_review_plan(pr_number=456, pr_data=sample_pr_data)
        
        assert plan is not None
        assert plan.context.pr_number == 456
    
    def test_create_pr_review_plan_missing_pr(self, planner, mock_gh_service):
        """Test PR review plan when PR doesn't exist."""
        mock_gh_service.get_pr.return_value = None
        
        plan = planner.create_pr_review_plan(pr_number=999)
        
        assert plan is None
        mock_gh_service.get_pr.assert_called_with(999)
    
    def test_create_bug_analysis_plan_with_issue(self, planner):
        """Test bug analysis plan with issue creation."""
        bug_description = "The application crashes when clicking the save button"
        
        plan = planner.create_bug_analysis_plan(
            bug_description=bug_description,
            create_issue=True
        )
        
        assert plan is not None
        assert plan.context.type == ContextType.BUG_ANALYSIS
        assert bug_description[:100] in plan.context.description
        
        # Should have 1 action: create issue
        assert len(plan.actions) == 1
        
        issue_action = plan.actions[0]
        assert issue_action.type.value == "create_issue"
        assert "Bug:" in issue_action.title
        assert bug_description in issue_action.body
        assert "bug" in issue_action.labels
        assert "needs-investigation" in issue_action.labels
        assert issue_action.dedupe_strategy.method == DedupeMethod.BY_TITLE_HASH
    
    def test_create_bug_analysis_plan_no_issue(self, planner):
        """Test bug analysis plan without issue creation."""
        plan = planner.create_bug_analysis_plan(
            bug_description="Test bug",
            create_issue=False
        )
        
        assert plan is not None
        assert plan.context.type == ContextType.BUG_ANALYSIS
        assert len(plan.actions) == 0
    
    def test_create_manual_plan_success(self, planner):
        """Test manual plan creation with valid actions."""
        actions = [
            {
                "type": "create_issue",
                "title": "Manual Issue",
                "body": "This is a manual issue",
                "labels": ["manual"],
                "dedupe_method": "by_title_hash"
            },
            {
                "type": "comment_pr",
                "pr_number": 123,
                "comment": "Manual comment",
                "dedupe_method": "by_content_signature"
            }
        ]
        
        plan = planner.create_manual_plan(
            actions=actions,
            description="Manual plan test"
        )
        
        assert plan is not None
        assert plan.context.type == ContextType.MANUAL
        assert plan.context.description == "Manual plan test"
        assert len(plan.actions) == 2
        
        # Verify actions
        issue_action = plan.actions[0]
        assert issue_action.type.value == "create_issue"
        assert issue_action.title == "Manual Issue"
        
        comment_action = plan.actions[1]
        assert comment_action.type.value == "comment_pr"
        assert comment_action.pr_number == 123
    
    def test_create_manual_plan_invalid_actions(self, planner):
        """Test manual plan creation with invalid actions."""
        invalid_actions = [
            {
                "type": "invalid_type",
                "title": "Test"
            },
            {
                "type": "create_issue",
                # Missing required fields
            }
        ]
        
        plan = planner.create_manual_plan(actions=invalid_actions)
        
        assert plan is not None
        # Should create default no-op plan
        assert len(plan.actions) == 1
        assert "No valid actions specified" in plan.actions[0].comment
    
    def test_create_manual_plan_empty_actions(self, planner):
        """Test manual plan creation with empty actions."""
        plan = planner.create_manual_plan(actions=[])
        
        assert plan is not None
        # Should create default no-op plan
        assert len(plan.actions) == 1
        assert plan.actions[0].type.value == "comment_issue"
        assert "No valid actions specified" in plan.actions[0].comment
    
    def test_parse_action_dict_create_issue(self, planner):
        """Test parsing create_issue action dictionary."""
        action_dict = {
            "type": "create_issue",
            "title": "Test Issue",
            "body": "Test body",
            "labels": ["test", "bug"],
            "assignees": ["user1"],
            "dedupe_method": "by_title_hash"
        }
        
        action = planner._parse_action_dict(action_dict)
        
        assert action is not None
        assert action.type.value == "create_issue"
        assert action.title == "Test Issue"
        assert action.body == "Test body"
        assert action.labels == ["test", "bug"]
        assert action.assignees == ["user1"]
        assert action.dedupe_strategy.method == DedupeMethod.BY_TITLE_HASH
    
    def test_parse_action_dict_create_pr(self, planner):
        """Test parsing create_pr action dictionary."""
        action_dict = {
            "type": "create_pr",
            "title": "Test PR",
            "body": "Test PR body",
            "head_branch": "feature-branch",
            "base_branch": "develop",
            "draft": True,
            "dedupe_method": "by_content_signature"
        }
        
        action = planner._parse_action_dict(action_dict)
        
        assert action is not None
        assert action.type.value == "create_pr"
        assert action.title == "Test PR"
        assert action.head_branch == "feature-branch"
        assert action.base_branch == "develop"
        assert action.draft is True
        assert action.dedupe_strategy.method == DedupeMethod.BY_CONTENT_SIGNATURE
    
    def test_parse_action_dict_comment_actions(self, planner):
        """Test parsing comment action dictionaries."""
        issue_comment_dict = {
            "type": "comment_issue",
            "issue_number": 123,
            "comment": "Test comment",
            "dedupe_method": "none"
        }
        
        pr_comment_dict = {
            "type": "comment_pr",
            "pr_number": 456,
            "comment": "PR comment",
            "dedupe_method": "none"
        }
        
        issue_action = planner._parse_action_dict(issue_comment_dict)
        pr_action = planner._parse_action_dict(pr_comment_dict)
        
        assert issue_action.type.value == "comment_issue"
        assert issue_action.issue_number == 123
        assert issue_action.comment == "Test comment"
        
        assert pr_action.type.value == "comment_pr"
        assert pr_action.pr_number == 456
        assert pr_action.comment == "PR comment"
    
    def test_parse_action_dict_invalid(self, planner):
        """Test parsing invalid action dictionary."""
        invalid_dict = {
            "type": "invalid_type"
        }
        
        action = planner._parse_action_dict(invalid_dict)
        assert action is None
        
        # Missing required fields
        invalid_dict2 = {
            "type": "create_issue"
            # Missing title and body
        }
        
        action2 = planner._parse_action_dict(invalid_dict2)
        assert action2 is None
    
    @patch('src.claude_tasker.handoff.planner.datetime')
    def test_generated_content_includes_timestamps(self, mock_datetime, planner, sample_issue_data):
        """Test that generated content includes timestamps."""
        # Mock datetime to return fixed time
        fixed_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_time
        
        # Test processing start comment
        comment = planner._generate_processing_start_comment(sample_issue_data)
        assert "2024-01-01T12:00:00Z" in comment
        assert "Processing Started" in comment
        
        # Test completion comment
        completion = planner._generate_completion_comment(sample_issue_data)
        assert "2024-01-01T12:00:00Z" in completion
        assert "Processing Complete" in completion
    
    def test_pr_content_generation(self, planner, sample_issue_data):
        """Test PR title and body generation from issue data."""
        title, body = planner._generate_pr_content(sample_issue_data, "feature-fix-123")
        
        assert f"Fix #{sample_issue_data.number}" in title
        assert sample_issue_data.title in title
        assert f"#{sample_issue_data.number}" in body
        assert "feature-fix-123" in body
        assert "## Summary" in body
        assert "## Test plan" in body
    
    def test_pr_review_comment_generation(self, planner, sample_pr_data):
        """Test PR review comment generation."""
        comment = planner._generate_pr_review_comment(sample_pr_data)
        
        assert "Automated PR Review" in comment
        assert f"#{sample_pr_data.number}" in comment
        assert sample_pr_data.title in comment
        assert sample_pr_data.head_ref in comment
        assert sample_pr_data.base_ref in comment
        assert f"+{sample_pr_data.additions}" in comment
        assert f"-{sample_pr_data.deletions}" in comment
        assert f"{sample_pr_data.changed_files} files" in comment
    
    def test_bug_issue_title_generation(self, planner):
        """Test bug issue title generation."""
        # Short description
        short_desc = "App crashes on save"
        title = planner._generate_bug_issue_title(short_desc)
        assert title == f"Bug: {short_desc}"
        
        # Long description (should be truncated)
        long_desc = "A" * 60
        title = planner._generate_bug_issue_title(long_desc)
        assert len(title) <= 53  # "Bug: " + 47 chars + "..."
        assert title.endswith("...")
        
        # Multi-line description (should use first line only)
        multiline_desc = "First line\nSecond line"
        title = planner._generate_bug_issue_title(multiline_desc)
        assert title == "Bug: First line"
        assert "Second line" not in title
    
    def test_bug_issue_body_generation(self, planner):
        """Test bug issue body generation."""
        bug_desc = "Application throws NullPointerException when user clicks submit"
        body = planner._generate_bug_issue_body(bug_desc)
        
        assert "## Bug Report" in body
        assert bug_desc in body
        assert "## Environment" in body
        assert "## Next Steps" in body
        assert "Claude Tasker (automated)" in body
        assert "bug, needs-investigation" in body