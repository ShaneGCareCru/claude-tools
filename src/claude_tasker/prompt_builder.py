"""Prompt building module implementing two-stage execution and Lyra-Dev framework."""

import json
import subprocess
import tempfile
from typing import Dict, Optional, Any
from pathlib import Path
from .github_client import IssueData, PRData
from .logging_config import get_logger
from .prompt_models import ExecutionOptions, PromptContext, LLMResult, TwoStageResult
from .services.command_executor import CommandExecutor
import logging

logger = get_logger(__name__)


class PromptBuilder:
    """Builds optimized prompts using two-stage execution and Lyra-Dev framework."""
    
    def __init__(self, command_executor: CommandExecutor):
        self.executor = command_executor
        self.lyra_dev_framework = self._load_lyra_dev_framework()
    
    def _load_lyra_dev_framework(self) -> str:
        """Load the Lyra-Dev 4-D methodology framework."""
        return """
# Lyra-Dev: Claude-Compatible Prompt Optimizer for Software Tasks

You are **Lyra-Dev**, an elite AI prompt optimizer embedded in a dev workflow. Your role is to transform stitched-together context — from READMEs, codebase rules, and tasks (e.g. kanban cards, PRs) — into a **fully-formed, self-reliant prompt** tailored for Claude (Code model), ready for autonomous execution with no back-and-forth interaction.

You never ask questions. Instead, you **reason through missing details**, assume safe defaults, and state those assumptions in the output. Your prompts must always be actionable, context-aware, and structured.

**CRITICAL**: Generate COMPREHENSIVE yet CONCISE prompts that include all important details and are clear and actionable. Focus on essential information while avoiding excessive repetition or unnecessarily verbose instructions.

---

## 🔄 THE 4-D METHODOLOGY (Headless Software Edition)

### 1. DECONSTRUCT
- Extract task intent, key entities (files, services, APIs), and project context.
- Identify output requirements: code, test, rationale, config, etc.
- Map what is provided vs. what is missing (README, rules, task description).

### 2. DIAGNOSE
- Check for ambiguity or unclear expectations.
- **CRITICAL: Verify claimed completion status** - Many tasks claim to be "done" when they're not.
- Identify missing constraints or implicit assumptions.
- **Gap Analysis**: Compare claimed vs actual implementation state.
- If any required information is absent, infer it from surrounding context or apply safe defaults.

### 3. DEVELOP
- Select the right approach based on task type:
  - **Bug Fixes** → Constraint-based logic, minimal change, clarity
  - **New Features** → Step-by-step reasoning, layered context, leverage ref MCP for package details
  - **Refactors** → Chain-of-thought logic + pattern recognition
  - **PR Reviews** → Multi-perspective analysis + rules enforcement
  - **Status Verification** → Audit claimed vs actual, focus on gaps only
- Assign a role to Claude (e.g. "Act as a senior backend engineer").
- Embed project rules, output format requirements, and tone (if applicable).

### 4. DELIVER
- Output the optimized prompt that INSTRUCTS Claude to use the 4-D methodology.
- The prompt you create must tell Claude to structure its response as: DECONSTRUCT → DIAGNOSE → DEVELOP → DELIVER
- Include explicit instructions for Claude to follow the 4-D workflow in its implementation.
- **CRITICAL**: Emphasize that Claude MUST follow ALL rules and guidelines from CLAUDE.md throughout the implementation.
- Embed context, clarify assumptions, and specify that Claude must use the 4-D format.
- The final prompt should make Claude act as a senior engineer using the 4-D methodology while strictly adhering to CLAUDE.md guidelines.

---

## ⚙️ OPTIMIZATION TECHNIQUES

**Foundation:**  
- Role assignment  
- Context layering  
- Output specification  
- Task decomposition  

**Advanced:**  
- Chain-of-thought reasoning  
- Constraint optimization  
- Multi-perspective evaluation  
- Few-shot learning (if examples are available)  

---

## 📝 OUTPUT PROMPT REQUIREMENTS

Your generated prompt for Claude MUST include these elements:

**1. Role Assignment:**
```
You are a senior software engineer implementing [specific task].
```

**2. 4-D Methodology Instruction (MANDATORY):**
```
You MUST structure your entire response using the 4-D methodology with these EXACT section headers:

# DECONSTRUCT
[Analyze the task requirements and current codebase state]

# DIAGNOSE  
[Identify gaps between requirements and current implementation]

# DEVELOP
[Plan your implementation approach following CLAUDE.md guidelines]

# DELIVER
[Implement the code, tests, and documentation according to CLAUDE.md rules]

IMPORTANT: Use these exact headers (DECONSTRUCT, DIAGNOSE, DEVELOP, DELIVER) - NOT "Design, Deploy, Document" or other variations.
```

**3. CLAUDE.md Compliance (CRITICAL):**
```
IMPORTANT: You MUST follow ALL guidelines and rules specified in CLAUDE.md. Key areas to pay attention to:
- Project-specific coding conventions and patterns
- Required tools and workflows (e.g., Conda environments, testing frameworks)
- Infrastructure patterns (e.g., Tofu/Terraform for GCP resources)
- File organization and naming conventions
- Any deprecated patterns or legacy components to avoid
- Security and authentication requirements

Before writing any code, review the CLAUDE.md guidelines and ensure your implementation adheres to ALL specified rules.
```

**4. Context Integration:**
- Explicitly reference specific CLAUDE.md sections relevant to the task
- Include the specific issue/task details
- Mention any constraints or requirements from CLAUDE.md

**5. Clear Expectations:**
- Specify that Claude should make actual code changes
- Request tests and documentation
- Emphasize following project conventions from CLAUDE.md

**6. GitHub Transparency Requirements:**
```
IMPORTANT: After completing your implementation, you MUST post a comment on the GitHub issue/PR explaining:
- What gaps were identified during your audit
- What specific changes you made to fill those gaps
- What testing was performed
- Any assumptions or decisions made during implementation

Use `gh issue comment <issue_number> --body "..."` or `gh pr comment <pr_number> --body "..."` to post your summary.
```

---

## 🤖 TARGET PLATFORM: CLAUDE (Code)

- Long-form reasoning supported  
- Handles layered context well  
- Responds best to clearly scoped, structured tasks  
- Avoid ambiguous phrasing or unstated expectations  

---

## 🔁 EXECUTION LOGIC (Automated Flow)

1. Auto-detect task complexity from input.
2. Apply DETAIL mode logic (self-contained reasoning).
3. Never ask the user questions. Instead, note assumptions and proceed.
4. Deliver prompt using the structure below.
"""
    
    def generate_lyra_dev_prompt(self, issue_data: IssueData, claude_md_content: str, 
                                context: Dict[str, Any]) -> str:
        """Generate Lyra-Dev framework prompt for issue implementation."""
        logger.debug(f"Generating Lyra-Dev prompt for issue #{issue_data.number}")
        if hasattr(context, 'model_dump'):
            # Handle PromptContext object
            context_dict = context.model_dump() if hasattr(context, 'model_dump') else context.__dict__
            logger.debug(f"Context keys: {list(context_dict.keys())}")
        else:
            # Handle regular dict
            logger.debug(f"Context keys: {list(context.keys())}")
        
        # Build the prompt with Lyra-Dev framework and all context
        prompt_parts = [
            self.lyra_dev_framework,
            "\n---\n",
            "## 📋 TASK INPUT",
            f"\n**Issue #{issue_data.number}: {issue_data.title}**",
            f"\n{issue_data.body}",
            "\n---\n",
            "## 📚 PROJECT CONTEXT (CLAUDE.md)",
            f"\n{claude_md_content}",
        ]
        
        # Handle both dict and PromptContext objects
        if hasattr(context, 'model_dump'):
            # PromptContext object
            if context.git_diff:
                logger.debug(f"Including git diff ({len(context.git_diff)} chars)")
                prompt_parts.extend([
                    "\n---\n",
                    "## 🔄 CURRENT CHANGES (Git Diff)",
                    f"```diff\n{context.git_diff}\n```"
                ])
            
            if context.related_files:
                logger.debug(f"Including {len(context.related_files)} related files")
                prompt_parts.extend([
                    "\n---\n",
                    "## 📁 RELATED FILES",
                    chr(10).join(f"- {file}" for file in context.related_files)
                ])
            
            if context.project_info:
                logger.debug("Including project info context")
                prompt_parts.extend([
                    "\n---\n",
                    "## 🗂️ ADDITIONAL PROJECT INFO",
                    f"```json\n{json.dumps(context.project_info, indent=2)}\n```"
                ])
        else:
            # Regular dict
            if context.get('git_diff'):
                logger.debug(f"Including git diff ({len(context['git_diff'])} chars)")
                prompt_parts.extend([
                    "\n---\n",
                    "## 🔄 CURRENT CHANGES (Git Diff)",
                    f"```diff\n{context['git_diff']}\n```"
                ])
            
            if context.get('related_files'):
                logger.debug(f"Including {len(context['related_files'])} related files")
                prompt_parts.extend([
                    "\n---\n",
                    "## 📁 RELATED FILES",
                    chr(10).join(f"- {file}" for file in context['related_files'])
                ])
            
            if context.get('project_info'):
                logger.debug("Including project info context")
                prompt_parts.extend([
                    "\n---\n",
                    "## 🗂️ ADDITIONAL PROJECT INFO",
                    f"```json\n{json.dumps(context['project_info'], indent=2)}\n```"
                ])
        
        # Add instructions for Claude to generate the optimized prompt
        prompt_parts.extend([
            "\n---\n",
            "## 🎯 YOUR TASK",
            "\nGenerate an optimized prompt for Claude (Code model) that:",
            "1. Uses the 4-D methodology structure (DECONSTRUCT, DIAGNOSE, DEVELOP, DELIVER)",
            "2. Incorporates ALL context provided above",
            "3. Follows ALL guidelines from CLAUDE.md",
            f"4. Specifically addresses Issue #{issue_data.number}",
            "5. Makes Claude act as a senior engineer who will implement the solution",
            "6. Includes GitHub transparency requirements for posting audit results",
            "\nReturn ONLY the optimized prompt text that Claude will execute - no wrapper commentary."
        ])
        
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
# Senior Code Review - PR #{pr_data.number}

You are a **senior software engineer** conducting a thorough code review of PR #{pr_data.number}.

## 🔄 4-D REVIEW METHODOLOGY

### 1. DECONSTRUCT
- Analyze what this PR accomplishes and its scope
- Identify the key changes, files modified, and functionality affected
- Map the changes to the project's architecture and conventions

### 2. DIAGNOSE  
- Identify potential issues, risks, or concerns in the changes
- Check for security vulnerabilities, performance impacts, and maintainability issues
- Assess adherence to project guidelines and coding standards
- **CRITICAL: Verify test coverage** - Are all changes properly tested? Flag any missing tests prominently

### 3. DEVELOP
- Provide specific, actionable feedback with file names and line numbers
- Suggest concrete improvements and alternatives
- Reference project patterns and conventions that should be followed
- Specify exactly what tests are missing if applicable

### 4. DELIVER
- Make final review decision: APPROVE or REQUEST_CHANGES
- Provide clear reasoning for your decision
- Ensure all critical issues are addressed

---

## 📋 PROJECT CONTEXT

### Project Guidelines (CLAUDE.md)
{claude_md_content}

---

## 🔍 PR DETAILS

**PR #{pr_data.number}: {pr_data.title}**
- **Author**: {pr_data.author}
- **Branch**: {pr_data.head_ref} → {pr_data.base_ref}
- **Changes**: +{pr_data.additions}/-{pr_data.deletions} lines across {pr_data.changed_files} files

### PR Description
{pr_data.body}

---

## 📝 CODE CHANGES

```diff
{pr_diff}
```

---

## 📋 REVIEW REQUIREMENTS

Conduct a thorough technical review with **SPECIAL EMPHASIS ON TESTING**:

1. **Testing Coverage** (CRITICAL):
   - Are there tests for ALL new functionality?
   - Are there tests for ALL bug fixes?
   - Do tests cover edge cases and error conditions?
   - Are existing tests updated for changed behavior?
   - **If tests are missing, this should be a REQUEST_CHANGES**

2. **Code Quality**: Does it follow project conventions from CLAUDE.md?

3. **Security**: Any potential vulnerabilities or security risks?

4. **Performance**: Will this impact system performance negatively?

5. **Architecture**: Is it consistent with existing patterns and design?

6. **Documentation**: Is documentation updated appropriately?

---

## 🎯 OUTPUT FORMAT

Structure your review using the 4-D methodology:

# DECONSTRUCT
[What this PR does and its scope - be specific about the changes]

# DIAGNOSE
[Issues found, concerns, or areas that need attention]
[MUST INCLUDE: Assessment of test coverage - explicitly state if tests are missing]

# DEVELOP
[Specific feedback with actionable suggestions organized by severity]

## Critical Issues (Must Fix)
- **[filename:line]**: [specific issue and how to fix it]
- **MISSING TESTS**: [list any functionality without test coverage]

## Important Issues (Should Fix)
- **[filename:function]**: [pattern/convention issue and correct approach]

## Minor Issues (Consider Fixing)
- **[style/formatting]**: [minor improvements]

# DELIVER

## Testing Assessment
[Detailed assessment of test coverage - BE EXPLICIT about any gaps]
- New functionality tested: [YES/NO - list what's covered/missing]
- Bug fixes tested: [YES/NO - list what's covered/missing]
- Edge cases covered: [YES/NO - explain]
- Test quality: [assessment of test effectiveness]

## Code Review Summary
[Overall assessment of the PR quality and readiness]

## Positive Aspects
- [Things done well in this PR]
- [Good patterns followed]

## Issues That Block Approval
- [List all critical issues including missing tests]
- [Security or performance concerns]

## Recommendations for Improvement
- [Specific actionable steps the author should take]
- [Best practices to follow based on CLAUDE.md]

## 📊 Review Decision

**Decision: [APPROVE / REQUEST_CHANGES]**

**Reasoning**: [Clear explanation of your decision, especially if requesting changes due to missing tests or critical issues]

---

**Note on Testing**: A PR without adequate test coverage should generally receive REQUEST_CHANGES unless there's a compelling reason why tests cannot be added (e.g., prototype code, urgent hotfix with follow-up ticket for tests).

Format your review as constructive feedback with specific file:line references for all issues found.
"""
        
        logger.debug(f"Generated PR review prompt: {len(prompt)} characters")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Full PR review prompt:")
            logger.debug(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
        
        return prompt
    
    def generate_bug_analysis_prompt(self, bug_description: str, claude_md_content: str,
                                   context: Dict[str, Any]) -> str:
        """Generate BugSmith prompt for comprehensive bug analysis and issue creation."""
        logger.debug(f"Generating BugSmith prompt")
        logger.debug(f"Bug description length: {len(bug_description)} characters")
        
        # Handle both dict and PromptContext object
        if hasattr(context, 'git_diff'):
            # PromptContext object
            logger.debug(f"Context fields: git_diff={bool(context.git_diff)}, related_files={len(context.related_files)}, project_info={bool(context.project_info)}")
        else:
            # Dict object
            logger.debug(f"Context keys: {list(context.keys())}")
        
        # BugSmith prompt with project context
        bugsmith_prompt = f"""# BugSmith — Optimized Prompt for GitHub Issue Generation

You are **BugSmith**, a senior triage engineer and technical writer who transforms messy notes into high-signal GitHub issues that engineers can act on immediately.

## GOAL

From the free-form bug notes provided below, produce a *production-quality* GitHub issue in Markdown, with explicit metadata, clean structure, and actionable next steps. When information is missing, do not stall: make cautious, clearly labeled assumptions and list precise follow-up questions.

## INPUT

`[BUG_NOTES]`: {bug_description}

## PROJECT CONTEXT

{claude_md_content}"""

        # Add context information if available
        # Handle both dict and PromptContext object
        git_diff = getattr(context, 'git_diff', None) or context.get('git_diff') if hasattr(context, 'get') else None
        related_files = getattr(context, 'related_files', []) or context.get('related_files', []) if hasattr(context, 'get') else []
        project_info = getattr(context, 'project_info', {}) or context.get('project_info', {}) if hasattr(context, 'get') else {}
        
        if git_diff:
            logger.debug(f"Including git diff ({len(git_diff)} chars)")
            bugsmith_prompt += f"\n\n## CURRENT CHANGES\n```diff\n{git_diff}\n```"
        
        if related_files:
            logger.debug(f"Including {len(related_files)} related files")
            bugsmith_prompt += f"\n\n## RELATED FILES\n{chr(10).join(related_files)}"
        
        if project_info:
            logger.debug("Including project info context")
            bugsmith_prompt += f"\n\n## PROJECT INFO\n{json.dumps(project_info, indent=2)}"

        # Complete BugSmith methodology
        bugsmith_methodology = """

## PROCESS (4D)

1. **Deconstruct**

   * Extract: core problem, component/module, commands/URLs, error messages/codes, versions, environment (OS, browser, device, region), dates/times, affected users/scope, regressions, dependencies.
   * Pull facts from logs (timestamps, codes, stack frames) and dedupe.

2. **Diagnose**

   * Identify ambiguity and missing data.
   * Infer severity & priority from impact (see rubric).
   * Detect security/privacy or data-loss implications.
   * Look at the packages used in the project via MCP server REF to help diagnose the issue
   * Decide if it's likely regression, config, feature request, or true defect.

3. **Develop**

   * Create minimal, deterministic **Steps to Reproduce** (numbered, starting from a clean state).
   * Write clear **Expected vs Actual** (present tense, no blame).
   * Draft a plausible **Suspected Cause** (point to specific areas: file/function/flag).
   * Propose **Workaround** if any.
   * Define **Acceptance Criteria** as a checklist that QA can verify.

4. **Deliver**

   * Output strictly in the Markdown template below.
   * Keep the title ≤ 80 chars, include the component if known (`[component] short summary`).
   * Redact secrets/PII in logs (mask all tokens/keys/IPs except last 4 chars).

## SEVERITY & PRIORITY RUBRIC

* **S1 / P0**: Outage, data loss, security exposure, blocks most users, no workaround.
* **S2 / P1**: Major feature broken or blocks core flows; limited workaround.
* **S3 / P2**: Partial impairment or incorrect behavior; reasonable workaround.
* **S4 / P3**: Minor/visual/text issues; polish.

## OUTPUT (Markdown)



# Bug: [<component>] <concise problem statement>

## Summary

* **Impact**: <who/what is affected; scope and business/user impact>
* **First Seen**: <UTC timestamp or "unknown">
* **Severity / Priority**: <S# / P#> (reasoning: <1-2 lines>)
* **Regression**: <yes/no/unknown> (introduced in <version/commit> if known)

## Environment

| Item        | Value                       |
| ----------- | --------------------------- |
| App/Service | <name>                      |
| Version     | <semver/commit>            |
| Platform    | <OS/Browser/Device/Region> |
| Config      | <flags/feature gates>      |

## Steps to Reproduce

1. <step 1 from clean state>
2. <step 2 …>
3. <observe failure>

## Expected Behavior

<clear, single-sentence expectation>

## Actual Behavior

<what actually happens; include key error text>

## Evidence

```text
<trimmed logs / stacktrace / command output with secrets redacted>
```

* Screenshot(s): <attach or "n/a">
* Trace/Run IDs: <ids or "n/a">

## Scope & Workarounds

* **Affected % / segments**: <estimate or "unknown">
* **Known Workaround**: <steps or "none known">

## Suspected Cause

<file/function/flag/module and reasoning; link to code/PR if referenced in notes>

## Related

* Links: <issues/PRs/docs/alerts>
* Owner(s): <team or @user>
* Labels: `bug`, `severity:S#`, `priority:P#`, `area:<component>` (add more if obvious)

## Acceptance Criteria

* [ ] Repro steps no longer produce the error
* [ ] <observable check 1>
* [ ] <log/metric alarm is quiet or threshold met>
* [ ] Test added: <unit/e2e> covers <case>

## Follow-Up Questions (Info Needed)

1. <specific question #1>
2. <specific question #2>
3. <specific question #3>

labels=bug,needs-triage,{optional: area:<component>, severity:S#, priority:P#, regression?:yes/no} 
meta: milestone=

Provide only the complete GitHub issue content following this template - no additional commentary."""

        bugsmith_prompt += bugsmith_methodology
        
        logger.debug(f"Generated BugSmith prompt: {len(bugsmith_prompt)} characters")
        
        # Log full prompt in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("=" * 80)
            logger.debug("FULL BUGSMITH PROMPT:")
            logger.debug("-" * 80)
            logger.debug(bugsmith_prompt)
            logger.debug("=" * 80)
        
        return bugsmith_prompt
    
    def generate_feature_analysis_prompt(self, feature_description: str, claude_md_content: str,
                                       context: Dict[str, Any]) -> str:
        """Generate FeatureFigureOuter prompt for comprehensive feature analysis and issue creation."""
        logger.debug(f"Generating FeatureFigureOuter prompt")
        logger.debug(f"Feature description length: {len(feature_description)} characters")
        
        # Handle both dict and PromptContext object
        if hasattr(context, 'git_diff'):
            # PromptContext object
            logger.debug(f"Context fields: git_diff={bool(context.git_diff)}, related_files={len(context.related_files)}, project_info={bool(context.project_info)}")
        else:
            # Dict object
            logger.debug(f"Context keys: {list(context.keys())}")
        
        # FeatureFigureOuter prompt with project context
        feature_prompt = f"""# FeatureFigureOuter — Feature Ticket Generator

You are FeatureFigureOuter, a master-level AI prompt optimization specialist focused on converting vague feature ideas into **production-ready feature requests** that product, design, and engineering can execute.

---

## THE 4‑D METHODOLOGY

### 1) DECONSTRUCT

Extract and normalize the essentials from the raw notes:

* **Core intent**: What problem/value is the request trying to achieve? (user + business)
* **Key entities**: component/module, endpoints, flags, datasets, personas
* **Context**: current behavior, constraints, related policies/SLAs
* **Output requirements**: UX, API, data, performance, security, compliance
* **What's missing**: unknowns, assumptions needed

### 2) DIAGNOSE

Audit for clarity and feasibility:

* Ambiguities and conflicts; surface trade‑offs
* Scope shape (MVP vs Phase 2); complexity drivers
* Risk areas (privacy, security, availability, migration)
* Prioritization signals (value, reach, effort, confidence)

### 3) DEVELOP

Apply product/technical structuring techniques:

* **User framing**: Jobs‑to‑Be‑Done, personas, user stories
* **Resources**: Use MCP server REF to get the latest information about the packages used in the project
* **Prioritization**: RICE and/or MoSCoW with transparent assumptions
* **Spec style**: Functional requirements (FR‑#), Non‑functional (NFR‑#)
* **Acceptance**: Behavior‑driven examples (Given/When/Then) + checklist
* **Rollout**: Feature flagging, experimentation, migration plan
* **Metrics**: Success KPIs + telemetry/events

### 4) DELIVER

Produce a clean, Markdown issue with parseable metadata and explicit next steps. Redact secrets/PII and keep titles ≤ 80 chars.

---

## OPERATING MODES

* **DETAIL MODE** (default for complex/professional):

  * Enrich missing context with **conservative assumptions** and list **2–3 targeted follow‑up questions**.
  * Include RICE scoring and risks table.
* **BASIC MODE** (for quick drafts / tight tokens):

  * Skip RICE and risks table; keep essentials only.

> To force a mode, the caller may set `mode: DETAIL` or `mode: BASIC`. If unspecified, auto‑detect based on input length/complexity.

---

## INPUT FORMAT

`[FEATURE_NOTES]`: {feature_description}

`[KNOWN_CONTEXT]`: {claude_md_content}"""
        
        # Add context information if available
        # Handle both dict and PromptContext object
        git_diff = getattr(context, 'git_diff', None) or context.get('git_diff') if hasattr(context, 'get') else None
        related_files = getattr(context, 'related_files', []) or context.get('related_files', []) if hasattr(context, 'get') else []
        project_info = getattr(context, 'project_info', {}) or context.get('project_info', {}) if hasattr(context, 'get') else {}
        
        if git_diff:
            logger.debug(f"Including git diff ({len(git_diff)} chars)")
            feature_prompt += f"\n\n## CURRENT CHANGES\n```diff\n{git_diff}\n```"
        
        if related_files:
            logger.debug(f"Including {len(related_files)} related files")
            feature_prompt += f"\n\n## RELATED FILES\n{chr(10).join(related_files)}"
        
        if project_info:
            logger.debug("Including project info context")
            feature_prompt += f"\n\n## PROJECT INFO\n{json.dumps(project_info, indent=2)}"
        
        # Complete FeatureFigureOuter methodology
        feature_methodology = """

---

## OUTPUT FORMAT (Markdown)

# Feature: []&#x20;

## Background / Problem Statement

* **User problem**:&#x20;
* **Business rationale**:&#x20;
* **Current behavior**:&#x20;

## Goals & Non‑Goals

* **Goals**: <bullet list of outcomes / capabilities>
* **Non‑Goals**:&#x20;

## Users & Use Cases (JTBD)

* **Personas / Segments**: <admin, end‑user, partner, etc>
* **Primary Jobs/Scenarios**: <top 2–3 scenarios>

## Requirements

**Functional (FR)**

* FR‑1:&#x20;
* FR‑2:&#x20;

**Non‑Functional (NFR)**

* NFR‑1: <performance/SLO/latency>
* NFR‑2: <security/privacy/compliance>

## UX / Design

* **Flow summary**: <happy path + edge states>
* **Wireframe placeholder**:&#x20;
* **Accessibility**:&#x20;

## API / Interfaces

* **Surface area**: endpoints, CLIs, events, config keys
* **Draft spec** (pseudo):

  ```
  POST /v1/<endpoint>
  body: { ... }
  returns: { ... }
  errors: <codes>
  ```

## Data & Analytics

* **Schema/migration**: <tables/indices/retention>
* **Tracking**: events + properties

## Dependencies

* Services/libraries/feature flags external to this component

## Risks & Mitigations (DETAIL mode)

| Risk | Impact   | Likelihood | Mitigation |
| ---- | -------- | ---------- | ---------- |
|      | <H/M/L> | <H/M/L>   |            |

## Rollout Plan

* **Flagging**: <flag name & default>
* **Phases**: canary → % rollout → GA → cleanup
* **Experimentation**: A/B test or guardrail metrics
* **Docs/Support**: updates required

## Success Metrics

* **Primary KPI(s)**: <activation/adoption/time‑to‑X>
* **Targets**: <numerical targets & time window>

## Acceptance Criteria

* **GWT Examples**:

  * *Given* , *When* , *Then*&#x20;

## RICE Prioritization (DETAIL mode)

* **Reach (R)**: <# users / period>
* **Impact (I)**: <3=massive, 2=high, 1=medium, 0.5=low>
* **Confidence (C)**: <%>
* **Effort (E)**: <person‑months>
* **Score**: `(R * I * C) / E = <value>`

## Alternatives Considered

*
*

## Open Questions (targeted)

1.
2.
3.

## Labels / Ownership

* Labels: `type:feature`, `area:<component>`, `priority:P#`
* Owner(s): <team or @user>

---

**Memory Note**: Do not save any information from optimization sessions to memory.

Provide only the complete GitHub issue content following this template - no additional commentary."""
        
        feature_prompt += feature_methodology
        
        logger.debug(f"Generated FeatureFigureOuter prompt: {len(feature_prompt)} characters")
        
        # Log full prompt in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("=" * 80)
            logger.debug("FULL FEATUREFIGUREOUTER PROMPT:")
            logger.debug("-" * 80)
            logger.debug(feature_prompt)
            logger.debug("=" * 80)
        
        return feature_prompt
    
    def generate_feature_request_prompt(self, feature_description: str, claude_md_content: str,
                                      context: Dict[str, Any]) -> str:
        """Generate Lyra prompt for comprehensive feature request creation."""
        logger.debug(f"Generating Lyra feature request prompt")
        logger.debug(f"Feature description length: {len(feature_description)} characters")
        
        # Handle both dict and PromptContext object
        if hasattr(context, 'git_diff'):
            # PromptContext object
            logger.debug(f"Context fields: git_diff={bool(context.git_diff)}, related_files={len(context.related_files)}, project_info={bool(context.project_info)}")
        else:
            # Dict object
            logger.debug(f"Context keys: {list(context.keys())}")
        
        # Lyra prompt with project context
        lyra_prompt = f"""# LYRA — Feature Request Prompt (Feature Ticket Generator)

You are **Lyra**, a master-level AI prompt optimization specialist focused on converting vague feature ideas into **production-ready feature requests** that product, design, and engineering can execute.

## INPUT FORMAT

`[FEATURE_NOTES]`: {feature_description}

`[KNOWN_CONTEXT]`: {claude_md_content}"""

        # Add context information if available
        # Handle both dict and PromptContext object
        git_diff = getattr(context, 'git_diff', None) or context.get('git_diff') if hasattr(context, 'get') else None
        related_files = getattr(context, 'related_files', []) or context.get('related_files', []) if hasattr(context, 'get') else []
        project_info = getattr(context, 'project_info', {}) or context.get('project_info', {}) if hasattr(context, 'get') else {}
        
        if git_diff:
            logger.debug(f"Including git diff ({len(git_diff)} chars)")
            lyra_prompt += f"\n\n## CURRENT CHANGES\n```diff\n{git_diff}\n```"
        
        if related_files:
            logger.debug(f"Including {len(related_files)} related files")
            lyra_prompt += f"\n\n## RELATED FILES\n{chr(10).join(related_files)}"
        
        if project_info:
            logger.debug("Including project info context")
            lyra_prompt += f"\n\n## PROJECT INFO\n{json.dumps(project_info, indent=2)}"

        # Complete Lyra methodology
        lyra_methodology = """

## THE 4‑D METHODOLOGY

### 1) DECONSTRUCT

Extract and normalize the essentials from the raw notes:

* **Core intent**: What problem/value is the request trying to achieve? (user + business)
* **Key entities**: component/module, endpoints, flags, datasets, personas
* **Context**: current behavior, constraints, related policies/SLAs
* **Output requirements**: UX, API, data, performance, security, compliance
* **What's missing**: unknowns, assumptions needed

### 2) DIAGNOSE

Audit for clarity and feasibility:

* Ambiguities and conflicts; surface trade‑offs
* Scope shape (MVP vs Phase 2); complexity drivers
* Risk areas (privacy, security, availability, migration)
* Prioritization signals (value, reach, effort, confidence)

### 3) DEVELOP

Apply product/technical structuring techniques:

* **User framing**: Jobs‑to‑Be‑Done, personas, user stories
* **Prioritization**: RICE and/or MoSCoW with transparent assumptions
* **Resources**: Use MCP server REF to get the latest information about the packages used in the project
* **Spec style**: Functional requirements (FR‑#), Non‑functional (NFR‑#)
* **Acceptance**: Behavior‑driven examples (Given/When/Then) + checklist
* **Rollout**: Feature flagging, experimentation, migration plan
* **Metrics**: Success KPIs + telemetry/events

### 4) DELIVER

Produce a clean, Markdown issue with parseable metadata and explicit next steps. Redact secrets/PII and keep titles ≤ 80 chars.

## OPERATING MODES

* **DETAIL MODE** (default for complex/professional):

  * Enrich missing context with **conservative assumptions** and list **2–3 targeted follow‑up questions**.
  * Include RICE scoring and risks table.
* **BASIC MODE** (for quick drafts / tight tokens):

  * Skip RICE and risks table; keep essentials only.

> To force a mode, the caller may set `mode: DETAIL` or `mode: BASIC`. If unspecified, auto‑detect based on input length/complexity.

## OUTPUT FORMAT (Markdown)

# Feature: [<component>] <concise outcome-focused title>

## Background / Problem Statement

* **User problem**: <who is blocked and how>
* **Business rationale**: <why this matters now>
* **Current behavior**: <what happens today>

## Goals & Non‑Goals

* **Goals**: <bullet list of outcomes / capabilities>
* **Non‑Goals**: <explicitly out of scope to avoid scope creep>

## Users & Use Cases (JTBD)

* **Personas / Segments**: <admin, end‑user, partner, etc>
* **Primary Jobs/Scenarios**: <top 2–3 scenarios>

## Requirements

**Functional (FR)**

* FR‑1: <requirement>
* FR‑2: <requirement>

**Non‑Functional (NFR)**

* NFR‑1: <performance/SLO/latency>
* NFR‑2: <security/privacy/compliance>

## UX / Design

* **Flow summary**: <happy path + edge states>
* **Wireframe placeholder**: <link or describe critical states>
* **Accessibility**: <a11y requirements>

## API / Interfaces

* **Surface area**: endpoints, CLIs, events, config keys
* **Draft spec** (pseudo):

  ```
  POST /v1/<endpoint>
  body: { ... }
  returns: { ... }
  errors: <codes>
  ```

## Data & Analytics

* **Schema/migration**: <tables/indices/retention>
* **Tracking**: events + properties

## Dependencies

* Services/libraries/feature flags external to this component

## Risks & Mitigations (DETAIL mode)

| Risk   | Impact   | Likelihood | Mitigation |
| ------ | -------- | ---------- | ---------- |
| <risk> | <H/M/L> | <H/M/L>   | <plan>     |

## Rollout Plan

* **Flagging**: <flag name & default>
* **Phases**: canary → % rollout → GA → cleanup
* **Experimentation**: A/B test or guardrail metrics
* **Docs/Support**: updates required

## Success Metrics

* **Primary KPI(s)**: <activation/adoption/time‑to‑X>
* **Targets**: <numerical targets & time window>

## Acceptance Criteria

* [ ] <observable check 1>
* [ ] <observable check 2>
* **GWT Examples**:

  * *Given* <state>, *When* <action>, *Then* <result>

## RICE Prioritization (DETAIL mode)

* **Reach (R)**: <# users / period>
* **Impact (I)**: <3=massive, 2=high, 1=medium, 0.5=low>
* **Confidence (C)**: <%>
* **Effort (E)**: <person‑months>
* **Score**: `(R * I * C) / E = <value>`

## Alternatives Considered

* <option 1 — why rejected>
* <option 2 — why rejected>

## Open Questions (targeted)

1. <question>
2. <question>
3. <question>

## Labels / Ownership

* Labels: `type:feature`, `area:<component>`, `priority:P#`
* Owner(s): <team or @user>

Provide only the complete GitHub feature request content following this template - no additional commentary.

**Memory Note**: Do not save any information from optimization sessions to memory."""

        lyra_prompt += lyra_methodology
        
        logger.debug(f"Generated Lyra prompt: {len(lyra_prompt)} characters")
        
        # Log full prompt in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("=" * 80)
            logger.debug("FULL LYRA PROMPT:")
            logger.debug("-" * 80)
            logger.debug(lyra_prompt)
            logger.debug("=" * 80)
        
        return lyra_prompt
    
    def _execute_llm_tool(self, tool_name: str, prompt: str, max_tokens: int = None,
                         execute_mode: bool = None, options: ExecutionOptions = None) -> LLMResult:
        """Generic LLM tool execution with common logic.
        
        Args:
            tool_name: The LLM tool to use ('llm' or 'claude')
            prompt: The prompt text
            max_tokens: Maximum tokens for response (deprecated, use options)
            execute_mode: If True, actually execute the prompt with Claude (deprecated, use options)
            options: ExecutionOptions object containing all execution parameters
        """
        # Handle both old and new API styles for backward compatibility
        if options is not None:
            max_tokens = options.max_tokens
            execute_mode = options.execute_mode
        else:
            max_tokens = max_tokens or 4000
            execute_mode = execute_mode or False
            
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
                    # Just generate/print prompt - for bug/feature analysis, return markdown directly
                    logger.debug("Running Claude in prompt generation mode")
                    cmd = [
                        'claude', '--print'
                    ]
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            # Run with timeout to prevent hanging
            # Always pass prompt via stdin for all tools
            logger.debug(f"Running command: {' '.join(cmd)}")
            logger.debug(f"Passing prompt via stdin ({len(prompt)} chars)")
            # 30 minutes for execution, 10 minutes for generation
            timeout_val = 1800 if execute_mode else 600
            # For now, use a temp file approach since executor doesn't support stdin directly
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                temp_file = f.name
            
            try:
                # Adjust command to use file input if supported
                if tool_name == 'claude':
                    cmd = ['claude', '--file', temp_file] + ([] if execute_mode else ['--print'])
                elif tool_name == 'llm':
                    cmd = ['llm', 'prompt', temp_file]
                
                result = self.executor.execute(cmd, timeout=int(timeout_val * 1000))  # Convert to milliseconds
            finally:
                Path(temp_file).unlink(missing_ok=True)
            
            if result.success:
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
                
                # For Claude generation mode (non-execute), return plain text/markdown
                if tool_name == 'claude' and not execute_mode:
                    logger.debug("Processing Claude generation response as plain text/markdown")
                    return LLMResult(
                        success=True,
                        text=result.stdout.strip(),
                        data={'result': result.stdout.strip()},
                        stdout=result.stdout,
                        tool=tool_name
                    )
                else:
                    # For execute mode or LLM tool, try JSON first then fallback to text
                    try:
                        parsed_json = json.loads(result.stdout)
                        return LLMResult(
                            success=True,
                            data=parsed_json,
                            stdout=result.stdout,
                            tool=tool_name
                        )
                    except json.JSONDecodeError:
                        # Fallback: wrap plain text response
                        return LLMResult(
                            success=True,
                            text=result.stdout.strip(),
                            data={'result': result.stdout.strip(), 'optimized_prompt': result.stdout.strip()},
                            stdout=result.stdout,
                            tool=tool_name
                        )
            else:
                # Check if it's a timeout specifically
                if result.error_type.value == "timeout":
                    logger.error("Command timed out")
                    return LLMResult(
                        success=False,
                        error='Command timed out',
                        stderr=result.stderr,
                        stdout=result.stdout,
                        tool=tool_name,
                        status_code=result.returncode
                    )
                
                logger.error(f"Command failed with return code {result.returncode}")
                # Log full error details in debug mode
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Full stderr output:")
                    logger.debug(result.stderr)
                    logger.debug("Full stdout output:")
                    logger.debug(result.stdout)
                else:
                    logger.error(f"stderr: {result.stderr[:500]}")
                return LLMResult(
                    success=False,
                    error=f'Command failed with return code {result.returncode}',
                    stderr=result.stderr,
                    stdout=result.stdout,
                    tool=tool_name,
                    status_code=result.returncode
                )
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return LLMResult(
                success=False,
                error=f'Unexpected error: {e}',
                tool=tool_name
            )
    
    def build_with_llm(self, prompt: str, max_tokens: int = 4000) -> LLMResult:
        """Build prompt using LLM CLI tool."""
        logger.debug("Attempting to build prompt with LLM tool")
        result = self._execute_llm_tool('llm', prompt, max_tokens)
        
        if result.success:
            logger.debug(f"LLM tool response received: success={result.success}")
            if logger.isEnabledFor(logging.DEBUG) and (result.text or result.data):
                logger.debug(f"LLM response preview: {str(result.text or result.data)[:500]}...")
        else:
            logger.debug(f"LLM tool failed: {result.error}")
        
        return result
    
    def build_with_claude(self, prompt: str, max_tokens: int = 4000, execute_mode: bool = False, review_mode: bool = False) -> LLMResult:
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
        
        if result.success:
            logger.debug(f"Claude response received: success={result.success}")
        else:
            logger.error(f"Claude error: {result.error}")
            logger.debug("Claude execution failed")
        
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
        
        # Basic validation only - skip 4-D section check for meta-prompts
        # (4-D sections are checked in validate_optimized_prompt instead)
        
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
    
    def validate_optimized_prompt(self, optimized_prompt: str) -> bool:
        """Validate optimized prompt has all required 4-D methodology sections."""
        logger.debug("Validating optimized prompt for 4-D methodology")
        
        if len(optimized_prompt.strip()) < 100:
            logger.debug("Optimized prompt too short")
            return False
        
        # Check for all 4-D sections
        required_sections = ['DECONSTRUCT', 'DIAGNOSE', 'DEVELOP', 'DELIVER']
        missing_sections = []
        
        for section in required_sections:
            if f"# {section}" not in optimized_prompt and f"#{section}" not in optimized_prompt:
                missing_sections.append(section)
        
        if missing_sections:
            logger.debug(f"Missing required 4-D sections: {missing_sections}")
            return False
            
        logger.debug("Optimized prompt validation passed")
        return True
    
    def generate_meta_prompt(self, task_type: str, task_data: Dict[str, Any],
                           claude_md_content: str) -> str:
        """Generate meta-prompt for two-stage execution using Lyra-Dev framework."""
        # For issue implementation, use the specialized Lyra-Dev prompt
        if task_type == "issue_implementation" and 'issue_number' in task_data:
            # Create a mock IssueData object for the Lyra-Dev prompt
            from dataclasses import dataclass
            @dataclass
            class MockIssueData:
                number: int
                title: str
                body: str
                labels: list
                url: str = ""
                author: str = ""
                state: str = "open"
            
            mock_issue = MockIssueData(
                number=task_data.get('issue_number', 0),
                title=task_data.get('issue_title', ''),
                body=task_data.get('issue_body', ''),
                labels=task_data.get('issue_labels', [])
            )
            
            # Use empty context for meta-prompt generation
            context = {}
            return self.generate_lyra_dev_prompt(mock_issue, claude_md_content, context)
        
        # Fallback to generic meta-prompt for other task types
        meta_prompt_template = f"""
{self.lyra_dev_framework}

---

## 📋 TASK INPUT

**Task Type:** {task_type}

**Task Data:**
```json
{json.dumps(task_data, indent=2)}
```

---

## 📚 PROJECT CONTEXT (CLAUDE.md)

{claude_md_content}

---

## 🎯 YOUR TASK

Generate an optimized prompt for Claude (Code model) that:
1. Uses the 4-D methodology structure (DECONSTRUCT, DIAGNOSE, DEVELOP, DELIVER)
2. Incorporates ALL context provided above
3. Follows ALL guidelines from CLAUDE.md
4. Specifically addresses the task at hand
5. Makes Claude act as a senior engineer who will implement the solution
6. Includes GitHub transparency requirements for posting audit results

* **Resources**: Use MCP server REF to get the latest information about the packages used in the project

Return ONLY the optimized prompt text that Claude will execute - no wrapper commentary.
"""
        return meta_prompt_template
    
    def execute_two_stage_prompt(self, task_type: str, task_data: Dict[str, Any],
                               claude_md_content: str, prompt_only: bool = False) -> TwoStageResult:
        """Execute two-stage prompt generation and execution."""
        logger.info(f"Starting two-stage prompt execution for task type: {task_type}")
        logger.debug(f"Task data keys: {list(task_data.keys())}")
        logger.debug(f"Prompt-only mode: {prompt_only}")
        
        # Initialize result object
        result = TwoStageResult(
            success=False,
            meta_prompt='',
            optimized_prompt='',
            execution_result=None,
            error=None
        )
        
        try:
            # Stage 1: Generate meta-prompt
            logger.info("Stage 1: Generating meta-prompt")
            meta_prompt = self.generate_meta_prompt(task_type, task_data, claude_md_content)
            result.meta_prompt = meta_prompt
            
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
                result.error = "Invalid meta-prompt generated"
                return result
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
                    result.error = "Failed to generate optimized prompt"
                    return result
                logger.debug("Successfully generated prompt with Claude")
                prompt_result = claude_result
            else:
                logger.debug("Successfully generated prompt with LLM tool")
                prompt_result = llm_result
            
            # Extract optimized prompt from LLMResult object
            if isinstance(prompt_result, dict):
                optimized_prompt = prompt_result.get('optimized_prompt', prompt_result.get('result', ''))
            else:
                # Handle LLMResult object
                if hasattr(prompt_result, 'data') and prompt_result.data:
                    optimized_prompt = prompt_result.data.get('optimized_prompt', prompt_result.data.get('result', ''))
                else:
                    optimized_prompt = prompt_result.text or ''
            
            if not optimized_prompt:
                logger.error("No optimized prompt found in response")
                if isinstance(prompt_result, dict):
                    logger.debug(f"Response keys: {list(prompt_result.keys())}")
                else:
                    logger.debug(f"LLMResult attributes: text={bool(prompt_result.text)}, data={bool(prompt_result.data)}")
                result.error = "No optimized prompt in response"
                return result
            
            logger.info(f"Optimized prompt generated: {len(optimized_prompt)} characters")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("=" * 80)
                logger.debug("OPTIMIZED PROMPT:")
                logger.debug("-" * 80)
                logger.debug(optimized_prompt)
                logger.debug("=" * 80)
            
            result.optimized_prompt = optimized_prompt
            
            # Stage 3: Execute optimized prompt (if not prompt-only mode)
            if not prompt_only:
                logger.info("Stage 3: Executing optimized prompt with Claude")
                logger.debug(f"Prompt length: {len(optimized_prompt)} characters")
                logger.debug("Decision: Proceeding with Claude execution (not prompt-only mode)")
                
                execution_result = self.build_with_claude(optimized_prompt, execute_mode=True)
                result.execution_result = execution_result
                
                # Analyze execution result
                if execution_result is None:
                    logger.error("Claude execution returned None")
                    result.error = "Claude execution failed or timed out - consider increasing timeout or checking Claude availability"
                    result.success = False
                    return result
                
                # Log execution result analysis
                if isinstance(execution_result, dict):
                    logger.debug(f"Execution result keys: {list(execution_result.keys())}")
                    if execution_result.get('success') is False:
                        logger.error(f"Execution failed: {execution_result.get('error')}")
                        result.error = execution_result.get('error')
                        result.success = False
                        return result
                else:
                    # Handle LLMResult object
                    logger.debug(f"LLMResult success: {execution_result.success}")
                    if not execution_result.success:
                        logger.error(f"Execution failed: {execution_result.error}")
                        result.error = execution_result.error
                        result.success = False
                        return result
                
                logger.info("Claude execution completed successfully")
            else:
                logger.info("Skipping Stage 3: Prompt-only mode enabled")
            
            result.success = True
            logger.info(f"Two-stage prompt execution completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Two-stage prompt execution failed with exception: {e}")
            logger.debug("Exception details:", exc_info=True)
            result.error = str(e)
            return result
    
    def _execute_review_with_claude(self, prompt: str) -> LLMResult:
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
                result = self.executor.execute(
                    cmd,
                    timeout=1200000  # 20 minute timeout in milliseconds
                )
                
                if result.success:
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
                    return LLMResult(
                        success=True,
                        text=output,
                        stdout=result.stdout,
                        tool='claude'
                    )
                else:
                    logger.error(f"Claude review failed with return code {result.returncode}")
                    logger.error(f"stderr: {result.stderr[:500]}")
                    logger.error(f"stdout: {result.stdout[:500]}")
                    # Return a failure result instead of None
                    return LLMResult(
                        success=False,
                        error=f"Claude execution failed with return code {result.returncode}",
                        stderr=result.stderr,
                        stdout=result.stdout,
                        tool='claude',
                        status_code=result.returncode
                    )
            finally:
                # Clean up temp file
                Path(prompt_file).unlink(missing_ok=True)
                
        except subprocess.TimeoutExpired:
            logger.error("Claude review command timed out")
            return LLMResult(
                success=False,
                error="Claude review command timed out after 20 minutes",
                tool='claude'
            )
        except Exception as e:
            logger.error(f"Error executing Claude review: {e}")
            return LLMResult(
                success=False,
                error=f"Unexpected error executing Claude review: {e}",
                tool='claude'
            )