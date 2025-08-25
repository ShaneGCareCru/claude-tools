"""
TechFlow Demo Self-Testing Framework

This framework provides comprehensive testing for the complete bug-to-resolution
workflow, ensuring quality gates at each stage and providing automated verification
of our LLM-driven development process.
"""

from .test_runner import TechFlowTestRunner
from .config import TestConfig, QualityGates, ScoringConfig

__all__ = [
    'TechFlowTestRunner',
    'TestConfig',
    'QualityGates', 
    'ScoringConfig'
]

__version__ = '1.0.0'