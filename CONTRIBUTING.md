# Contributing to ios-simulator-mcp

Thank you for your interest in contributing to ios-simulator-mcp! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- macOS (required for iOS Simulator)
- Python 3.11 or higher
- Xcode and iOS Simulator installed

### Setting Up Your Environment

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ios-simulator-mcp.git
   cd ios-simulator-mcp
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

3. **Install the package in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks** (optional but recommended):
   ```bash
   pre-commit install
   ```

## Development Workflow

### Making Changes

1. **Create a new branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and test them thoroughly

3. **Run linting and formatting**:
   ```bash
   # Check linting
   ruff check .

   # Format code
   ruff format .

   # Type checking
   mypy ios_simulator_mcp.py
   ```

4. **Test the package**:
   ```bash
   # Test building the package
   python -m build

   # Test the MCP server locally
   python ios_simulator_mcp.py
   ```

### Code Style

- We use **Ruff** for linting and formatting
- Follow PEP 8 guidelines
- Line length: 100 characters
- Use type hints where appropriate
- Write clear, descriptive commit messages

### Commit Messages

Follow the conventional commits specification:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `chore:` - Maintenance tasks
- `refactor:` - Code refactoring
- `test:` - Test additions or changes

Examples:
```
feat: add support for video recording
fix: handle simulator not found error
docs: update README with new examples
```

## Submitting Changes

### Pull Request Process

1. **Update documentation** if you've added new features

2. **Ensure all checks pass**:
   - Linting and formatting
   - Type checks
   - Package builds successfully

3. **Push your changes**:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create a Pull Request**:
   - Go to the repository on GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template with details about your changes
   - Reference any related issues

5. **Respond to feedback**:
   - Address any review comments
   - Make requested changes
   - Push updates to your branch

## Reporting Issues

### Bug Reports

When reporting bugs, please include:
- iOS Simulator version and macOS version
- Python version
- Steps to reproduce the issue
- Expected behavior vs actual behavior
- Error messages or logs
- Minimal code example if applicable

### Feature Requests

When requesting features:
- Clearly describe the feature and its use case
- Explain why it would be valuable
- Provide examples of how it would work

## Testing

### Manual Testing

Test your changes with:
- Different iOS Simulator versions
- Different device types (iPhone, iPad)
- Various commands and edge cases

### Testing the MCP Server

```bash
# Start the server
python ios_simulator_mcp.py

# In another terminal, test with Claude Desktop or other MCP client
# Follow the setup instructions in README.md
```

## Code Review Guidelines

When reviewing PRs:
- Be respectful and constructive
- Focus on the code, not the person
- Provide specific, actionable feedback
- Acknowledge good solutions

## Getting Help

- Open an issue for questions
- Check existing issues and discussions
- Review the README and documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
