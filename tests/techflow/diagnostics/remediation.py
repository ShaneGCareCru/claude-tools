"""
Remediation engine for applying fixes to common test failures.
"""

import os
import time
import logging
from typing import List, Dict, Any


class RemediationEngine:
    """Engine for applying automated remediation strategies."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Define remediation strategies
        self.remediation_strategies = {
            'timeout': [
                'increase_timeout',
                'check_network_connectivity',
                'retry_with_backoff'
            ],
            'auth_failure': [
                'check_github_token',
                'refresh_credentials',
                'verify_permissions'
            ],
            'rate_limit': [
                'apply_exponential_backoff',
                'check_api_quota',
                'switch_to_different_token'
            ],
            'command_not_found': [
                'verify_cli_installation',
                'check_path_configuration',
                'suggest_installation_steps'
            ],
            'branch_issues': [
                'create_new_branch',
                'cleanup_stale_branches',
                'verify_base_branch'
            ],
            'content_quality_issue': [
                'regenerate_with_improved_prompt',
                'apply_content_templates',
                'increase_context_detail'
            ],
            'workflow_state_issue': [
                'reset_workflow_state',
                'verify_preconditions',
                'cleanup_artifacts'
            ]
        }
    
    def get_recommendations(self, primary_cause: str, test_run, failures: List) -> List[str]:
        """Get remediation recommendations for a given cause."""
        if primary_cause not in self.remediation_strategies:
            return ['manual_investigation_required']
        
        recommendations = self.remediation_strategies[primary_cause].copy()
        
        # Add context-specific recommendations
        if test_run.retry_count > 0:
            recommendations.append('consider_manual_intervention')
        
        if len(failures) > 1:
            recommendations.append('investigate_systemic_issues')
        
        return recommendations
    
    def apply_remediation(self, primary_cause: str, actions: List[str], test_run) -> bool:
        """Apply remediation actions."""
        success = False
        
        for action in actions:
            try:
                if self._apply_single_action(action, test_run):
                    success = True
                    test_run.add_log(f"Successfully applied remediation: {action}")
                    break  # Stop on first successful remediation
                else:
                    test_run.add_log(f"Remediation action failed: {action}", "WARNING")
                    
            except Exception as e:
                self.logger.error(f"Error applying remediation {action}: {e}")
                test_run.add_log(f"Remediation error for {action}: {e}", "ERROR")
        
        return success
    
    def _apply_single_action(self, action: str, test_run) -> bool:
        """Apply a single remediation action."""
        self.logger.debug(f"Applying remediation action: {action}")
        
        if action == 'increase_timeout':
            return self._increase_timeout(test_run)
        elif action == 'retry_with_backoff':
            return self._retry_with_backoff(test_run)
        elif action == 'check_github_token':
            return self._check_github_token(test_run)
        elif action == 'apply_exponential_backoff':
            return self._apply_exponential_backoff(test_run)
        elif action == 'verify_cli_installation':
            return self._verify_cli_installation(test_run)
        elif action == 'create_new_branch':
            return self._create_new_branch(test_run)
        elif action == 'regenerate_with_improved_prompt':
            return self._regenerate_with_improved_prompt(test_run)
        elif action == 'reset_workflow_state':
            return self._reset_workflow_state(test_run)
        else:
            # Generic actions that don't require implementation
            return self._apply_generic_action(action, test_run)
    
    def _increase_timeout(self, test_run) -> bool:
        """Increase timeout for subsequent operations."""
        current_timeout = self.config.timeout_seconds
        new_timeout = min(current_timeout * 1.5, 1800)  # Max 30 minutes
        
        self.config.timeout_seconds = int(new_timeout)
        test_run.add_log(f"Increased timeout from {current_timeout} to {new_timeout} seconds")
        return True
    
    def _retry_with_backoff(self, test_run) -> bool:
        """Apply exponential backoff delay."""
        backoff_delay = self.config.backoff_factor ** test_run.retry_count
        max_delay = 60  # Maximum 1 minute delay
        
        actual_delay = min(backoff_delay, max_delay)
        test_run.add_log(f"Applying backoff delay: {actual_delay} seconds")
        time.sleep(actual_delay)
        return True
    
    def _check_github_token(self, test_run) -> bool:
        """Verify GitHub token is present and valid."""
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            test_run.add_log("GITHUB_TOKEN environment variable not set", "ERROR")
            return False
        
        # Basic token format check
        if not token.startswith(('ghp_', 'github_pat_')):
            test_run.add_log("GITHUB_TOKEN format appears invalid", "WARNING")
            return False
        
        test_run.add_log("GitHub token present and format appears valid")
        return True
    
    def _apply_exponential_backoff(self, test_run) -> bool:
        """Apply longer backoff for rate limiting."""
        # For rate limiting, use longer delays
        rate_limit_delay = 60 * (2 ** test_run.retry_count)  # 1min, 2min, 4min, etc.
        max_rate_delay = 300  # Maximum 5 minutes
        
        actual_delay = min(rate_limit_delay, max_rate_delay)
        test_run.add_log(f"Applying rate limit backoff: {actual_delay} seconds")
        time.sleep(actual_delay)
        return True
    
    def _verify_cli_installation(self, test_run) -> bool:
        """Verify CLI tools are installed and accessible."""
        import subprocess
        
        tools_to_check = [
            ('gh', 'GitHub CLI'),
            (self.config.cli_path, 'Claude Tasker CLI'),
            ('git', 'Git')
        ]
        
        all_present = True
        for tool, name in tools_to_check:
            try:
                result = subprocess.run([tool, '--version'], capture_output=True, timeout=10)
                if result.returncode == 0:
                    test_run.add_log(f"{name} is available")
                else:
                    test_run.add_log(f"{name} not working properly", "ERROR")
                    all_present = False
            except (subprocess.TimeoutExpired, FileNotFoundError):
                test_run.add_log(f"{name} not found or not accessible", "ERROR")
                all_present = False
        
        return all_present
    
    def _create_new_branch(self, test_run) -> bool:
        """Force creation of a new branch strategy."""
        # Switch to always_new branch strategy
        original_strategy = self.config.branch_strategy
        self.config.branch_strategy = 'always_new'
        
        test_run.add_log(f"Switched branch strategy from {original_strategy} to always_new")
        return True
    
    def _regenerate_with_improved_prompt(self, test_run) -> bool:
        """Improve prompt generation context."""
        # This would involve enhancing the prompt with more context
        # For now, just log the intent
        test_run.add_log("Regeneration with improved prompt context recommended")
        return True  # Assume we can improve prompts
    
    def _reset_workflow_state(self, test_run) -> bool:
        """Reset workflow state for clean retry."""
        # Clear any cached state
        test_run.issue_num = None
        test_run.pr_num = None
        test_run.branch_name = None
        
        test_run.add_log("Reset workflow state for clean retry")
        return True
    
    def _apply_generic_action(self, action: str, test_run) -> bool:
        """Apply generic remediation actions."""
        generic_actions = {
            'check_network_connectivity': 'Network connectivity check recommended',
            'refresh_credentials': 'Credential refresh recommended',
            'verify_permissions': 'Permission verification recommended',
            'check_api_quota': 'API quota check recommended',
            'switch_to_different_token': 'Token rotation recommended',
            'check_path_configuration': 'PATH configuration check recommended',
            'suggest_installation_steps': 'Installation steps provided in logs',
            'cleanup_stale_branches': 'Stale branch cleanup recommended',
            'verify_base_branch': 'Base branch verification recommended',
            'apply_content_templates': 'Content template application recommended',
            'increase_context_detail': 'Context detail enhancement recommended',
            'verify_preconditions': 'Precondition verification recommended',
            'cleanup_artifacts': 'Artifact cleanup recommended',
            'manual_investigation_required': 'Manual investigation required',
            'consider_manual_intervention': 'Consider manual intervention',
            'investigate_systemic_issues': 'Systemic issues investigation needed'
        }
        
        message = generic_actions.get(action, f"Unknown remediation action: {action}")
        test_run.add_log(message, "INFO")
        
        # Generic actions are considered "successful" for logging purposes
        return True