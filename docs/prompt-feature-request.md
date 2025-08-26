# Feature Request Prompt Generation

## Overview
Documents the prompt generation workflow when running `claude-tasker-py --feature "{description}"` for creating feature request issues.

## ASCII Workflow

```
┌──────────────────────────────────────────────────────────────┐
│        claude-tasker-py --feature "add dark mode toggle"     │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  1. PARSE DESCRIPTION  │
        │  (Extract feature req) │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  2. GATHER CONTEXT     │
        │  • CLAUDE.md           │
        │  • Current codebase    │
        │  • Related files       │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  3. BUILD LYRA         │
        │     FEATURE PROMPT     │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  4. EXECUTE CLAUDE     │
        │  (Generate feature     │
        │   specification)       │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  5. EXTRACT ISSUE      │
        │  Parse structured      │
        │  feature request       │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  6. CREATE GITHUB      │
        │     ISSUE              │
        │  • Apply labels        │
        │  • Set metadata        │
        └────────────────────────┘
```

## Detailed Step-by-Step Process

### Step 1: Parse Description
- Extract feature description from command line
- Identify key components mentioned
- Detect potential technical terms or references

### Step 2: Gather Context
- Load `CLAUDE.md` for project conventions
- Search codebase for related components:
  - Existing similar features
  - Relevant modules/files
  - Current architecture patterns
- Check for existing issues or PRs related to the feature

### Step 3: Build Lyra Feature Prompt
The system generates a comprehensive feature analysis prompt:

```markdown
# LYRA — Feature Request Prompt (Feature Ticket Generator)

You are **Lyra**, a master-level AI prompt optimization specialist focused on converting vague feature ideas into **production-ready feature requests**.

## INPUT FORMAT

`[FEATURE_NOTES]`: add dark mode toggle to application settings

`[KNOWN_CONTEXT]`: [CLAUDE.md content]

## THE 4‑D METHODOLOGY

### 1) DECONSTRUCT
- Core intent: What problem/value is being achieved?
- Key entities: components, endpoints, flags, personas
- Context: current behavior, constraints, SLAs
- Output requirements: UX, API, data, performance

### 2) DIAGNOSE
- Audit for clarity and feasibility
- Scope shape (MVP vs Phase 2)
- Risk areas (privacy, security, migration)
- Prioritization signals (value, reach, effort)

### 3) DEVELOP
- User framing: Jobs-to-Be-Done, personas
- Resources: Use MCP server REF for package info
- Spec style: Functional (FR) and Non-functional (NFR)
- Acceptance: Given/When/Then examples
- Rollout: Feature flags, experimentation

### 4) DELIVER
- Clean Markdown issue with metadata
- Redact secrets/PII
- Keep titles ≤ 80 chars
```

### Step 4: Execute Claude
- Run Claude with feature prompt
- Claude analyzes and expands the feature request:
  - Identifies user problems and business value
  - Defines functional requirements
  - Specifies non-functional requirements
  - Creates acceptance criteria
  - Performs RICE prioritization
  - Identifies risks and mitigations

### Step 5: Extract Structured Issue
Parse Claude's response to extract:
- Feature title (concise, <80 chars)
- Comprehensive description
- Requirements list
- Acceptance criteria
- Priority assessment
- Labels and metadata

### Step 6: Create GitHub Issue
- Execute: `gh issue create --title "[title]" --body "[content]"`
- Apply appropriate labels:
  - `type:feature`
  - `area:[component]`
  - `priority:P[#]`
- Link to related issues if found
- Notify relevant team members

## Example Generated Feature Request

```markdown
# Feature: [Settings] Dark Mode Toggle

## Background / Problem Statement
* **User problem**: Users working in low-light environments experience eye strain
* **Business rationale**: Improve user retention and accessibility compliance
* **Current behavior**: Application only supports light theme

## Goals & Non‑Goals
* **Goals**: 
  - Provide system-wide dark theme option
  - Persist user preference across sessions
  - Support automatic switching based on OS settings
* **Non‑Goals**:
  - Custom color themes (out of scope for MVP)
  - Per-component theme overrides

## Users & Use Cases (JTBD)
* **Personas**: All application users
* **Primary Jobs**:
  - When working at night, users want reduced eye strain
  - When switching devices, users want consistent theme

## Requirements

**Functional (FR)**
* FR‑1: Toggle switch in settings panel
* FR‑2: Theme persists across sessions
* FR‑3: Respects OS dark mode preference

**Non‑Functional (NFR)**
* NFR‑1: Theme switch completes in <100ms
* NFR‑2: WCAG AAA contrast compliance
* NFR‑3: No flash of unstyled content on load

## UX / Design
* **Flow summary**: Settings → Appearance → Theme Toggle
* **Edge states**: Handle mid-animation theme switches
* **Accessibility**: Announce theme change to screen readers

## API / Interfaces
```typescript
POST /api/v1/user/preferences
{
  "theme": "dark" | "light" | "system"
}
```

## Data & Analytics
* **Tracking**: Theme selection events
* **Properties**: theme_value, trigger_source

## Risks & Mitigations
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| CSS conflicts | High | Medium | Audit existing styles |
| Performance | Low | Low | Lazy-load theme CSS |

## Rollout Plan
* **Flagging**: `feature.dark_mode` (default: false)
* **Phases**: 10% → 50% → 100% over 2 weeks
* **Experimentation**: A/B test engagement metrics

## Success Metrics
* **Primary KPIs**: Theme adoption rate, session duration
* **Targets**: 30% adoption within 30 days

## Acceptance Criteria
* [ ] Toggle appears in settings
* [ ] Theme persists on refresh
* [ ] Respects OS preference when set to "system"
* **GWT Example**:
  * *Given* user prefers dark mode
  * *When* they toggle the switch
  * *Then* entire app updates to dark theme

## RICE Prioritization
* **Reach**: 10,000 users/month
* **Impact**: 2 (high)
* **Confidence**: 90%
* **Effort**: 1.5 person-months
* **Score**: (10000 * 2 * 0.9) / 1.5 = 12,000

## Labels / Ownership
* Labels: `type:feature`, `area:settings`, `priority:P2`
* Owner: @frontend-team

---
🤖 Generated via agent coordination with [Claude Code]
```

## Key Features

- **Structured expansion**: Transforms brief descriptions into comprehensive specs
- **RICE prioritization**: Data-driven priority scoring
- **Risk analysis**: Identifies and mitigates potential issues
- **Acceptance criteria**: Clear, testable requirements
- **API specifications**: Technical implementation details
- **Rollout strategy**: Phased deployment planning