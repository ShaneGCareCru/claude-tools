"""Core workflow logic and orchestration for claude-tasker execution."""
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from .pr_body_generator import PRBodyGenerator


class WorkflowLogic:
    """Orchestrates claude-tasker execution workflow with agent coordination."""
    
    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize workflow logic.
        
        Args:
            repo_path: Path to git repository. Defaults to current directory.
        """
        self.repo_path = repo_path or Path.cwd()
        self.agents_dir = self.repo_path / ".claude" / "agents"
        self.pr_body_generator = PRBodyGenerator(repo_path)
        
    def execute_two_stage_workflow(self, issue_number: str, mode: str = "issue") -> Dict[str, Any]:
        """Execute two-stage workflow: meta-prompt generation → Claude execution.
        
        Args:
            issue_number: GitHub issue number
            mode: Execution mode ('issue', 'pr-review', 'bug')
            
        Returns:
            Dictionary containing workflow results
        """
        # Stage 1: Meta-prompt generation
        meta_prompt = self.generate_meta_prompt(issue_number, mode)
        
        # Stage 2: Claude execution with optimized prompt
        result = self.execute_with_claude(meta_prompt, issue_number)
        
        return {
            "meta_prompt": meta_prompt,
            "execution_result": result,
            "mode": mode,
            "issue_number": issue_number
        }
    
    def generate_meta_prompt(self, issue_number: str, mode: str) -> Dict[str, Any]:
        """Generate meta-prompt for optimized Claude execution.
        
        Args:
            issue_number: GitHub issue number
            mode: Execution mode
            
        Returns:
            Meta-prompt structure
        """
        # Get issue context
        issue_context = self._get_issue_context(issue_number)
        
        # Select appropriate agent
        agent_content = self._select_agent(mode)
        
        # Build meta-prompt
        meta_prompt = {
            "mode": mode,
            "issue_number": issue_number,
            "issue_context": issue_context,
            "agent": agent_content,
            "framework": "lyra-dev-4d",
            "instructions": self._build_4d_instructions()
        }
        
        return meta_prompt
    
    def execute_with_claude(self, meta_prompt: Dict[str, Any], issue_number: str) -> Dict[str, Any]:
        """Execute Claude with optimized prompt from meta-prompt stage.
        
        Args:
            meta_prompt: Generated meta-prompt structure
            issue_number: GitHub issue number
            
        Returns:
            Claude execution results
        """
        try:
            # Create temporary prompt file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(meta_prompt, f, indent=2)
                prompt_file = f.name
            
            # Execute Claude with JSON prompt
            result = subprocess.run(
                ["claude", "--input", prompt_file, "--output-format", "json"],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            # Clean up
            Path(prompt_file).unlink(missing_ok=True)
            
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"raw_output": result.stdout, "error": "Invalid JSON response"}
            else:
                return {"error": result.stderr, "returncode": result.returncode}
                
        except Exception as e:
            return {"error": str(e), "stage": "claude_execution"}
    
    def _get_issue_context(self, issue_number: str) -> Dict[str, Any]:
        """Get GitHub issue context.
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Issue context dictionary
        """
        try:
            result = subprocess.run(
                ["gh", "issue", "view", issue_number, "--json", "title,body,labels,assignees"],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            
        except Exception:
            pass
        
        return {
            "title": "Unknown Issue",
            "body": "Unable to fetch issue details",
            "labels": [],
            "assignees": []
        }
    
    def _select_agent(self, mode: str) -> Optional[str]:
        """Select appropriate agent based on execution mode.
        
        Args:
            mode: Execution mode
            
        Returns:
            Agent content or None if not found
        """
        agent_map = {
            "issue": "github-issue-implementer.md",
            "pr-review": "pr-reviewer.md",
            "bug": "bug-analyzer.md"
        }
        
        if not self.agents_dir.exists():
            return None
        
        agent_file = agent_map.get(mode)
        if not agent_file:
            return None
        
        agent_path = self.agents_dir / agent_file
        if agent_path.exists():
            try:
                return agent_path.read_text(encoding='utf-8')
            except Exception:
                pass
        
        return None
    
    def _build_4d_instructions(self) -> Dict[str, str]:
        """Build Lyra-Dev 4-D methodology instructions.
        
        Returns:
            4-D framework instructions
        """
        return {
            "DECONSTRUCT": "Analyze the task requirements and current codebase state",
            "DIAGNOSE": "Identify gaps between claimed and actual implementation status",
            "DEVELOP": "Create step-by-step implementation plan",
            "DELIVER": "Implement the solution with proper testing and documentation"
        }
    
    def verify_completion_status(self, issue_number: str) -> Dict[str, Any]:
        """Implement status verification protocol to detect false completion claims.
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Status verification results
        """
        # Get current issue status
        issue_context = self._get_issue_context(issue_number)
        
        # Check for completion indicators
        title = issue_context.get("title", "").lower()
        body = issue_context.get("body", "").lower()
        labels = [label.get("name", "").lower() for label in issue_context.get("labels", [])]
        
        completion_indicators = [
            "completed" in title,
            "done" in title,
            "completed" in body,
            "completed" in labels,
            "done" in labels
        ]
        
        claims_completion = any(completion_indicators)
        
        # Verify against actual implementation
        # This would need integration with actual verification logic
        verification_result = {
            "issue_number": issue_number,
            "claims_completion": claims_completion,
            "title_indicates_completion": "completed" in title or "done" in title,
            "labels_indicate_completion": "completed" in labels or "done" in labels,
            "verification_needed": claims_completion
        }
        
        return verification_result
    
    def execute_audit_and_implement(self, issue_number: str) -> Dict[str, Any]:
        """Execute AUDIT-AND-IMPLEMENT workflow.
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Audit and implementation results
        """
        results = {}
        
        # Audit phase
        audit_prompt = self._build_audit_prompt(issue_number)
        audit_result = self._execute_claude_command(audit_prompt, "audit")
        results["audit"] = audit_result
        
        # Implementation phase (if audit reveals gaps)
        if audit_result.get("gaps_found", True):
            impl_prompt = self._build_implementation_prompt(issue_number, audit_result)
            impl_result = self._execute_claude_command(impl_prompt, "implement")
            results["implementation"] = impl_result
        
        return results
    
    def _build_audit_prompt(self, issue_number: str) -> str:
        """Build audit phase prompt.
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Audit prompt string
        """
        issue_context = self._get_issue_context(issue_number)
        
        return f"""AUDIT PHASE - Issue #{issue_number}

Issue: {issue_context.get('title', 'Unknown')}
Description: {issue_context.get('body', 'No description')}

Please audit the current implementation status:
1. What has been claimed as completed?
2. What evidence exists in the codebase?
3. What gaps exist between claims and reality?
4. What work remains to be done?

Provide a structured audit report."""
    
    def _build_implementation_prompt(self, issue_number: str, audit_result: Dict[str, Any]) -> str:
        """Build implementation phase prompt.
        
        Args:
            issue_number: GitHub issue number
            audit_result: Results from audit phase
            
        Returns:
            Implementation prompt string
        """
        return f"""IMPLEMENTATION PHASE - Issue #{issue_number}

Based on audit findings: {audit_result.get('raw_output', 'Audit completed')}

Please implement the identified missing components:
1. Address each gap identified in the audit
2. Follow TDD approach where tests exist
3. Maintain existing code conventions
4. Provide working, tested implementations

Focus only on filling the gaps, not duplicating existing work."""
    
    def _execute_claude_command(self, prompt: str, phase: str) -> Dict[str, Any]:
        """Execute Claude command for specific phase.
        
        Args:
            prompt: Prompt content
            phase: Execution phase name
            
        Returns:
            Execution results
        """
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                temp_file = f.name
            
            result = subprocess.run(
                ["claude", "--input", temp_file],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            Path(temp_file).unlink(missing_ok=True)
            
            return {
                "phase": phase,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
        except Exception as e:
            return {
                "phase": phase,
                "error": str(e),
                "success": False
            }
    
    def process_issue_range(self, start: int, end: int, timeout: int = 10, prompt_only: bool = False) -> List[Dict[str, Any]]:
        """Process a range of GitHub issues.
        
        Args:
            start: Start issue number
            end: End issue number  
            timeout: Delay between issues in seconds
            prompt_only: Only generate prompts, don't execute
            
        Returns:
            List of processing results
        """
        results = []
        
        for issue_num in range(start, end + 1):
            issue_number = str(issue_num)
            
            try:
                if prompt_only:
                    # Generate meta-prompt only
                    meta_prompt = self.generate_meta_prompt(issue_number, "issue")
                    results.append({
                        "issue_number": issue_number,
                        "meta_prompt": meta_prompt,
                        "mode": "prompt_only"
                    })
                else:
                    # Full execution
                    result = self.execute_two_stage_workflow(issue_number, "issue")
                    results.append(result)
                
                # Delay between issues
                if issue_num < end:
                    time.sleep(timeout)
                    
            except Exception as e:
                results.append({
                    "issue_number": issue_number,
                    "error": str(e),
                    "success": False
                })
        
        return results
    
    def create_timestamped_branch(self, issue_number: str) -> Dict[str, Any]:
        """Create timestamped branch for issue.
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Branch creation results
        """
        timestamp = str(int(time.time()))
        branch_name = f"issue-{issue_number}-{timestamp}"
        
        try:
            result = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            return {
                "branch_name": branch_name,
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
            
        except Exception as e:
            return {
                "branch_name": branch_name,
                "success": False,
                "error": str(e)
            }
    
    def handle_exponential_backoff(self, command: List[str], max_retries: int = 3) -> subprocess.CompletedProcess:
        """Handle API rate limits with exponential backoff.
        
        Args:
            command: Command to execute
            max_retries: Maximum number of retries
            
        Returns:
            Final command result
        """
        for attempt in range(max_retries + 1):
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    cwd=self.repo_path
                )
                
                # Check for rate limit in stderr
                if result.stderr and "rate limit" in result.stderr.lower():
                    if attempt < max_retries:
                        # Exponential backoff: 2^attempt seconds
                        wait_time = 2 ** attempt
                        time.sleep(wait_time)
                        continue
                
                return result
                
            except Exception as e:
                if attempt == max_retries:
                    # Return a failed result
                    return subprocess.CompletedProcess(
                        command, 1, "", str(e)
                    )
                time.sleep(2 ** attempt)
        
        # Should not reach here, but return failed result as fallback
        return subprocess.CompletedProcess(command, 1, "", "Max retries exceeded")