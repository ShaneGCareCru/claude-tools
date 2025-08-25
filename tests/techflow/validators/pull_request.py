"""
Pull request validator for TechFlow test framework.
"""

import subprocess
import json
import logging

from .registry import ValidationResult


class PullRequestValidator:
    """Validator for pull request quality."""
    
    def __init__(self, quality_gates):
        self.quality_gates = quality_gates
        self.logger = logging.getLogger(__name__)
    
    def validate(self, pr_num: int) -> ValidationResult:
        """Validate pull request quality."""
        result = ValidationResult(valid=True, score=5.0)
        
        try:
            # Get PR data via GitHub CLI
            pr_data = self._get_pr_data(pr_num)
            if not pr_data:
                result.add_error(f"Could not retrieve PR #{pr_num}")
                return result
            
            # Validate PR links to issue
            if self.quality_gates.pr_must_link_issue:
                self._validate_issue_link(pr_data, result)
            
            # Validate PR has diff/changes
            if self.quality_gates.pr_must_have_diff:
                self._validate_has_changes(pr_num, result)
            
            # Validate target branch
            if self.quality_gates.pr_must_target_main:
                self._validate_target_branch(pr_data, result)
            
            # Validate PR description quality
            self._validate_description_quality(pr_data, result)
            
            # Calculate final score
            self._calculate_score(result)
            
        except Exception as e:
            result.add_error(f"Validation error: {str(e)}")
            self.logger.error(f"Error validating PR #{pr_num}: {e}")
        
        return result
    
    def _get_pr_data(self, pr_num: int) -> dict:
        """Get PR data from GitHub API."""
        try:
            cmd = ['gh', 'pr', 'view', str(pr_num), '--json', 
                   'title,body,baseRefName,headRefName,state,number,url']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.error(f"GitHub CLI error: {result.stderr}")
                return {}
            
            return json.loads(result.stdout)
            
        except Exception as e:
            self.logger.error(f"Error getting PR data: {e}")
            return {}
    
    def _validate_issue_link(self, pr_data: dict, result: ValidationResult) -> None:
        """Validate that PR links to an issue."""
        pr_body = pr_data.get('body', '')
        pr_title = pr_data.get('title', '')
        
        # Look for issue references in title and body
        import re
        issue_patterns = [
            r'#(\d+)',
            r'[Cc]loses #?(\d+)',
            r'[Ff]ixes #?(\d+)', 
            r'[Rr]esolves #?(\d+)',
            r'[Ii]ssue #?(\d+)'
        ]
        
        linked_issues = set()
        for pattern in issue_patterns:
            matches = re.findall(pattern, pr_title + ' ' + pr_body)
            linked_issues.update(matches)
        
        result.add_detail('linked_issues', list(linked_issues))
        
        if not linked_issues:
            result.add_error("PR does not reference any issues")
            result.score -= 1.0
        else:
            result.add_detail('issue_link_found', True)
    
    def _validate_has_changes(self, pr_num: int, result: ValidationResult) -> None:
        """Validate that PR has actual code changes."""
        try:
            # Get PR diff stats
            cmd = ['gh', 'pr', 'diff', str(pr_num), '--name-only']
            diff_result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if diff_result.returncode != 0:
                result.add_warning("Could not retrieve PR diff")
                return
            
            changed_files = [f.strip() for f in diff_result.stdout.split('\n') if f.strip()]
            result.add_detail('changed_files', changed_files)
            result.add_detail('files_changed_count', len(changed_files))
            
            if len(changed_files) == 0:
                result.add_error("PR has no file changes")
                result.score -= 2.0
            elif len(changed_files) < self.quality_gates.pr_min_files_changed:
                result.add_warning(f"PR changes only {len(changed_files)} files")
                result.score -= 0.5
            
        except Exception as e:
            result.add_warning(f"Could not validate PR changes: {e}")
    
    def _validate_target_branch(self, pr_data: dict, result: ValidationResult) -> None:
        """Validate PR targets the correct branch."""
        base_branch = pr_data.get('baseRefName', '')
        head_branch = pr_data.get('headRefName', '')
        
        result.add_detail('base_branch', base_branch)
        result.add_detail('head_branch', head_branch)
        
        if base_branch != 'main':
            result.add_error(f"PR targets '{base_branch}' instead of 'main'")
            result.score -= 0.5
        
        if head_branch == base_branch:
            result.add_error("PR head and base branches are the same")
            result.score -= 1.0
    
    def _validate_description_quality(self, pr_data: dict, result: ValidationResult) -> None:
        """Validate PR description quality."""
        pr_title = pr_data.get('title', '')
        pr_body = pr_data.get('body', '')
        
        result.add_detail('title', pr_title)
        result.add_detail('body_length', len(pr_body))
        
        # Validate title
        if not pr_title:
            result.add_error("PR title is empty")
            result.score -= 1.0
        elif len(pr_title) < 10:
            result.add_warning("PR title is very short")
            result.score -= 0.2
        
        # Validate body
        if not pr_body:
            result.add_warning("PR has no description")
            result.score -= 0.5
        elif len(pr_body) < 50:
            result.add_warning("PR description is very brief")
            result.score -= 0.3
        
        # Look for common PR sections
        expected_sections = ['Summary', 'Changes', 'Test', 'Testing']
        found_sections = []
        for section in expected_sections:
            if section.lower() in pr_body.lower():
                found_sections.append(section)
        
        result.add_detail('pr_sections_found', found_sections)
        
        if len(found_sections) == 0:
            result.add_warning("PR description lacks structure (no recognizable sections)")
            result.score -= 0.2
    
    def _calculate_score(self, result: ValidationResult) -> None:
        """Calculate final validation score."""
        # Ensure score is within valid range
        result.score = max(0.0, min(5.0, result.score))
        
        # If there are errors, mark as invalid
        if result.errors:
            result.valid = False
        
        # Set validity based on score threshold  
        if result.score < 3.0:
            result.valid = False