# Bug Analysis Prompt Generation

## Overview
Documents the prompt generation workflow when running `claude-tasker-py --bug "{description}"` for analyzing bugs and creating detailed issue reports.

## ASCII Workflow

```
┌──────────────────────────────────────────────────────────────┐
│     claude-tasker-py --bug "login fails with 500 error"     │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  1. PARSE BUG          │
        │     DESCRIPTION        │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  2. GATHER CONTEXT     │
        │  • CLAUDE.md           │
        │  • Git diff/status     │
        │  • Error patterns      │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  3. BUILD BUGSMITH     │
        │     PROMPT             │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  4. EXECUTE CLAUDE     │
        │  (Analyze & diagnose)  │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  5. EXTRACT BUG        │
        │     REPORT             │
        │  Parse structured      │
        │  issue content         │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  6. CREATE GITHUB      │
        │     ISSUE              │
        │  • Set severity/prio   │
        │  • Apply bug labels    │
        └────────────────────────┘
```

## Detailed Step-by-Step Process

### Step 1: Parse Bug Description
- Extract bug report from command line input
- Identify key elements:
  - Error messages or codes
  - Affected components
  - Reproduction context
- Detect technical indicators (status codes, stack traces)

### Step 2: Gather Context
- Load `CLAUDE.md` for debugging guidelines
- Check current git state for recent changes
- Search for related error patterns:
  - Log files
  - Similar closed issues
  - Error handling code
- Identify potentially affected files

### Step 3: Build BugSmith Prompt
The system generates a comprehensive bug analysis prompt:

```markdown
# BugSmith — Optimized Prompt for GitHub Issue Generation

You are **BugSmith**, a senior triage engineer who transforms messy notes into high-signal GitHub issues.

## GOAL
From the bug notes, produce a *production-quality* GitHub issue with explicit metadata, clean structure, and actionable next steps.

## INPUT
`[BUG_NOTES]`: login fails with 500 error when user has special characters in email

## PROJECT CONTEXT
[CLAUDE.md content]

## PROCESS (4D)

1. **Deconstruct**
   * Extract: core problem, component, error codes
   * Pull facts from logs, dedupe
   * Map versions, environment, affected scope

2. **Diagnose**
   * Identify ambiguity and missing data
   * Infer severity & priority from impact
   * Detect security/privacy implications
   * Use MCP server REF for package diagnosis
   * Determine: regression, config, or defect

3. **Develop**
   * Create minimal Steps to Reproduce
   * Write Expected vs Actual behavior
   * Draft Suspected Cause
   * Propose Workaround
   * Define Acceptance Criteria

4. **Deliver**
   * Output in Markdown template
   * Title ≤ 80 chars with component
   * Redact secrets/PII in logs

## SEVERITY & PRIORITY RUBRIC
* **S1/P0**: Outage, data loss, security, no workaround
* **S2/P1**: Major feature broken, limited workaround
* **S3/P2**: Partial impairment, reasonable workaround
* **S4/P3**: Minor/visual issues
```

### Step 4: Execute Claude Analysis
- Run Claude with BugSmith prompt
- Claude performs comprehensive analysis:
  - Extracts facts from description
  - Diagnoses root cause possibilities
  - Determines severity/priority
  - Creates reproduction steps
  - Identifies affected components
  - Proposes fixes or workarounds

### Step 5: Extract Bug Report
Parse Claude's structured response containing:
- Bug title with component tag
- Severity and priority assessment
- Environment details
- Reproduction steps
- Expected vs actual behavior
- Evidence (logs, screenshots)
- Suspected cause
- Acceptance criteria
- Follow-up questions

### Step 6: Create GitHub Issue
- Execute: `gh issue create --title "[title]" --body "[content]"`
- Apply bug-specific labels:
  - `bug`
  - `severity:S[#]`
  - `priority:P[#]`
  - `area:[component]`
  - `needs-triage` (if applicable)
- Link related issues or PRs
- Assign to appropriate team

## Example Generated Bug Report

```markdown
# Bug: [Auth] Login fails with 500 error for special character emails

## Summary
* **Impact**: Users with special characters in email addresses cannot login
* **First Seen**: 2024-01-15 14:30 UTC
* **Severity / Priority**: S2 / P1 (blocks login for subset of users, security implications)
* **Regression**: Yes (introduced in v2.3.1, commit #abc123)

## Environment
| Item        | Value                       |
| ----------- | --------------------------- |
| App/Service | auth-service                |
| Version     | 2.3.1-production           |
| Platform    | Node.js 18.17 / Ubuntu 22.04 |
| Config      | standard production flags   |

## Steps to Reproduce
1. Navigate to login page (https://app.example.com/login)
2. Enter email: test+user@example.com
3. Enter valid password
4. Click "Login" button
5. Observe 500 error response

## Expected Behavior
User should be successfully authenticated and redirected to dashboard

## Actual Behavior
Server returns 500 Internal Server Error with message "Invalid email format"

## Evidence
```text
[2024-01-15 14:30:15] ERROR auth.service.js:142
TypeError: Cannot read property 'toLowerCase' of undefined
  at validateEmail (/app/src/auth/validators.js:23)
  at AuthService.login (/app/src/auth/auth.service.js:142)
  Stack trace... [truncated]
  
Request ID: req_7f3d2a1b
User Agent: Mozilla/5.0 Chrome/120.0
```

* Screenshot(s): [attached]
* Trace IDs: req_7f3d2a1b, req_8e4c3b2c

## Scope & Workarounds
* **Affected %**: ~5% of users (those with + or other special chars)
* **Known Workaround**: Users can create alternate account without special characters

## Suspected Cause
Email validation regex in `/src/auth/validators.js:23` doesn't properly escape special characters before processing. The `+` character is being interpreted as regex operator instead of literal character.

## Related
* Links: PR #456 (introduced regression), Issue #789 (similar validation bug)
* Owner(s): @auth-team
* Labels: `bug`, `severity:S2`, `priority:P1`, `area:auth`, `regression`

## Acceptance Criteria
* [ ] Users with special characters in email can login successfully
* [ ] Email validation properly handles: + . - _ @ characters
* [ ] Unit tests added for special character email validation
* [ ] No performance regression in login flow
* [ ] Error messages don't expose internal implementation details

## Follow-Up Questions (Info Needed)
1. What is the complete list of special characters we support in email addresses?
2. Are there any security considerations for expanding email validation?
3. Should we migrate existing users with affected emails?

---
🤖 Generated via agent coordination with [Claude Code]
```

## Key Features

- **Forensic analysis**: Extracts all relevant facts from bug description
- **Severity assessment**: Uses standardized S1-S4/P0-P3 rubric
- **Root cause analysis**: Identifies likely causes and affected code
- **Reproduction clarity**: Numbered steps from clean state
- **Security awareness**: Redacts sensitive information
- **Actionable output**: Clear acceptance criteria and next steps