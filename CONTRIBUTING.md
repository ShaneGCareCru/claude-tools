# Contributing to Claude Tools

Thank you for your interest in contributing to Claude Tools! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/claude-tools.git`
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes thoroughly
6. Commit with clear messages
7. Push to your fork
8. Submit a pull request

## Development Guidelines

### Code Style

- Use bash best practices
- Ensure scripts pass `shellcheck` validation
- Maintain consistent formatting
- Add comments for complex logic
- Use meaningful variable names

### Testing

Before submitting a PR:
- Test the script with various inputs
- Verify error handling works correctly
- Check edge cases
- Ensure no regressions in existing functionality

### Commit Messages

- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, etc.)
- Keep the first line under 50 characters
- Add detailed description if needed

Example:
```
Add validation for GitHub CLI authentication

- Check if gh is authenticated before proceeding
- Provide helpful error message with login instructions
- Exit gracefully if authentication fails
```

## Pull Request Process

1. Ensure your branch is up to date with master
2. Fill out the PR template completely
3. Link any related issues
4. Wait for review and address feedback
5. Once approved, it will be merged

## Reporting Issues

- Use the GitHub issue tracker
- Search existing issues first
- Provide clear reproduction steps
- Include environment details
- Add relevant logs or error messages

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Assume good intentions

## Questions?

Feel free to open an issue for any questions about contributing!