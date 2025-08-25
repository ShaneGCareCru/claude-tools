"""
Evidence collector for TechFlow test framework.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .reporter import ReportGenerator


class EvidenceCollector:
    """Collects and organizes test evidence."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.reporter = ReportGenerator(config)
        
        # Create evidence directory
        self.evidence_dir = Path(config.evidence_dir)
        self.evidence_dir.mkdir(exist_ok=True)
    
    def collect_run_summary(self, test_run) -> Path:
        """Collect complete evidence for a test run."""
        run_dir = self.evidence_dir / f"run-{test_run.run_id}"
        run_dir.mkdir(exist_ok=True)
        
        # Save raw run data
        run_data_file = run_dir / "run_data.json"
        self._save_run_data(test_run, run_data_file)
        
        # Save artifacts
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        self._save_artifacts(test_run, artifacts_dir)
        
        # Generate reports
        reports_dir = run_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        self._generate_reports(test_run, reports_dir)
        
        # Save logs
        logs_file = run_dir / "test_run.log"
        self._save_logs(test_run, logs_file)
        
        self.logger.info(f"Evidence collected in: {run_dir}")
        return run_dir
    
    def _save_run_data(self, test_run, file_path: Path) -> None:
        """Save raw test run data as JSON."""
        data = {
            'run_id': test_run.run_id,
            'start_time': test_run.start_time.isoformat(),
            'end_time': test_run.end_time.isoformat() if test_run.end_time else None,
            'duration': test_run.duration,
            'success': test_run.success,
            'quality_score': test_run.quality_score,
            'retry_count': test_run.retry_count,
            'issue_num': test_run.issue_num,
            'pr_num': test_run.pr_num,
            'branch_name': test_run.branch_name,
            'config': {
                'cli_path': test_run.config.cli_path if test_run.config else None,
                'branch_strategy': test_run.config.branch_strategy if test_run.config else None,
                'timeout_seconds': test_run.config.timeout_seconds if test_run.config else None,
                'max_retries': test_run.config.max_retries if test_run.config else None
            },
            'artifacts': [
                {
                    'type': artifact.artifact_type,
                    'identifier': artifact.identifier,
                    'url': artifact.url,
                    'metadata': artifact.metadata,
                    'created_at': artifact.created_at.isoformat()
                }
                for artifact in test_run.artifacts
            ],
            'failures': [
                {
                    'stage': failure.stage,
                    'failure_type': failure.failure_type,
                    'message': failure.message,
                    'details': failure.details,
                    'timestamp': failure.timestamp.isoformat(),
                    'diagnostic_info': failure.diagnostic_info
                }
                for failure in test_run.failures
            ]
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_artifacts(self, test_run, artifacts_dir: Path) -> None:
        """Save test artifacts."""
        for artifact in test_run.artifacts:
            artifact_file = artifacts_dir / f"{artifact.artifact_type}_{artifact.identifier}.json"
            
            artifact_data = {
                'type': artifact.artifact_type,
                'identifier': artifact.identifier,
                'url': artifact.url,
                'content': artifact.content,
                'metadata': artifact.metadata,
                'created_at': artifact.created_at.isoformat()
            }
            
            with open(artifact_file, 'w') as f:
                json.dump(artifact_data, f, indent=2)
    
    def _generate_reports(self, test_run, reports_dir: Path) -> None:
        """Generate various report formats."""
        # Generate HTML report
        html_report = reports_dir / "report.html"
        self.reporter.generate_html_report(test_run, html_report)
        
        # Generate markdown summary
        md_report = reports_dir / "summary.md"
        self.reporter.generate_markdown_summary(test_run, md_report)
        
        # Generate JSON summary for programmatic access
        json_report = reports_dir / "summary.json"
        self.reporter.generate_json_summary(test_run, json_report)
    
    def _save_logs(self, test_run, logs_file: Path) -> None:
        """Save test run logs."""
        with open(logs_file, 'w') as f:
            f.write(f"Test Run Logs - {test_run.run_id}\n")
            f.write(f"={'=' * 50}\n\n")
            
            for log_entry in test_run.logs:
                f.write(f"{log_entry}\n")
    
    def collect_system_info(self) -> Dict[str, Any]:
        """Collect system information for diagnostics."""
        import platform
        import subprocess
        import sys
        
        system_info = {
            'timestamp': datetime.now().isoformat(),
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor()
            },
            'python': {
                'version': sys.version,
                'executable': sys.executable
            },
            'environment': {},
            'tools': {}
        }
        
        # Collect relevant environment variables
        env_vars = [
            'GITHUB_TOKEN',
            'CLAUDE_LOG_LEVEL',
            'CLAUDE_BRANCH_STRATEGY',
            'TECHFLOW_REPO_PATH'
        ]
        
        for var in env_vars:
            value = os.getenv(var)
            if value:
                # Mask sensitive values
                if 'token' in var.lower() or 'key' in var.lower():
                    system_info['environment'][var] = f"{value[:8]}***"
                else:
                    system_info['environment'][var] = value
            else:
                system_info['environment'][var] = None
        
        # Check tool versions
        tools = [
            ('gh', 'GitHub CLI'),
            ('git', 'Git'),
            ('python', 'Python')
        ]
        
        for tool, description in tools:
            try:
                result = subprocess.run([tool, '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    system_info['tools'][tool] = {
                        'available': True,
                        'version': result.stdout.strip(),
                        'description': description
                    }
                else:
                    system_info['tools'][tool] = {
                        'available': False,
                        'error': result.stderr.strip(),
                        'description': description
                    }
            except Exception as e:
                system_info['tools'][tool] = {
                    'available': False,
                    'error': str(e),
                    'description': description
                }
        
        return system_info