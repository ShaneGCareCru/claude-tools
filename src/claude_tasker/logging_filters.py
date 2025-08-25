# logging_filters.py
import os
import re
import logging

REDACT = os.getenv("PROMPT_LOG_REDACT", "1") != "0"
FULL = os.getenv("PROMPT_LOG_FULL", "0") == "1"

_TOKEN_PATTERNS = [
    re.compile(r'(sk-[A-Za-z0-9]{8,})'),
    re.compile(r'(xox[abpr]-[A-Za-z0-9-]{10,})'),
    re.compile(r'(ghp_[A-Za-z0-9]{20,})'),
    re.compile(r'(?i)(api[_-]?key|token|secret)["\':\s=]+([A-Za-z0-9_\-]{12,})'),
]

def redact(s: str) -> str:
    """Redact sensitive tokens from strings."""
    if not REDACT:
        return s
    out = s
    for pat in _TOKEN_PATTERNS:
        out = pat.sub(r'***REDACTED***', out)
    return out

class PromptLogFilter(logging.Filter):
    """Filter that optionally redacts prompt contents."""
    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "__is_prompt__", False) and REDACT:
            if isinstance(record.msg, str):
                record.msg = redact(record.msg)
            elif isinstance(record.args, tuple):
                record.args = tuple(redact(str(a)) for a in record.args)
        return True