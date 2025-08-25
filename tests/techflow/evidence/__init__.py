"""
Evidence collection module for TechFlow test framework.

This module provides evidence collection and reporting capabilities
for test runs, including artifact collection and report generation.
"""

from .collector import EvidenceCollector
from .reporter import ReportGenerator
from .templates import ReportTemplates

__all__ = [
    'EvidenceCollector',
    'ReportGenerator',
    'ReportTemplates'
]