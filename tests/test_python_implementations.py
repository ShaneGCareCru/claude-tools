"""Unit tests for Python implementations of PRBodyGenerator and WorkflowLogic."""
import json
import subprocess
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, Mock, mock_open

from src.claude_tasker.pr_body_generator import PRBodyGenerator
from src.claude_tasker.workflow_logic import WorkflowLogic


class TestPRBodyGeneratorImplementation:
    """Test PRBodyGenerator Python implementation."""
    
    def test_init(self, tmp_path):
        """Test PRBodyGenerator initialization."""
        generator = PRBodyGenerator(tmp_path)
        assert generator.repo_path == tmp_path
        assert generator.github_dir == tmp_path / ".github"
    
    def test_detect_pr_template_not_exists(self, tmp_path):
        """Test template detection when .github directory doesn't exist."""
        generator = PRBodyGenerator(tmp_path)
        assert generator.detect_pr_template() is None
    
    def test_detect_pr_template_exists(self, tmp_path):
        """Test template detection when template files exist."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        
        template_file = github_dir / "pull_request_template.md"
        template_content = "# PR Template\n## Summary\n## Changes"
        template_file.write_text(template_content)
        
        generator = PRBodyGenerator(tmp_path)
        result = generator.detect_pr_template()
        assert result == template_content
    
    def test_template_priority_order(self, tmp_path):
        """Test template detection priority order."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        
        # Create multiple templates
        templates = [
            ("PULL_REQUEST_TEMPLATE.md", "UPPERCASE template"),
            ("pull_request_template.md", "lowercase template"),  # Higher priority
            ("pull_request_template.txt", "txt template")
        ]
        
        for name, content in templates:
            (github_dir / name).write_text(content)
        
        generator = PRBodyGenerator(tmp_path)
        # Should prioritize pull_request_template.md over others
        result = generator.detect_pr_template()
        assert result == "lowercase template"
    
    def test_aggregate_context_success(self, tmp_path):
        """Test successful context aggregation."""
        generator = PRBodyGenerator(tmp_path)
        
        with patch('subprocess.run') as mock_run:
            def side_effect(*args, **kwargs):
                cmd = args[0] if isinstance(args[0], list) else [args[0]]
                cmd_str = ' '.join(cmd)
                if 'gh' in cmd and 'issue' in cmd and 'view' in cmd:
                    issue_data = {
                        "title": "Test Issue",
                        "body": "Test body",
                        "labels": [{"name": "bug"}]
                    }
                    return Mock(returncode=0, stdout=json.dumps(issue_data))
                elif 'git' in cmd and 'diff' in cmd and 'main...HEAD' in cmd_str:
                    return Mock(returncode=0, stdout="diff content")
                elif 'git' in cmd and 'log' in cmd and '--oneline' in cmd:
                    return Mock(returncode=0, stdout="abc123 Test commit")
                else:
                    return Mock(returncode=0, stdout="")
            
            mock_run.side_effect = side_effect
            
            context = generator.aggregate_context("123")
            
            assert "issue" in context
            assert context["issue"]["title"] == "Test Issue"
            assert context["diff"] == "diff content"
            assert context["commits"] == "abc123 Test commit"
    
    def test_aggregate_context_failure(self, tmp_path):
        """Test context aggregation with command failures."""
        generator = PRBodyGenerator(tmp_path)
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Command failed")
            
            context = generator.aggregate_context("123")
            
            # Should handle failures gracefully
            assert context["issue"]["title"] == "Unknown Issue"
            assert context["diff"] == ""
            assert context["commits"] == ""
    
    def test_generate_fallback_body(self, tmp_path):
        """Test fallback body generation."""
        generator = PRBodyGenerator(tmp_path)
        
        context = {
            "issue": {
                "title": "Test Issue",
                "body": "Test description"
            }
        }
        
        result = generator._generate_fallback_body(context)
        
        assert "## Summary" in result
        assert "Test Issue" in result
        assert "Test description" in result
        assert "## Changes Made" in result
        assert "## Testing" in result
    
    @patch('subprocess.run')
    def test_generate_with_llm_tool_available(self, mock_run, tmp_path):
        """Test PR generation with LLM tool available."""
        generator = PRBodyGenerator(tmp_path)
        
        def side_effect(*args, **kwargs):
            cmd = args[0] if isinstance(args[0], list) else [args[0]]
            cmd_str = ' '.join(cmd)
            if 'command' in cmd and 'llm' in cmd:
                return Mock(returncode=0, stdout="/usr/bin/llm")
            elif 'llm' in cmd and 'chat' in cmd:
                return Mock(returncode=0, stdout="Generated PR body")
            else:
                return Mock(returncode=0, stdout="")
        
        mock_run.side_effect = side_effect
        
        context = {"issue": {"title": "Test"}}
        result = generator.generate_with_llm(context)
        
        assert result == "Generated PR body"
    
    @patch('subprocess.run')
    def test_generate_with_claude_fallback(self, mock_run, tmp_path):
        """Test PR generation falling back to Claude."""
        generator = PRBodyGenerator(tmp_path)
        
        def side_effect(*args, **kwargs):
            cmd = args[0] if isinstance(args[0], list) else [args[0]]
            cmd_str = ' '.join(cmd)
            if 'command' in cmd and 'llm' in cmd:
                return Mock(returncode=1, stderr="llm not found")
            elif 'claude' in cmd:
                return Mock(returncode=0, stdout="Claude generated body")
            else:
                return Mock(returncode=0, stdout="")
        
        mock_run.side_effect = side_effect
        
        context = {"issue": {"title": "Test"}}
        result = generator.generate_with_llm(context)
        
        assert result == "Claude generated body"


class TestWorkflowLogicImplementation:
    """Test WorkflowLogic Python implementation."""
    
    def test_init(self, tmp_path):
        """Test WorkflowLogic initialization."""
        workflow = WorkflowLogic(tmp_path)
        assert workflow.repo_path == tmp_path
        assert workflow.agents_dir == tmp_path / ".claude" / "agents"
        assert isinstance(workflow.pr_body_generator, PRBodyGenerator)
    
    def test_get_issue_context_success(self, tmp_path):
        """Test successful issue context retrieval."""
        workflow = WorkflowLogic(tmp_path)
        
        with patch('subprocess.run') as mock_run:
            issue_data = {
                "title": "Test Issue",
                "body": "Test body",
                "labels": [{"name": "bug"}],
                "assignees": []
            }
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(issue_data)
            )
            
            result = workflow._get_issue_context("123")
            
            assert result == issue_data
    
    def test_get_issue_context_failure(self, tmp_path):
        """Test issue context retrieval failure."""
        workflow = WorkflowLogic(tmp_path)
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Command failed")
            
            result = workflow._get_issue_context("123")
            
            assert result["title"] == "Unknown Issue"
            assert result["body"] == "Unable to fetch issue details"
    
    def test_select_agent_exists(self, tmp_path):
        """Test agent selection when agent file exists."""
        workflow = WorkflowLogic(tmp_path)
        
        # Create agent file
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "github-issue-implementer.md"
        agent_content = "# GitHub Issue Implementer\nAgent content"
        agent_file.write_text(agent_content)
        
        result = workflow._select_agent("issue")
        
        assert result == agent_content
    
    def test_select_agent_not_exists(self, tmp_path):
        """Test agent selection when agent file doesn't exist."""
        workflow = WorkflowLogic(tmp_path)
        
        result = workflow._select_agent("issue")
        
        assert result is None
    
    def test_build_4d_instructions(self, tmp_path):
        """Test 4-D methodology instructions building."""
        workflow = WorkflowLogic(tmp_path)
        
        result = workflow._build_4d_instructions()
        
        expected_keys = ["DECONSTRUCT", "DIAGNOSE", "DEVELOP", "DELIVER"]
        assert all(key in result for key in expected_keys)
        assert "Analyze the task requirements" in result["DECONSTRUCT"]
    
    def test_verify_completion_status(self, tmp_path):
        """Test completion status verification."""
        workflow = WorkflowLogic(tmp_path)
        
        with patch.object(workflow, '_get_issue_context') as mock_context:
            mock_context.return_value = {
                "title": "Test Issue - COMPLETED",
                "body": "This work is completed",
                "labels": [{"name": "completed"}]
            }
            
            result = workflow.verify_completion_status("123")
            
            assert result["claims_completion"] is True
            assert result["title_indicates_completion"] is True
            assert result["labels_indicate_completion"] is True
    
    def test_create_timestamped_branch_success(self, tmp_path):
        """Test successful timestamped branch creation."""
        workflow = WorkflowLogic(tmp_path)
        
        with patch('subprocess.run') as mock_run, \
             patch('time.time', return_value=1234567890):
            
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Switched to branch",
                stderr=""
            )
            
            result = workflow.create_timestamped_branch("123")
            
            assert result["branch_name"] == "issue-123-1234567890"
            assert result["success"] is True
    
    def test_create_timestamped_branch_failure(self, tmp_path):
        """Test failed timestamped branch creation."""
        workflow = WorkflowLogic(tmp_path)
        
        with patch('subprocess.run') as mock_run, \
             patch('time.time', return_value=1234567890):
            
            mock_run.side_effect = Exception("Git command failed")
            
            result = workflow.create_timestamped_branch("123")
            
            assert result["branch_name"] == "issue-123-1234567890"
            assert result["success"] is False
            assert "Git command failed" in result["error"]
    
    def test_generate_meta_prompt(self, tmp_path):
        """Test meta-prompt generation."""
        workflow = WorkflowLogic(tmp_path)
        
        with patch.object(workflow, '_get_issue_context') as mock_context, \
             patch.object(workflow, '_select_agent') as mock_agent:
            
            mock_context.return_value = {"title": "Test Issue"}
            mock_agent.return_value = "Agent content"
            
            result = workflow.generate_meta_prompt("123", "issue")
            
            assert result["mode"] == "issue"
            assert result["issue_number"] == "123"
            assert result["framework"] == "lyra-dev-4d"
            assert "DECONSTRUCT" in result["instructions"]
    
    @patch('subprocess.run')
    def test_handle_exponential_backoff_success(self, mock_run, tmp_path):
        """Test exponential backoff with eventual success."""
        workflow = WorkflowLogic(tmp_path)
        
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Return subprocess.CompletedProcess with string stderr
                return subprocess.CompletedProcess(args[0], 1, "", "API rate limit exceeded")
            else:
                return subprocess.CompletedProcess(args[0], 0, "Success", "")
        
        mock_run.side_effect = side_effect
        
        with patch('time.sleep'):  # Mock sleep for testing
            result = workflow.handle_exponential_backoff(["gh", "issue", "view", "123"])
        
        assert result.returncode == 0
        assert result.stdout == "Success"
        assert call_count == 3
    
    def test_execute_two_stage_workflow(self, tmp_path):
        """Test two-stage workflow execution."""
        workflow = WorkflowLogic(tmp_path)
        
        with patch.object(workflow, 'generate_meta_prompt') as mock_meta, \
             patch.object(workflow, 'execute_with_claude') as mock_execute:
            
            mock_meta.return_value = {"test": "meta_prompt"}
            mock_execute.return_value = {"test": "execution_result"}
            
            result = workflow.execute_two_stage_workflow("123", "issue")
            
            assert result["meta_prompt"] == {"test": "meta_prompt"}
            assert result["execution_result"] == {"test": "execution_result"}
            assert result["mode"] == "issue"
            assert result["issue_number"] == "123"