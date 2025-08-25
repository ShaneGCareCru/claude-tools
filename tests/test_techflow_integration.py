"""
Integration tests for TechFlow test framework.

This module tests the complete TechFlow testing framework to ensure
all components work together properly.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from tests.techflow import TechFlowTestRunner, TestConfig
from tests.techflow.test_runner import TestRun, TestArtifact, TestFailure


class TestTechFlowIntegration:
    """Integration tests for the TechFlow framework."""
    
    def test_config_from_environment(self):
        """Test configuration creation from environment variables."""
        with patch.dict(os.environ, {
            'TEST_MAX_RETRIES': '5',
            'TEST_TIMEOUT_SECONDS': '1200',
            'CLAUDE_BRANCH_STRATEGY': 'always_new',
            'CLAUDE_LOG_LEVEL': 'DEBUG'
        }):
            config = TestConfig.from_environment()
            
            assert config.max_retries == 5
            assert config.timeout_seconds == 1200
            assert config.branch_strategy == 'always_new'
            assert config.log_level == 'DEBUG'
    
    def test_config_validation_success(self):
        """Test successful configuration validation."""
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
                f.write('#!/usr/bin/env python\nprint("test")\n')
                temp_cli = f.name
            
            try:
                os.chmod(temp_cli, 0o755)
                config = TestConfig(cli_path=temp_cli)
                errors = config.validate()
                assert len(errors) == 0
            finally:
                os.unlink(temp_cli)
    
    def test_config_validation_errors(self):
        """Test configuration validation with errors."""
        config = TestConfig(
            cli_path='/nonexistent/path',
            timeout_seconds=30,
            max_retries=0
        )
        
        with patch.dict(os.environ, {}, clear=True):
            errors = config.validate()
            
            assert len(errors) >= 3  # Missing token, bad path, bad timeout, bad retries
            assert any('GITHUB_TOKEN' in error for error in errors)
            assert any('CLI path does not exist' in error for error in errors)
            assert any('Timeout must be at least 60' in error for error in errors)
            assert any('Max retries must be at least 1' in error for error in errors)
    
    def test_test_runner_initialization(self):
        """Test TechFlowTestRunner initialization."""
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
                f.write('#!/usr/bin/env python\nprint("test")\n')
                temp_cli = f.name
            
            try:
                os.chmod(temp_cli, 0o755)
                config = TestConfig(cli_path=temp_cli)
                runner = TechFlowTestRunner(config)
                
                assert runner.config == config
                assert runner.cli.cli_path == temp_cli
                assert runner.validators is not None
                assert runner.diagnostics is not None
                assert runner.evidence is not None
                
            finally:
                os.unlink(temp_cli)
    
    def test_test_runner_invalid_config(self):
        """Test TechFlowTestRunner with invalid configuration."""
        config = TestConfig(cli_path='/nonexistent/path')
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Configuration errors"):
                TechFlowTestRunner(config)
    
    def test_test_artifact_creation(self):
        """Test TestArtifact creation and properties."""
        artifact = TestArtifact(
            artifact_type="issue",
            identifier="123",
            url="https://github.com/test/repo/issues/123",
            content="Test issue content",
            metadata={'branch': 'test-branch'}
        )
        
        assert artifact.artifact_type == "issue"
        assert artifact.identifier == "123"
        assert artifact.url == "https://github.com/test/repo/issues/123"
        assert artifact.content == "Test issue content"
        assert artifact.metadata['branch'] == 'test-branch'
        assert artifact.created_at is not None
    
    def test_test_failure_creation(self):
        """Test TestFailure creation and properties."""
        failure = TestFailure(
            stage="bug_creation",
            failure_type="cli_execution_failed",
            message="Command failed",
            details="Error details here"
        )
        
        assert failure.stage == "bug_creation"
        assert failure.failure_type == "cli_execution_failed"
        assert failure.message == "Command failed"
        assert failure.details == "Error details here"
        assert failure.timestamp is not None
    
    def test_test_run_artifact_management(self):
        """Test TestRun artifact management."""
        run = TestRun()
        
        artifact = TestArtifact(
            artifact_type="issue",
            identifier="123"
        )
        
        run.add_artifact(artifact)
        assert len(run.artifacts) == 1
        assert run.artifacts[0] == artifact
    
    def test_test_run_failure_management(self):
        """Test TestRun failure management."""
        run = TestRun()
        assert run.success is False  # Default
        
        failure = TestFailure(
            stage="test",
            failure_type="test_error",
            message="Test error"
        )
        
        run.add_failure(failure)
        assert len(run.failures) == 1
        assert run.failures[0] == failure
        assert run.success is False  # Should remain False after adding failure
    
    def test_test_run_logging(self):
        """Test TestRun log management."""
        run = TestRun()
        
        run.add_log("Test message", "INFO")
        run.add_log("Debug message", "DEBUG")
        
        assert len(run.logs) == 2
        assert "INFO: Test message" in run.logs[0]
        assert "DEBUG: Debug message" in run.logs[1]
    
    def test_cli_command_wrapper(self):
        """Test CLICommandWrapper execution."""
        from tests.techflow.test_runner import CLICommandWrapper
        
        # Test successful command
        wrapper = CLICommandWrapper('/bin/echo', timeout=10)
        result = wrapper.execute_command(['hello', 'world'])
        
        assert result['success'] is True
        assert result['returncode'] == 0
        assert 'hello world' in result['stdout']
        assert result['execution_time'] > 0
    
    def test_cli_command_wrapper_failure(self):
        """Test CLICommandWrapper with failing command."""
        from tests.techflow.test_runner import CLICommandWrapper
        
        wrapper = CLICommandWrapper('/bin/false', timeout=10)
        result = wrapper.execute_command([])
        
        assert result['success'] is False
        assert result['returncode'] != 0
        assert result['execution_time'] > 0
    
    def test_cli_command_wrapper_nonexistent(self):
        """Test CLICommandWrapper with nonexistent command."""
        from tests.techflow.test_runner import CLICommandWrapper
        
        wrapper = CLICommandWrapper('/nonexistent/command', timeout=10)
        result = wrapper.execute_command([])
        
        assert result['success'] is False
        assert result['returncode'] == -1
        assert 'No such file' in result['stderr'] or 'not found' in result['stderr'].lower()
    
    @pytest.mark.parametrize("test_case,expected", [
        # Issue parsing test cases
        ("Created issue #123", 123),
        ("Issue #456 was created", 456),
        ("See issue #789 for details", 789),
        ("#999 is the issue number", 999),
        ("No issue number here", None),
        ("", None),
    ])
    def test_issue_number_parsing(self, test_case, expected):
        """Test issue number parsing from CLI output."""
        from tests.techflow.test_runner import TechFlowTestRunner
        from tests.techflow.config import TestConfig
        
        config = TestConfig()
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
                f.write('#!/usr/bin/env python\n')
                temp_cli = f.name
            
            try:
                config.cli_path = temp_cli
                runner = TechFlowTestRunner(config)
                result = runner._parse_issue_number(test_case)
                assert result == expected
            finally:
                os.unlink(temp_cli)
    
    @pytest.mark.parametrize("test_case,expected", [
        # PR parsing test cases
        ("Created pull request #123", 123),
        ("PR #456 is ready", 456),
        ("Pull Request #789", 789),
        ("https://github.com/user/repo/pull/999", 999),
        ("No PR number here", None),
        ("", None),
    ])
    def test_pr_number_parsing(self, test_case, expected):
        """Test PR number parsing from CLI output."""
        from tests.techflow.test_runner import TechFlowTestRunner
        from tests.techflow.config import TestConfig
        
        config = TestConfig()
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
                f.write('#!/usr/bin/env python\n')
                temp_cli = f.name
            
            try:
                config.cli_path = temp_cli
                runner = TechFlowTestRunner(config)
                result = runner._parse_pr_number(test_case)
                assert result == expected
            finally:
                os.unlink(temp_cli)
    
    @pytest.mark.parametrize("test_case,expected", [
        # Branch parsing test cases
        ("Created branch: feature-123", "feature-123"),
        ("Branch: issue-456-789", "issue-456-789"),
        ("issue-999-1234567890", "issue-999-1234567890"),
        ("No branch info", None),
        ("", None),
    ])
    def test_branch_name_parsing(self, test_case, expected):
        """Test branch name parsing from CLI output."""
        from tests.techflow.test_runner import TechFlowTestRunner
        from tests.techflow.config import TestConfig
        
        config = TestConfig()
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
                f.write('#!/usr/bin/env python\n')
                temp_cli = f.name
            
            try:
                config.cli_path = temp_cli
                runner = TechFlowTestRunner(config)
                result = runner._parse_branch_name(test_case)
                assert result == expected
            finally:
                os.unlink(temp_cli)
    
    def test_evidence_collection_directory_creation(self):
        """Test that evidence collection creates necessary directories."""
        from tests.techflow.evidence import EvidenceCollector
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TestConfig(evidence_dir=temp_dir)
            collector = EvidenceCollector(config)
            
            assert Path(temp_dir).exists()
            assert collector.evidence_dir == Path(temp_dir)
    
    def test_bug_description_generation(self):
        """Test bug description generation."""
        from tests.techflow.test_runner import TechFlowTestRunner
        
        config = TestConfig()
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
                f.write('#!/usr/bin/env python\n')
                temp_cli = f.name
            
            try:
                config.cli_path = temp_cli
                runner = TechFlowTestRunner(config)
                description = runner._generate_test_bug_description()
                
                # Check that description contains required sections
                assert "Bug Description" in description
                assert "Reproduction Steps" in description
                assert "Expected Behavior" in description
                assert "Actual Behavior" in description
                assert "Acceptance Criteria" in description
                assert len(description) > 100  # Should be substantial
                
            finally:
                os.unlink(temp_cli)