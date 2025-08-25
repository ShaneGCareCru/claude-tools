"""
Comprehensive tests for TechFlow evidence collection and reporting system.

This module tests the evidence collection, report generation, and
template rendering capabilities of the framework.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from tests.techflow.config import TestConfig
from tests.techflow.test_runner import TestRun, TestArtifact, TestFailure
from tests.techflow.evidence import EvidenceCollector, ReportGenerator, ReportTemplates


class TestEvidenceCollector:
    """Test EvidenceCollector class."""
    
    def test_evidence_collector_creation(self):
        """Test EvidenceCollector initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TestConfig(evidence_dir=temp_dir)
            collector = EvidenceCollector(config)
            
            assert collector.config == config
            assert collector.evidence_dir == Path(temp_dir)
            assert collector.evidence_dir.exists()
            assert collector.reporter is not None
    
    def test_collect_run_summary_complete(self):
        """Test complete run summary collection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TestConfig(evidence_dir=temp_dir)
            collector = EvidenceCollector(config)
            
            # Create a test run with all components
            test_run = TestRun()
            test_run.run_id = "test123"
            test_run.success = True
            test_run.quality_score = 4.2
            test_run.issue_num = 456
            test_run.pr_num = 789
            test_run.branch_name = "test-branch"
            test_run.config = config
            test_run.end_time = datetime.now(timezone.utc)
            
            # Add artifacts
            test_run.add_artifact(TestArtifact(
                artifact_type="issue",
                identifier="456",
                url="https://github.com/test/repo/issues/456"
            ))
            
            # Add failures
            test_run.add_failure(TestFailure(
                stage="test",
                failure_type="test_error",
                message="Test failure"
            ))
            
            # Add logs
            test_run.add_log("Test log entry")
            
            # Collect evidence
            run_dir = collector.collect_run_summary(test_run)
            
            # Verify directory structure
            assert run_dir.exists()
            assert run_dir.name == f"run-{test_run.run_id}"
            assert (run_dir / "run_data.json").exists()
            assert (run_dir / "artifacts").exists()
            assert (run_dir / "reports").exists()
            assert (run_dir / "test_run.log").exists()
    
    def test_save_run_data(self):
        """Test run data JSON serialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TestConfig(evidence_dir=temp_dir)
            collector = EvidenceCollector(config)
            
            test_run = TestRun()
            test_run.run_id = "test456"
            test_run.success = False
            test_run.quality_score = 2.1
            test_run.config = config
            test_run.end_time = datetime.now(timezone.utc)
            
            test_file = Path(temp_dir) / "test_data.json"
            collector._save_run_data(test_run, test_file)
            
            # Verify file exists and contains expected data
            assert test_file.exists()
            
            with open(test_file) as f:
                data = json.load(f)
            
            assert data['run_id'] == "test456"
            assert data['success'] is False
            assert data['quality_score'] == 2.1
            assert 'start_time' in data
            assert 'config' in data
    
    def test_save_artifacts(self):
        """Test artifact serialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TestConfig(evidence_dir=temp_dir)
            collector = EvidenceCollector(config)
            
            test_run = TestRun()
            test_run.add_artifact(TestArtifact(
                artifact_type="issue",
                identifier="123",
                url="https://github.com/test/repo/issues/123",
                content="Issue content here",
                metadata={'priority': 'high'}
            ))
            
            artifacts_dir = Path(temp_dir) / "artifacts"
            artifacts_dir.mkdir()
            
            collector._save_artifacts(test_run, artifacts_dir)
            
            # Verify artifact file
            artifact_file = artifacts_dir / "issue_123.json"
            assert artifact_file.exists()
            
            with open(artifact_file) as f:
                data = json.load(f)
            
            assert data['type'] == 'issue'
            assert data['identifier'] == '123'
            assert data['url'] == 'https://github.com/test/repo/issues/123'
            assert data['content'] == 'Issue content here'
            assert data['metadata']['priority'] == 'high'
    
    def test_save_logs(self):
        """Test log file generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TestConfig(evidence_dir=temp_dir)
            collector = EvidenceCollector(config)
            
            test_run = TestRun()
            test_run.run_id = "test789"
            test_run.add_log("First log entry", "INFO")
            test_run.add_log("Second log entry", "DEBUG")
            test_run.add_log("Error occurred", "ERROR")
            
            logs_file = Path(temp_dir) / "test.log"
            collector._save_logs(test_run, logs_file)
            
            # Verify log file
            assert logs_file.exists()
            
            content = logs_file.read_text()
            assert "test789" in content
            assert "First log entry" in content
            assert "Second log entry" in content
            assert "Error occurred" in content
    
    @patch('subprocess.run')
    @patch('platform.system')
    @patch('platform.release')
    def test_collect_system_info(self, mock_release, mock_system, mock_run):
        """Test system information collection."""
        config = TestConfig()
        collector = EvidenceCollector(config)
        
        # Mock system information
        mock_system.return_value = "Linux"
        mock_release.return_value = "5.4.0"
        
        # Mock tool version checks
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "version 1.0.0"
        mock_run.return_value = mock_result
        
        with patch.dict('os.environ', {
            'GITHUB_TOKEN': 'ghp_test12345678901234567890123456789012',
            'CLAUDE_LOG_LEVEL': 'DEBUG'
        }):
            system_info = collector.collect_system_info()
            
            assert 'timestamp' in system_info
            assert system_info['platform']['system'] == 'Linux'
            assert system_info['platform']['release'] == '5.4.0'
            assert 'GITHUB_TOKEN' in system_info['environment']
            assert system_info['environment']['GITHUB_TOKEN'].endswith('***')
            assert system_info['environment']['CLAUDE_LOG_LEVEL'] == 'DEBUG'
            assert 'gh' in system_info['tools']
            assert 'git' in system_info['tools']


class TestReportGenerator:
    """Test ReportGenerator class."""
    
    def test_report_generator_creation(self):
        """Test ReportGenerator initialization."""
        config = TestConfig()
        generator = ReportGenerator(config)
        
        assert generator.config == config
        assert generator.templates is not None
    
    def test_generate_html_report(self):
        """Test HTML report generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TestConfig()
            generator = ReportGenerator(config)
            
            test_run = TestRun()
            test_run.success = True
            test_run.quality_score = 4.5
            test_run.config = config
            
            output_path = Path(temp_dir) / "report.html"
            generator.generate_html_report(test_run, output_path)
            
            assert output_path.exists()
            content = output_path.read_text()
            assert '<!DOCTYPE html>' in content
            assert 'TechFlow Test Report' in content
            assert '4.5' in content
    
    def test_generate_markdown_summary(self):
        """Test Markdown summary generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TestConfig()
            generator = ReportGenerator(config)
            
            test_run = TestRun()
            test_run.success = False
            test_run.quality_score = 2.3
            test_run.config = config
            
            output_path = Path(temp_dir) / "summary.md"
            generator.generate_markdown_summary(test_run, output_path)
            
            assert output_path.exists()
            content = output_path.read_text()
            assert '# TechFlow Test Report' in content
            assert '❌ FAILED' in content
            assert '2.3' in content
    
    def test_generate_json_summary(self):
        """Test JSON summary generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TestConfig()
            generator = ReportGenerator(config)
            
            test_run = TestRun()
            test_run.run_id = "test123"
            test_run.success = True
            test_run.config = config
            
            output_path = Path(temp_dir) / "summary.json"
            generator.generate_json_summary(test_run, output_path)
            
            assert output_path.exists()
            
            with open(output_path) as f:
                data = json.load(f)
            
            assert data['run_id'] == 'test123'
            assert data['success'] is True
            assert data['status'] == 'PASSED'
    
    def test_build_report_context_complete(self):
        """Test complete report context building."""
        config = TestConfig()
        generator = ReportGenerator(config)
        
        test_run = TestRun()
        test_run.run_id = "ctx123"
        test_run.success = True
        test_run.quality_score = 3.8
        test_run.retry_count = 1
        test_run.issue_num = 456
        test_run.pr_num = 789
        test_run.branch_name = "feature-branch"
        test_run.config = config
        test_run.start_time = datetime(2023, 12, 1, 10, 0, 0, tzinfo=timezone.utc)
        test_run.end_time = datetime(2023, 12, 1, 10, 5, 30, tzinfo=timezone.utc)
        
        # Add artifacts
        test_run.add_artifact(TestArtifact(
            artifact_type="pull_request",
            identifier="789",
            url="https://github.com/test/repo/pull/789"
        ))
        
        # Add failures
        test_run.add_failure(TestFailure(
            stage="review",
            failure_type="quality_gate_failed",
            message="Review quality insufficient"
        ))
        
        context = generator._build_report_context(test_run)
        
        assert context['run_id'] == 'ctx123'
        assert context['success'] is True
        assert context['status'] == 'PASSED'
        assert context['quality_score'] == 3.8
        assert context['duration'] == '330.0s'
        assert context['retry_count'] == 1
        assert context['issue_num'] == 456
        assert context['pr_num'] == 789
        assert context['branch_name'] == 'feature-branch'
        assert len(context['artifacts']) == 1
        assert len(context['failures']) == 1
        assert context['failure_count'] == 1
        assert 'config' in context
        assert 'quality_assessment' in context
        assert 'recommendations' in context
    
    def test_assess_quality_excellent(self):
        """Test quality assessment for excellent score."""
        config = TestConfig()
        generator = ReportGenerator(config)
        
        test_run = TestRun()
        test_run.quality_score = 4.8
        
        assessment = generator._assess_quality(test_run)
        
        assert assessment['score'] == 4.8
        assert assessment['grade'] == 'Excellent'
        assert assessment['color'] == 'green'
        assert assessment['max_score'] == 5.0
    
    def test_assess_quality_poor(self):
        """Test quality assessment for poor score."""
        config = TestConfig()
        generator = ReportGenerator(config)
        
        test_run = TestRun()
        test_run.quality_score = 1.5
        
        assessment = generator._assess_quality(test_run)
        
        assert assessment['score'] == 1.5
        assert assessment['grade'] == 'Poor'
        assert assessment['color'] == 'red'
    
    def test_generate_recommendations_success(self):
        """Test recommendation generation for successful run."""
        config = TestConfig()
        generator = ReportGenerator(config)
        
        test_run = TestRun()
        test_run.success = True
        test_run.quality_score = 4.0
        test_run.retry_count = 0
        test_run.start_time = datetime.now(timezone.utc)
        test_run.end_time = datetime.now(timezone.utc)
        
        recommendations = generator._generate_recommendations(test_run)
        
        assert "no action needed" in recommendations[0].lower()
    
    def test_generate_recommendations_failures(self):
        """Test recommendation generation for failed run."""
        config = TestConfig()
        generator = ReportGenerator(config)
        
        test_run = TestRun()
        test_run.success = False
        test_run.quality_score = 2.0
        test_run.retry_count = 3
        test_run.start_time = datetime.now(timezone.utc)
        test_run.end_time = test_run.start_time.replace(
            second=test_run.start_time.second + 700  # Long duration
        )
        
        # Add multiple failures
        test_run.add_failure(TestFailure(stage="bug_creation", failure_type="test", message="test"))
        test_run.add_failure(TestFailure(stage="implementation", failure_type="test", message="test"))
        test_run.add_failure(TestFailure(stage="validation", failure_type="test", message="test"))
        
        recommendations = generator._generate_recommendations(test_run)
        
        assert any("Investigation required" in rec for rec in recommendations)
        assert any("Quality score below" in rec for rec in recommendations)
        assert any("Retries occurred" in rec for rec in recommendations)
        assert any("Long execution time" in rec for rec in recommendations)
        assert any("Multiple failures" in rec for rec in recommendations)
        assert any("Bug creation issues" in rec for rec in recommendations)
        assert any("Implementation issues" in rec for rec in recommendations)
        assert any("Validation failures" in rec for rec in recommendations)


class TestReportTemplates:
    """Test ReportTemplates class."""
    
    def test_report_templates_creation(self):
        """Test ReportTemplates initialization."""
        templates = ReportTemplates()
        assert templates is not None
    
    def test_render_html_template_success(self):
        """Test HTML template rendering for successful run."""
        templates = ReportTemplates()
        
        context = {
            'run_id': 'test123',
            'timestamp': '2023-12-01 10:00:00 UTC',
            'success': True,
            'status': 'PASSED',
            'quality_score': 4.2,
            'quality_assessment': {'grade': 'Good', 'color': 'blue'},
            'duration': '120.5s',
            'retry_count': 0,
            'artifacts': [
                {
                    'type': 'Issue',
                    'identifier': '123',
                    'url': 'https://github.com/test/repo/issues/123',
                    'created': '10:00:00'
                }
            ],
            'failure_count': 0,
            'failures': [],
            'config': {
                'cli_path': './claude-tasker-py',
                'branch_strategy': 'reuse',
                'timeout': '900s',
                'max_retries': '3'
            },
            'recommendations': ['Test run completed successfully - no action needed']
        }
        
        html_content = templates.render_html_template(context)
        
        assert '<!DOCTYPE html>' in html_content
        assert 'test123' in html_content
        assert '✅ TEST PASSED' in html_content
        assert '4.2/5.0' in html_content
        assert 'Good' in html_content
        assert '120.5s' in html_content
        assert 'Issue' in html_content
        assert 'no action needed' in html_content
    
    def test_render_html_template_failure(self):
        """Test HTML template rendering for failed run."""
        templates = ReportTemplates()
        
        context = {
            'run_id': 'test456',
            'timestamp': '2023-12-01 11:00:00 UTC',
            'success': False,
            'status': 'FAILED',
            'quality_score': 2.1,
            'quality_assessment': {'grade': 'Poor', 'color': 'red'},
            'duration': '300.0s',
            'retry_count': 2,
            'artifacts': [],
            'failure_count': 2,
            'failures': [
                {
                    'stage': 'Bug Creation',
                    'type': 'CLI Execution Failed',
                    'message': 'Authentication failed',
                    'details': 'Invalid token',
                    'timestamp': '11:05:00'
                }
            ],
            'config': {
                'cli_path': './claude-tasker-py',
                'branch_strategy': 'always_new',
                'timeout': '1200s',
                'max_retries': '5'
            },
            'recommendations': [
                'Investigation required - test run failed',
                'Quality score below threshold'
            ]
        }
        
        html_content = templates.render_html_template(context)
        
        assert 'test456' in html_content
        assert '❌ TEST FAILED' in html_content
        assert '2.1/5.0' in html_content
        assert 'Poor' in html_content
        assert '300.0s' in html_content
        assert '2' in html_content  # retry count
        assert 'Bug Creation - CLI Execution Failed' in html_content
        assert 'Authentication failed' in html_content
        assert 'Investigation required' in html_content
    
    def test_render_markdown_template_success(self):
        """Test Markdown template rendering for successful run."""
        templates = ReportTemplates()
        
        context = {
            'run_id': 'md123',
            'timestamp': '2023-12-01 12:00:00 UTC',
            'success': True,
            'status': 'PASSED',
            'quality_score': 3.9,
            'quality_assessment': {'grade': 'Good'},
            'duration': '180.0s',
            'retry_count': 1,
            'artifacts': [
                {
                    'type': 'PR',
                    'identifier': '456',
                    'url': 'https://github.com/test/repo/pull/456',
                    'created': '12:05:00'
                }
            ],
            'failure_count': 0,
            'failures': [],
            'config': {
                'cli_path': './test-cli',
                'branch_strategy': 'reuse',
                'timeout': '900s',
                'max_retries': '3'
            },
            'recommendations': ['Everything looks good']
        }
        
        md_content = templates.render_markdown_template(context)
        
        assert '# TechFlow Test Report' in md_content
        assert 'md123' in md_content
        assert '✅ PASSED' in md_content
        assert '3.9/5.0 (Good)' in md_content
        assert '| Duration | 180.0s |' in md_content
        assert '🎯 Artifacts Created' in md_content
        assert 'PR' in md_content
        assert '[View](https://github.com/test/repo/pull/456)' in md_content
        assert '- Everything looks good' in md_content
    
    def test_render_markdown_template_with_failures(self):
        """Test Markdown template rendering with failures."""
        templates = ReportTemplates()
        
        context = {
            'run_id': 'md456',
            'timestamp': '2023-12-01 13:00:00 UTC',
            'success': False,
            'status': 'FAILED',
            'quality_score': 1.8,
            'quality_assessment': {'grade': 'Poor'},
            'duration': '450.0s',
            'retry_count': 3,
            'artifacts': [],
            'failure_count': 1,
            'failures': [
                {
                    'stage': 'Implementation',
                    'type': 'Quality Gate Failed',
                    'message': 'PR validation failed',
                    'details': 'Missing issue link',
                    'timestamp': '13:10:00'
                }
            ],
            'config': {
                'cli_path': './test-cli',
                'branch_strategy': 'always_new',
                'timeout': '1800s',
                'max_retries': '5'
            },
            'recommendations': [
                'Review quality gates',
                'Check PR requirements'
            ]
        }
        
        md_content = templates.render_markdown_template(context)
        
        assert '❌ FAILED' in md_content
        assert '1.8/5.0 (Poor)' in md_content
        assert '❌ Failures' in md_content
        assert '### Implementation - Quality Gate Failed' in md_content
        assert '**Message:** PR validation failed' in md_content
        assert '**Details:** Missing issue link' in md_content
        assert '**Time:** 13:10:00' in md_content
        assert '- Review quality gates' in md_content
        assert '- Check PR requirements' in md_content