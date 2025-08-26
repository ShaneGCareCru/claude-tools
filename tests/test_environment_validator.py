"""Comprehensive unit tests for environment validator module."""

import os
import subprocess
import tempfile
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.claude_tasker.environment_validator import EnvironmentValidator
from src.claude_tasker.services.command_executor import CommandExecutor
from src.claude_tasker.services.git_service import GitService


class TestEnvironmentValidator(TestCase):
    """Test environment validator functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        mock_executor = Mock(spec=CommandExecutor)
        mock_git_service = Mock(spec=GitService)
        mock_git_service.executor = mock_executor  # Add executor attribute
        self.validator = EnvironmentValidator(mock_git_service)
    
    def test_init(self):
        """Test validator initialization."""
        self.assertIn('git', self.validator.required_tools)
        self.assertIn('gh', self.validator.required_tools)
        self.assertIn('jq', self.validator.required_tools)
        self.assertIn('claude', self.validator.optional_tools)
        self.assertIn('llm', self.validator.optional_tools)
    
    def test_validate_git_repository_valid(self):
        """Test git repository validation with valid repo."""
        from src.claude_tasker.services.command_executor import CommandResult, CommandErrorType
        
        # Mock GitService rev_parse method to return success
        result = CommandResult(
            returncode=0,
            stdout='.git',
            stderr='',
            command=['git', 'rev-parse', '--git-dir'],
            execution_time=1.0,
            error_type=CommandErrorType.SUCCESS,
            attempts=1,
            success=True
        )
        self.validator.git_service.rev_parse.return_value = result
        
        valid, message = self.validator.validate_git_repository()
        
        self.assertTrue(valid)
        self.assertEqual(message, "Valid git repository")
        self.validator.git_service.rev_parse.assert_called_once_with('--git-dir', cwd='.')
    
    def test_validate_git_repository_invalid(self):
        """Test git repository validation with invalid repo."""
        from src.claude_tasker.services.command_executor import CommandResult, CommandErrorType
        
        # Mock GitService rev_parse method to return failure
        result = CommandResult(
            returncode=1,
            stdout='',
            stderr='not a git repository',
            command=['git', 'rev-parse', '--git-dir'],
            execution_time=1.0,
            error_type=CommandErrorType.GENERAL_ERROR,
            attempts=1,
            success=False
        )
        self.validator.git_service.rev_parse.return_value = result
        
        valid, message = self.validator.validate_git_repository()
        
        self.assertFalse(valid)
        self.assertEqual(message, "Not a git repository")
    
    def test_validate_git_repository_custom_path(self):
        """Test git repository validation with custom path."""
        from src.claude_tasker.services.command_executor import CommandResult, CommandErrorType
        
        # Mock GitService rev_parse method to return success
        result = CommandResult(
            returncode=0,
            stdout='.git',
            stderr='',
            command=['git', 'rev-parse', '--git-dir'],
            execution_time=1.0,
            error_type=CommandErrorType.SUCCESS,
            attempts=1,
            success=True
        )
        self.validator.git_service.rev_parse.return_value = result
        
        valid, message = self.validator.validate_git_repository("/custom/path")
        
        self.assertTrue(valid)
        self.validator.git_service.rev_parse.assert_called_once_with('--git-dir', cwd='/custom/path')
    
    def test_validate_git_repository_git_not_found(self):
        """Test git repository validation when git not found."""
        # Mock GitService rev_parse method to raise FileNotFoundError
        self.validator.git_service.rev_parse.side_effect = FileNotFoundError("Git not found")
        
        valid, message = self.validator.validate_git_repository()
        
        self.assertFalse(valid)
        self.assertEqual(message, "Git validation error: Git not found")
    
    def test_validate_github_remote_valid(self):
        """Test GitHub remote validation with valid remote."""
        # Mock GitService get_remote_url method to return GitHub URL
        self.validator.git_service.get_remote_url.return_value = 'https://github.com/owner/repo.git'
        
        valid, message = self.validator.validate_github_remote()
        
        self.assertTrue(valid)
        self.assertIn('GitHub remote:', message)
        self.assertIn('https://github.com/owner/repo.git', message)
        self.validator.git_service.get_remote_url.assert_called_once_with('origin', cwd='.')
    
    def test_validate_github_remote_no_github(self):
        """Test GitHub remote validation with non-GitHub remote."""
        # Mock GitService get_remote_url method to return non-GitHub URL
        self.validator.git_service.get_remote_url.return_value = 'https://gitlab.com/owner/repo.git'
        
        valid, message = self.validator.validate_github_remote()
        
        self.assertFalse(valid)
        self.assertEqual(message, "No GitHub remote found")
    
    def test_validate_github_remote_no_remote(self):
        """Test GitHub remote validation with no remote."""
        # Mock GitService get_remote_url method to return None
        self.validator.git_service.get_remote_url.return_value = None
        
        valid, message = self.validator.validate_github_remote()
        
        self.assertFalse(valid)
        self.assertEqual(message, "No GitHub remote found")
    
    def test_validate_github_remote_custom_path(self):
        """Test GitHub remote validation with custom path."""
        # Mock GitService get_remote_url method to return GitHub URL
        self.validator.git_service.get_remote_url.return_value = 'https://github.com/owner/repo.git'
        
        valid, message = self.validator.validate_github_remote("/custom/path")
        
        self.assertTrue(valid)
        self.validator.git_service.get_remote_url.assert_called_once_with('origin', cwd='/custom/path')
    
    def test_validate_github_remote_git_not_found(self):
        """Test GitHub remote validation when git not found."""
        # Mock GitService get_remote_url method to raise FileNotFoundError
        self.validator.git_service.get_remote_url.side_effect = FileNotFoundError("Git not found")
        
        valid, message = self.validator.validate_github_remote()
        
        self.assertFalse(valid)
        self.assertEqual(message, "Remote validation error: Git not found")
    
    @patch('os.path.exists')
    def test_check_claude_md_exists(self, mock_exists):
        """Test CLAUDE.md check when file exists."""
        mock_exists.return_value = True
        
        valid, message = self.validator.check_claude_md()
        
        self.assertTrue(valid)
        self.assertIn('CLAUDE.md found at', message)
        mock_exists.assert_called_once_with('./CLAUDE.md')
    
    @patch('os.path.exists')
    def test_check_claude_md_missing(self, mock_exists):
        """Test CLAUDE.md check when file is missing."""
        mock_exists.return_value = False
        
        valid, message = self.validator.check_claude_md()
        
        self.assertFalse(valid)
        self.assertEqual(message, "CLAUDE.md not found - required for project context")
    
    @patch('os.path.exists')
    def test_check_claude_md_custom_path(self, mock_exists):
        """Test CLAUDE.md check with custom path."""
        mock_exists.return_value = True
        
        valid, message = self.validator.check_claude_md("/custom/path")
        
        self.assertTrue(valid)
        mock_exists.assert_called_once_with('/custom/path/CLAUDE.md')
    
    @patch('shutil.which')
    def test_check_tool_availability_available(self, mock_which):
        """Test tool availability check when tool is available."""
        mock_which.return_value = '/usr/bin/git'
        
        available, status = self.validator.check_tool_availability('git')
        
        self.assertTrue(available)
        self.assertEqual(status, 'git found at /usr/bin/git')
        mock_which.assert_called_once_with('git')
    
    @patch('shutil.which')
    def test_check_tool_availability_not_available(self, mock_which):
        """Test tool availability check when tool is not available."""
        mock_which.return_value = None
        
        available, status = self.validator.check_tool_availability('nonexistent')
        
        self.assertFalse(available)
        self.assertEqual(status, 'nonexistent not found')
    
    @patch('shutil.which')
    def test_check_tool_availability_exception(self, mock_which):
        """Test tool availability check with exception."""
        mock_which.side_effect = Exception("Process error")
        
        available, status = self.validator.check_tool_availability('git')
        
        self.assertFalse(available)
        self.assertEqual(status, 'Error checking git: Process error')
    
    def test_get_missing_dependencies_no_missing(self):
        """Test getting missing dependencies when none are missing."""
        validation_results = {
            'tool_status': {
                'git': {'available': True, 'required': True},
                'gh': {'available': True, 'required': True},
                'claude': {'available': False, 'required': False}
            }
        }
        
        missing = self.validator.get_missing_dependencies(validation_results)
        
        self.assertEqual(missing, [])
    
    def test_get_missing_dependencies_some_missing(self):
        """Test getting missing dependencies when some are missing."""
        validation_results = {
            'tool_status': {
                'git': {'available': False, 'required': True},
                'gh': {'available': True, 'required': True},
                'jq': {'available': False, 'required': True},
                'claude': {'available': False, 'required': False}
            }
        }
        
        missing = self.validator.get_missing_dependencies(validation_results)
        
        self.assertIn('git', missing)
        self.assertIn('jq', missing)
        self.assertNotIn('gh', missing)
        self.assertNotIn('claude', missing)
    
    def test_get_missing_dependencies_empty_results(self):
        """Test getting missing dependencies with empty results."""
        validation_results = {}
        
        missing = self.validator.get_missing_dependencies(validation_results)
        
        self.assertEqual(missing, [])
    
    def test_format_validation_report_success(self):
        """Test formatting validation report for successful validation."""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'tool_status': {
                'git': {
                    'available': True,
                    'status': 'git found at /usr/bin/git',
                    'required': True
                },
                'claude': {
                    'available': True,
                    'status': 'claude found at /usr/local/bin/claude',
                    'required': False
                }
            }
        }
        
        report = self.validator.format_validation_report(validation_results)
        
        self.assertIn('✅ Environment validation passed', report)
        self.assertIn('✅ git (required)', report)
        self.assertIn('✅ claude (optional)', report)
    
    def test_format_validation_report_failure(self):
        """Test formatting validation report for failed validation."""
        validation_results = {
            'valid': False,
            'errors': ['Git repository check failed', 'Missing tool: jq'],
            'warnings': ['Claude CLI not found'],
            'tool_status': {
                'git': {
                    'available': False,
                    'status': 'git not found',
                    'required': True
                },
                'claude': {
                    'available': False,
                    'status': 'claude not found',
                    'required': False
                }
            }
        }
        
        report = self.validator.format_validation_report(validation_results)
        
        self.assertIn('❌ Environment validation failed', report)
        self.assertIn('ERROR: Git repository check failed', report)
        self.assertIn('ERROR: Missing tool: jq', report)
        self.assertIn('WARNING: Claude CLI not found', report)
        self.assertIn('❌ git (required)', report)
        self.assertIn('❌ claude (optional)', report)
    
    @patch.object(EnvironmentValidator, 'validate_git_repository')
    @patch.object(EnvironmentValidator, 'validate_github_remote')
    @patch.object(EnvironmentValidator, 'check_claude_md')
    @patch.object(EnvironmentValidator, 'check_tool_availability')
    def test_validate_all_dependencies_success(self, mock_tool, mock_claude_md, mock_remote, mock_git):
        """Test comprehensive validation when all checks pass."""
        # Mock successful responses
        mock_git.return_value = (True, "Valid git repo")
        mock_remote.return_value = (True, "GitHub remote found")
        mock_claude_md.return_value = (True, "CLAUDE.md found")
        mock_tool.side_effect = [
            (True, "git found"),    # git
            (True, "gh found"),     # gh
            (True, "jq found"),     # jq
            (True, "claude found"), # claude
            (True, "llm found")     # llm
        ]
        
        results = self.validator.validate_all_dependencies()
        
        self.assertTrue(results['valid'])
        self.assertEqual(len(results['errors']), 0)
        self.assertEqual(len(results['warnings']), 0)
        self.assertTrue(results['tool_status']['git']['available'])
        self.assertTrue(results['tool_status']['claude']['available'])
    
    @patch.object(EnvironmentValidator, 'validate_git_repository')
    @patch.object(EnvironmentValidator, 'validate_github_remote')
    @patch.object(EnvironmentValidator, 'check_claude_md')
    @patch.object(EnvironmentValidator, 'check_tool_availability')
    def test_validate_all_dependencies_git_failure(self, mock_tool, mock_claude_md, mock_remote, mock_git):
        """Test comprehensive validation when git check fails."""
        mock_git.return_value = (False, "Not a git repo")
        mock_remote.return_value = (True, "GitHub remote found")
        mock_claude_md.return_value = (True, "CLAUDE.md found")
        mock_tool.return_value = (True, "tool found")
        
        results = self.validator.validate_all_dependencies()
        
        self.assertFalse(results['valid'])
        self.assertGreater(len(results['errors']), 0)
        self.assertIn('Git repository check failed', results['errors'][0])
    
    @patch.object(EnvironmentValidator, 'validate_git_repository')
    @patch.object(EnvironmentValidator, 'validate_github_remote')
    @patch.object(EnvironmentValidator, 'check_claude_md')
    @patch.object(EnvironmentValidator, 'check_tool_availability')
    def test_validate_all_dependencies_remote_failure(self, mock_tool, mock_claude_md, mock_remote, mock_git):
        """Test comprehensive validation when GitHub remote check fails."""
        mock_git.return_value = (True, "Valid git repo")
        mock_remote.return_value = (False, "No GitHub remote")
        mock_claude_md.return_value = (True, "CLAUDE.md found")
        mock_tool.return_value = (True, "tool found")
        
        results = self.validator.validate_all_dependencies()
        
        self.assertFalse(results['valid'])
        self.assertIn('GitHub remote check failed', results['errors'][0])
    
    @patch.object(EnvironmentValidator, 'validate_git_repository')
    @patch.object(EnvironmentValidator, 'validate_github_remote')
    @patch.object(EnvironmentValidator, 'check_claude_md')
    @patch.object(EnvironmentValidator, 'check_tool_availability')
    def test_validate_all_dependencies_claude_md_failure(self, mock_tool, mock_claude_md, mock_remote, mock_git):
        """Test comprehensive validation when CLAUDE.md check fails."""
        mock_git.return_value = (True, "Valid git repo")
        mock_remote.return_value = (True, "GitHub remote found")
        mock_claude_md.return_value = (False, "CLAUDE.md not found")
        mock_tool.return_value = (True, "tool found")
        
        results = self.validator.validate_all_dependencies()
        
        self.assertFalse(results['valid'])
        # Find the CLAUDE.md error in the errors list
        claude_error_found = any('CLAUDE.md check failed' in error for error in results['errors'])
        self.assertTrue(claude_error_found)
    
    @patch.object(EnvironmentValidator, 'validate_git_repository')
    @patch.object(EnvironmentValidator, 'validate_github_remote')
    @patch.object(EnvironmentValidator, 'check_claude_md')
    @patch.object(EnvironmentValidator, 'check_tool_availability')
    def test_validate_all_dependencies_required_tool_missing(self, mock_tool, mock_claude_md, mock_remote, mock_git):
        """Test comprehensive validation when required tool is missing."""
        mock_git.return_value = (True, "Valid git repo")
        mock_remote.return_value = (True, "GitHub remote found")
        mock_claude_md.return_value = (True, "CLAUDE.md found")
        mock_tool.side_effect = [
            (False, "git not found"),  # git
            (True, "gh found"),        # gh
            (True, "jq found"),        # jq
            (True, "claude found"),    # claude
            (True, "llm found")        # llm
        ]
        
        results = self.validator.validate_all_dependencies()
        
        self.assertFalse(results['valid'])
        self.assertFalse(results['tool_status']['git']['available'])
        self.assertTrue(results['tool_status']['gh']['available'])
        # Find the missing tools error in the errors list
        missing_tools_error_found = any('Missing required tools' in error for error in results['errors'])
        self.assertTrue(missing_tools_error_found)
    
    @patch.object(EnvironmentValidator, 'validate_git_repository')
    @patch.object(EnvironmentValidator, 'validate_github_remote')
    @patch.object(EnvironmentValidator, 'check_claude_md')
    @patch.object(EnvironmentValidator, 'check_tool_availability')
    def test_validate_all_dependencies_claude_missing_not_prompt_only(self, mock_tool, mock_claude_md, mock_remote, mock_git):
        """Test validation when Claude is missing and not in prompt-only mode."""
        mock_git.return_value = (True, "Valid git repo")
        mock_remote.return_value = (True, "GitHub remote found")
        mock_claude_md.return_value = (True, "CLAUDE.md found")
        mock_tool.side_effect = [
            (True, "git found"),     # git
            (True, "gh found"),      # gh
            (True, "jq found"),      # jq
            (False, "claude not found"), # claude
            (True, "llm found")      # llm
        ]
        
        results = self.validator.validate_all_dependencies(prompt_only=False)
        
        self.assertTrue(results['valid'])  # Should still be valid (claude is optional)
        self.assertGreater(len(results['warnings']), 0)
        self.assertIn('claude not found', results['warnings'][0])
        self.assertIn('Use --prompt-only flag', results['warnings'][0])
    
    @patch.object(EnvironmentValidator, 'validate_git_repository')
    @patch.object(EnvironmentValidator, 'validate_github_remote')
    @patch.object(EnvironmentValidator, 'check_claude_md')
    @patch.object(EnvironmentValidator, 'check_tool_availability')
    def test_validate_all_dependencies_claude_missing_prompt_only(self, mock_tool, mock_claude_md, mock_remote, mock_git):
        """Test validation when Claude is missing but in prompt-only mode."""
        mock_git.return_value = (True, "Valid git repo")
        mock_remote.return_value = (True, "GitHub remote found")
        mock_claude_md.return_value = (True, "CLAUDE.md found")
        mock_tool.side_effect = [
            (True, "git found"),     # git
            (True, "gh found"),      # gh
            (True, "jq found"),      # jq
            (False, "claude not found"), # claude
            (True, "llm found")      # llm
        ]
        
        results = self.validator.validate_all_dependencies(prompt_only=True)
        
        self.assertTrue(results['valid'])
        # Should not generate warning about --prompt-only flag since we're already in prompt-only mode
        claude_warnings = [w for w in results['warnings'] if 'claude' in w and 'prompt-only' in w]
        self.assertEqual(len(claude_warnings), 0)
    
    @patch.object(EnvironmentValidator, 'validate_git_repository')
    @patch.object(EnvironmentValidator, 'validate_github_remote')
    @patch.object(EnvironmentValidator, 'check_claude_md')
    @patch.object(EnvironmentValidator, 'check_tool_availability')
    def test_validate_all_dependencies_llm_missing(self, mock_tool, mock_claude_md, mock_remote, mock_git):
        """Test validation when LLM tool is missing."""
        mock_git.return_value = (True, "Valid git repo")
        mock_remote.return_value = (True, "GitHub remote found")
        mock_claude_md.return_value = (True, "CLAUDE.md found")
        mock_tool.side_effect = [
            (True, "git found"),     # git
            (True, "gh found"),      # gh
            (True, "jq found"),      # jq
            (True, "claude found"),  # claude
            (False, "llm not found") # llm
        ]
        
        results = self.validator.validate_all_dependencies()
        
        self.assertTrue(results['valid'])
        self.assertGreater(len(results['warnings']), 0)
        self.assertIn('llm not found', results['warnings'][0])
        self.assertIn('Will use Claude for prompt generation', results['warnings'][0])
    
    @patch.object(EnvironmentValidator, 'validate_git_repository')
    @patch.object(EnvironmentValidator, 'validate_github_remote')
    @patch.object(EnvironmentValidator, 'check_claude_md')
    @patch.object(EnvironmentValidator, 'check_tool_availability')
    def test_validate_all_dependencies_custom_path(self, mock_tool, mock_claude_md, mock_remote, mock_git):
        """Test comprehensive validation with custom path."""
        mock_git.return_value = (True, "Valid git repo")
        mock_remote.return_value = (True, "GitHub remote found")
        mock_claude_md.return_value = (True, "CLAUDE.md found")
        mock_tool.return_value = (True, "tool found")
        
        results = self.validator.validate_all_dependencies("/custom/path")
        
        mock_git.assert_called_once_with("/custom/path")
        mock_remote.assert_called_once_with("/custom/path")
        mock_claude_md.assert_called_once_with("/custom/path")
    
    def test_validate_all_dependencies_structure(self):
        """Test that validate_all_dependencies returns correct structure."""
        with patch.object(self.validator, 'validate_git_repository', return_value=(True, "test")), \
             patch.object(self.validator, 'validate_github_remote', return_value=(True, "test")), \
             patch.object(self.validator, 'check_claude_md', return_value=(True, "test")), \
             patch.object(self.validator, 'check_tool_availability', return_value=(True, "test")):
            
            results = self.validator.validate_all_dependencies()
            
            # Check structure
            self.assertIn('valid', results)
            self.assertIn('errors', results)
            self.assertIn('warnings', results)
            self.assertIn('tool_status', results)
            
            # Check tool_status structure
            for tool in ['git', 'gh', 'jq', 'claude', 'llm']:
                self.assertIn(tool, results['tool_status'])
                self.assertIn('available', results['tool_status'][tool])
                self.assertIn('status', results['tool_status'][tool])
                self.assertIn('required', results['tool_status'][tool])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])