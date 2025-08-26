# PR Review Prompt Generation

## Overview
Documents the prompt generation workflow when running `claude-tasker-py --review-pr {pr_number}` for reviewing pull requests.

## ASCII Workflow

```
┌──────────────────────────────────────────────────────────────┐
│                claude-tasker-py --review-pr 123              │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  1. FETCH PR DATA      │
        │  (GitHub API via gh)   │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  2. GET PR DIFF        │
        │  (Full changeset)      │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  3. LOAD CLAUDE.md     │
        │  (Project guidelines)  │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  4. BUILD REVIEW       │
        │     PROMPT             │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  5. EXECUTE CLAUDE     │
        │  (Review mode with     │
        │   full output capture) │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  6. FORMAT & POST      │
        │     REVIEW             │
        │  • Parse assessment    │
        │  • Post as PR comment  │
        └────────────────────────┘
```

## Detailed Step-by-Step Process

### Step 1: Fetch PR Data
- Execute: `gh pr view {pr_number} --json number,title,body,headRefName,baseRefName,author,additions,deletions,changedFiles,url`
- Parse response to create PRData object with:
  - PR metadata (number, title, author)
  - Branch information (head, base)
  - Change statistics (additions, deletions, files)

### Step 2: Get PR Diff
- Execute: `gh pr diff {pr_number}`
- Capture complete unified diff of all changes
- Includes context lines for better review accuracy

### Step 3: Load Project Guidelines
- Read `CLAUDE.md` for project-specific review criteria
- Extract relevant sections:
  - Coding conventions
  - Testing requirements
  - Security guidelines
  - Performance standards

### Step 4: Build Review Prompt
The system generates a comprehensive review prompt:

```markdown
You are conducting a comprehensive code review for this pull request.

## PR Information
**PR #123: [Title]**
Author: [username]
Branch: feature-branch → main
Changes: +150/-75 lines across 8 files

## PR Description
[Original PR body content]

## Code Changes
```diff
[Complete PR diff]
```

## Project Guidelines (CLAUDE.md)
[Relevant CLAUDE.md sections]

## Review Instructions
Provide a thorough code review covering:
1. **Code Quality**: Style, conventions, best practices
2. **Functionality**: Logic correctness, edge cases
3. **Testing**: Test coverage and quality
4. **Documentation**: Comments and docs
5. **Performance**: Potential implications
6. **Security**: Vulnerabilities and concerns
7. **Maintainability**: Organization and future-proofing

## Output Format
### ✅ Overall Assessment
[Brief summary]

### Code Review Details
1. **Code Quality** ⭐⭐⭐⭐⭐
[Assessment]

2. **Functionality** ⭐⭐⭐⭐⭐
[Assessment]

[... all 7 categories ...]

### 🔧 Suggestions for Improvement
[Actionable suggestions]

### ✅ Approval Recommendation (MUST HAVE)
[APPROVE / REQUEST_CHANGES - with reasoning]
```

### Step 5: Execute Claude Review
- Run: `claude -p --permission-mode bypassPermissions`
- Pass review prompt via temporary file to avoid escaping issues
- Capture full output with 20-minute timeout
- Claude performs multi-perspective analysis:
  - Line-by-line code inspection
  - Pattern recognition for common issues
  - CLAUDE.md compliance verification
  - Security and performance evaluation

### Step 6: Format and Post Review
- Parse Claude's structured response
- Extract key sections:
  - Overall assessment
  - Category ratings (1-5 stars)
  - Specific suggestions
  - Approval recommendation
- Post as PR comment: `gh pr comment {pr_number} --body "[review]"`

## Example Review Output

```markdown
## 🤖 Automated Code Review

### ✅ Overall Assessment
This PR successfully implements the user authentication feature with good code quality and comprehensive tests. Minor improvements suggested for error handling and documentation.

### Code Review Details

1. **Code Quality** ⭐⭐⭐⭐⭐
   Excellent adherence to project conventions. Clean, readable code with consistent formatting.

2. **Functionality** ⭐⭐⭐⭐☆
   Logic is sound, but missing edge case handling for concurrent session limits.

3. **Testing** ⭐⭐⭐⭐⭐
   Comprehensive test coverage (95%). Good mix of unit and integration tests.

4. **Documentation** ⭐⭐⭐☆☆
   Code is self-documenting but lacks JSDoc comments for public APIs.

5. **Performance** ⭐⭐⭐⭐☆
   Efficient implementation. Consider caching user permissions for better performance.

6. **Security** ⭐⭐⭐⭐⭐
   Proper input validation and sanitization. Good use of prepared statements.

7. **Maintainability** ⭐⭐⭐⭐⭐
   Well-organized code structure. Follows SOLID principles effectively.

### 🔧 Suggestions for Improvement

1. Add rate limiting to authentication endpoints
2. Include JSDoc comments for public methods in auth.service.ts
3. Consider extracting magic numbers to configuration constants
4. Add error recovery mechanism for database connection failures

### ✅ Approval Recommendation
**APPROVE** - The implementation is solid with only minor suggestions that can be addressed in follow-up PRs.

---
🤖 Generated via agent coordination with [Claude Code](https://claude.ai/code)
```

## Key Features

- **Multi-perspective analysis**: Reviews code from multiple angles
- **CLAUDE.md enforcement**: Ensures compliance with project standards
- **Structured output**: Consistent, parseable review format
- **Star ratings**: Visual assessment across 7 key categories
- **Actionable feedback**: Specific, implementable suggestions
- **Clear recommendation**: Explicit APPROVE/REQUEST_CHANGES decision