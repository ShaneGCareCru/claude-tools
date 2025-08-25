"""
Report generator for TechFlow test framework.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from .templates import ReportTemplates


class ReportGenerator:
    """Generates various report formats for test runs."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.templates = ReportTemplates()
    
    def generate_html_report(self, test_run, output_path: Path) -> None:
        """Generate HTML report for test run."""
        context = self._build_report_context(test_run)
        html_content = self.templates.render_html_template(context)
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        self.logger.debug(f"HTML report generated: {output_path}")
    
    def generate_markdown_summary(self, test_run, output_path: Path) -> None:
        """Generate Markdown summary for test run."""
        context = self._build_report_context(test_run)
        md_content = self.templates.render_markdown_template(context)
        
        with open(output_path, 'w') as f:
            f.write(md_content)
        
        self.logger.debug(f"Markdown report generated: {output_path}")
    
    def generate_json_summary(self, test_run, output_path: Path) -> None:
        """Generate JSON summary for test run."""
        context = self._build_report_context(test_run)
        
        with open(output_path, 'w') as f:
            json.dump(context, f, indent=2, default=str)
        
        self.logger.debug(f"JSON report generated: {output_path}")
    
    def _build_report_context(self, test_run) -> Dict[str, Any]:
        """Build context data for report templates."""
        return {
            'run_id': test_run.run_id,
            'timestamp': test_run.start_time.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'success': test_run.success,
            'status': 'PASSED' if test_run.success else 'FAILED',
            'quality_score': test_run.quality_score,
            'duration': f"{test_run.duration:.1f}s" if test_run.duration else "N/A",
            'retry_count': test_run.retry_count,
            
            # Artifacts
            'issue_num': test_run.issue_num,
            'pr_num': test_run.pr_num,
            'branch_name': test_run.branch_name,
            'artifacts': [
                {
                    'type': artifact.artifact_type.replace('_', ' ').title(),
                    'identifier': artifact.identifier,
                    'url': artifact.url,
                    'created': artifact.created_at.strftime('%H:%M:%S')
                }
                for artifact in test_run.artifacts
            ],
            
            # Failures
            'failure_count': len(test_run.failures),
            'failures': [
                {
                    'stage': failure.stage.replace('_', ' ').title(),
                    'type': failure.failure_type.replace('_', ' ').title(),
                    'message': failure.message,
                    'details': failure.details,
                    'timestamp': failure.timestamp.strftime('%H:%M:%S')
                }
                for failure in test_run.failures
            ],
            
            # Configuration
            'config': {
                'cli_path': test_run.config.cli_path if test_run.config else 'N/A',
                'branch_strategy': test_run.config.branch_strategy if test_run.config else 'N/A',
                'timeout': f"{test_run.config.timeout_seconds}s" if test_run.config else 'N/A',
                'max_retries': test_run.config.max_retries if test_run.config else 'N/A'
            },
            
            # Quality assessment
            'quality_assessment': self._assess_quality(test_run),
            
            # Recommendations
            'recommendations': self._generate_recommendations(test_run)
        }
    
    def _assess_quality(self, test_run) -> Dict[str, Any]:
        """Assess overall quality of the test run."""
        score = test_run.quality_score
        
        if score >= 4.5:
            grade = 'Excellent'
            color = 'green'
        elif score >= 3.5:
            grade = 'Good'
            color = 'blue'
        elif score >= 2.5:
            grade = 'Fair'
            color = 'orange'
        else:
            grade = 'Poor'
            color = 'red'
        
        return {
            'score': score,
            'grade': grade,
            'color': color,
            'max_score': 5.0
        }
    
    def _generate_recommendations(self, test_run) -> list:
        """Generate recommendations based on test results."""
        recommendations = []
        
        if not test_run.success:
            recommendations.append("Investigation required - test run failed")
        
        if test_run.quality_score < 3.0:
            recommendations.append("Quality score below threshold - review content generation")
        
        if test_run.retry_count > 0:
            recommendations.append("Retries occurred - check for intermittent issues")
        
        if test_run.duration and test_run.duration > 600:  # 10 minutes
            recommendations.append("Long execution time - consider optimization")
        
        if len(test_run.failures) > 2:
            recommendations.append("Multiple failures - investigate systemic issues")
        
        # Stage-specific recommendations
        failure_stages = [f.stage for f in test_run.failures]
        if 'bug_creation' in failure_stages:
            recommendations.append("Bug creation issues - check CLI and authentication")
        
        if 'implementation' in failure_stages:
            recommendations.append("Implementation issues - review prompts and context")
        
        if any('validation' in stage for stage in failure_stages):
            recommendations.append("Validation failures - review quality gates and content")
        
        if not recommendations:
            recommendations.append("Test run completed successfully - no action needed")
        
        return recommendations