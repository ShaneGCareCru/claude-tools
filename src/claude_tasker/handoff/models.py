"""Pydantic models for handoff plan schema."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Union, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class DedupeMethod(str, Enum):
    """Deduplication methods."""
    DEDUPE_MARKER = "dedupe_marker"
    BY_TITLE_HASH = "by_title_hash"
    BY_CONTENT_SIGNATURE = "by_content_signature"
    NONE = "none"


class ContextType(str, Enum):
    """Context types for plan generation."""
    ISSUE = "issue"
    PR = "pr"
    BUG_ANALYSIS = "bug_analysis"
    MANUAL = "manual"


class ActionType(str, Enum):
    """Action types supported in plans."""
    CREATE_ISSUE = "create_issue"
    CREATE_PR = "create_pr"
    COMMENT_ISSUE = "comment_issue"
    COMMENT_PR = "comment_pr"


class DedupeStrategy(BaseModel):
    """Deduplication strategy configuration."""
    method: DedupeMethod
    marker: Optional[str] = None
    signature_lines: int = Field(default=3, ge=1, le=10)

    @model_validator(mode='after')
    def marker_required_for_dedupe_marker(self):
        if self.method == DedupeMethod.DEDUPE_MARKER and not self.marker:
            raise ValueError('marker is required when method is dedupe_marker')
        return self


class Context(BaseModel):
    """Context information for plan generation."""
    type: ContextType
    issue_number: Optional[int] = Field(None, ge=1)
    pr_number: Optional[int] = Field(None, ge=1)
    branch: Optional[str] = None
    repository: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$')
    description: Optional[str] = None

    @model_validator(mode='after')
    def validate_context_requirements(self):
        if self.type == ContextType.ISSUE and not self.issue_number:
            raise ValueError('issue_number is required when type is issue')
        if self.type == ContextType.PR and not self.pr_number:
            raise ValueError('pr_number is required when type is pr')
        
        return self


class Action(BaseModel):
    """Base action class."""
    type: ActionType
    dedupe_strategy: DedupeStrategy

    model_config = {"use_enum_values": True}


class CreateIssueAction(Action):
    """Action to create a GitHub issue."""
    type: Literal[ActionType.CREATE_ISSUE] = ActionType.CREATE_ISSUE
    title: str = Field(..., min_length=1, max_length=256)
    body: str = Field(..., min_length=1, max_length=65536)
    labels: Optional[List[str]] = Field(None, max_length=20)
    assignees: Optional[List[str]] = Field(None, max_length=10)

    @field_validator('labels')
    def validate_labels(cls, v):
        if v:
            for label in v:
                if not label or len(label) > 50:
                    raise ValueError('Label must be between 1 and 50 characters')
        return v

    @field_validator('assignees')
    def validate_assignees(cls, v):
        if v:
            import re
            for assignee in v:
                if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,38}[a-zA-Z0-9])?$', assignee):
                    raise ValueError(f'Invalid GitHub username format: {assignee}')
        return v


class CreatePRAction(Action):
    """Action to create a GitHub pull request."""
    type: Literal[ActionType.CREATE_PR] = ActionType.CREATE_PR
    title: str = Field(..., min_length=1, max_length=256)
    body: str = Field(..., min_length=1, max_length=65536)
    head_branch: str = Field(..., min_length=1, max_length=255)
    base_branch: str = Field(default="main")
    draft: bool = Field(default=False)


class CommentIssueAction(Action):
    """Action to comment on a GitHub issue."""
    type: Literal[ActionType.COMMENT_ISSUE] = ActionType.COMMENT_ISSUE
    issue_number: int = Field(..., ge=1)
    comment: str = Field(..., min_length=1, max_length=65536)


class CommentPRAction(Action):
    """Action to comment on a GitHub pull request."""
    type: Literal[ActionType.COMMENT_PR] = ActionType.COMMENT_PR
    pr_number: int = Field(..., ge=1)
    comment: str = Field(..., min_length=1, max_length=65536)


class Plan(BaseModel):
    """Complete handoff plan with actions and context."""
    version: Literal["1.0"] = "1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    op_id: str = Field(default_factory=lambda: f"op_{uuid.uuid4().hex[:16]}")
    context: Context
    actions: List[Union[CreateIssueAction, CreatePRAction, CommentIssueAction, CommentPRAction]] = Field(default_factory=list)

    @field_validator('op_id')
    def validate_op_id(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v) or len(v) < 8 or len(v) > 64:
            raise ValueError('op_id must be 8-64 characters, alphanumeric with _ and - allowed')
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(by_alias=True, mode='json')

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.model_dump(by_alias=True), indent=2, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> 'Plan':
        """Create Plan from JSON string."""
        return cls.model_validate_json(json_str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Plan':
        """Create Plan from dictionary."""
        return cls.model_validate(data)

    model_config = {
        "use_enum_values": True
    }