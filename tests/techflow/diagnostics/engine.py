"""
Diagnostic engine for TechFlow test framework.

This module provides diagnostic capabilities to analyze test failures
and suggest remediation strategies.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .triage import TriageMatrix
from .remediation import RemediationEngine


@dataclass
class DiagnosticResult:
    """Result of a diagnostic analysis."""
    
    primary_cause: Optional[str] = None
    contributing_factors: List[str] = None
    recommended_actions: List[str] = None
    confidence_score: float = 0.0
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.contributing_factors is None:
            self.contributing_factors = []
        if self.recommended_actions is None:
            self.recommended_actions = []
        if self.details is None:
            self.details = {}


class DiagnosticEngine:
    """Engine for diagnosing test failures and recommending remediation."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.triage = TriageMatrix()
        self.remediation = RemediationEngine(config)
    
    def diagnose_failure(self, test_run, failure_stage: str) -> DiagnosticResult:
        """Diagnose a test failure and recommend actions."""
        self.logger.debug(f"Diagnosing failure in stage: {failure_stage}")
        
        result = DiagnosticResult()
        
        try:
            # Get failure information
            stage_failures = [f for f in test_run.failures if f.stage == failure_stage]
            if not stage_failures:
                result.primary_cause = "unknown"
                result.confidence_score = 0.1
                return result
            
            primary_failure = stage_failures[0]
            
            # Use triage matrix to identify potential causes
            triage_result = self.triage.analyze_failure(primary_failure, test_run)
            result.primary_cause = triage_result.get('primary_cause')
            result.contributing_factors = triage_result.get('contributing_factors', [])
            result.confidence_score = triage_result.get('confidence', 0.5)
            
            # Get remediation recommendations
            remediation_actions = self.remediation.get_recommendations(
                result.primary_cause, 
                test_run, 
                stage_failures
            )
            result.recommended_actions = remediation_actions
            
            # Add diagnostic details
            result.details = {
                'failure_count': len(stage_failures),
                'retry_count': test_run.retry_count,
                'stage': failure_stage,
                'failure_types': [f.failure_type for f in stage_failures],
                'triage_analysis': triage_result
            }
            
            self.logger.info(f"Diagnosis complete: {result.primary_cause} (confidence: {result.confidence_score})")
            
        except Exception as e:
            self.logger.error(f"Error during diagnosis: {e}")
            result.primary_cause = "diagnostic_error"
            result.details['error'] = str(e)
        
        return result
    
    def try_remediation(self, test_run, failure_stage: str) -> bool:
        """Attempt to apply remediation for a failure."""
        diagnosis = self.diagnose_failure(test_run, failure_stage)
        
        if not diagnosis.recommended_actions:
            self.logger.warning("No remediation actions available")
            return False
        
        try:
            success = self.remediation.apply_remediation(
                diagnosis.primary_cause,
                diagnosis.recommended_actions,
                test_run
            )
            
            if success:
                test_run.add_log(f"Applied remediation for {diagnosis.primary_cause}")
            else:
                test_run.add_log(f"Remediation failed for {diagnosis.primary_cause}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error applying remediation: {e}")
            test_run.add_log(f"Remediation error: {e}", "ERROR")
            return False
    
    def generate_diagnostic_report(self, test_run) -> Dict[str, Any]:
        """Generate a comprehensive diagnostic report."""
        report = {
            'run_id': test_run.run_id,
            'overall_status': 'success' if test_run.success else 'failed',
            'quality_score': test_run.quality_score,
            'duration': test_run.duration,
            'retry_count': test_run.retry_count,
            'diagnoses': []
        }
        
        # Diagnose each failure
        for failure in test_run.failures:
            diagnosis = self.diagnose_failure(test_run, failure.stage)
            report['diagnoses'].append({
                'stage': failure.stage,
                'failure_type': failure.failure_type,
                'message': failure.message,
                'diagnosis': diagnosis.__dict__
            })
        
        # Add overall recommendations
        if test_run.failures:
            report['overall_recommendations'] = self._generate_overall_recommendations(test_run)
        
        return report
    
    def _generate_overall_recommendations(self, test_run) -> List[str]:
        """Generate overall recommendations based on all failures."""
        recommendations = []
        
        # Check for patterns across failures
        failure_types = [f.failure_type for f in test_run.failures]
        failure_stages = [f.stage for f in test_run.failures]
        
        # Pattern: Multiple CLI execution failures
        if failure_types.count('cli_execution_failed') > 1:
            recommendations.append("Multiple CLI execution failures detected - check authentication and permissions")
        
        # Pattern: Quality gate failures
        if failure_types.count('quality_gate_failed') > 1:
            recommendations.append("Multiple quality gate failures - review content generation prompts")
        
        # Pattern: Early stage failures
        if any(stage in ['bug_creation', 'bug_validation'] for stage in failure_stages):
            recommendations.append("Early stage failures suggest environment or configuration issues")
        
        # Pattern: High retry count
        if test_run.retry_count >= 2:
            recommendations.append("High retry count suggests intermittent issues - check network and API limits")
        
        return recommendations