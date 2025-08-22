"""Prompt building module implementing two-stage execution and Lyra-Dev framework."""

import subprocess
import json
import tempfile
from typing import Dict, Optional, Any, List
from pathlib import Path
from .github_client import IssueData, PRData


class PromptBuilder:
    """Builds optimized prompts using two-stage execution and Lyra-Dev framework."""
    
    def __init__(self):
        self.lyra_dev_framework = self._load_lyra_dev_framework()
    
    def _load_lyra_dev_framework(self) -> str:
        """Load the Lyra-Dev 4-D methodology framework."""
        return """
You are a senior software engineer implementing tasks using the Lyra-Dev 4-D methodology.

You MUST structure your entire response using the 4-D methodology with these EXACT section headers:

# DECONSTRUCT
Analyze the task requirements and current codebase state to understand what needs to be built.

# DIAGNOSE  
Identify gaps between requirements and current implementation. Focus on verifying claimed completion status and identifying actual missing pieces.

# DEVELOP
Plan your implementation approach. Specify how to fill identified gaps and ensure robust functionality.

# DELIVER
Implement the missing pieces of functionality, ensuring all modifications adhere to project conventions. Include tests and documentation as necessary.

IMPORTANT: Use these exact headers (DECONSTRUCT, DIAGNOSE, DEVELOP, DELIVER) - NOT "Design, Deploy, Document" or other variations.

IMPORTANT: You MUST follow ALL guidelines and rules specified in CLAUDE.md. Key areas:
- Project-specific coding conventions and patterns  
- Required tools and workflows
- Comprehensive testing requirements
- Error handling and performance standards

Before writing any code, review the CLAUDE.md guidelines and ensure your implementation adheres to ALL specified rules.
"""
    
    def generate_lyra_dev_prompt(self, issue_data: IssueData, claude_md_content: str, 
                                context: Dict[str, Any]) -> str:
        """Generate Lyra-Dev framework prompt for issue implementation."""
        prompt_parts = [
            self.lyra_dev_framework,
            f"\n## Issue Context\n**Issue #{issue_data.number}: {issue_data.title}**\n{issue_data.body}",
            f"\n## Project Guidelines (CLAUDE.md)\n{claude_md_content}",
        ]
        
        if context.get('git_diff'):
            prompt_parts.append(f"\n## Current Changes\n```diff\n{context['git_diff']}\n```")
        
        if context.get('related_files'):
            prompt_parts.append(f"\n## Related Files\n{chr(10).join(context['related_files'])}")
        
        if context.get('project_info'):
            prompt_parts.append(f"\n## Project Context\n{json.dumps(context['project_info'], indent=2)}")
        
        return "\n".join(prompt_parts)
    
    def generate_pr_review_prompt(self, pr_data: PRData, pr_diff: str, 
                                 claude_md_content: str) -> str:
        """Generate prompt for PR review analysis."""
        return f"""
You are conducting a comprehensive code review for this pull request.

## PR Information
**PR #{pr_data.number}: {pr_data.title}**
Author: {pr_data.author}
Branch: {pr_data.head_ref} → {pr_data.base_ref}
Changes: +{pr_data.additions}/-{pr_data.deletions} lines across {pr_data.changed_files} files

## PR Description
{pr_data.body}

## Code Changes
```diff
{pr_diff}
```

## Project Guidelines (CLAUDE.md)
{claude_md_content}

## Review Instructions
Provide a thorough code review covering:
1. **Code Quality**: Style, conventions, and best practices
2. **Functionality**: Logic correctness and edge cases
3. **Testing**: Test coverage and quality
4. **Documentation**: Code comments and documentation
5. **Performance**: Potential performance implications
6. **Security**: Security considerations and vulnerabilities
7. **Maintainability**: Code organization and future maintainability

Format your review as constructive feedback with specific suggestions for improvement.
"""
    
    def generate_bug_analysis_prompt(self, bug_description: str, claude_md_content: str,
                                   context: Dict[str, Any]) -> str:
        """Generate prompt for bug analysis and issue creation."""
        prompt_parts = [
            "You are analyzing a bug report to create a comprehensive GitHub issue.",
            f"\n## Bug Description\n{bug_description}",
            f"\n## Project Guidelines (CLAUDE.md)\n{claude_md_content}",
        ]
        
        if context.get('recent_commits'):
            prompt_parts.append(f"\n## Recent Commits\n{context['recent_commits']}")
        
        if context.get('error_logs'):
            prompt_parts.append(f"\n## Error Logs\n{context['error_logs']}")
        
        prompt_parts.append("""
## Analysis Instructions
1. **Root Cause Analysis**: Identify potential root causes
2. **Reproduction Steps**: Define clear steps to reproduce the issue
3. **Impact Assessment**: Evaluate severity and scope of the bug
4. **Solution Approach**: Suggest potential solution strategies
5. **Issue Creation**: Format as a comprehensive GitHub issue

Provide your analysis and create a well-structured GitHub issue with:
- Clear title
- Detailed description
- Reproduction steps
- Expected vs actual behavior
- Suggested labels
- Priority assessment
""")
        
        return "\n".join(prompt_parts)
    
    def _execute_llm_tool(self, tool_name: str, prompt: str, max_tokens: int = 4000) -> Optional[Dict[str, Any]]:
        """Generic LLM tool execution with common logic."""
        prompt_file = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name
            
            # Build command based on tool
            if tool_name == 'llm':
                cmd = [
                    'llm', 'prompt', prompt_file,
                    '--max-tokens', str(max_tokens),
                    '--output-format', 'json'
                ]
            elif tool_name == 'claude':
                cmd = [
                    'claude', '--file', prompt_file,
                    '--max-tokens', str(max_tokens),
                    '--output-format', 'json'
                ]
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return None
                
        except (FileNotFoundError, json.JSONDecodeError, Exception):
            return None
        finally:
            # Ensure cleanup even on exception
            if prompt_file and Path(prompt_file).exists():
                Path(prompt_file).unlink()
    
    def build_with_llm(self, prompt: str, max_tokens: int = 4000) -> Optional[Dict[str, Any]]:
        """Build prompt using LLM CLI tool."""
        return self._execute_llm_tool('llm', prompt, max_tokens)
    
    def build_with_claude(self, prompt: str, max_tokens: int = 4000) -> Optional[Dict[str, Any]]:
        """Build prompt using Claude CLI tool."""
        return self._execute_llm_tool('claude', prompt, max_tokens)
    
    def validate_meta_prompt(self, meta_prompt: str) -> bool:
        """Validate meta-prompt to prevent infinite loops."""
        # Check for minimum content requirements
        if len(meta_prompt.strip()) < 100:
            return False
        
        # Check for presence of key sections
        required_sections = ['DECONSTRUCT', 'DIAGNOSE', 'DEVELOP', 'DELIVER']
        for section in required_sections:
            if section not in meta_prompt:
                return False
        
        # Check for problematic patterns that might cause loops
        problematic_patterns = [
            'generate another prompt',
            'create a meta-prompt',
            'build a prompt for',
            'construct a prompt'
        ]
        
        meta_lower = meta_prompt.lower()
        for pattern in problematic_patterns:
            if pattern in meta_lower:
                return False
        
        return True
    
    def generate_meta_prompt(self, task_type: str, task_data: Dict[str, Any],
                           claude_md_content: str) -> str:
        """Generate meta-prompt for two-stage execution."""
        meta_prompt_template = f"""
You are an expert prompt engineer creating an optimized prompt for claude-tasker execution.

## Task Type: {task_type}

## Task Data:
{json.dumps(task_data, indent=2)}

## Project Context (CLAUDE.md):
{claude_md_content}

## Instructions:
Create an optimized prompt that:
1. Uses the Lyra-Dev 4-D methodology (DECONSTRUCT, DIAGNOSE, DEVELOP, DELIVER)
2. Incorporates all relevant context and requirements
3. Follows project-specific guidelines from CLAUDE.md
4. Ensures comprehensive implementation with proper testing
5. Includes clear acceptance criteria and validation steps

Return ONLY the optimized prompt text - no additional commentary or wrapper text.
"""
        return meta_prompt_template
    
    def execute_two_stage_prompt(self, task_type: str, task_data: Dict[str, Any],
                               claude_md_content: str, prompt_only: bool = False) -> Dict[str, Any]:
        """Execute two-stage prompt generation and execution."""
        results = {
            'success': False,
            'meta_prompt': '',
            'optimized_prompt': '',
            'execution_result': None,
            'error': None
        }
        
        try:
            # Stage 1: Generate meta-prompt
            meta_prompt = self.generate_meta_prompt(task_type, task_data, claude_md_content)
            results['meta_prompt'] = meta_prompt
            
            # Validate meta-prompt
            if not self.validate_meta_prompt(meta_prompt):
                results['error'] = "Invalid meta-prompt generated"
                return results
            
            # Stage 2: Generate optimized prompt
            llm_result = self.build_with_llm(meta_prompt)
            if not llm_result:
                claude_result = self.build_with_claude(meta_prompt)
                if not claude_result:
                    results['error'] = "Failed to generate optimized prompt"
                    return results
                prompt_result = claude_result
            else:
                prompt_result = llm_result
            
            optimized_prompt = prompt_result.get('optimized_prompt', '')
            if not optimized_prompt:
                results['error'] = "No optimized prompt in response"
                return results
            
            results['optimized_prompt'] = optimized_prompt
            
            # Stage 3: Execute optimized prompt (if not prompt-only mode)
            if not prompt_only:
                execution_result = self.build_with_claude(optimized_prompt)
                results['execution_result'] = execution_result
            
            results['success'] = True
            return results
            
        except Exception as e:
            results['error'] = str(e)
            return results