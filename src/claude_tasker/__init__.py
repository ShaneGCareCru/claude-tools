"""Claude Tasker - Enhanced task runner for Claude Code with GitHub integration."""

__version__ = "1.0.0"
__author__ = "Claude Tasker Team"

from .cli import main
from .environment_validator import EnvironmentValidator
from .github_client import GitHubClient
from .workspace_manager import WorkspaceManager
from .prompt_builder import PromptBuilder
from .pr_body_generator import PRBodyGenerator
from .workflow_logic import WorkflowLogic

__all__ = [
    "main",
    "EnvironmentValidator", 
    "GitHubClient",
    "WorkspaceManager",
    "PromptBuilder", 
    "PRBodyGenerator",
    "WorkflowLogic"
]