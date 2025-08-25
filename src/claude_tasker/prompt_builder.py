"""Prompt building module implementing two-stage execution and Lyra-Dev framework."""

import subprocess
import json
import tempfile
from typing import Dict, Optional, Any
from pathlib import Path
from .github_client import IssueData, PRData
from .logging_config import get_logger
from .prompt_models import ExecutionOptions, PromptContext, LLMResult, TwoStageResult
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
        if hasattr(context, 'model_dump'):
            # Handle PromptContext object
            context_dict = context.model_dump() if hasattr(context, 'model_dump') else context.__dict__
            logger.debug(f"Context keys: {list(context_dict.keys())}")
        else:
            # Handle regular dict
            logger.debug(f"Context keys: {list(context.keys())}")
        
        prompt_parts = [
            self.lyra_dev_framework,
            (f"\n## Issue Context\n**Issue #{issue_data.number}: "
             f"{issue_data.title}**\n{issue_data.body}"),
            f"\n## Project Guidelines (CLAUDE.md)\n{claude_md_content}",
        ]
        
        # Handle both dict and PromptContext objects
        if hasattr(context, 'model_dump'):
            # PromptContext object
            if context.git_diff:
                logger.debug(f"Including git diff ({len(context.git_diff)} chars)")
                prompt_parts.append(f"\n## Current Changes\n```diff\n{context.git_diff}\n```")
            
            if context.related_files:
                logger.debug(f"Including {len(context.related_files)} related files")
                prompt_parts.append(f"\n## Related Files\n{chr(10).join(context.related_files)}")
            
            if context.project_info:
                logger.debug("Including project info context")
                prompt_parts.append(
                    f"\n## Project Context\n{json.dumps(context.project_info, indent=2)}")
        else:
            # Regular dict
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

<!-- meta: labels=bug,needs-triage,{optional: area:<component>, severity:S#, priority:P#, regression?:yes/no} -->

<!-- meta: assignees=@oncall,{optional: @owner} -->

<!-- meta: milestone= -->

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

<!-- meta: type=feature, needs-triage, {optional: area:<component>, priority:P#, epic:<link or id>, rice:<R|I|C|E=values>, mode:<DETAIL|BASIC>} -->

<!-- meta: assignees=@oncall,{optional: @owner} -->

<!-- meta: milestone= -->

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
                    # Just generate/print prompt - with JSON output format for parsing
                    logger.debug("Running Claude in prompt generation mode")
                    cmd = [
                        'claude', '--print', '--output-format', 'json', prompt
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
                
                # For Claude generation mode (non-execute), try JSON first then plain text
                if tool_name == 'claude' and not execute_mode:
                    logger.debug("Processing Claude generation response")
                    try:
                        parsed_json = json.loads(result.stdout)
                        logger.debug("Claude generation response parsed as JSON")
                        return LLMResult(
                            success=True,
                            data=parsed_json,
                            stdout=result.stdout,
                            tool=tool_name
                        )
                    except json.JSONDecodeError:
                        logger.debug("Claude generation response processed as plain text")
                        return LLMResult(
                            success=True,
                            text=result.stdout.strip(),
                            data={'result': result.stdout.strip(), 'optimized_prompt': result.stdout.strip()},
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
                
        except subprocess.TimeoutExpired:
            logger.error("Command timed out")
            return LLMResult(
                success=False,
                error='Command timed out',
                tool=tool_name
            )
        except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
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
                else:
                    # Handle LLMResult object
                    logger.debug(f"LLMResult success: {execution_result.success}")
                    if not execution_result.success:
                        logger.error(f"Execution failed: {execution_result.error}")
                        results['error'] = execution_result.error
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