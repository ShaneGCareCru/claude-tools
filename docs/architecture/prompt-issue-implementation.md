# Issue Implementation Prompt Generation

## Overview
Documents the prompt generation workflow when running `claude-tasker-py {issue_number}` for implementing GitHub issues.

## ASCII Workflow

```
┌──────────────────────────────────────────────────────────────┐
│                    claude-tasker-py 45                       │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  1. FETCH ISSUE DATA   │
        │  (GitHub API via gh)   │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  2. LOAD CONTEXT       │
        │  • CLAUDE.md           │
        │  • Git diff            │
        │  • Related files       │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  3. GENERATE META      │
        │     PROMPT (Lyra-Dev)  │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  4. LLM/CLAUDE GEN     │
        │  Creates optimized     │
        │  prompt from meta      │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  5. VALIDATE PROMPT    │
        │  • Check 4-D sections  │
        │  • Verify structure    │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  6. EXECUTE WITH       │
        │     CLAUDE CODE        │
        │  (--permission-mode    │
        │   bypassPermissions)   │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  7. POST RESULTS       │
        │  • Commit changes      │
        │  • Create PR           │
        │  • Comment on issue    │
        └────────────────────────┘
```

## Detailed Step-by-Step Process

### Step 1: Fetch Issue Data
- Execute: `gh issue view {issue_number} --json number,title,body,labels,url,author,state`
- Parse JSON response to extract issue details
- Validate issue is open and actionable

### Step 2: Load Context
- Read `CLAUDE.md` for project-specific guidelines
- Check for uncommitted changes: `git diff`
- Identify related files based on issue content
- Gather any project metadata if specified

### Step 3: Generate Meta-Prompt (Lyra-Dev Framework)
The system creates a meta-prompt containing:
- **Lyra-Dev Framework**: Complete prompt optimization methodology
- **Issue Context**: Issue number, title, body, and labels
- **Project Guidelines**: Full CLAUDE.md content
- **Current State**: Any existing git diffs or changes
- **Task Instructions**: Specific directives for optimized prompt generation

Key components included:
```markdown
# Lyra-Dev: Claude-Compatible Prompt Optimizer for Software Tasks

## 🔄 THE 4-D METHODOLOGY (Headless Software Edition)
### 1. DECONSTRUCT
- Extract task intent, key entities, project context
- Map provided vs missing information

### 2. DIAGNOSE
- CRITICAL: Verify claimed completion status
- Gap Analysis: Compare claimed vs actual implementation
- Identify missing constraints or assumptions

### 3. DEVELOP
- Select approach: Bug Fixes → minimal change
- New Features → leverage ref MCP for package details
- Status Verification → audit gaps only

### 4. DELIVER
- Output optimized prompt for Claude
- Include 4-D structure instructions
- Emphasize CLAUDE.md compliance
```

### Step 4: Generate Optimized Prompt
- Pass meta-prompt to `llm` tool or `claude --print --output-format json`
- LLM generates a structured prompt that:
  - Assigns Claude the role of senior engineer
  - Includes explicit 4-D methodology headers
  - Embeds all context and requirements
  - Specifies GitHub transparency requirements

### Step 5: Validate Generated Prompt
- Check for required 4-D sections: DECONSTRUCT, DIAGNOSE, DEVELOP, DELIVER
- Verify minimum length (>100 characters)
- Ensure no problematic meta-patterns
- Confirm CLAUDE.md compliance instructions present

### Step 6: Execute Implementation
- Run: `claude -p --permission-mode bypassPermissions`
- Pass optimized prompt via stdin
- Claude executes with:
  - Full autonomy (no user interaction)
  - 30-minute timeout for complex tasks
  - Structured 4-D response format

### Step 7: Post Results
- Check for changes: `git status`
- If changes exist:
  - Commit with standardized message
  - Push to branch `issue-{number}-{timestamp}`
  - Create PR with comprehensive body
  - Comment on issue with audit results
- If no changes:
  - Comment explaining issue already complete
  - Close workflow gracefully

## Example Generated Prompt Structure

```markdown
You are a senior software engineer implementing Issue #45.

You MUST structure your entire response using the 4-D methodology:

# DECONSTRUCT
[Analyze the task requirements and current codebase state]

# DIAGNOSE  
[Identify gaps between requirements and current implementation]

# DEVELOP
[Plan implementation following CLAUDE.md guidelines]

# DELIVER
[Implement code, tests, and documentation per CLAUDE.md rules]

IMPORTANT: Follow ALL guidelines in CLAUDE.md including:
- Project-specific coding conventions
- Required tools and workflows
- Testing requirements
- Error handling standards

## Issue Context
**Issue #45: [Title]**
[Issue body content]

## Project Guidelines (CLAUDE.md)
[Full CLAUDE.md content]

## Current Changes
[Any git diffs]

## GitHub Transparency
Post audit results using:
`gh issue comment 45 --body "..."`
```

## Key Features

- **Two-stage execution**: Eliminates meta-prompt recursion issues
- **Gap analysis focus**: Verifies claimed vs actual completion
- **No-questions policy**: Claude reasons through missing details
- **CLAUDE.md compliance**: Multiple enforcement checkpoints
- **Automated workflow**: From issue to PR without manual intervention