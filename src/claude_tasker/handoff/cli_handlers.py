"""CLI handlers for handoff planning and validation commands."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from .planner import Planner
from .validator import Validator
from .models import Plan, Context, ContextType
from ..services.command_executor import CommandExecutor
from ..services.git_service import GitService
from ..services.gh_service import GhService


logger = logging.getLogger(__name__)


class HandoffCLI:
    """CLI handlers for handoff operations."""
    
    def __init__(self, 
                 command_executor: Optional[CommandExecutor] = None,
                 git_service: Optional[GitService] = None,
                 gh_service: Optional[GhService] = None):
        """
        Initialize handoff CLI handlers with dependency injection support.
        
        Args:
            command_executor: Command executor service (created if None)
            git_service: Git service (created if None)
            gh_service: GitHub service (created if None)
        """
        # Initialize services with DI support
        self.command_executor = command_executor or CommandExecutor()
        self.git_service = git_service or GitService(self.command_executor)
        self.gh_service = gh_service or GhService(self.command_executor)
        
        # Initialize handoff components
        self.planner = Planner(self.gh_service)
        self.validator = Validator(self.git_service, self.gh_service)
    
    def handle_plan_command(self, 
                          issue_number: Optional[int] = None,
                          pr_number: Optional[int] = None,
                          bug_description: Optional[str] = None,
                          feature_description: Optional[str] = None,
                          output_file: Optional[str] = None) -> int:
        """
        Handle plan generation command.
        
        Args:
            issue_number: Issue number for plan
            pr_number: PR number for plan
            bug_description: Bug description for analysis plan
            feature_description: Feature description for analysis plan
            output_file: Optional output file path
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            plan = None
            
            if issue_number:
                # Get current branch for PR creation
                current_branch = self.git_service.get_current_branch()
                plan = self.planner.create_issue_processing_plan(
                    issue_number=issue_number,
                    branch_name=current_branch
                )
                
            elif pr_number:
                plan = self.planner.create_pr_review_plan(pr_number=pr_number)
                
            elif bug_description:
                plan = self.planner.create_bug_analysis_plan(
                    bug_description=bug_description,
                    create_issue=True
                )
                
            elif feature_description:
                plan = self.planner.create_bug_analysis_plan(
                    bug_description=f"Feature request: {feature_description}",
                    create_issue=True
                )
            
            if not plan:
                logger.error("Failed to generate plan")
                print("Error: Failed to generate plan", file=sys.stderr)
                return 1
            
            # Validate the generated plan
            validation_result = self.validator.validate_plan_object(plan)
            if not validation_result.valid:
                logger.warning(f"Generated plan has validation issues: {validation_result.format_report()}")
                print(f"Warning: Generated plan has issues:\n{validation_result.format_report()}", file=sys.stderr)
            
            # Determine output path
            if output_file:
                output_path = Path(output_file)
            else:
                # Default output to .claude-tasker/handoff/<timestamp>.<op-id>.json
                handoff_dir = Path(".claude-tasker/handoff")
                handoff_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}.{plan.op_id}.json"
                output_path = handoff_dir / filename
            
            # Write plan to file with path validation
            try:
                # Resolve path to prevent traversal attacks
                resolved_path = output_path.resolve()
                working_dir = Path.cwd().resolve()
                
                # Ensure the resolved path is within the working directory
                if not str(resolved_path).startswith(str(working_dir)):
                    raise ValueError(f"Path traversal attempt blocked: {output_path}")
                
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
                with open(resolved_path, 'w', encoding='utf-8') as f:
                    f.write(plan.to_json())
                    
                # Update output_path for display
                output_path = resolved_path
                
            except OSError as e:
                logger.error(f"Failed to write plan file: {e}")
                print(f"Error: Failed to write plan file: {e}", file=sys.stderr)
                return 1
            
            print(f"✅ Plan generated: {output_path}")
            
            # Print plan summary
            print(f"\n📋 Plan Summary:")
            print(f"  Operation ID: {plan.op_id}")
            print(f"  Context: {plan.context.type.value}")
            print(f"  Actions: {len(plan.actions)}")
            
            if plan.context.issue_number:
                print(f"  Issue: #{plan.context.issue_number}")
            if plan.context.pr_number:
                print(f"  PR: #{plan.context.pr_number}")
            if plan.context.branch:
                print(f"  Branch: {plan.context.branch}")
            
            for i, action in enumerate(plan.actions, 1):
                print(f"  Action {i}: {action.type.value}")
            
            if validation_result.warnings:
                print(f"\n⚠️  Validation warnings: {len(validation_result.warnings)}")
            
            return 0
            
        except Exception as e:
            logger.error(f"Plan generation failed: {e}")
            print(f"Error: Plan generation failed: {e}", file=sys.stderr)
            return 1
    
    def handle_validate_command(self, plan_file: str) -> int:
        """
        Handle plan validation command.
        
        Args:
            plan_file: Path to plan file to validate
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            plan_path = Path(plan_file)
            
            if not plan_path.exists():
                print(f"Error: Plan file not found: {plan_path}", file=sys.stderr)
                return 1
            
            # Validate the plan
            validation_result = self.validator.validate_plan_file(plan_path)
            
            # Print validation report
            print(validation_result.format_report())
            
            if validation_result.valid:
                # Print additional plan information if valid
                try:
                    with open(plan_path, 'r', encoding='utf-8') as f:
                        plan_dict = json.load(f)
                    
                    plan = Plan.from_dict(plan_dict)
                    
                    print(f"\n📋 Plan Information:")
                    print(f"  Operation ID: {plan.op_id}")
                    print(f"  Created: {plan.timestamp.isoformat()}")
                    print(f"  Context: {plan.context.type.value}")
                    print(f"  Actions: {len(plan.actions)}")
                    
                    # Show action summary
                    action_summary = {}
                    for action in plan.actions:
                        # Handle both enum and string values
                        action_type = action.type.value if hasattr(action.type, 'value') else str(action.type)
                        action_summary[action_type] = action_summary.get(action_type, 0) + 1
                    
                    for action_type, count in action_summary.items():
                        print(f"    {action_type}: {count}")
                        
                except Exception as e:
                    logger.warning(f"Could not load additional plan info: {e}")
                
                return 0
            else:
                return 1
                
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            print(f"Error: Validation failed: {e}", file=sys.stderr)
            return 1
    
    def list_plans(self, handoff_dir: Optional[Path] = None) -> List[Path]:
        """
        List available plan files.
        
        Args:
            handoff_dir: Directory to search for plans
            
        Returns:
            List of plan file paths
        """
        if handoff_dir is None:
            handoff_dir = Path(".claude-tasker/handoff")
        
        if not handoff_dir.exists():
            return []
        
        return list(handoff_dir.glob("*.json"))
    
    def get_schema_info(self) -> dict:
        """Get schema information for help."""
        return self.validator.get_schema_info()


def create_default_handoff_dir():
    """Create default handoff directory structure."""
    handoff_dir = Path(".claude-tasker/handoff")
    handoff_dir.mkdir(parents=True, exist_ok=True)
    
    # Create README if it doesn't exist
    readme_path = handoff_dir / "README.md"
    if not readme_path.exists():
        readme_content = """# Claude Tasker Handoff Plans

This directory contains handoff plans generated by claude-tasker.

## Plan Files

Plans are stored as JSON files with the naming convention:
`YYYYMMDD_HHMMSS.<op-id>.json`

## Validation

You can validate plan files using:
```bash
claude-tasker --validate <plan-file>
```

## Schema

Plans follow the schema defined in `src/claude_tasker/handoff/schema.json`.

## Operations

Each plan includes:
- **Context**: Issue/PR/bug analysis context
- **Actions**: List of operations to perform
- **Deduplication**: Strategies to prevent duplicate operations
"""
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)