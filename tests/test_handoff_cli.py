"""Tests for handoff CLI handlers."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.claude_tasker.handoff.cli_handlers import HandoffCLI, create_default_handoff_dir
from src.claude_tasker.handoff.models import (
    Plan, Context, ContextType, DedupeStrategy, DedupeMethod, CommentIssueAction
)


class TestHandoffCLI:
    """Test HandoffCLI class."""
    
    @pytest.fixture
    def handoff_cli(self):
        """Create HandoffCLI instance with mocked services."""
        with patch('src.claude_tasker.handoff.cli_handlers.CommandExecutor'), \
             patch('src.claude_tasker.handoff.cli_handlers.GitService'), \
             patch('src.claude_tasker.handoff.cli_handlers.GhService'):
            cli = HandoffCLI()
            # Mock services
            cli.git_service = Mock()
            cli.gh_service = Mock()
            cli.planner = Mock()
            cli.validator = Mock()
            return cli
    
    @pytest.fixture
    def sample_plan(self):
        """Create sample plan for testing."""
        context = Context(type=ContextType.ISSUE, issue_number=123)
        action = CommentIssueAction(
            issue_number=123,
            comment="Test comment",
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.BY_CONTENT_SIGNATURE)
        )
        return Plan(context=context, actions=[action], op_id="test_op_123")
    
    def test_handle_plan_command_issue_success(self, handoff_cli, sample_plan):
        """Test successful plan command for issue."""
        # Mock services
        handoff_cli.git_service.get_current_branch.return_value = "feature-branch"
        handoff_cli.planner.create_issue_processing_plan.return_value = sample_plan
        
        # Mock validation
        from src.claude_tasker.handoff.validator import ValidationResult
        validation_result = ValidationResult(valid=True)
        handoff_cli.validator.validate_plan_object.return_value = validation_result
        
        # Create temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('pathlib.Path.cwd', return_value=Path(temp_dir)):
                result = handoff_cli.handle_plan_command(issue_number=123)
        
        assert result == 0
        handoff_cli.planner.create_issue_processing_plan.assert_called_once_with(
            issue_number=123,
            branch_name="feature-branch"
        )
        handoff_cli.validator.validate_plan_object.assert_called_once()
    
    def test_handle_plan_command_pr_success(self, handoff_cli, sample_plan):
        """Test successful plan command for PR."""
        # Update sample plan for PR context
        sample_plan.context.type = ContextType.PR
        sample_plan.context.pr_number = 456
        
        handoff_cli.planner.create_pr_review_plan.return_value = sample_plan
        
        # Mock validation
        from src.claude_tasker.handoff.validator import ValidationResult
        validation_result = ValidationResult(valid=True)
        handoff_cli.validator.validate_plan_object.return_value = validation_result
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('pathlib.Path.cwd', return_value=Path(temp_dir)):
                result = handoff_cli.handle_plan_command(pr_number=456)
        
        assert result == 0
        handoff_cli.planner.create_pr_review_plan.assert_called_once_with(pr_number=456)
    
    def test_handle_plan_command_bug_success(self, handoff_cli, sample_plan):
        """Test successful plan command for bug analysis."""
        sample_plan.context.type = ContextType.BUG_ANALYSIS
        handoff_cli.planner.create_bug_analysis_plan.return_value = sample_plan
        
        from src.claude_tasker.handoff.validator import ValidationResult
        validation_result = ValidationResult(valid=True)
        handoff_cli.validator.validate_plan_object.return_value = validation_result
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('pathlib.Path.cwd', return_value=Path(temp_dir)):
                result = handoff_cli.handle_plan_command(bug_description="Test bug")
        
        assert result == 0
        handoff_cli.planner.create_bug_analysis_plan.assert_called_once_with(
            bug_description="Test bug",
            create_issue=True
        )
    
    def test_handle_plan_command_feature_success(self, handoff_cli, sample_plan):
        """Test successful plan command for feature request."""
        sample_plan.context.type = ContextType.BUG_ANALYSIS  # Planner treats features as bug analysis
        handoff_cli.planner.create_bug_analysis_plan.return_value = sample_plan
        
        from src.claude_tasker.handoff.validator import ValidationResult
        validation_result = ValidationResult(valid=True)
        handoff_cli.validator.validate_plan_object.return_value = validation_result
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('pathlib.Path.cwd', return_value=Path(temp_dir)):
                result = handoff_cli.handle_plan_command(feature_description="New feature")
        
        assert result == 0
        handoff_cli.planner.create_bug_analysis_plan.assert_called_once_with(
            bug_description="Feature request: New feature",
            create_issue=True
        )
    
    def test_handle_plan_command_plan_generation_failure(self, handoff_cli):
        """Test plan command when plan generation fails."""
        handoff_cli.planner.create_issue_processing_plan.return_value = None
        
        result = handoff_cli.handle_plan_command(issue_number=123)
        
        assert result == 1
    
    def test_handle_plan_command_validation_warnings(self, handoff_cli, sample_plan):
        """Test plan command with validation warnings."""
        handoff_cli.planner.create_issue_processing_plan.return_value = sample_plan
        
        from src.claude_tasker.handoff.validator import ValidationResult
        validation_result = ValidationResult(valid=True)
        validation_result.add_warning("Test warning")
        handoff_cli.validator.validate_plan_object.return_value = validation_result
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('pathlib.Path.cwd', return_value=Path(temp_dir)):
                result = handoff_cli.handle_plan_command(issue_number=123)
        
        assert result == 0  # Should still succeed with warnings
    
    def test_handle_plan_command_custom_output_file(self, handoff_cli, sample_plan):
        """Test plan command with custom output file."""
        handoff_cli.planner.create_issue_processing_plan.return_value = sample_plan
        
        from src.claude_tasker.handoff.validator import ValidationResult
        validation_result = ValidationResult(valid=True)
        handoff_cli.validator.validate_plan_object.return_value = validation_result
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "custom_plan.json"
            result = handoff_cli.handle_plan_command(
                issue_number=123,
                output_file=str(output_file)
            )
            
            assert result == 0
            assert output_file.exists()
            
            # Verify plan was written correctly
            with open(output_file) as f:
                saved_plan = json.load(f)
            assert saved_plan["op_id"] == "test_op_123"
    
    def test_handle_plan_command_exception(self, handoff_cli):
        """Test plan command with exception."""
        handoff_cli.planner.create_issue_processing_plan.side_effect = Exception("Test error")
        
        result = handoff_cli.handle_plan_command(issue_number=123)
        
        assert result == 1
    
    def test_handle_validate_command_success(self, handoff_cli, sample_plan):
        """Test successful validate command."""
        from src.claude_tasker.handoff.validator import ValidationResult
        validation_result = ValidationResult(valid=True)
        handoff_cli.validator.validate_plan_file.return_value = validation_result
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(sample_plan.to_json())
            f.flush()
            
            result = handoff_cli.handle_validate_command(f.name)
            
            assert result == 0
            handoff_cli.validator.validate_plan_file.assert_called_once()
            
            # Clean up
            Path(f.name).unlink()
    
    def test_handle_validate_command_file_not_found(self, handoff_cli):
        """Test validate command with non-existent file."""
        from src.claude_tasker.handoff.validator import ValidationResult
        validation_result = ValidationResult(valid=False)
        validation_result.add_error("Plan file not found")
        handoff_cli.validator.validate_plan_file.return_value = validation_result
        
        result = handoff_cli.handle_validate_command("non-existent.json")
        
        assert result == 1
    
    def test_handle_validate_command_validation_failure(self, handoff_cli):
        """Test validate command with validation failure."""
        from src.claude_tasker.handoff.validator import ValidationResult
        validation_result = ValidationResult(valid=False)
        validation_result.add_error("Validation failed")
        handoff_cli.validator.validate_plan_file.return_value = validation_result
        
        # Create a temporary invalid plan file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": "plan"}')
            f.flush()
            
            result = handoff_cli.handle_validate_command(f.name)
            
            assert result == 1
            
            # Clean up
            Path(f.name).unlink()
    
    def test_handle_validate_command_exception(self, handoff_cli):
        """Test validate command with exception."""
        handoff_cli.validator.validate_plan_file.side_effect = Exception("Test error")
        
        result = handoff_cli.handle_validate_command("test.json")
        
        assert result == 1
    
    def test_list_plans_empty_directory(self, handoff_cli):
        """Test listing plans in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plans = handoff_cli.list_plans(Path(temp_dir))
            assert len(plans) == 0
    
    def test_list_plans_with_files(self, handoff_cli, sample_plan):
        """Test listing plans with existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            handoff_dir = Path(temp_dir) / "handoff"
            handoff_dir.mkdir()
            
            # Create some plan files
            plan1 = handoff_dir / "plan1.json"
            plan2 = handoff_dir / "plan2.json"
            non_plan = handoff_dir / "readme.txt"
            
            plan1.write_text(sample_plan.to_json())
            plan2.write_text(sample_plan.to_json())
            non_plan.write_text("Not a plan")
            
            plans = handoff_cli.list_plans(handoff_dir)
            
            assert len(plans) == 2
            plan_names = [p.name for p in plans]
            assert "plan1.json" in plan_names
            assert "plan2.json" in plan_names
            assert "readme.txt" not in plan_names
    
    def test_list_plans_nonexistent_directory(self, handoff_cli):
        """Test listing plans in non-existent directory."""
        plans = handoff_cli.list_plans(Path("/non/existent/path"))
        assert len(plans) == 0
    
    def test_get_schema_info(self, handoff_cli):
        """Test getting schema information."""
        mock_info = {
            "supported_actions": ["create_issue", "create_pr"],
            "supported_dedupe_methods": ["by_title_hash", "none"]
        }
        handoff_cli.validator.get_schema_info.return_value = mock_info
        
        info = handoff_cli.get_schema_info()
        
        assert info == mock_info
        handoff_cli.validator.get_schema_info.assert_called_once()


class TestCreateDefaultHandoffDir:
    """Test create_default_handoff_dir function."""
    
    def test_create_default_handoff_dir_success(self):
        """Test successful creation of default handoff directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            import os
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                create_default_handoff_dir()
                
                handoff_dir = Path(temp_dir) / ".claude-tasker" / "handoff"
                readme_file = handoff_dir / "README.md"
                
                assert handoff_dir.exists()
                assert handoff_dir.is_dir()
                assert readme_file.exists()
                
                # Verify README content
                readme_content = readme_file.read_text()
                assert "Claude Tasker Handoff Plans" in readme_content
                assert "## Plan Files" in readme_content
                assert "## Validation" in readme_content
            finally:
                os.chdir(old_cwd)
    
    def test_create_default_handoff_dir_already_exists(self):
        """Test creation when directory already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            handoff_dir = Path(temp_dir) / ".claude-tasker" / "handoff"
            readme_file = handoff_dir / "README.md"
            
            # Create directory and README manually
            handoff_dir.mkdir(parents=True)
            readme_file.write_text("Existing README")
            
            with patch('pathlib.Path.cwd', return_value=Path(temp_dir)):
                create_default_handoff_dir()
                
                # Should not overwrite existing README
                assert readme_file.read_text() == "Existing README"


class TestHandoffCLIIntegration:
    """Integration tests for HandoffCLI."""
    
    def test_full_plan_workflow(self):
        """Test complete plan generation workflow."""
        # This test uses real components (no mocking) to test integration
        from src.claude_tasker.handoff.cli_handlers import HandoffCLI
        
        cli = HandoffCLI()
        
        # Test bug analysis plan (doesn't require external services)
        with tempfile.TemporaryDirectory() as temp_dir:
            import os
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                result = cli.handle_plan_command(
                    bug_description="Test integration bug"
                )
            finally:
                os.chdir(old_cwd)
            
            # Should succeed
            assert result == 0
            
            # Should create handoff directory and plan file
            handoff_dir = Path(temp_dir) / ".claude-tasker" / "handoff"
            assert handoff_dir.exists()
            
            plan_files = list(handoff_dir.glob("*.json"))
            assert len(plan_files) == 1
            
            # Verify plan content
            with open(plan_files[0]) as f:
                plan_data = json.load(f)
            
            assert plan_data["version"] == "1.0"
            assert plan_data["context"]["type"] == "bug_analysis"
            assert len(plan_data["actions"]) == 1
            assert plan_data["actions"][0]["type"] == "create_issue"
    
    def test_full_validation_workflow(self):
        """Test complete validation workflow."""
        from src.claude_tasker.handoff.cli_handlers import HandoffCLI
        from src.claude_tasker.handoff.models import Plan, Context, ContextType, CommentIssueAction, DedupeStrategy, DedupeMethod
        
        # Create a valid plan
        context = Context(type=ContextType.MANUAL)
        action = CommentIssueAction(
            issue_number=123,
            comment="Test comment",
            dedupe_strategy=DedupeStrategy(method=DedupeMethod.NONE)
        )
        plan = Plan(context=context, actions=[action])
        
        cli = HandoffCLI()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(plan.to_json())
            f.flush()
            
            result = cli.handle_validate_command(f.name)
            
            # Should succeed
            assert result == 0
            
            # Clean up
            Path(f.name).unlink()