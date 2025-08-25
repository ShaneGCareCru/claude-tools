"""
Comprehensive tests for TechFlow diagnostic and remediation system.

This module tests the diagnostic engine, triage matrix, and remediation
capabilities to ensure proper failure analysis and automated recovery.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from tests.techflow.config import TestConfig
from tests.techflow.test_runner import TestRun, TestFailure
from tests.techflow.diagnostics import DiagnosticEngine, TriageMatrix, RemediationEngine
from tests.techflow.diagnostics.engine import DiagnosticResult


class TestDiagnosticResult:
    """Test DiagnosticResult class."""
    
    def test_diagnostic_result_creation(self):
        """Test DiagnosticResult creation with defaults."""
        result = DiagnosticResult()
        
        assert result.primary_cause is None
        assert result.contributing_factors == []
        assert result.recommended_actions == []
        assert result.confidence_score == 0.0
        assert result.details == {}
    
    def test_diagnostic_result_with_data(self):
        """Test DiagnosticResult creation with data."""
        result = DiagnosticResult(
            primary_cause="auth_failure",
            contributing_factors=["rate_limit", "network_error"],
            recommended_actions=["check_github_token", "retry_with_backoff"],
            confidence_score=0.8,
            details={"attempts": 3}
        )
        
        assert result.primary_cause == "auth_failure"
        assert "rate_limit" in result.contributing_factors
        assert "check_github_token" in result.recommended_actions
        assert result.confidence_score == 0.8
        assert result.details["attempts"] == 3


class TestTriageMatrix:
    """Test TriageMatrix class."""
    
    def test_triage_matrix_creation(self):
        """Test TriageMatrix initialization."""
        triage = TriageMatrix()
        
        assert 'cli_execution_failed' in triage.triage_rules
        assert 'issue_parsing_failed' in triage.triage_rules
        assert 'quality_gate_failed' in triage.triage_rules
        assert len(triage.contributing_factors) > 0
    
    def test_analyze_failure_cli_timeout(self):
        """Test failure analysis for CLI timeout."""
        triage = TriageMatrix()
        
        failure = TestFailure(
            stage="bug_creation",
            failure_type="cli_execution_failed",
            message="Command timed out after 900 seconds",
            details="Process exceeded maximum execution time"
        )
        
        test_run = TestRun()
        result = triage.analyze_failure(failure, test_run)
        
        assert result['primary_cause'] == 'timeout'
        assert result['confidence'] > 0.7
        assert 'timed out' in result['evidence'][0].lower()
    
    def test_analyze_failure_auth_error(self):
        """Test failure analysis for authentication error."""
        triage = TriageMatrix()
        
        failure = TestFailure(
            stage="bug_creation",
            failure_type="cli_execution_failed",
            message="Authentication failed: Invalid credentials",
            details="GitHub API returned 401 Unauthorized"
        )
        
        test_run = TestRun()
        result = triage.analyze_failure(failure, test_run)
        
        assert result['primary_cause'] == 'auth_failure'
        assert result['confidence'] > 0.8
        assert len(result['evidence']) > 0
    
    def test_analyze_failure_rate_limit(self):
        """Test failure analysis for rate limiting."""
        triage = TriageMatrix()
        
        failure = TestFailure(
            stage="implementation",
            failure_type="cli_execution_failed",
            message="API rate limit exceeded",
            details="Too many requests in the last hour"
        )
        
        test_run = TestRun()
        result = triage.analyze_failure(failure, test_run)
        
        assert result['primary_cause'] == 'rate_limit'
        assert result['confidence'] > 0.7
    
    def test_analyze_failure_unknown_type(self):
        """Test failure analysis for unknown failure type."""
        triage = TriageMatrix()
        
        failure = TestFailure(
            stage="unknown",
            failure_type="unknown_failure_type",
            message="Something went wrong"
        )
        
        test_run = TestRun()
        result = triage.analyze_failure(failure, test_run)
        
        assert result['primary_cause'] == 'unknown_failure_type'
        assert result['confidence'] == 0.1
    
    def test_analyze_failure_no_pattern_match(self):
        """Test failure analysis when no patterns match."""
        triage = TriageMatrix()
        
        failure = TestFailure(
            stage="bug_creation",
            failure_type="cli_execution_failed",
            message="Unknown error occurred",
            details="No specific details available"
        )
        
        test_run = TestRun()
        result = triage.analyze_failure(failure, test_run)
        
        assert result['primary_cause'] == 'execution_environment'  # Default
        assert result['confidence'] == 0.3
    
    def test_identify_contributing_factors(self):
        """Test contributing factor identification."""
        triage = TriageMatrix()
        
        test_run = TestRun()
        test_run.retry_count = 3
        test_run.start_time = datetime.now(timezone.utc)
        test_run.end_time = datetime.now(timezone.utc)
        test_run.add_log("Rate limit exceeded")
        test_run.add_log("Environment configuration issue")
        
        # Manually set duration to trigger long execution factor
        from datetime import timedelta
        test_run.end_time = test_run.start_time + timedelta(seconds=700)
        
        failure_text = "rate limit api error"
        factors = triage._identify_contributing_factors(test_run, failure_text)
        
        assert 'high_retry_count' in factors
        assert 'api_issues' in factors
        assert 'long_execution_time' in factors
    
    def test_get_cause_description(self):
        """Test cause description retrieval."""
        triage = TriageMatrix()
        
        description = triage.get_cause_description('auth_failure')
        assert 'authentication failed' in description.lower()
        assert 'credentials' in description.lower()
        
        description = triage.get_cause_description('unknown_cause')
        assert 'unknown cause' in description.lower()


class TestRemediationEngine:
    """Test RemediationEngine class."""
    
    def test_remediation_engine_creation(self):
        """Test RemediationEngine initialization."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        assert engine.config == config
        assert 'timeout' in engine.remediation_strategies
        assert 'auth_failure' in engine.remediation_strategies
        assert 'rate_limit' in engine.remediation_strategies
    
    def test_get_recommendations_known_cause(self):
        """Test getting recommendations for known cause."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        recommendations = engine.get_recommendations('auth_failure', test_run, [])
        
        assert 'check_github_token' in recommendations
        assert 'refresh_credentials' in recommendations
        assert 'verify_permissions' in recommendations
    
    def test_get_recommendations_unknown_cause(self):
        """Test getting recommendations for unknown cause."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        recommendations = engine.get_recommendations('unknown_cause', test_run, [])
        
        assert 'manual_investigation_required' in recommendations
    
    def test_get_recommendations_with_retries(self):
        """Test getting recommendations when retries have occurred."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        test_run.retry_count = 2
        
        recommendations = engine.get_recommendations('timeout', test_run, [])
        
        assert 'consider_manual_intervention' in recommendations
    
    def test_apply_remediation_success(self):
        """Test successful remediation application."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        
        with patch.object(engine, '_apply_single_action', return_value=True) as mock_apply:
            success = engine.apply_remediation('timeout', ['increase_timeout'], test_run)
            
            assert success is True
            mock_apply.assert_called_once_with('increase_timeout', test_run)
    
    def test_apply_remediation_failure(self):
        """Test failed remediation application."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        
        with patch.object(engine, '_apply_single_action', return_value=False) as mock_apply:
            success = engine.apply_remediation('timeout', ['increase_timeout'], test_run)
            
            assert success is False
            mock_apply.assert_called_once_with('increase_timeout', test_run)
    
    def test_apply_remediation_exception(self):
        """Test remediation application with exception."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        
        with patch.object(engine, '_apply_single_action', side_effect=Exception("Test error")):
            success = engine.apply_remediation('timeout', ['increase_timeout'], test_run)
            
            assert success is False
            assert len(test_run.logs) > 0
    
    def test_increase_timeout(self):
        """Test timeout increase remediation."""
        config = TestConfig(timeout_seconds=900)
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        success = engine._increase_timeout(test_run)
        
        assert success is True
        assert config.timeout_seconds > 900
        assert config.timeout_seconds <= 1800  # Max limit
    
    def test_retry_with_backoff(self):
        """Test retry with backoff remediation."""
        config = TestConfig(backoff_factor=2.0)
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        test_run.retry_count = 2
        
        start_time = time.time()
        success = engine._retry_with_backoff(test_run)
        end_time = time.time()
        
        assert success is True
        # Should have applied some delay (less than max)
        assert end_time - start_time > 0
        assert end_time - start_time <= 60  # Max delay cap
    
    @patch.dict('os.environ', {'GITHUB_TOKEN': 'ghp_test12345678901234567890123456789012'})
    def test_check_github_token_valid(self):
        """Test GitHub token validation with valid token."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        success = engine._check_github_token(test_run)
        
        assert success is True
        assert len(test_run.logs) > 0
        assert 'valid' in test_run.logs[-1]
    
    @patch.dict('os.environ', {}, clear=True)
    def test_check_github_token_missing(self):
        """Test GitHub token validation with missing token."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        success = engine._check_github_token(test_run)
        
        assert success is False
        assert any('not set' in log for log in test_run.logs)
    
    @patch.dict('os.environ', {'GITHUB_TOKEN': 'invalid_token_format'})
    def test_check_github_token_invalid_format(self):
        """Test GitHub token validation with invalid format."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        success = engine._check_github_token(test_run)
        
        assert success is False
        assert any('invalid' in log for log in test_run.logs)
    
    def test_apply_exponential_backoff(self):
        """Test exponential backoff for rate limiting."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        test_run.retry_count = 1
        
        start_time = time.time()
        success = engine._apply_exponential_backoff(test_run)
        end_time = time.time()
        
        assert success is True
        # Should have applied backoff delay
        assert end_time - start_time > 0
    
    @patch('subprocess.run')
    def test_verify_cli_installation_success(self, mock_run):
        """Test CLI installation verification with all tools present."""
        config = TestConfig(cli_path='./test-cli')
        engine = RemediationEngine(config)
        
        # Mock successful tool checks
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        test_run = TestRun()
        success = engine._verify_cli_installation(test_run)
        
        assert success is True
        assert mock_run.call_count >= 3  # gh, claude-tasker, git
    
    @patch('subprocess.run')
    def test_verify_cli_installation_failure(self, mock_run):
        """Test CLI installation verification with missing tools."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        # Mock failed tool checks
        mock_run.side_effect = FileNotFoundError("Command not found")
        
        test_run = TestRun()
        success = engine._verify_cli_installation(test_run)
        
        assert success is False
        assert any('not found' in log for log in test_run.logs)
    
    def test_create_new_branch(self):
        """Test branch strategy change remediation."""
        config = TestConfig(branch_strategy='reuse')
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        success = engine._create_new_branch(test_run)
        
        assert success is True
        assert config.branch_strategy == 'always_new'
        assert 'always_new' in test_run.logs[-1]
    
    def test_reset_workflow_state(self):
        """Test workflow state reset remediation."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        test_run.issue_num = 123
        test_run.pr_num = 456
        test_run.branch_name = 'test-branch'
        
        success = engine._reset_workflow_state(test_run)
        
        assert success is True
        assert test_run.issue_num is None
        assert test_run.pr_num is None
        assert test_run.branch_name is None
    
    def test_apply_generic_action(self):
        """Test generic remediation action application."""
        config = TestConfig()
        engine = RemediationEngine(config)
        
        test_run = TestRun()
        success = engine._apply_generic_action('manual_investigation_required', test_run)
        
        assert success is True
        assert 'Manual investigation required' in test_run.logs[-1]


class TestDiagnosticEngine:
    """Test DiagnosticEngine class."""
    
    def test_diagnostic_engine_creation(self):
        """Test DiagnosticEngine initialization."""
        config = TestConfig()
        engine = DiagnosticEngine(config)
        
        assert engine.config == config
        assert engine.triage is not None
        assert engine.remediation is not None
    
    def test_diagnose_failure_success(self):
        """Test successful failure diagnosis."""
        config = TestConfig()
        engine = DiagnosticEngine(config)
        
        test_run = TestRun()
        failure = TestFailure(
            stage="bug_creation",
            failure_type="cli_execution_failed",
            message="Authentication failed"
        )
        test_run.add_failure(failure)
        
        with patch.object(engine.triage, 'analyze_failure') as mock_analyze:
            mock_analyze.return_value = {
                'primary_cause': 'auth_failure',
                'contributing_factors': ['rate_limit'],
                'confidence': 0.8,
                'evidence': ['auth pattern found']
            }
            
            with patch.object(engine.remediation, 'get_recommendations') as mock_remediation:
                mock_remediation.return_value = ['check_github_token']
                
                result = engine.diagnose_failure(test_run, 'bug_creation')
                
                assert result.primary_cause == 'auth_failure'
                assert result.confidence_score == 0.8
                assert 'check_github_token' in result.recommended_actions
                assert 'rate_limit' in result.contributing_factors
    
    def test_diagnose_failure_no_failures(self):
        """Test diagnosis when no failures exist for stage."""
        config = TestConfig()
        engine = DiagnosticEngine(config)
        
        test_run = TestRun()
        result = engine.diagnose_failure(test_run, 'nonexistent_stage')
        
        assert result.primary_cause == 'unknown'
        assert result.confidence_score == 0.1
    
    def test_diagnose_failure_exception(self):
        """Test diagnosis with exception during analysis."""
        config = TestConfig()
        engine = DiagnosticEngine(config)
        
        test_run = TestRun()
        failure = TestFailure(stage="test", failure_type="test", message="test")
        test_run.add_failure(failure)
        
        with patch.object(engine.triage, 'analyze_failure', side_effect=Exception("Test error")):
            result = engine.diagnose_failure(test_run, 'test')
            
            assert result.primary_cause == 'diagnostic_error'
            assert 'error' in result.details
    
    def test_try_remediation_success(self):
        """Test successful remediation attempt."""
        config = TestConfig()
        engine = DiagnosticEngine(config)
        
        test_run = TestRun()
        failure = TestFailure(stage="test", failure_type="test", message="test")
        test_run.add_failure(failure)
        
        with patch.object(engine, 'diagnose_failure') as mock_diagnose:
            mock_diagnose.return_value = DiagnosticResult(
                primary_cause='auth_failure',
                recommended_actions=['check_github_token']
            )
            
            with patch.object(engine.remediation, 'apply_remediation', return_value=True) as mock_apply:
                success = engine.try_remediation(test_run, 'test')
                
                assert success is True
                mock_apply.assert_called_once()
    
    def test_try_remediation_no_actions(self):
        """Test remediation when no actions available."""
        config = TestConfig()
        engine = DiagnosticEngine(config)
        
        test_run = TestRun()
        
        with patch.object(engine, 'diagnose_failure') as mock_diagnose:
            mock_diagnose.return_value = DiagnosticResult(
                primary_cause='unknown',
                recommended_actions=[]
            )
            
            success = engine.try_remediation(test_run, 'test')
            
            assert success is False
    
    def test_generate_diagnostic_report(self):
        """Test diagnostic report generation."""
        config = TestConfig()
        engine = DiagnosticEngine(config)
        
        test_run = TestRun()
        test_run.success = False
        test_run.quality_score = 2.5
        test_run.retry_count = 1
        
        failure = TestFailure(stage="test", failure_type="test_error", message="Test failed")
        test_run.add_failure(failure)
        
        with patch.object(engine, 'diagnose_failure') as mock_diagnose:
            mock_diagnose.return_value = DiagnosticResult(
                primary_cause='test_failure',
                confidence_score=0.9
            )
            
            report = engine.generate_diagnostic_report(test_run)
            
            assert report['overall_status'] == 'failed'
            assert report['quality_score'] == 2.5
            assert report['retry_count'] == 1
            assert len(report['diagnoses']) == 1
            assert report['diagnoses'][0]['stage'] == 'test'
            assert 'overall_recommendations' in report
    
    def test_generate_overall_recommendations(self):
        """Test overall recommendation generation."""
        config = TestConfig()
        engine = DiagnosticEngine(config)
        
        test_run = TestRun()
        test_run.retry_count = 3
        
        # Add multiple CLI execution failures
        for i in range(3):
            failure = TestFailure(
                stage=f"stage_{i}",
                failure_type="cli_execution_failed",
                message=f"CLI failed {i}"
            )
            test_run.add_failure(failure)
        
        recommendations = engine._generate_overall_recommendations(test_run)
        
        assert any('Multiple CLI execution failures' in rec for rec in recommendations)
        assert any('High retry count' in rec for rec in recommendations)
        assert len(recommendations) > 1