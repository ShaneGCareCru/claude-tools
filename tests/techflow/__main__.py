"""
TechFlow test framework CLI entry point.

This allows running the framework as a module:
python -m tests.techflow
"""

from .cli import main

if __name__ == '__main__':
    exit(main())