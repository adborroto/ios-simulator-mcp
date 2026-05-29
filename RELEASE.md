# Release Process

This document describes how to publish new releases of ios-simulator-mcp to PyPI.

## Setup (One-time)

### Configure PyPI Trusted Publishing

The release pipeline uses PyPI's trusted publishing feature, which doesn't require API tokens. Here's how to set it up:

1. **Go to PyPI**: Visit https://pypi.org/manage/account/publishing/

2. **Add a new publisher**:
   - PyPI Project Name: `ios-simulator-mcp`
   - Owner: `adborroto`
   - Repository name: `ios-simulator-mcp`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`

### Configure GitHub Environments

1. Go to your repository on GitHub: https://github.com/adborroto/ios-simulator-mcp/settings/environments

2. Create the environment:
   - **pypi**: For production releases

3. (Optional) Add protection rules to require manual approval before publishing

## Creating a Release

1. **Update the version** in `pyproject.toml`:
   ```toml
   version = "0.2.0"  # Update this line
   ```

2. **Commit and push** the version change:
   ```bash
   git add pyproject.toml
   git commit -m "chore: bump version to 0.2.0"
   git push origin main
   ```

3. **Create a GitHub release**:
   - Go to https://github.com/adborroto/ios-simulator-mcp/releases/new
   - Create a new tag (e.g., `v0.2.0`)
   - Set the release title (e.g., `v0.2.0`)
   - Add release notes describing changes
   - Click "Publish release"

4. **Automated publishing**:
   - The GitHub Action will automatically:
     - Build the package
     - Publish to PyPI

5. **Verify the release**:
   - Check PyPI: https://pypi.org/project/ios-simulator-mcp/
   - Test installation: `pip install ios-simulator-mcp`

## Troubleshooting

- **First release**: You may need to manually create the project on PyPI first by uploading an initial version, or set up trusted publishing before the first automated release
- **Permission errors**: Ensure trusted publishing is correctly configured on PyPI
- **Build errors**: Check the GitHub Actions logs for details

## Manual Publishing (Alternative)

If you need to publish manually:

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Upload to TestPyPI (optional)
python -m twine upload --repository testpypi dist/*

# Upload to PyPI
python -m twine upload dist/*
```
