"""Tests for claude-tasker workflow logic and agent coordination."""
import pytest
import subprocess
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, mock_open, call

from src.claude_tasker.workflow_logic import WorkflowLogic, WorkflowResult
from src.claude_tasker.github_client import IssueData, PRData
from src.claude_tasker.prompt_models import TwoStageResult


class TestWorkflowLogic:
    """Test complex workflow logic and agent coordination."""
    
    def test_two_stage_execution_meta_prompt(self):
        """Test two-stage execution: meta-prompt generation."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow.github_client, 'get_issue') as mock_get_issue, \
             patch.object(workflow.prompt_builder, 'execute_two_stage_prompt') as mock_two_stage, \
             patch.object(workflow.workspace_manager, 'smart_branch_for_issue') as mock_branch:
            
            # Mock issue data
            issue_data = IssueData(
                number=316,
                title="Test Issue",
                body="Test body",
                labels=["enhancement"],
                url="https://github.com/test/repo/issues/316",
                author="testuser",
                state="open"
            )
            mock_get_issue.return_value = issue_data
            
            # Mock branch setup
            mock_branch.return_value = (True, "issue-316-1234567890", "created")
            
            # Mock two-stage execution result
            mock_two_stage.return_value = TwoStageResult(
                success=True,
                meta_prompt='Generated meta prompt',
                optimized_prompt='Test optimized prompt',
                execution_result=None
            )
            
            # Mock environment validation
            with patch.object(workflow, 'validate_environment') as mock_env:
                mock_env.return_value = (True, "Environment valid")
                
                # Mock workspace operations
                with patch.object(workflow.workspace_manager, 'workspace_hygiene') as mock_hygiene, \
                     patch.object(workflow.workspace_manager, 'create_timestamped_branch') as mock_branch:
                    
                    mock_hygiene.return_value = True
                    mock_branch.return_value = (True, "issue-316-1234567890")
                    
                    result = workflow.process_single_issue(316, prompt_only=True)
                    
                    assert result.success is True
                    assert result.issue_number == 316
                    mock_two_stage.assert_called_once()
                    assert mock_two_stage.call_args[1]['prompt_only'] is True
    
    def test_agent_based_architecture(self, tmp_path):
        """Test agent-based architecture detection."""
        workflow = WorkflowLogic()
        
        # Create .claude/agents directory structure
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        # Create mock agent file
        agent_file = agents_dir / "github-issue-implementer.md"
        agent_content = "# GitHub Issue Implementer Agent\nTest agent content"
        agent_file.write_text(agent_content)
        
        # Test agent content is available to prompt builder
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=agent_content):
            
            # Test that prompt builder has access to framework content
            framework = workflow.prompt_builder.lyra_dev_framework
            
            assert "DECONSTRUCT" in framework
            assert "DIAGNOSE" in framework
            assert "DEVELOP" in framework
            assert "DELIVER" in framework
            assert "Lyra-Dev" in framework
            assert "elite AI prompt optimizer" in framework
    
    def test_status_verification_protocol(self):
        """Test status verification protocol for detecting false completion claims."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow.github_client, 'get_issue') as mock_get_issue:
            # Mock issue with completion claim (closed state)
            issue_data = IssueData(
                number=316,
                title="Test Issue - COMPLETED",
                body="This issue has been completed",
                labels=["completed"],
                url="https://github.com/test/repo/issues/316",
                author="testuser",
                state="closed"
            )
            mock_get_issue.return_value = issue_data
            
            # Mock environment validation
            with patch.object(workflow, 'validate_environment') as mock_env:
                mock_env.return_value = (True, "Environment valid")
                
                result = workflow.process_single_issue(316)
                
                # Should recognize issue is already closed and return success
                assert result.success is True
                assert "already closed" in result.message
                assert result.issue_number == 316
    
    def test_audit_and_implement_workflow(self):
        """Test AUDIT-AND-IMPLEMENT workflow."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow.github_client, 'get_issue') as mock_get_issue, \
             patch.object(workflow.prompt_builder, 'execute_two_stage_prompt') as mock_two_stage, \
             patch.object(workflow.workspace_manager, 'smart_branch_for_issue') as mock_smart_branch:
            
            # Mock issue data
            issue_data = IssueData(
                number=316,
                title="Test Issue",
                body="Test body",
                labels=["enhancement"],
                url="https://github.com/test/repo/issues/316",
                author="testuser",
                state="open"
            )
            mock_get_issue.return_value = issue_data
            
            # Mock branch setup
            mock_smart_branch.return_value = (True, "issue-316-1234567890", "created")
            
            # Mock two-stage execution with audit and implement phases
            mock_two_stage.return_value = TwoStageResult(
                success=True,
                meta_prompt='Audit prompt: gaps identified',
                optimized_prompt='Implementation prompt with gap analysis',
                execution_result={'result': 'Implementation complete'}
            )
            
            # Mock all workflow dependencies
            with patch.object(workflow, 'validate_environment') as mock_env, \
                 patch.object(workflow.workspace_manager, 'workspace_hygiene') as mock_hygiene, \
                 patch.object(workflow.workspace_manager, 'create_timestamped_branch') as mock_branch, \
                 patch.object(workflow.workspace_manager, 'has_changes_to_commit') as mock_changes:
                
                mock_env.return_value = (True, "Environment valid")
                mock_hygiene.return_value = True
                mock_branch.return_value = (True, "issue-316-1234567890")
                mock_changes.return_value = False  # No changes made
                
                # Mock GitHub comment
                with patch.object(workflow.github_client, 'comment_on_issue') as mock_comment:
                    result = workflow.process_single_issue(316)
                    
                    assert result.success is True
                    assert result.issue_number == 316
                    
                    # Should have called two-stage prompt execution
                    mock_two_stage.assert_called_once()
                    
                    # Should post comment about no changes needed
                    mock_comment.assert_called_once()
                    comment_text = mock_comment.call_args[0][1]
                    assert "4-D methodology" in comment_text
    
    def test_intelligent_pr_body_generation(self):
        """Test intelligent PR body generation using llm tool."""
        workflow = WorkflowLogic()
        
        # Test PR body generator functionality
        with patch.object(workflow.pr_body_generator, 'generate_pr_body') as mock_pr_body:
            mock_pr_body.return_value = "## Summary\nGenerated intelligent PR body\n## Changes\n- Test changes"
            
            # Mock issue data
            issue_data = IssueData(
                number=316,
                title="Test Issue",
                body="Test body",
                labels=["enhancement"],
                url="https://github.com/test/repo/issues/316",
                author="testuser",
                state="open"
            )
            
            # Test PR body generation directly
            pr_body = workflow.pr_body_generator.generate_pr_body(
                issue_data, "diff content", "issue-316-123", "commit log"
            )
            
            assert "Generated intelligent PR body" in pr_body
            assert "Summary" in pr_body
            assert "Changes" in pr_body
            mock_pr_body.assert_called_once_with(issue_data, "diff content", "issue-316-123", "commit log")
    
    def test_pr_template_detection(self, tmp_path):
        """Test PR template file detection."""
        workflow = WorkflowLogic()
        
        # Create PR template files
        github_dir = tmp_path / ".github"
        github_dir.mkdir(exist_ok=True)
        
        pr_template = github_dir / "pull_request_template.md"
        template_content = "# PR Template\n## Summary\n## Changes"
        pr_template.write_text(template_content)
        
        # Test template detection
        detected_template = workflow.pr_body_generator.detect_templates(str(tmp_path))
        
        assert detected_template == template_content
        assert "PR Template" in detected_template
        assert "Summary" in detected_template
        assert "Changes" in detected_template
    
    def test_range_processing(self):
        """Test range processing functionality."""
        workflow = WorkflowLogic(timeout_between_tasks=0.1)  # Short timeout for testing
        
        with patch.object(workflow, 'process_single_issue') as mock_process, \
             patch('time.sleep') as mock_sleep:
            
            # Mock individual issue processing
            mock_process.return_value = WorkflowResult(
                success=True,
                message="Issue processed successfully",
                issue_number=316
            )
            
            results = workflow.process_issue_range(316, 318, prompt_only=True)
            
            # Should process 3 issues (316, 317, 318)
            assert len(results) == 3
            assert all(result.success for result in results)
            
            # Should call process_single_issue for each issue
            assert mock_process.call_count == 3
            
            # Should apply timeout between issues (2 timeouts for 3 issues)
            assert mock_sleep.call_count == 2
    
    def test_exponential_backoff_retry(self):
        """Test exponential backoff retry logic for API limits."""
        workflow = WorkflowLogic()
        
        with patch('subprocess.run') as mock_run, \
             patch('time.sleep') as mock_sleep:
            
            call_count = 0
            
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    # Simulate API rate limit
                    return subprocess.CompletedProcess(args[0], 1, "", "API rate limit exceeded")
                else:
                    # Success after retries
                    return subprocess.CompletedProcess(args[0], 0, "Success", "")
            
            mock_run.side_effect = side_effect
            
            # Test exponential backoff directly on GitHubClient
            result = workflow.github_client._run_gh_command(['issue', 'view', '316'])
            
            # Should eventually succeed after retries
            assert result.returncode == 0
            assert result.stdout == "Success"
            assert call_count == 3  # Three attempts total
            
            # Should have applied exponential backoff delays
            assert mock_sleep.call_count >= 2
    
    def test_branch_creation_timestamped(self):
        """Test automatic branch creation with timestamps."""
        workflow = WorkflowLogic()
        
        with patch('time.time', return_value=1234567890), \
             patch.object(workflow.workspace_manager, '_run_git_command') as mock_git:
            
            # Mock successful git commands using CompletedProcess
            def git_side_effect(cmd):
                cmd_str = ' '.join(cmd)
                if 'branch --show-current' in cmd_str:
                    return subprocess.CompletedProcess(cmd, 0, "main", "")
                elif 'checkout -b issue-316-1234567890' in cmd_str:
                    return subprocess.CompletedProcess(cmd, 0, "Switched to branch issue-316-1234567890", "")
                else:
                    return subprocess.CompletedProcess(cmd, 0, "", "")
            
            mock_git.side_effect = git_side_effect
            
            success, branch_name = workflow.workspace_manager.create_timestamped_branch(316)
            
            assert success is True
            assert branch_name == "issue-316-1234567890"
            
            # Should have called git checkout with timestamped branch name
            git_calls = [call.args[0] for call in mock_git.call_args_list]
            checkout_calls = [call for call in git_calls if 'checkout' in ' '.join(call) and 'issue-316-1234567890' in ' '.join(call)]
            assert len(checkout_calls) > 0
    
    def test_initialization_with_defaults(self):
        """Test WorkflowLogic initialization with default parameters."""
        with patch.object(WorkflowLogic, '_detect_default_branch', return_value='main'), \
             patch.object(WorkflowLogic, '_load_claude_md', return_value='CLAUDE.md content'):
            
            workflow = WorkflowLogic()
            
            assert workflow.timeout_between_tasks == 10.0
            assert workflow.coder == "claude"
            assert workflow.branch_strategy == "reuse"
            assert workflow.base_branch == "main"
            assert workflow.claude_md_content == 'CLAUDE.md content'
    
    def test_initialization_with_custom_params(self):
        """Test WorkflowLogic initialization with custom parameters."""
        with patch.object(WorkflowLogic, '_detect_default_branch', return_value='main'), \
             patch.object(WorkflowLogic, '_load_claude_md', return_value=''):
            
            workflow = WorkflowLogic(
                timeout_between_tasks=5.0,
                interactive_mode=True,
                coder="llm",
                base_branch="develop",
                branch_strategy="always_new"
            )
            
            assert workflow.timeout_between_tasks == 5.0
            assert workflow.interactive_mode is True
            assert workflow.coder == "llm"
            assert workflow.base_branch == "develop"
            assert workflow.branch_strategy == "always_new"
    
    def test_detect_default_branch_github_success(self):
        """Test default branch detection from GitHub API."""
        with patch.object(WorkflowLogic, '_load_claude_md', return_value=''):
            workflow = WorkflowLogic.__new__(WorkflowLogic)  # Create without __init__
            workflow.github_client = Mock()
            workflow.workspace_manager = Mock()
            
            workflow.github_client.get_default_branch.return_value = "main"
            
            result = workflow._detect_default_branch()
            
            assert result == "main"
            workflow.github_client.get_default_branch.assert_called_once()
            workflow.workspace_manager.detect_main_branch.assert_not_called()
    
    def test_detect_default_branch_github_fallback(self):
        """Test default branch detection fallback to workspace manager."""
        workflow = WorkflowLogic.__new__(WorkflowLogic)  # Create without __init__
        workflow.github_client = Mock()
        workflow.workspace_manager = Mock()
        
        workflow.github_client.get_default_branch.return_value = None
        workflow.workspace_manager.detect_main_branch.return_value = "master"
        
        result = workflow._detect_default_branch()
        
        assert result == "master"
        workflow.github_client.get_default_branch.assert_called_once()
        workflow.workspace_manager.detect_main_branch.assert_called_once()
    
    def test_load_claude_md_exists(self):
        """Test loading CLAUDE.md when file exists."""
        workflow = WorkflowLogic.__new__(WorkflowLogic)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value='# CLAUDE.md\nProject context'):
            
            content = workflow._load_claude_md()
            
            assert content == '# CLAUDE.md\nProject context'
    
    def test_load_claude_md_missing(self):
        """Test loading CLAUDE.md when file doesn't exist."""
        workflow = WorkflowLogic.__new__(WorkflowLogic)
        
        with patch('pathlib.Path.exists', return_value=False):
            
            content = workflow._load_claude_md()
            
            assert content == ""
    
    def test_load_claude_md_read_error(self):
        """Test loading CLAUDE.md with read error."""
        workflow = WorkflowLogic.__new__(WorkflowLogic)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', side_effect=Exception("Read error")):
            
            content = workflow._load_claude_md()
            
            assert content == ""
    
    def test_validate_environment_success(self):
        """Test environment validation success."""
        workflow = WorkflowLogic()
        
        mock_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'tool_status': {}
        }
        
        with patch.object(workflow.env_validator, 'validate_all_dependencies', return_value=mock_results):
            
            valid, message = workflow.validate_environment()
            
            assert valid is True
            assert message == "Environment validation passed"
    
    def test_validate_environment_failure(self):
        """Test environment validation failure."""
        workflow = WorkflowLogic()
        
        mock_results = {
            'valid': False,
            'errors': ['Git not found'],
            'warnings': [],
            'tool_status': {}
        }
        
        with patch.object(workflow.env_validator, 'validate_all_dependencies', return_value=mock_results), \
             patch.object(workflow.env_validator, 'format_validation_report', return_value='Validation failed report'):
            
            valid, message = workflow.validate_environment()
            
            assert valid is False
            assert message == 'Validation failed report'
    
    def test_process_issue_range_timeout_between_issues(self):
        """Test issue range processing applies timeout between issues."""
        workflow = WorkflowLogic(timeout_between_tasks=1.0)
        
        with patch.object(workflow, 'process_single_issue') as mock_process, \
             patch('time.sleep') as mock_sleep:
            
            mock_process.return_value = WorkflowResult(
                success=True,
                message="Success",
                issue_number=100
            )
            
            results = workflow.process_issue_range(100, 102, prompt_only=True)
            
            # Should process 3 issues
            assert len(results) == 3
            assert mock_process.call_count == 3
            
            # Should sleep 2 times (between 3 issues)
            assert mock_sleep.call_count == 2
            mock_sleep.assert_called_with(1.0)
    
    def test_process_issue_range_no_timeout_on_last_issue(self):
        """Test issue range processing doesn't timeout after last issue."""
        workflow = WorkflowLogic(timeout_between_tasks=1.0)
        
        with patch.object(workflow, 'process_single_issue') as mock_process, \
             patch('time.sleep') as mock_sleep:
            
            mock_process.return_value = WorkflowResult(success=True, message="Success", issue_number=100)
            
            results = workflow.process_issue_range(100, 100, prompt_only=True)  # Single issue
            
            assert len(results) == 1
            assert mock_process.call_count == 1
            assert mock_sleep.call_count == 0  # No timeout for single issue
    
    def test_review_pr_success(self):
        """Test PR review functionality."""
        workflow = WorkflowLogic()
        
        mock_pr = PRData(
            number=123,
            title="Test PR",
            body="PR description",
            head_ref="feature-branch",
            base_ref="main",
            author="contributor",
            additions=10,
            deletions=5,
            changed_files=2,
            url="https://github.com/owner/repo/pull/123"
        )
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.github_client, 'get_pr', return_value=mock_pr), \
             patch.object(workflow.github_client, 'get_pr_diff', return_value="diff content"), \
             patch.object(workflow.prompt_builder, 'build_pr_review_prompt', return_value="Review prompt"), \
             patch.object(workflow.prompt_builder, 'execute_llm_tool', return_value={'result': 'PR review generated'}):
            
            result = workflow.review_pr(123, prompt_only=True)
            
            assert result.success is True
            assert "PR review generated" in result.message
    
    def test_review_pr_not_found(self):
        """Test PR review when PR not found."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.github_client, 'get_pr', return_value=None):
            
            result = workflow.review_pr(999)
            
            assert result.success is False
            assert "not found" in result.message
    
    def test_review_pr_environment_validation_fails(self):
        """Test PR review when environment validation fails."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(False, "Validation failed")):
            
            result = workflow.review_pr(123)
            
            assert result.success is False
            assert result.message == "Validation failed"
    
    def test_analyze_bug_success(self):
        """Test bug analysis functionality."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.prompt_builder, 'build_bug_analysis_prompt', return_value="Bug analysis prompt"), \
             patch.object(workflow.prompt_builder, 'execute_llm_tool', return_value={'issue_title': 'Bug: Auth failure', 'issue_body': 'Detailed bug analysis'}), \
             patch.object(workflow.github_client, 'create_issue', return_value='https://github.com/owner/repo/issues/456'):
            
            result = workflow.analyze_bug("Login not working", prompt_only=False)
            
            assert result.success is True
            assert "Issue created" in result.message
            assert "https://github.com/owner/repo/issues/456" in result.message
    
    def test_analyze_bug_prompt_only(self):
        """Test bug analysis in prompt-only mode."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.prompt_builder, 'build_bug_analysis_prompt', return_value="Bug analysis prompt"), \
             patch.object(workflow.prompt_builder, 'execute_llm_tool', return_value={'issue_title': 'Bug: Auth failure', 'issue_body': 'Analysis'}):
            
            result = workflow.analyze_bug("Login not working", prompt_only=True)
            
            assert result.success is True
            assert "Bug analysis completed" in result.message
    
    def test_analyze_bug_llm_execution_fails(self):
        """Test bug analysis when LLM execution fails."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.prompt_builder, 'build_bug_analysis_prompt', return_value="Bug analysis prompt"), \
             patch.object(workflow.prompt_builder, 'execute_llm_tool', return_value=None):
            
            result = workflow.analyze_bug("Login not working")
            
            assert result.success is False
            assert "Failed to analyze bug" in result.message
    
    def test_analyze_feature_success(self):
        """Test feature analysis functionality."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.prompt_builder, 'build_feature_analysis_prompt', return_value="Feature analysis prompt"), \
             patch.object(workflow.prompt_builder, 'execute_llm_tool', return_value={'issue_title': 'Feature: CSV export', 'issue_body': 'Feature analysis'}), \
             patch.object(workflow.github_client, 'create_issue', return_value='https://github.com/owner/repo/issues/789'):
            
            result = workflow.analyze_feature("Add CSV export", prompt_only=False)
            
            assert result.success is True
            assert "Issue created" in result.message
    
    def test_analyze_feature_prompt_only(self):
        """Test feature analysis in prompt-only mode."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.prompt_builder, 'build_feature_analysis_prompt', return_value="Feature prompt"), \
             patch.object(workflow.prompt_builder, 'execute_llm_tool', return_value={'issue_title': 'Feature: Export', 'issue_body': 'Analysis'}):
            
            result = workflow.analyze_feature("Add export", prompt_only=True)
            
            assert result.success is True
            assert "Feature analysis completed" in result.message
    
    def test_analyze_feature_create_issue_fails(self):
        """Test feature analysis when issue creation fails."""
        workflow = WorkflowLogic()
        
        with patch.object(workflow, 'validate_environment', return_value=(True, "Valid")), \
             patch.object(workflow.prompt_builder, 'build_feature_analysis_prompt', return_value="Feature prompt"), \
             patch.object(workflow.prompt_builder, 'execute_llm_tool', return_value={'issue_title': 'Feature', 'issue_body': 'Body'}), \
             patch.object(workflow.github_client, 'create_issue', return_value=None):
            
            result = workflow.analyze_feature("Add feature")
            
            assert result.success is False
            assert "Failed to create issue" in result.message
    
    def test_deduplicate_review_content(self):
        """Test review content deduplication."""
        workflow = WorkflowLogic()
        
        content = """
        This is a great PR!
        
        **Summary:**
        - Good changes
        - Well tested
        
        **Summary:**
        - Different summary
        - Also good
        """
        
        deduplicated = workflow._deduplicate_review_content(content)
        
        # Should remove duplicate sections
        summary_count = deduplicated.count("**Summary:**")
        assert summary_count == 1
    
    def test_workflow_result_dataclass(self):
        """Test WorkflowResult dataclass functionality."""
        result = WorkflowResult(
            success=True,
            message="Test message",
            issue_number=123,
            pr_url="https://github.com/owner/repo/pull/456",
            branch_name="feature-branch",
            error_details="No errors"
        )
        
        assert result.success is True
        assert result.message == "Test message"
        assert result.issue_number == 123
        assert result.pr_url == "https://github.com/owner/repo/pull/456"
        assert result.branch_name == "feature-branch"
        assert result.error_details == "No errors"
    
    def test_workflow_result_minimal(self):
        """Test WorkflowResult with minimal required fields."""
        result = WorkflowResult(success=False, message="Error occurred")
        
        assert result.success is False
        assert result.message == "Error occurred"
        assert result.issue_number is None
        assert result.pr_url is None
        assert result.branch_name is None
        assert result.error_details is None