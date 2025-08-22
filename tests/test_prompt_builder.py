"""Tests for claude-tasker prompt building and two-stage execution workflow."""
import pytest
import subprocess
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, mock_open


@pytest.mark.skip(reason="Prompt builder tests need updating for Python module - currently test bash script behavior")
class TestPromptBuilder:
    """Test prompt building and two-stage execution functionality."""
    
    def test_lyra_dev_framework_generation(self, claude_tasker_script, mock_git_repo):
        """Test generation of Lyra-Dev framework prompts."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('builtins.open', mock_open()):
            
            # Mock file objects
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test_prompt.json'
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'claude' in cmd and '--output-format json' in cmd:
                    # Meta-prompt stage response - Lyra-Dev framework
                    lyra_response = {
                        "optimized_prompt": "# Lyra-Dev: Claude-Compatible Prompt Optimizer\\n\\nYou are **Lyra-Dev**, an elite AI prompt optimizer...",
                        "analysis": "Task requires implementation of test framework"
                    }
                    return Mock(returncode=0, stdout=json.dumps(lyra_response), stderr="")
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
            
            # Should complete without error and use Lyra-Dev framework
            assert result.returncode == 0
            # Verify Claude was called for meta-prompt generation
            claude_calls = [call for call in mock_run.call_args_list 
                           if 'claude' in str(call.args) and '--output-format json' in str(call.args)]
            assert len(claude_calls) > 0
    
    def test_two_stage_execution_pipeline(self, claude_tasker_script, mock_git_repo):
        """Test complete two-stage execution: meta-prompt → optimized prompt → execution."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('builtins.open', mock_open()):
            
            # Mock file objects for intermediate files
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test_prompt.json'
            
            stage = 0
            
            def cmd_side_effect(*args, **kwargs):
                nonlocal stage
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'claude' in cmd and '--output-format json' in cmd:
                    stage += 1
                    if stage == 1:
                        # Stage 1: Meta-prompt generation (prompt builder)
                        meta_response = {
                            "optimized_prompt": "Optimized implementation prompt for Claude execution",
                            "analysis": "Gap analysis completed, implementation required"
                        }
                        return Mock(returncode=0, stdout=json.dumps(meta_response), stderr="")
                    else:
                        # Stage 2: Execution with optimized prompt
                        execution_response = {
                            "result": "Implementation completed successfully",
                            "changes": ["Added test framework", "Updated configuration"]
                        }
                        return Mock(returncode=0, stdout=json.dumps(execution_response), stderr="")
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
            
            # Should complete two-stage execution successfully
            assert result.returncode == 0
            # Verify both stages were executed
            assert stage == 2  # Both meta-prompt and execution stages called
    
    def test_prompt_optimization_with_llm_fallback(self, claude_tasker_script, mock_git_repo):
        """Test prompt optimization using LLM tool with Claude fallback."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('builtins.open', mock_open()):
            
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test_prompt.json'
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'command -v llm' in cmd:
                    # LLM tool is available
                    return Mock(returncode=0, stdout="/usr/bin/llm", stderr="")
                elif 'llm' in cmd and 'chat' in cmd:
                    # LLM tool for prompt optimization
                    return Mock(returncode=0, stdout="Optimized prompt using LLM tool", stderr="")
                elif 'claude' in cmd:
                    # Fallback to Claude execution
                    return Mock(returncode=0, stdout="Claude execution result", stderr="")
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
            
            # Should use LLM tool when available
            assert result.returncode == 0
            llm_calls = [call for call in mock_run.call_args_list 
                        if 'llm' in str(call.args)]
            assert len(llm_calls) > 0
    
    def test_json_extraction_and_processing(self, claude_tasker_script, mock_git_repo):
        """Test JSON extraction from Claude responses and text processing."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('builtins.open', mock_open()):
            
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test_prompt.json'
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'claude' in cmd and '--output-format json' in cmd:
                    # Valid JSON response from Claude
                    valid_json = {
                        "optimized_prompt": "Structured prompt content",
                        "analysis": "Detailed gap analysis",
                        "implementation_steps": ["Step 1", "Step 2", "Step 3"]
                    }
                    return Mock(returncode=0, stdout=json.dumps(valid_json), stderr="")
                elif 'jq' in cmd:
                    # JSON processing
                    return Mock(returncode=0, stdout="Extracted text content", stderr="")
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
            
            # Should process JSON successfully
            assert result.returncode == 0
            # Verify jq was used for JSON processing
            jq_calls = [call for call in mock_run.call_args_list 
                       if 'jq' in str(call.args)]
            assert len(jq_calls) > 0
    
    def test_meta_prompt_validation(self, claude_tasker_script, mock_git_repo):
        """Test validation that executor doesn't return another meta-prompt."""
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('builtins.open', mock_open()):
            
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test_prompt.json'
            
            def cmd_side_effect(*args, **kwargs):
                cmd = ' '.join(args[0]) if isinstance(args[0], list) else args[0]
                
                if 'git rev-parse --git-dir' in cmd:
                    return Mock(returncode=0, stdout=".git", stderr="")
                elif 'git config --get remote.origin.url' in cmd:
                    return Mock(returncode=0, stdout="https://github.com/test/repo.git", stderr="")
                elif 'gh issue view' in cmd:
                    issue_data = {"title": "Test Issue", "body": "Test", "labels": []}
                    return Mock(returncode=0, stdout=json.dumps(issue_data), stderr="")
                elif 'claude' in cmd and '--output-format json' in cmd:
                    # Meta-prompt stage
                    meta_response = {
                        "optimized_prompt": "Implementation prompt for execution",
                        "analysis": "Ready for execution"
                    }
                    return Mock(returncode=0, stdout=json.dumps(meta_response), stderr="")
                elif 'claude' in cmd:
                    # Executor stage - should NOT return another meta-prompt
                    return Mock(returncode=0, stdout="Implementation completed without meta-prompts", stderr="")
                elif 'grep' in cmd and 'OPTIMIZED PROMPT FOR CLAUDE' in cmd:
                    # Validation check for meta-prompt detection
                    return Mock(returncode=1, stdout="", stderr="")  # Not found = good
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
            
            # Should complete without meta-prompt loops
            assert result.returncode == 0
            # Verify meta-prompt validation occurred
            grep_calls = [call for call in mock_run.call_args_list 
                         if 'grep' in str(call.args) and 'OPTIMIZED PROMPT' in str(call.args)]
            assert len(grep_calls) > 0