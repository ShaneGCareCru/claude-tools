"""Prompt building module implementing two-stage execution and Lyra-Dev framework."""

import subprocess
import json
import tempfile
from typing import Dict, Optional, Any
from pathlib import Path
from .github_client import IssueData, PRData
from src.claude_tasker.logging_config import get_logger
import logging

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
Identify gaps between requirements and current implementation. Focus on verifying claimed
completion status and identifying actual missing pieces.

# DEVELOP
Plan your implementation approach. Specify how to fill identified gaps and ensure robust
functionality.

# DELIVER
Implement the missing pieces of functionality, ensuring all modifications adhere to project
conventions. Include tests and documentation as necessary.

IMPORTANT: Use these exact headers (DECONSTRUCT, DIAGNOSE, DEVELOP, DELIVER) - NOT
"Design, Deploy, Document" or other variations.

IMPORTANT: You MUST follow ALL guidelines and rules specified in CLAUDE.md. Key areas:
- Project-specific coding conventions and patterns  
- Required tools and workflows
- Comprehensive testing requirements
- Error handling and performance standards

Before writing any code, review the CLAUDE.md guidelines and ensure your implementation
adheres to ALL specified rules.
"""
    
    def generate_lyra_dev_prompt(self, issue_data: IssueData, claude_md_content: str, 
                                context: Dict[str, Any]) -> str:
        """Generate Lyra-Dev framework prompt for issue implementation."""
        logger.debug(f"Generating Lyra-Dev prompt for issue #{issue_data.number}")
        logger.debug(f"Context keys: {list(context.keys())}")
        
        prompt_parts = [
            self.lyra_dev_framework,
            (f"\n## Issue Context\n**Issue #{issue_data.number}: "
             f"{issue_data.title}**\n{issue_data.body}"),
            f"\n## Project Guidelines (CLAUDE.md)\n{claude_md_content}",
        ]
        
        if context.get('git_diff'):
            logger.debug(f"Including git diff ({len(context['git_diff'])} chars)")
            prompt_parts.append(f"\n## Current Changes\n```diff\n{context['git_diff']}\n```")
        
        if context.get('related_files'):
            logger.debug(f"Including {len(context['related_files'])} related files")
            prompt_parts.append(f"\n## Related Files\n{chr(10).join(context['related_files'])}")
        
        if context.get('project_info'):
            logger.debug("Including project info context")
            prompt_parts.append(
                f"\n## Project Context\n{json.dumps(context['project_info'], indent=2)}")
        
        final_prompt = "\n".join(prompt_parts)
        logger.debug(f"Generated Lyra-Dev prompt: {len(final_prompt)} characters")
        return final_prompt
    
    def generate_pr_review_prompt(self, pr_data: PRData, pr_diff: str, 
                                 claude_md_content: str) -> str:
        """Generate prompt for PR review analysis."""
        logger.debug(f"Generating PR review prompt for PR #{pr_data.number}")
        logger.debug(f"PR: {pr_data.title} by {pr_data.author}")
        logger.debug(
            f"Changes: +{pr_data.additions}/-{pr_data.deletions} lines "
            f"across {pr_data.changed_files} files")
        
        prompt = f"""
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
        
        logger.debug(f"Generated PR review prompt: {len(prompt)} characters")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Full PR review prompt:")
            logger.debug(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
        
        return prompt
    
    def generate_bug_analysis_prompt(self, bug_description: str, claude_md_content: str,
                                   context: Dict[str, Any]) -> str:
        """Generate prompt for bug analysis and issue creation."""
        logger.debug(f"Generating bug analysis prompt")
        logger.debug(f"Bug description length: {len(bug_description)} characters")
        logger.debug(f"Context keys: {list(context.keys())}")
        
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
        
        logger.debug(f"Generated bug analysis prompt: {len(prompt)} characters")
        return prompt
    
    def _execute_llm_tool(self, tool_name: str, prompt: str, max_tokens: int = 4000,
                         execute_mode: bool = False) -> Optional[Dict[str, Any]]:
        """Generic LLM tool execution with common logic.
        
        Args:
            tool_name: The LLM tool to use ('llm' or 'claude')
            prompt: The prompt text
            max_tokens: Maximum tokens for response
            execute_mode: If True, actually execute the prompt with Claude (not just print)
        """
        logger.debug(f"_execute_llm_tool called with tool={tool_name}, execute_mode={execute_mode}")
        logger.debug(f"Prompt length: {len(prompt)} characters")
        
        # Log full prompt in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("=" * 80)
            logger.debug("FULL PROMPT CONTENT:")
            logger.debug("-" * 80)
            logger.debug(prompt)
            logger.debug("=" * 80)
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
                    logger.debug(f"Prompt preview (first 500 chars): {prompt[:500]}...")
                    logger.debug(f"Decision: Using Claude for code implementation")
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
                # 20 minutes for execution, 2 minutes for generation
                timeout_val = 1200 if execute_mode else 120
                result = subprocess.run(cmd, input=prompt, capture_output=True, text=True, check=False, timeout=timeout_val)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
            
            if result.returncode == 0:
                if execute_mode:
                    logger.debug(f"Claude execution completed successfully")
                    logger.debug(f"Output length: {len(result.stdout)} chars")
                    
                    # Log full response in debug mode
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("=" * 80)
                        logger.debug("FULL CLAUDE RESPONSE:")
                        logger.debug("-" * 80)
                        logger.debug(result.stdout)
                        logger.debug("=" * 80)
                    else:
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
                # Log full error details in debug mode
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Full stderr output:")
                    logger.debug(result.stderr)
                    logger.debug("Full stdout output:")
                    logger.debug(result.stdout)
                else:
                    logger.error(f"stderr: {result.stderr[:500]}")
                return {
                    'success': False,
                    'error': f'Command failed with return code {result.returncode}',
                    'stderr': result.stderr,
                    'stdout': result.stdout
                }
                
        except subprocess.TimeoutExpired:
            logger.error("Command timed out")
            return {
                'success': False,
                'error': 'Command timed out'
            }
        except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
            logger.error(f"Error: {e}")
            return {
                'success': False,
                'error': f'Unexpected error: {e}'
            }
    
    def build_with_llm(self, prompt: str, max_tokens: int = 4000) -> Optional[Dict[str, Any]]:
        """Build prompt using LLM CLI tool."""
        logger.debug("Attempting to build prompt with LLM tool")
        result = self._execute_llm_tool('llm', prompt, max_tokens)
        
        if result:
            logger.debug(f"LLM tool response received: {result.get('success', True)}")
            if logger.isEnabledFor(logging.DEBUG) and result.get('result'):
                logger.debug(f"LLM response preview: {str(result.get('result'))[:500]}...")
        else:
            logger.debug("LLM tool returned None or failed")
        
        return result
    
    def build_with_claude(self, prompt: str, max_tokens: int = 4000, execute_mode: bool = False, review_mode: bool = False) -> Optional[Dict[str, Any]]:
        """Build prompt using Claude CLI tool.
        
        Args:
            prompt: The prompt text
            max_tokens: Maximum tokens for response
            execute_mode: If True, actually execute the prompt (make code changes)
            review_mode: If True, run in review mode to capture full output
        """
        logger.debug(f"Building with Claude: execute_mode={execute_mode}, review_mode={review_mode}")
        
        if review_mode:
            logger.debug("Decision: Using review-specific execution for PR review")
            # For PR reviews, run Claude and capture the full output
            return self._execute_review_with_claude(prompt)
        
        result = self._execute_llm_tool('claude', prompt, max_tokens, execute_mode)
        
        if result:
            logger.debug(f"Claude response received: success={result.get('success', True)}")
            if result.get('error'):
                logger.error(f"Claude error: {result.get('error')}")
        else:
            logger.debug("Claude returned None or failed")
        
        return result
    
    def validate_meta_prompt(self, meta_prompt: str) -> bool:
        """Validate meta-prompt to prevent infinite loops."""
        logger.debug("Validating meta-prompt")
        
        # Check for None or empty
        if not meta_prompt:
            logger.debug("Validation failed: Meta-prompt is None or empty")
            return False
        
        # Check for minimum content requirements
        if len(meta_prompt.strip()) < 100:
            logger.debug(f"Validation failed: Meta-prompt too short ({len(meta_prompt.strip())} chars < 100)")
            return False
        
        # Check for presence of key sections
        required_sections = ['DECONSTRUCT', 'DIAGNOSE', 'DEVELOP', 'DELIVER']
        missing_sections = []
        for section in required_sections:
            if section not in meta_prompt:
                missing_sections.append(section)
        
        if missing_sections:
            logger.debug(f"Validation failed: Missing required sections: {missing_sections}")
            return False
        
        # Check for problematic patterns that might cause loops
        problematic_patterns = [
            'generate another prompt',
            'create a meta-prompt',
            'build a prompt for',
            'construct a prompt'
        ]
        
        meta_lower = meta_prompt.lower()
        found_patterns = []
        for pattern in problematic_patterns:
            if pattern in meta_lower:
                found_patterns.append(pattern)
        
        if found_patterns:
            logger.debug(f"Validation failed: Found problematic patterns: {found_patterns}")
            return False
        
        logger.debug("Meta-prompt validation passed")
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
        logger.info(f"Starting two-stage prompt execution for task type: {task_type}")
        logger.debug(f"Task data keys: {list(task_data.keys())}")
        logger.debug(f"Prompt-only mode: {prompt_only}")
        
        results = {
            'success': False,
            'meta_prompt': '',
            'optimized_prompt': '',
            'execution_result': None,
            'error': None
        }
        
        try:
            # Stage 1: Generate meta-prompt
            logger.info("Stage 1: Generating meta-prompt")
            meta_prompt = self.generate_meta_prompt(task_type, task_data, claude_md_content)
            results['meta_prompt'] = meta_prompt
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("=" * 80)
                logger.debug("META-PROMPT GENERATED:")
                logger.debug("-" * 80)
                logger.debug(meta_prompt)
                logger.debug("=" * 80)
            
            # Validate meta-prompt
            logger.debug("Validating meta-prompt")
            if not self.validate_meta_prompt(meta_prompt):
                logger.error("Meta-prompt validation failed")
                logger.debug(f"Meta-prompt length: {len(meta_prompt)}")
                logger.debug(f"Meta-prompt contains required sections: {all(s in meta_prompt for s in ['DECONSTRUCT', 'DIAGNOSE', 'DEVELOP', 'DELIVER'])}")
                results['error'] = "Invalid meta-prompt generated"
                return results
            logger.debug("Meta-prompt validation passed")
            
            # Stage 2: Generate optimized prompt
            logger.info("Stage 2: Generating optimized prompt")
            logger.debug("Attempting to use LLM tool first")
            llm_result = self.build_with_llm(meta_prompt)
            if not llm_result:
                logger.debug("LLM tool failed or unavailable, falling back to Claude")
                claude_result = self.build_with_claude(meta_prompt)
                if not claude_result:
                    logger.error("Both LLM and Claude tools failed to generate optimized prompt")
                    results['error'] = "Failed to generate optimized prompt"
                    return results
                logger.debug("Successfully generated prompt with Claude")
                prompt_result = claude_result
            else:
                logger.debug("Successfully generated prompt with LLM tool")
                prompt_result = llm_result
            
            optimized_prompt = prompt_result.get('optimized_prompt', prompt_result.get('result', ''))
            if not optimized_prompt:
                logger.error("No optimized prompt found in response")
                logger.debug(f"Response keys: {list(prompt_result.keys())}")
                results['error'] = "No optimized prompt in response"
                return results
            
            logger.info(f"Optimized prompt generated: {len(optimized_prompt)} characters")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("=" * 80)
                logger.debug("OPTIMIZED PROMPT:")
                logger.debug("-" * 80)
                logger.debug(optimized_prompt)
                logger.debug("=" * 80)
            
            results['optimized_prompt'] = optimized_prompt
            
            # Stage 3: Execute optimized prompt (if not prompt-only mode)
            if not prompt_only:
                logger.info("Stage 3: Executing optimized prompt with Claude")
                logger.debug(f"Prompt length: {len(optimized_prompt)} characters")
                logger.debug("Decision: Proceeding with Claude execution (not prompt-only mode)")
                
                execution_result = self.build_with_claude(optimized_prompt, execute_mode=True)
                results['execution_result'] = execution_result
                
                # Analyze execution result
                if execution_result is None:
                    logger.error("Claude execution returned None")
                    results['error'] = "Claude execution failed or timed out - consider increasing timeout or checking Claude availability"
                    results['success'] = False
                    return results
                
                # Log execution result analysis
                if isinstance(execution_result, dict):
                    logger.debug(f"Execution result keys: {list(execution_result.keys())}")
                    if execution_result.get('success') is False:
                        logger.error(f"Execution failed: {execution_result.get('error')}")
                        results['error'] = execution_result.get('error')
                        results['success'] = False
                        return results
                
                logger.info("Claude execution completed successfully")
            else:
                logger.info("Skipping Stage 3: Prompt-only mode enabled")
            
            results['success'] = True
            logger.info(f"Two-stage prompt execution completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Two-stage prompt execution failed with exception: {e}")
            logger.debug("Exception details:", exc_info=True)
            results['error'] = str(e)
            return results
    
    def _execute_review_with_claude(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Execute Claude specifically for PR reviews.
        
        This method runs Claude in headless mode and captures the full output
        for PR review comments.
        """
        logger.info("Executing Claude for PR review")
        logger.debug(f"PR review prompt length: {len(prompt)} characters")
        
        # Log full PR review prompt in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("=" * 80)
            logger.debug("FULL PR REVIEW PROMPT:")
            logger.debug("-" * 80)
            logger.debug(prompt)
            logger.debug("=" * 80)
        try:
            # Write prompt to temporary file to avoid shell escaping issues
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name
            
            try:
                # Run Claude in headless mode to generate the review
                cmd = ['claude', '-p', prompt_file, '--permission-mode', 'bypassPermissions']
                
                logger.debug(f"Running command: {cmd}")
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
                    logger.info(f"Claude review completed successfully")
                    logger.debug(f"Output length: {len(output)} chars")
                    
                    # Log full review response in debug mode
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("=" * 80)
                        logger.debug("FULL PR REVIEW RESPONSE:")
                        logger.debug("-" * 80)
                        logger.debug(output)
                        logger.debug("=" * 80)
                    
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
                'error': f"Unexpected error executing Claude review: {e}",
                'exception': str(e)
            }