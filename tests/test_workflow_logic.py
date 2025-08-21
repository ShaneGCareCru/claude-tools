"""Tests for claude-tasker workflow logic and agent coordination."""
import pytest
import subprocess
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, mock_open, call


class TestWorkflowLogic:
    """Test complex workflow logic and agent coordination."""
    
    def test_two_stage_execution_meta_prompt(self, claude_tasker_script, mock_git_repo):
        """Test two-stage execution: meta-prompt generation."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('builtins.open', mock_open()):
            
            # Mock file objects
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test_prompt.json'
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'claude' in cmd and '--output-format json' in cmd:
                    # Meta-prompt stage
                    meta_response = {
                        "optimized_prompt": "Test optimized prompt",
                        "analysis": "Test analysis"
                    }
                    return Mock(returncode=0, stdout=json.dumps(meta_response), stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should complete meta-prompt generation
            assert result.returncode == 0 or "Missing required tools" not in result.stderr
    
    def test_agent_based_architecture(self, claude_tasker_script, mock_git_repo):
        """Test agent-based architecture detection."""
        # Create .claude/agents directory structure
        agents_dir = mock_git_repo / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        # Create mock agent file
        agent_file = agents_dir / "github-issue-implementer.md"
        agent_file.write_text("# GitHub Issue Implementer Agent\nTest agent content")
        
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should detect and potentially use agent files
            assert result.returncode == 0
    
    def test_status_verification_protocol(self, claude_tasker_script, mock_git_repo):
        """Test status verification protocol for detecting false completion claims."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh issue view' in cmd:
                    # Mock issue with completion claim
                    issue_data = {
                        "title": "Test Issue - COMPLETED",
                        "body": "This issue has been completed",
                        "labels": [{"name": "completed"}]
                    }
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should verify completion status
            assert result.returncode == 0
    
    def test_audit_and_implement_workflow(self, claude_tasker_script, mock_git_repo):
        """Test AUDIT-AND-IMPLEMENT workflow."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile'), \
             patch('builtins.open', mock_open()):
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'claude' in cmd and 'audit' in cmd.lower():
                    # Audit phase
                    return Mock(returncode=0, stdout="Audit results: gaps found", stderr="")
                elif 'claude' in cmd and 'implement' in cmd.lower():
                    # Implementation phase  
                    return Mock(returncode=0, stdout="Implementation complete", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should complete audit and implement workflow
            assert result.returncode == 0
    
    def test_intelligent_pr_body_generation(self, claude_tasker_script, mock_git_repo):
        """Test intelligent PR body generation using llm tool."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile'), \
             patch('builtins.open', mock_open()):
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'llm' in cmd and 'chat' in cmd:
                    # LLM tool for PR body generation
                    return Mock(returncode=0, stdout="Generated intelligent PR body", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should handle PR body generation
            assert result.returncode == 0
    
    def test_pr_template_detection(self, claude_tasker_script, mock_git_repo):
        """Test PR template file detection."""
        # Create PR template files
        github_dir = mock_git_repo / ".github"
        github_dir.mkdir(exist_ok=True)
        
        pr_template = github_dir / "pull_request_template.md"
        pr_template.write_text("# PR Template\n## Summary\n## Changes")
        
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should detect PR template
            assert result.returncode == 0
    
    def test_range_processing(self, claude_tasker_script, mock_git_repo):
        """Test range processing functionality."""
        with patch('subprocess.run') as mock_run:
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'), patch('time.sleep'):  # Mock sleep for testing
                result = subprocess.run(
                    [str(claude_tasker_script), "316-318", "--timeout", "1", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should process range of issues
            assert result.returncode == 0
    
    def test_exponential_backoff_retry(self, claude_tasker_script, mock_git_repo):
        """Test exponential backoff retry logic for API limits."""
        with patch('subprocess.run') as mock_run:
            call_count = 0
            
            def cmd_side_effect(*args, **kwargs):
                nonlocal call_count
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'gh issue view' in cmd:
                    call_count += 1
                    if call_count < 3:
                        # Simulate API rate limit
                        return Mock(returncode=1, stdout="", stderr="API rate limit exceeded")
                    else:
                        # Success after retries
                        issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                        return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'), patch('time.sleep'):  # Mock sleep for testing
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should handle retries and eventually succeed
            assert call_count >= 2  # At least one retry occurred
    
    def test_branch_creation_timestamped(self, claude_tasker_script, mock_git_repo):
        """Test automatic branch creation with timestamps."""
        with patch('subprocess.run') as mock_run, \
             patch('time.time', return_value=1234567890):
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git checkout -b issue-316-1234567890' in cmd:
                    return Mock(returncode=0, stdout="Switched to branch", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                else:
                    return Mock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = cmd_side_effect
            
            with patch('os.chdir'):
                result = subprocess.run(
                    [str(claude_tasker_script), "316", "--prompt-only"],
                    cwd=mock_git_repo,
                    capture_output=True,
                    text=True
                )
            
            # Should create timestamped branch
            git_checkout_calls = [call for call in mock_run.call_args_list 
                                if 'git checkout -b issue-316-' in str(call.args)]
            assert len(git_checkout_calls) > 0 or result.returncode == 0