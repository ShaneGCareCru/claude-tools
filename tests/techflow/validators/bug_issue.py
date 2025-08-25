"""
Bug issue quality validator for TechFlow test framework.
"""

import subprocess
import json
import re
from typing import List, Set
import logging

from .registry import ValidationResult


class BugIssueValidator:
    """Validator for bug issue quality."""
    
    REQUIRED_SECTIONS = [
        'Bug Description',
        'Reproduction Steps', 
        'Expected Behavior',
        'Actual Behavior',
        'Root Cause Analysis',
        'Acceptance Criteria',
        'Test Plan',
        'Rollback Plan'
    ]
    
    def __init__(self, quality_gates):
        self.quality_gates = quality_gates
        self.logger = logging.getLogger(__name__)
    
    def validate(self, issue_num: int) -> ValidationResult:
        """Validate bug issue quality."""
        result = ValidationResult(valid=True, score=5.0)
        
        try:
            # Get issue content via GitHub CLI
            issue_data = self._get_issue_data(issue_num)
            if not issue_data:
                result.add_error(f"Could not retrieve issue #{issue_num}")
                return result
            
            issue_body = issue_data.get('body', '')
            issue_title = issue_data.get('title', '')
            
            result.add_detail('title', issue_title)
            result.add_detail('body_length', len(issue_body))
            
            # Validate required sections
            self._validate_required_sections(issue_body, result)
            
            # Validate acceptance criteria
            self._validate_acceptance_criteria(issue_body, result)
            
            # Validate section content quality
            self._validate_section_quality(issue_body, result)
            
            # Validate title quality
            self._validate_title_quality(issue_title, result)
            
            # Calculate final score
            self._calculate_score(result)
            
        except Exception as e:
            result.add_error(f"Validation error: {str(e)}")
            self.logger.error(f"Error validating issue #{issue_num}: {e}")
        
        return result
    
    def _get_issue_data(self, issue_num: int) -> dict:
        """Get issue data from GitHub API."""
        try:
            cmd = ['gh', 'issue', 'view', str(issue_num), '--json', 'title,body,state,labels']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.error(f"GitHub CLI error: {result.stderr}")
                return {}
            
            return json.loads(result.stdout)
            
        except Exception as e:
            self.logger.error(f"Error getting issue data: {e}")
            return {}
    
    def _validate_required_sections(self, issue_body: str, result: ValidationResult) -> None:
        """Validate that all required sections are present."""
        missing_sections = []
        found_sections = set()
        
        for section in self.REQUIRED_SECTIONS:
            # Look for section headers (with various formats)
            patterns = [
                f"## {section}",
                f"# {section}",
                f"**{section}**",
                f"{section}:",
                f"### {section}"
            ]
            
            section_found = False
            for pattern in patterns:
                if pattern.lower() in issue_body.lower():
                    section_found = True
                    found_sections.add(section)
                    break
            
            if not section_found:
                missing_sections.append(section)
        
        result.add_detail('found_sections', list(found_sections))
        result.add_detail('missing_sections', missing_sections)
        
        if missing_sections:
            result.add_error(f"Missing required sections: {', '.join(missing_sections)}")
            result.score -= len(missing_sections) * 0.5
        
        if len(found_sections) < self.quality_gates.bug_required_sections:
            result.add_error(f"Only {len(found_sections)} sections found, need {self.quality_gates.bug_required_sections}")
    
    def _validate_acceptance_criteria(self, issue_body: str, result: ValidationResult) -> None:
        """Validate acceptance criteria section."""
        # Look for acceptance criteria items (checkboxes)
        criteria_patterns = [
            r'- \[ \].*',  # - [ ] item
            r'\* \[ \].*',  # * [ ] item  
            r'\d+\.\s+.*',  # 1. item
            r'- .*',       # - item
            r'\* .*'       # * item
        ]
        
        criteria_count = 0
        for pattern in criteria_patterns:
            matches = re.findall(pattern, issue_body, re.MULTILINE)
            criteria_count += len(matches)
        
        result.add_detail('acceptance_criteria_count', criteria_count)
        
        if criteria_count < self.quality_gates.bug_min_acceptance_criteria:
            result.add_error(f"Need at least {self.quality_gates.bug_min_acceptance_criteria} acceptance criteria, found {criteria_count}")
            result.score -= 0.5
    
    def _validate_section_quality(self, issue_body: str, result: ValidationResult) -> None:
        """Validate quality of section content."""
        sections = issue_body.split('##')  # Split by section headers
        
        short_sections = []
        for i, section in enumerate(sections[1:], 1):  # Skip first split (before first ##)
            section_lines = [line.strip() for line in section.split('\n') if line.strip()]
            section_content = '\n'.join(section_lines[1:])  # Skip header line
            
            if len(section_content) < self.quality_gates.bug_min_section_length:
                section_name = section_lines[0] if section_lines else f"Section {i}"
                short_sections.append(section_name)
        
        result.add_detail('short_sections', short_sections)
        
        if short_sections:
            result.add_warning(f"Short sections detected: {', '.join(short_sections)}")
            result.score -= len(short_sections) * 0.2
    
    def _validate_title_quality(self, issue_title: str, result: ValidationResult) -> None:
        """Validate issue title quality."""
        if not issue_title:
            result.add_error("Issue title is empty")
            result.score -= 1.0
            return
        
        if len(issue_title) < 10:
            result.add_warning("Issue title is very short")
            result.score -= 0.2
        
        if len(issue_title) > 100:
            result.add_warning("Issue title is very long")
            result.score -= 0.2
        
        # Check for descriptive keywords
        quality_keywords = ['bug', 'error', 'issue', 'problem', 'fail', 'missing', 'incorrect']
        has_quality_keyword = any(keyword in issue_title.lower() for keyword in quality_keywords)
        
        if not has_quality_keyword:
            result.add_warning("Title could be more descriptive about the issue type")
            result.score -= 0.1
    
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