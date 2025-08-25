"""
Triage matrix for mapping symptoms to potential causes.
"""

from typing import Dict, List, Any
import re


class TriageMatrix:
    """Maps failure symptoms to potential root causes."""
    
    def __init__(self):
        self.triage_rules = {
            # CLI execution failures
            'cli_execution_failed': {
                'symptoms': [
                    ('timeout', 'command timed out', 0.8),
                    ('permission_denied', 'permission denied', 0.9),
                    ('auth_failure', 'authentication failed|unauthorized', 0.9),
                    ('rate_limit', 'rate limit|too many requests', 0.8),
                    ('network_error', 'connection|network|timeout', 0.7),
                    ('command_not_found', 'command not found|no such file', 0.9),
                    ('invalid_arguments', 'invalid argument|unknown flag', 0.8)
                ],
                'default_cause': 'execution_environment'
            },
            
            # Issue creation/parsing failures
            'issue_parsing_failed': {
                'symptoms': [
                    ('output_format_changed', 'could not parse.*number', 0.8),
                    ('cli_output_truncated', 'output.*truncated|incomplete', 0.7),
                    ('unexpected_format', 'unexpected.*format|parsing.*failed', 0.8)
                ],
                'default_cause': 'output_parsing_issue'
            },
            
            # PR creation/parsing failures
            'pr_parsing_failed': {
                'symptoms': [
                    ('no_pr_created', 'no.*pr.*created|failed.*create.*pr', 0.9),
                    ('branch_issues', 'branch.*not.*found|invalid.*branch', 0.8),
                    ('push_failure', 'failed.*push|permission.*denied.*push', 0.9)
                ],
                'default_cause': 'pr_creation_issue'
            },
            
            # Quality gate failures
            'quality_gate_failed': {
                'symptoms': [
                    ('missing_sections', 'missing.*section|section.*not.*found', 0.8),
                    ('insufficient_content', 'too.*short|not.*enough.*content', 0.7),
                    ('format_issues', 'format.*invalid|structure.*incorrect', 0.7),
                    ('validation_failed', 'validation.*failed|criteria.*not.*met', 0.8)
                ],
                'default_cause': 'content_quality_issue'
            },
            
            # Precondition failures
            'precondition_failed': {
                'symptoms': [
                    ('missing_issue', 'no.*issue.*number|issue.*not.*found', 0.9),
                    ('missing_pr', 'no.*pr.*number|pr.*not.*found', 0.9),
                    ('invalid_state', 'invalid.*state|precondition.*not.*met', 0.8)
                ],
                'default_cause': 'workflow_state_issue'
            }
        }
        
        # Contributing factor patterns
        self.contributing_factors = {
            'high_retry_count': (r'retry.*count.*[3-9]', 0.6),
            'long_execution_time': (r'execution.*time.*[0-9]{3,}', 0.5),
            'multiple_failures': (r'failure.*count.*[2-9]', 0.7),
            'environment_issues': (r'environment|config|setup', 0.4),
            'api_issues': (r'api.*error|rate.*limit|quota', 0.6)
        }
    
    def analyze_failure(self, failure, test_run) -> Dict[str, Any]:
        """Analyze a failure and determine potential causes."""
        result = {
            'primary_cause': None,
            'contributing_factors': [],
            'confidence': 0.0,
            'evidence': []
        }
        
        # Get failure type rules
        failure_type = failure.failure_type
        if failure_type not in self.triage_rules:
            result['primary_cause'] = 'unknown_failure_type'
            result['confidence'] = 0.1
            return result
        
        rules = self.triage_rules[failure_type]
        
        # Analyze failure message and details
        text_to_analyze = ' '.join([
            failure.message or '',
            failure.details or '',
            str(failure.diagnostic_info)
        ]).lower()
        
        # Find matching symptoms
        best_match = None
        best_confidence = 0.0
        
        for cause, pattern, confidence in rules['symptoms']:
            if re.search(pattern, text_to_analyze, re.IGNORECASE):
                if confidence > best_confidence:
                    best_match = cause
                    best_confidence = confidence
                    result['evidence'].append(f"Pattern '{pattern}' matched in failure text")
        
        # Set primary cause
        if best_match:
            result['primary_cause'] = best_match
            result['confidence'] = best_confidence
        else:
            result['primary_cause'] = rules['default_cause']
            result['confidence'] = 0.3
        
        # Identify contributing factors
        result['contributing_factors'] = self._identify_contributing_factors(test_run, text_to_analyze)
        
        return result
    
    def _identify_contributing_factors(self, test_run, failure_text: str) -> List[str]:
        """Identify contributing factors from test run context."""
        factors = []
        
        # Check for patterns in failure text
        for factor, (pattern, confidence) in self.contributing_factors.items():
            if re.search(pattern, failure_text, re.IGNORECASE):
                factors.append(factor)
        
        # Check test run characteristics
        if test_run.retry_count >= 2:
            factors.append('high_retry_count')
        
        if test_run.duration and test_run.duration > 600:  # 10 minutes
            factors.append('long_execution_time')
        
        if len(test_run.failures) > 2:
            factors.append('multiple_failures')
        
        # Check for specific patterns in logs
        all_logs = ' '.join(test_run.logs).lower()
        if 'environment' in all_logs or 'config' in all_logs:
            factors.append('environment_issues')
        
        if 'rate limit' in all_logs or 'api error' in all_logs:
            factors.append('api_issues')
        
        return list(set(factors))  # Remove duplicates
    
    def get_cause_description(self, cause: str) -> str:
        """Get human-readable description of a cause."""
        descriptions = {
            'timeout': 'Command execution timed out, possibly due to network issues or system load',
            'permission_denied': 'Insufficient permissions to execute the required operation',
            'auth_failure': 'Authentication failed, check API tokens and credentials',
            'rate_limit': 'API rate limit exceeded, requests are being throttled',
            'network_error': 'Network connectivity issues preventing successful execution',
            'command_not_found': 'Required command or tool is not installed or not in PATH',
            'invalid_arguments': 'Invalid command line arguments or flags provided',
            'output_format_changed': 'CLI output format has changed, parsing logic needs update',
            'cli_output_truncated': 'CLI output was truncated, preventing successful parsing',
            'no_pr_created': 'Pull request was not created successfully',
            'branch_issues': 'Branch-related problems preventing PR creation',
            'push_failure': 'Failed to push changes to remote repository',
            'missing_sections': 'Required sections missing from generated content',
            'insufficient_content': 'Generated content is too brief or lacks detail',
            'format_issues': 'Content format does not match expected structure',
            'missing_issue': 'Issue number not available for subsequent operations',
            'missing_pr': 'PR number not available for subsequent operations',
            'workflow_state_issue': 'Workflow state inconsistency preventing operation',
            'content_quality_issue': 'Generated content does not meet quality standards',
            'execution_environment': 'Environment configuration or setup problems',
            'unknown_failure_type': 'Failure type not recognized by diagnostic system'
        }
        
        return descriptions.get(cause, f'Unknown cause: {cause}')