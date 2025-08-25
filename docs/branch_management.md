# Intelligent Branch Management

Claude Tasker now includes intelligent branch management that can reuse existing branches from open PRs, similar to the original bash implementation but with better edge case handling.

## Features

### Smart Branch Reuse
- **Automatic PR Detection**: Finds existing open PRs for an issue
- **Branch Reuse**: Reuses existing PR branches when available
- **Fallback to New**: Creates new timestamped branches when needed
- **Cleanup**: Optionally removes old branches to keep repository clean

### Branch Strategies

The tool supports three branch management strategies:

1. **`reuse` (default)**: Intelligently reuses existing PR branches when possible, creates new ones when needed
2. **`always_new`**: Always creates new timestamped branches (original Python behavior)
3. **`reuse_or_fail`**: Must reuse an existing branch, fails if none exists

## Usage

### Command Line Options

```bash
# Use smart branching (default)
./claude-tasker-py 123

# Explicitly set branch strategy
./claude-tasker-py 123 --branch-strategy reuse

# Always create new branches (disable smart branching)
./claude-tasker-py 123 --no-smart-branching

# Or use the always_new strategy
./claude-tasker-py 123 --branch-strategy always_new

# Require reusing existing branch
./claude-tasker-py 123 --branch-strategy reuse_or_fail
```

### Environment Variables

```bash
# Enable/disable smart branching
export CLAUDE_SMART_BRANCHING=true  # default

# Enable automatic cleanup of old branches
export CLAUDE_CLEANUP_OLD_BRANCHES=true

# Number of branches to keep per issue (default: 3)
export CLAUDE_KEEP_BRANCHES=3
```

## How It Works

### Branch Reuse Logic

1. **Check for existing PR**: Searches for open PRs related to the issue
2. **Reuse PR branch**: If PR exists, checkout and reuse its branch
3. **Check local branches**: If no PR, look for existing local branches
4. **Create new branch**: If no existing branches, create timestamped branch

### Branch Naming Convention

Branches follow the pattern: `issue-{number}-{timestamp}`

Examples:
- `issue-123-1735123456`
- `issue-456-1735123789`

### Edge Cases Handled

1. **Remote-only branches**: Automatically fetches and creates local tracking branch
2. **Uncommitted changes**: Detects and preserves uncommitted work
3. **Branch conflicts**: Falls back to creating new branch if checkout fails
4. **Offline mode**: Continues working even if remote operations fail
5. **Missing base branch**: Creates base branch from origin if needed

## Visual Indicators

The tool provides clear feedback about branch operations:

- 🔄 **Already on branch**: Working on the current branch
- ♻️ **Reusing branch**: Reused an existing branch
- 🌿 **Created branch**: Created a new timestamped branch

## Comparison with Bash Implementation

| Feature | Bash (Archived) | Python (Enhanced) |
|---------|----------------|-------------------|
| PR reuse | ✅ Supported | ✅ Supported |
| Branch cleanup | ❌ Not implemented | ✅ Automatic cleanup |
| Strategy options | ❌ Fixed behavior | ✅ Configurable |
| Error handling | Basic | Comprehensive |
| Offline support | Limited | Full fallback support |
| Testing | None | Full test coverage |

## Benefits

### Efficiency
- **Reduces branch proliferation**: Reuses existing work instead of creating duplicates
- **Saves time**: No need to recreate branches for ongoing work
- **Preserves context**: Maintains commit history in existing branches

### Safety
- **Non-destructive**: Never force-pushes or overwrites existing work
- **Validation**: Ensures branch matches expected issue number
- **Fallback**: Always has a safe path forward if reuse fails

### Flexibility
- **Configurable**: Choose the strategy that fits your workflow
- **Environment-aware**: Respects environment variables for automation
- **Interactive support**: Works in both interactive and headless modes

## Examples

### Example 1: Reusing Existing PR Branch
```bash
$ ./claude-tasker-py 123
♻️  Reusing existing branch: issue-123-1735123456
# Continues work on existing PR #456
```

### Example 2: Creating New Branch
```bash
$ ./claude-tasker-py 789 --branch-strategy always_new
🌿 Created new branch: issue-789-1735124567
# Always creates fresh branch
```

### Example 3: With Cleanup
```bash
$ export CLAUDE_CLEANUP_OLD_BRANCHES=true
$ ./claude-tasker-py 123
🌿 Created new branch: issue-123-1735125678
Cleaned up 2 old branches for issue #123
```

## Troubleshooting

### Branch Mismatch Warning
If you're on a branch for a different issue:
```
⚠️  Warning: Branch 'issue-456-xxx' suggests issue #456, but processing issue #123
```
Solution: Switch to main branch first or use `--branch-strategy always_new`

### Cannot Reuse Branch
If branch reuse fails:
```
Could not checkout existing branch: [error details]
Creating new timestamped branch instead...
```
The tool automatically falls back to creating a new branch.

### Reuse Required But Failed
With `--branch-strategy reuse_or_fail`:
```
Error: No existing branch found and strategy requires reuse
```
Solution: Create a PR first or use a different strategy.

## Best Practices

1. **Default strategy is best**: The default `reuse` strategy works well for most workflows
2. **Clean up periodically**: Enable `CLAUDE_CLEANUP_OLD_BRANCHES` to prevent branch accumulation
3. **Use reuse_or_fail for CI**: In automated environments, use `reuse_or_fail` to ensure consistency
4. **Monitor branch count**: Keep an eye on the number of branches per issue

## Implementation Details

The intelligent branch management is implemented in:
- `src/claude_tasker/branch_manager.py`: Core branch management logic
- `src/claude_tasker/workspace_manager.py`: Integration with workspace operations
- `tests/test_branch_manager.py`: Comprehensive test coverage

The implementation follows SOLID principles with clear separation of concerns and full test coverage.