# prompt_models.py
from __future__ import annotations
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field

class ExecutionOptions(BaseModel):
    """Options for LLM execution."""
    max_tokens: int = Field(4000, ge=256, le=120000)
    execute_mode: bool = False
    review_mode: bool = False
    timeout_seconds: int = Field(120, ge=30, le=7200)

class PromptContext(BaseModel):
    """Context information for prompt generation."""
    git_diff: Optional[str] = None
    related_files: List[str] = Field(default_factory=list)
    project_info: Dict[str, Any] = Field(default_factory=dict)

class LLMResult(BaseModel):
    """Result from LLM execution."""
    success: bool = True
    text: Optional[str] = None         # raw text output
    data: Optional[Dict[str, Any]] = None  # renamed from json to avoid shadowing
    error: Optional[str] = None
    stderr: Optional[str] = None
    stdout: Optional[str] = None
    tool: Optional[str] = None         # 'llm' or 'claude'
    status_code: Optional[int] = None

class TwoStageResult(BaseModel):
    """Result from two-stage prompt execution."""
    success: bool = False
    meta_prompt: str = ""
    optimized_prompt: str = ""
    execution_result: Optional[LLMResult] = None
    error: Optional[str] = None