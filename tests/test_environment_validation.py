"""Tests for claude-tasker environment validation and dependency checking."""
import pytest
import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from unittest.mock import patch, Mock
from src.claude_tasker.environment_validator import EnvironmentValidator
from src.claude_tasker.workflow_logic import WorkflowLogic
from src.claude_tasker.services.git_service import GitService
from src.claude_tasker.services.command_executor import CommandExecutor


class TestEnvironmentValidator:
    """Test EnvironmentValidator class directly."""
    
    def test_init(self):
        """Test EnvironmentValidator initialization."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        assert 'git' in validator.required_tools
        assert 'gh' in validator.required_tools
        assert 'jq' in validator.required_tools
        assert 'claude' in validator.optional_tools
        assert 'llm' in validator.optional_tools
    
    def test_validate_git_repository_valid(self):
        """Test git repository validation when valid."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        
        # Mock the rev_parse method to return a successful result
        from src.claude_tasker.services.command_executor import CommandResult, CommandErrorType
        mock_result = CommandResult(
            returncode=0,
            stdout=".git",
            stderr="",
            command="git rev-parse --git-dir",
            execution_time=1.0,
            error_type=CommandErrorType.SUCCESS,
            attempts=1,
            success=True
        )
        mock_git_service.rev_parse.return_value = mock_result
        
        validator = EnvironmentValidator(mock_git_service)
        valid, message = validator.validate_git_repository()
        
        assert valid is True
        assert "Valid git repository" in message
        mock_git_service.rev_parse.assert_called_once_with('--git-dir', cwd='.')
    
    def test_validate_git_repository_invalid(self):
        """Test git repository validation when invalid."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        
        # Mock the rev_parse method to return a failed result
        from src.claude_tasker.services.command_executor import CommandResult, CommandErrorType
        mock_result = CommandResult(
            returncode=1,
            stdout="",
            stderr="not a git repository",
            command="git rev-parse --git-dir",
            execution_time=1.0,
            error_type=CommandErrorType.GENERAL_ERROR,
            attempts=1,
            success=False
        )
        mock_git_service.rev_parse.return_value = mock_result
        
        validator = EnvironmentValidator(mock_git_service)
        valid, message = validator.validate_git_repository()
        
        assert valid is False
        assert "Not a git repository" in message
    
    def test_validate_git_repository_git_not_found(self):
        """Test git repository validation when git command not found."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        
        # Mock the rev_parse method to raise an exception
        mock_git_service.rev_parse.side_effect = FileNotFoundError("git not found")
        
        validator = EnvironmentValidator(mock_git_service)
        valid, message = validator.validate_git_repository()
        
        assert valid is False
        assert "Git validation error: git not found" in message
    
    def test_validate_github_remote_valid(self):
        """Test GitHub remote validation when valid."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        
        # Mock the get_remote_url method to return a GitHub URL
        mock_git_service.get_remote_url.return_value = "https://github.com/user/repo.git"
        
        validator = EnvironmentValidator(mock_git_service)
        valid, message = validator.validate_github_remote()
        
        assert valid is True
        assert "GitHub remote:" in message
        assert "github.com/user/repo.git" in message
        mock_git_service.get_remote_url.assert_called_once_with('origin', cwd='.')
    
    def test_validate_github_remote_no_github(self):
        """Test GitHub remote validation when no GitHub remote."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        
        # Mock the get_remote_url method to return a non-GitHub URL
        mock_git_service.get_remote_url.return_value = "https://gitlab.com/user/repo.git"
        
        validator = EnvironmentValidator(mock_git_service)
        valid, message = validator.validate_github_remote()
        
        assert valid is False
        assert "No GitHub remote found" in message
    
    def test_validate_github_remote_no_remote(self):
        """Test GitHub remote validation when no remote at all."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        
        # Mock the get_remote_url method to return None (no remote)
        mock_git_service.get_remote_url.return_value = None
        
        validator = EnvironmentValidator(mock_git_service)
        valid, message = validator.validate_github_remote()
        
        assert valid is False
        assert "No GitHub remote found" in message
    
    def test_check_claude_md_exists(self, tmp_path):
        """Test CLAUDE.md check when file exists."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Test CLAUDE.md")
        
        valid, message = validator.check_claude_md(str(tmp_path))
        
        assert valid is True
        assert "CLAUDE.md found at" in message
        assert str(claude_md) in message
    
    def test_check_claude_md_missing(self, tmp_path):
        """Test CLAUDE.md check when file is missing."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        
        valid, message = validator.check_claude_md(str(tmp_path))
        
        assert valid is False
        assert "CLAUDE.md not found" in message
        assert "required for project context" in message
    
    def test_check_tool_availability_found(self):
        """Test tool availability check when tool is found."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        
        # Mock shutil.which to return a path
        with patch('shutil.which', return_value='/usr/bin/git'):
            available, status = validator.check_tool_availability('git')
            
            assert available is True
            assert "git found at /usr/bin/git" in status
    
    def test_check_tool_availability_not_found(self):
        """Test tool availability check when tool is not found."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            
            available, status = validator.check_tool_availability('nonexistent')
            
            assert available is False
            assert "nonexistent not found" in status
    
    def test_check_tool_availability_exception(self):
        """Test tool availability check when exception occurs."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        
        # Mock shutil.which to raise an exception
        with patch('shutil.which', side_effect=Exception("Test error")):
            available, status = validator.check_tool_availability('git')
            
            assert available is False
            assert "Error checking git: Test error" in status
    
    def test_validate_all_dependencies_success(self, tmp_path):
        """Test comprehensive validation when all dependencies are met."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Test")
        
        with patch.object(validator, 'validate_git_repository', return_value=(True, "Valid git repository")), \
             patch.object(validator, 'validate_github_remote', return_value=(True, "GitHub remote found")), \
             patch.object(validator, 'check_tool_availability') as mock_tool_check:
            
            def tool_side_effect(tool):
                return (True, f"{tool} found")
            mock_tool_check.side_effect = tool_side_effect
            
            result = validator.validate_all_dependencies(str(tmp_path))
            
            assert result['valid'] is True
            assert len(result['errors']) == 0
            assert len(result['warnings']) == 0
            assert 'git' in result['tool_status']
            assert 'gh' in result['tool_status']
            assert 'jq' in result['tool_status']
            assert 'claude' in result['tool_status']
            assert 'llm' in result['tool_status']
    
    def test_validate_all_dependencies_missing_git_repo(self, tmp_path):
        """Test validation when not in git repository."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        
        with patch.object(validator, 'validate_git_repository', return_value=(False, "Not a git repository")), \
             patch.object(validator, 'validate_github_remote', return_value=(True, "GitHub remote found")), \
             patch.object(validator, 'check_tool_availability', return_value=(True, "tool found")):
            
            result = validator.validate_all_dependencies(str(tmp_path))
            
            assert result['valid'] is False
            assert any("Git repository check failed" in error for error in result['errors'])
    
    def test_validate_all_dependencies_missing_claude_md(self, tmp_path):
        """Test validation when CLAUDE.md is missing."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        
        with patch.object(validator, 'validate_git_repository', return_value=(True, "Valid git repository")), \
             patch.object(validator, 'validate_github_remote', return_value=(True, "GitHub remote found")), \
             patch.object(validator, 'check_tool_availability', return_value=(True, "tool found")):
            
            result = validator.validate_all_dependencies(str(tmp_path))
            
            assert result['valid'] is False
            assert any("CLAUDE.md check failed" in error for error in result['errors'])
    
    def test_validate_all_dependencies_missing_required_tools(self, tmp_path):
        """Test validation when required tools are missing."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Test")
        
        def tool_side_effect(tool):
            if tool == 'gh':
                return (False, "gh not found")
            return (True, f"{tool} found")
        
        with patch.object(validator, 'validate_git_repository', return_value=(True, "Valid git repository")), \
             patch.object(validator, 'validate_github_remote', return_value=(True, "GitHub remote found")), \
             patch.object(validator, 'check_tool_availability', side_effect=tool_side_effect):
            
            result = validator.validate_all_dependencies(str(tmp_path))
            
            assert result['valid'] is False
            assert any("Missing required tools: gh (GitHub CLI)" in error for error in result['errors'])
            assert result['tool_status']['gh']['available'] is False
            assert result['tool_status']['gh']['required'] is True
    
    def test_validate_all_dependencies_missing_optional_tools_not_prompt_only(self, tmp_path):
        """Test validation when optional tools missing and not prompt-only mode."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Test")
        
        def tool_side_effect(tool):
            if tool == 'claude':
                return (False, "claude not found")
            elif tool == 'llm':
                return (False, "llm not found")
            return (True, f"{tool} found")
        
        with patch.object(validator, 'validate_git_repository', return_value=(True, "Valid git repository")), \
             patch.object(validator, 'validate_github_remote', return_value=(True, "GitHub remote found")), \
             patch.object(validator, 'check_tool_availability', side_effect=tool_side_effect):
            
            result = validator.validate_all_dependencies(str(tmp_path), prompt_only=False)
            
            assert result['valid'] is True  # Optional tools don't make it invalid
            assert len(result['warnings']) == 2
            assert any("claude not found" in warning for warning in result['warnings'])
            assert any("llm not found" in warning for warning in result['warnings'])
    
    def test_validate_all_dependencies_missing_optional_tools_prompt_only(self, tmp_path):
        """Test validation when optional tools missing in prompt-only mode."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Test")
        
        def tool_side_effect(tool):
            if tool == 'claude':
                return (False, "claude not found")
            elif tool == 'llm':
                return (False, "llm not found")
            return (True, f"{tool} found")
        
        with patch.object(validator, 'validate_git_repository', return_value=(True, "Valid git repository")), \
             patch.object(validator, 'validate_github_remote', return_value=(True, "GitHub remote found")), \
             patch.object(validator, 'check_tool_availability', side_effect=tool_side_effect):
            
            result = validator.validate_all_dependencies(str(tmp_path), prompt_only=True)
            
            assert result['valid'] is True
            # In prompt-only mode, claude warning shouldn't be shown
            assert len(result['warnings']) == 1  # Only llm warning
            assert any("llm not found" in warning for warning in result['warnings'])
    
    def test_get_missing_dependencies(self):
        """Test getting list of missing required dependencies."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        
        validation_results = {
            'tool_status': {
                'git': {'available': True, 'required': True},
                'gh': {'available': False, 'required': True},
                'jq': {'available': True, 'required': True},
                'claude': {'available': False, 'required': False}
            }
        }
        
        missing = validator.get_missing_dependencies(validation_results)
        
        assert missing == ['gh']
    
    def test_format_validation_report_success(self):
        """Test formatting validation report for successful validation."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'tool_status': {
                'git': {'available': True, 'status': 'git found', 'required': True},
                'claude': {'available': True, 'status': 'claude found', 'required': False}
            }
        }
        
        report = validator.format_validation_report(validation_results)
        
        assert "✅ Environment validation passed" in report
        assert "✅ git (required)" in report
        assert "✅ claude (optional)" in report
    
    def test_format_validation_report_failure(self):
        """Test formatting validation report for failed validation."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        
        validation_results = {
            'valid': False,
            'errors': ['Missing required tool: gh'],
            'warnings': ['Claude not found'],
            'tool_status': {
                'git': {'available': True, 'status': 'git found', 'required': True},
                'gh': {'available': False, 'status': 'gh not found', 'required': True}
            }
        }
        
        report = validator.format_validation_report(validation_results)
        
        assert "❌ Environment validation failed" in report
        assert "ERROR: Missing required tool: gh" in report
        assert "WARNING: Claude not found" in report
        assert "✅ git (required)" in report
        assert "❌ gh (required)" in report


class TestWorkflowLogicEnvironmentValidation:
    """Test environment validation integration with WorkflowLogic."""
    
    def test_validate_environment_success(self):
        """Test WorkflowLogic.validate_environment when validation succeeds."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow.env_validator, 'validate_all_dependencies') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'tool_status': {}
            }
            
            valid, message = workflow.validate_environment()
            
            assert valid is True
            assert "Environment validation passed" in message
            mock_validate.assert_called_once_with(prompt_only=False)
    
    def test_validate_environment_failure(self):
        """Test WorkflowLogic.validate_environment when validation fails."""
        workflow = WorkflowLogic()
        
        validation_results = {
            'valid': False,
            'errors': ['Missing required tool'],
            'warnings': [],
            'tool_status': {}
        }
        
        with patch.object(workflow.env_validator, 'validate_all_dependencies', return_value=validation_results), \
             patch.object(workflow.env_validator, 'format_validation_report', return_value="Validation failed"):
            
            valid, message = workflow.validate_environment()
            
            assert valid is False
            assert "Validation failed" in message
    
    def test_validate_environment_prompt_only(self):
        """Test WorkflowLogic.validate_environment in prompt-only mode."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow.env_validator, 'validate_all_dependencies') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'tool_status': {}
            }
            
            valid, message = workflow.validate_environment(prompt_only=True)
            
            assert valid is True
            mock_validate.assert_called_once_with(prompt_only=True)


class TestEnvironmentValidationIntegration:
    """Test environment validation in end-to-end scenarios."""
    
    def test_missing_git_tool_integration(self, tmp_path):
        """Test behavior when git tool is missing."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        
        def tool_side_effect(tool):
            if tool == 'git':
                return (False, "git not found")
            return (True, f"{tool} found")
        
        with patch.object(validator, 'validate_git_repository', return_value=(False, "Git not found")), \
             patch.object(validator, 'validate_github_remote', return_value=(False, "Git not found")), \
             patch.object(validator, 'check_tool_availability', side_effect=tool_side_effect):
            
            result = validator.validate_all_dependencies(str(tmp_path))
            
            assert result['valid'] is False
            assert any("Git not found" in error for error in result['errors'])
            assert any("Missing required tools: git" in error for error in result['errors'])
    
    def test_missing_github_cli_integration(self, tmp_path):
        """Test behavior when GitHub CLI is missing."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Test")
        
        def tool_side_effect(tool):
            if tool == 'gh':
                return (False, "gh not found")
            return (True, f"{tool} found")
        
        with patch.object(validator, 'validate_git_repository', return_value=(True, "Valid git repository")), \
             patch.object(validator, 'validate_github_remote', return_value=(True, "GitHub remote found")), \
             patch.object(validator, 'check_tool_availability', side_effect=tool_side_effect):
            
            result = validator.validate_all_dependencies(str(tmp_path))
            
            assert result['valid'] is False
            errors = " ".join(result['errors'])
            assert "Missing required tools: gh (GitHub CLI)" in errors
    
    def test_missing_jq_tool_integration(self, tmp_path):
        """Test behavior when jq tool is missing.""" 
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Test")
        
        def tool_side_effect(tool):
            if tool == 'jq':
                return (False, "jq not found")
            return (True, f"{tool} found")
        
        with patch.object(validator, 'validate_git_repository', return_value=(True, "Valid git repository")), \
             patch.object(validator, 'validate_github_remote', return_value=(True, "GitHub remote found")), \
             patch.object(validator, 'check_tool_availability', side_effect=tool_side_effect):
            
            result = validator.validate_all_dependencies(str(tmp_path))
            
            assert result['valid'] is False
            errors = " ".join(result['errors'])
            assert "Missing required tools: jq" in errors
    
    def test_no_github_remote_integration(self, tmp_path):
        """Test behavior when no GitHub remote is configured."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor
        validator = EnvironmentValidator(mock_git_service)
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Test")
        
        with patch.object(validator, 'validate_git_repository', return_value=(True, "Valid git repository")), \
             patch.object(validator, 'validate_github_remote', return_value=(False, "No GitHub remote found")), \
             patch.object(validator, 'check_tool_availability', return_value=(True, "tool found")):
            
            result = validator.validate_all_dependencies(str(tmp_path))
            
            assert result['valid'] is False
            assert any("GitHub remote check failed" in error for error in result['errors'])
    
    def test_interactive_mode_tty_check(self):
        """Test TTY detection for interactive mode (integration test)."""
        # This tests the actual TTY detection logic in WorkflowLogic
        workflow = WorkflowLogic()
        
        # Test with isatty mocked
        with patch('os.isatty', return_value=True):
            # Interactive mode should be detected
            # This is tested indirectly through WorkflowLogic constructor
            assert hasattr(workflow, 'interactive_mode')
            
        with patch('os.isatty', return_value=False):
            # Non-interactive mode should be detected  
            workflow2 = WorkflowLogic()
            assert hasattr(workflow2, 'interactive_mode')