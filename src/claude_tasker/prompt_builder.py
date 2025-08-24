"""Prompt building module implementing two-stage execution and Lyra-Dev framework."""

import subprocess
import json
import tempfile
from typing import Dict, Optional, Any
from pathlib import Path
from .github_client import IssueData, PRData
from src.claude_tasker.logging_config import get_logger

logger = get_logger(__name__)


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

## Output Format
Provide your review in this exact format:

### ✅ Overall Assessment
[Brief summary of the PR's quality and readiness]

### Code Review Details

1. **Code Quality** ⭐⭐⭐⭐⭐
[Your assessment here]

2. **Functionality** ⭐⭐⭐⭐⭐
[Your assessment here]

3. **Testing** ⭐⭐⭐⭐⭐
[Your assessment here]

4. **Documentation** ⭐⭐⭐⭐⭐
[Your assessment here]

5. **Performance** ⭐⭐⭐⭐⭐
[Your assessment here]

6. **Security** ⭐⭐⭐⭐⭐
[Your assessment here]

7. **Maintainability** ⭐⭐⭐⭐⭐
[Your assessment here]

### 🔧 Suggestions for Improvement
[List specific, actionable suggestions]

### ✅ Approval Recommendation
[APPROVE / REQUEST_CHANGES / COMMENT - with clear reasoning]

Format your review as constructive feedback with specific suggestions for improvement.
"""
    
    def generate_bug_analysis_prompt(self, bug_description: str, claude_md_content: str,
                                   context: Dict[str, Any]) -> str:
        """Generate prompt for bug analysis and issue creation."""
        # Use a simpler, more focused prompt to avoid Claude CLI timeouts
        prompt = f"""Analyze this bug and create a GitHub issue:

Bug Description: {bug_description}

Create a well-structured GitHub issue with:

**Title**: Bug: [concise description]

**Description**:
- **Summary**: What's wrong?
- **Steps to Reproduce**: How to trigger the bug
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens  
- **Potential Cause**: Likely root cause
- **Suggested Fix**: How to resolve it

Keep the response focused and practical. Format as markdown."""
        
        return prompt
    
    def _execute_llm_tool(self, tool_name: str, prompt: str, max_tokens: int = 4000, execute_mode: bool = False) -> Optional[Dict[str, Any]]:
        """Generic LLM tool execution with common logic.
        
        Args:
            tool_name: The LLM tool to use ('llm' or 'claude')
            prompt: The prompt text
            max_tokens: Maximum tokens for response
            execute_mode: If True, actually execute the prompt with Claude (not just print)
        """
        logger.debug(f"_execute_llm_tool called with tool={tool_name}, execute_mode={execute_mode}")
        try:
            # Build command based on tool
            if tool_name == 'llm':
                # LLM tool uses stdin for prompts
                logger.debug("Using llm tool")
                cmd = [
                    'llm', 'prompt', '-'
                ]
            elif tool_name == 'claude':
                if execute_mode:
                    # Actually execute with Claude to make code changes
                    logger.debug("Executing Claude in implementation mode")
                    logger.debug(f"Prompt preview (first 200 chars): {prompt[:200]}...")
                    # Use headless mode (-p) with permission bypass for autonomous execution
                    cmd = [
                        'claude', '-p', '--permission-mode', 'bypassPermissions'
                    ]
                else:
                    # Just generate/print prompt
                    logger.debug("Running Claude in prompt generation mode")
                    cmd = [
                        'claude', '--print',
                        '--output-format', 'json',
                        prompt
                    ]
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            # Run with timeout to prevent hanging
            # Pass prompt via stdin for both llm and claude execute mode
            if tool_name == 'llm' or (tool_name == 'claude' and execute_mode):
                logger.debug(f"Running command: {' '.join(cmd)}")
                logger.debug(f"Passing prompt via stdin ({len(prompt)} chars)")
                timeout_val = 1200 if execute_mode else 120  # 20 minutes for execution, 2 minutes for generation
                result = subprocess.run(cmd, input=prompt, capture_output=True, text=True, check=False, timeout=timeout_val)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
            
            if result.returncode == 0:
                if execute_mode:
                    logger.debug(f"Claude execution completed successfully")
                    logger.debug(f"Output length: {len(result.stdout)} chars")
                    logger.debug(f"Output preview: {result.stdout[:500]}...")
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    # Fallback: wrap plain text response
                    return {
                        'result': result.stdout.strip(),
                        'optimized_prompt': result.stdout.strip()
                    }
            else:
                logger.error(f"Command failed with return code {result.returncode}")
                logger.error(f"stderr: {result.stderr[:500]}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Command timed out")
            return None
        except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
            logger.error(f"Error: {e}")
            return None
    
    def build_with_llm(self, prompt: str, max_tokens: int = 4000) -> Optional[Dict[str, Any]]:
        """Build prompt using LLM CLI tool."""
        return self._execute_llm_tool('llm', prompt, max_tokens)
    
    def build_with_claude(self, prompt: str, max_tokens: int = 4000, execute_mode: bool = False, review_mode: bool = False) -> Optional[Dict[str, Any]]:
        """Build prompt using Claude CLI tool.
        
        Args:
            prompt: The prompt text
            max_tokens: Maximum tokens for response
            execute_mode: If True, actually execute the prompt (make code changes)
            review_mode: If True, run in review mode to capture full output
        """
        if review_mode:
            # For PR reviews, run Claude and capture the full output
            return self._execute_review_with_claude(prompt)
        return self._execute_llm_tool('claude', prompt, max_tokens, execute_mode)
    
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
            
            optimized_prompt = prompt_result.get('optimized_prompt', prompt_result.get('result', ''))
            if not optimized_prompt:
                results['error'] = "No optimized prompt in response"
                return results
            
            results['optimized_prompt'] = optimized_prompt
            
            # Stage 3: Execute optimized prompt (if not prompt-only mode)
            if not prompt_only:
                logger.debug("Stage 3: Executing optimized prompt with Claude")
                logger.debug(f"Prompt length: {len(optimized_prompt)} characters")
                execution_result = self.build_with_claude(optimized_prompt, execute_mode=True)
                results['execution_result'] = execution_result
                logger.debug(f"Execution result: {execution_result is not None}")
                
                # Check if execution actually succeeded
                if execution_result is None:
                    results['error'] = "Claude execution failed or timed out - consider increasing timeout or checking Claude availability"
                    results['success'] = False
                    return results
            
            results['success'] = True
            return results
            
        except Exception as e:
            results['error'] = str(e)
            return results
    
    def _execute_review_with_claude(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Execute Claude specifically for PR reviews.
        
        This method runs Claude in headless mode and captures the full output
        for PR review comments.
        """
        logger.debug("Executing Claude for PR review")
        try:
            # Write prompt to temporary file to avoid shell escaping issues
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name
            
            try:
                # Run Claude in headless mode to generate the review
                cmd = ['claude', '-p', prompt_file, '--permission-mode', 'bypassPermissions']
                
                logger.debug(f"Running command: {' '.join(cmd)}")
                logger.debug(f"Prompt length: {len(prompt)} chars")
                
                # Execute with longer timeout for review generation
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=1200  # 20 minute timeout for reviews
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    logger.debug(f"Claude review completed successfully")
                    logger.debug(f"Output length: {len(output)} chars")
                    
                    # For reviews, we want the full output as the response
                    return {
                        'response': output,
                        'success': True
                    }
                else:
                    logger.error(f"Claude review failed with return code {result.returncode}")
                    logger.error(f"stderr: {result.stderr[:500]}")
                    logger.error(f"stdout: {result.stdout[:500]}")
                    # Return a failure result instead of None
                    return {
                        'success': False,
                        'error': f"Claude execution failed with return code {result.returncode}",
                        'stderr': result.stderr,
                        'stdout': result.stdout
                    }
            finally:
                # Clean up temp file
                Path(prompt_file).unlink(missing_ok=True)
                
        except subprocess.TimeoutExpired:
            logger.error("Claude review command timed out")
            return {
                'success': False,
                'error': "Claude review command timed out after 20 minutes",
                'timeout': True
            }
        except Exception as e:
            logger.error(f"Error executing Claude review: {e}")
            return {
                'success': False,
                'error': f"Unexpected error executing Claude review: {str(e)}",
                'exception': str(e)
            }