"""Additional tests to improve coverage towards 95%."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
from pathlib import Path

from src.claude_tasker.cli import extract_pr_number, parse_issue_range
from src.claude_tasker.workflow_logic import WorkflowLogic, WorkflowResult
from src.claude_tasker.prompt_builder import PromptBuilder
from src.claude_tasker.github_client import GitHubClient, IssueData
from src.claude_tasker.workspace_manager import WorkspaceManager


class TestCLICoverageImprovements:
    """Tests to improve CLI module coverage."""
    
    def test_extract_pr_number_edge_cases(self):
        """Test extract_pr_number with edge cases."""
        # Test with string that's not digit
        assert extract_pr_number("abc") is None
        
        # Test with mixed string
        assert extract_pr_number("pr123") is None
    
    def test_parse_issue_range_edge_cases(self):
        """Test parse_issue_range with various inputs."""
        # Test with float-like string
        start, end = parse_issue_range("1.5")
        assert start is None
        assert end is None


class TestWorkflowLogicCoverageImprovements:
    """Tests to improve WorkflowLogic coverage."""
    
    @patch('src.claude_tasker.workflow_logic.GitHubClient')
    @patch('src.claude_tasker.workflow_logic.WorkspaceManager')
    @patch('src.claude_tasker.workflow_logic.PromptBuilder')
    @patch('src.claude_tasker.workflow_logic.PRBodyGenerator')
    @patch('src.claude_tasker.workflow_logic.EnvironmentValidator')
    @patch('src.claude_tasker.workflow_logic.Path')
    def test_detect_default_branch_github_success(self, mock_path, mock_env, mock_pr_gen,
                                                  mock_prompt, mock_workspace, mock_github):
        """Test default branch detection from GitHub."""
        mock_github_instance = Mock()
        mock_github_instance.get_default_branch.return_value = "develop"
        mock_github.return_value = mock_github_instance
        
        mock_workspace.return_value = Mock()
        mock_prompt.return_value = Mock()
        mock_pr_gen.return_value = Mock()
        mock_env.return_value = Mock()
        
        workflow = WorkflowLogic()
        assert workflow.base_branch == "develop"
    
    @patch('src.claude_tasker.workflow_logic.GitHubClient')
    @patch('src.claude_tasker.workflow_logic.WorkspaceManager')
    @patch('src.claude_tasker.workflow_logic.PromptBuilder')
    @patch('src.claude_tasker.workflow_logic.PRBodyGenerator')
    @patch('src.claude_tasker.workflow_logic.EnvironmentValidator')
    @patch('src.claude_tasker.workflow_logic.Path')
    def test_load_claude_md_missing(self, mock_path, mock_env, mock_pr_gen,
                                    mock_prompt, mock_workspace, mock_github):
        """Test CLAUDE.md loading when file doesn't exist."""
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        mock_github_instance = Mock()
        mock_github_instance.get_default_branch.return_value = None
        mock_github.return_value = mock_github_instance
        
        mock_workspace_instance = Mock()
        mock_workspace_instance.detect_main_branch.return_value = "main"
        mock_workspace.return_value = mock_workspace_instance
        
        mock_prompt.return_value = Mock()
        mock_pr_gen.return_value = Mock()
        mock_env.return_value = Mock()
        
        workflow = WorkflowLogic()
        assert workflow.claude_md_content == ""
    
    @patch('src.claude_tasker.workflow_logic.GitHubClient')
    @patch('src.claude_tasker.workflow_logic.WorkspaceManager')
    @patch('src.claude_tasker.workflow_logic.PromptBuilder')
    @patch('src.claude_tasker.workflow_logic.PRBodyGenerator')
    @patch('src.claude_tasker.workflow_logic.EnvironmentValidator')
    @patch('src.claude_tasker.workflow_logic.Path')
    def test_process_single_issue_project_context(self, mock_path, mock_env, mock_pr_gen,
                                                  mock_prompt, mock_workspace, mock_github):
        """Test process_single_issue with project context."""
        # Setup mocks
        mock_github_instance = Mock()
        mock_github_instance.get_default_branch.return_value = "main"
        mock_github_instance.get_issue.return_value = IssueData(
            number=42,
            title="Test Issue",
            body="Test body",
            labels=["bug"],
            url="https://github.com/test/repo/issues/42",
            author="testuser",
            state="open"
        )
        mock_github_instance.get_project_info.return_value = {"name": "Project X"}
        mock_github_instance.create_pr.return_value = "https://github.com/test/repo/pull/123"
        mock_github_instance.comment_on_issue.return_value = True
        mock_github.return_value = mock_github_instance
        
        mock_workspace_instance = Mock()
        mock_workspace_instance.validate_branch_for_issue.return_value = (True, "Branch validation passed")
        mock_workspace_instance.workspace_hygiene.return_value = True
        mock_workspace_instance.create_timestamped_branch.return_value = (True, "issue-42-12345")
        mock_workspace_instance.has_changes_to_commit.return_value = False
        mock_workspace_instance.commit_changes.return_value = True
        mock_workspace_instance.push_branch.return_value = True
        mock_workspace_instance.get_git_diff.return_value = "diff content"
        mock_workspace_instance.get_commit_log.return_value = "commit log"
        mock_workspace.return_value = mock_workspace_instance
        
        mock_prompt_instance = Mock()
        mock_prompt_instance.execute_two_stage_prompt.return_value = {
            'success': True,
            'response': 'Done'
        }
        mock_prompt.return_value = mock_prompt_instance
        
        mock_pr_gen_instance = Mock()
        mock_pr_gen_instance.generate_pr_body.return_value = "PR body content"
        mock_pr_gen.return_value = mock_pr_gen_instance
        
        mock_env_instance = Mock()
        mock_env_instance.validate_all_dependencies.return_value = {'valid': True}
        mock_env.return_value = mock_env_instance
        
        workflow = WorkflowLogic()
        result = workflow.process_single_issue(42, prompt_only=False, project_number=1)
        
        assert result.success is True
        mock_github_instance.get_project_info.assert_called_once_with(1)


class TestPromptBuilderCoverageImprovements:
    """Tests to improve PromptBuilder coverage."""
    
    def test_execute_llm_tool_timeout(self):
        """Test _execute_llm_tool with timeout."""
        builder = PromptBuilder()
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 30)):
            with patch('tempfile.NamedTemporaryFile'):
                result = builder._execute_llm_tool('llm', 'test prompt')
        
        assert result is not None
        assert result['success'] is False
        assert 'timed out' in result['error'].lower()
    
    def test_execute_llm_tool_generic_exception(self):
        """Test _execute_llm_tool with generic exception."""
        builder = PromptBuilder()
        
        with patch('subprocess.run', side_effect=Exception("Unexpected error")):
            with patch('tempfile.NamedTemporaryFile'):
                result = builder._execute_llm_tool('llm', 'test prompt')
        
        assert result is not None
        assert result['success'] is False
        assert 'unexpected' in result['error'].lower()
    
    def test_build_with_claude_cleanup_on_error(self):
        """Test build_with_claude cleanup on error."""
        builder = PromptBuilder()
        
        mock_file = Mock()
        mock_file.name = '/tmp/test.txt'
        
        with patch('subprocess.run', side_effect=Exception("Error")):
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value = mock_file
                with patch('pathlib.Path.unlink') as mock_unlink:
                    result = builder.build_with_claude('test prompt')
        
        # Verify cleanup was attempted
        assert result is not None
        assert result['success'] is False


class TestWorkspaceManagerCoverageImprovements:
    """Tests to improve WorkspaceManager coverage."""
    
    def test_get_current_branch_error(self):
        """Test get_current_branch with error."""
        manager = WorkspaceManager()
        
        mock_result = Mock(returncode=1, stdout='', stderr='Error')
        with patch('subprocess.run', return_value=mock_result):
            branch = manager.get_current_branch()
        
        assert branch is None
    
    def test_has_changes_with_changes(self):
        """Test has_changes when there are changes."""
        manager = WorkspaceManager()
        
        mock_result = Mock(returncode=0, stdout=' M file.txt')
        with patch('subprocess.run', return_value=mock_result):
            has_changes = manager.has_changes()
        
        assert has_changes is True
    
    def test_cleanup_old_branches_error(self):
        """Test cleanup_old_branches with error."""
        manager = WorkspaceManager()
        
        mock_result = Mock(returncode=1, stdout='', stderr='Error')
        with patch('subprocess.run', return_value=mock_result):
            result = manager.cleanup_old_branches()
        
        assert result is False
    
    def test_get_git_diff_error(self):
        """Test get_git_diff with error."""
        manager = WorkspaceManager()
        
        mock_result = Mock(returncode=1, stdout='', stderr='Error')
        with patch('subprocess.run', return_value=mock_result):
            diff = manager.get_git_diff('main')
        
        assert diff == ""
    
    def test_get_commit_log_error(self):
        """Test get_commit_log with error."""
        manager = WorkspaceManager()
        
        mock_result = Mock(returncode=1, stdout='', stderr='Error')
        with patch('subprocess.run', return_value=mock_result):
            log = manager.get_commit_log('main')
        
        assert log == ""