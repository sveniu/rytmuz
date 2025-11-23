# Release Process

This document describes how to release a new version of rytmuz to PyPI.

## Prerequisites

### One-time Setup: Configure PyPI Trusted Publisher

#### For First Release (Pending Publisher):
1. Go to https://pypi.org/manage/account/publishing/
2. Click "Add a new pending publisher"
3. Fill in:
   - **Owner:** sveniu
   - **Repository name:** rytmuz
   - **Workflow name:** release.yml
   - **Environment name:** pypi
4. Click "Add"

The package will be automatically created on PyPI when you push your first release tag.

#### For Subsequent Releases (Existing Package):
If the package already exists on PyPI, configure the trusted publisher at:
https://pypi.org/manage/project/rytmuz/settings/publishing/

#### Optional: Configure TestPyPI
For testing releases before production:
1. Go to https://test.pypi.org/manage/account/publishing/
2. Add a pending publisher with:
   - **Owner:** sveniu
   - **Repository name:** rytmuz
   - **Workflow name:** test-release.yml
   - **Environment name:** testpypi

### GitHub Environment Setup

1. Go to your GitHub repository settings
2. Navigate to **Settings** → **Environments**
3. Create a new environment named `pypi`
4. (Optional) Add protection rules:
   - Require reviewers for manual approval
   - Restrict to main branch only

5. Repeat for `testpypi` if using test releases

## Release Steps

### 1. Prepare the Release

Update version in `pyproject.toml`:

```bash
# Option 1: Use uv version command
uv version --bump patch   # For bug fixes (0.1.0 → 0.1.1)
uv version --bump minor   # For new features (0.1.0 → 0.2.0)
uv version --bump major   # For breaking changes (0.1.0 → 1.0.0)

# Option 2: Edit manually
# Edit pyproject.toml: version = "0.1.1"
```

### 2. Commit and Tag

```bash
# Commit the version bump
git add pyproject.toml uv.lock
git commit -m "chore: bump version to 0.1.1"

# Create an annotated tag
git tag -a v0.1.1 -m "Release v0.1.1"

# Push to GitHub (this triggers the release workflow)
git push origin main --tags
```

### 3. Monitor the Release

1. Go to your GitHub repository
2. Click on **Actions** tab
3. Watch the "Release to PyPI" workflow run
4. Workflow will:
   - Build the package
   - Test the package installation
   - Publish to PyPI (via trusted publishing)
   - Create a GitHub release with auto-generated notes

### 4. Verify the Release

Check that the release is available:

```bash
# Install from PyPI
uvx rytmuz@0.1.1

# Or check the PyPI page
open https://pypi.org/project/rytmuz/
```

## Testing Releases (Optional)

Before releasing to production PyPI, you can test with TestPyPI:

### 1. Trigger Test Release

1. Go to GitHub **Actions** tab
2. Select "Test Release (TestPyPI)" workflow
3. Click "Run workflow"
4. Click the green "Run workflow" button

### 2. Verify TestPyPI Release

```bash
# Install from TestPyPI
uvx --index https://test.pypi.org/simple rytmuz

# Or check TestPyPI page
open https://test.pypi.org/project/rytmuz/
```

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features, backwards compatible
- **PATCH** (0.0.1): Bug fixes, backwards compatible

### Pre-release Versions

```bash
uv version --bump alpha   # 0.1.0 → 0.1.1a1
uv version --bump beta    # 0.1.1a1 → 0.1.1b1
uv version --bump rc      # 0.1.1b1 → 0.1.1rc1
uv version --bump stable  # 0.1.1rc1 → 0.1.1
```

## Troubleshooting

### Release Failed: "No such environment"

You need to create the GitHub environment:
1. Go to repository **Settings** → **Environments**
2. Create environment named `pypi` (or `testpypi`)

### Release Failed: "Trusted publishing exchange failed"

Configure the trusted publisher on PyPI:
1. Go to https://pypi.org/manage/account/publishing/
2. Add pending publisher with correct repository and workflow details

### Package Import Failed

Check that all dependencies are correctly specified in `pyproject.toml` and that the package structure is correct.

### GitHub Release Creation Failed

Ensure the workflow has `contents: write` permission in the `permissions` section.

## Security Notes

- **No API tokens needed**: Uses PyPI's trusted publishing (OIDC)
- **Short-lived credentials**: Tokens expire after 15 minutes
- **Automatic attestations**: PEP 740 attestations generated automatically
- **Minimal permissions**: Workflow uses least-privilege principle

## Manual Release (Emergency Only)

If GitHub Actions is unavailable, you can release manually:

```bash
# Build the package
uv build

# Publish to PyPI (requires API token configured)
uv publish

# Create GitHub release manually
gh release create v0.1.1 --title "rytmuz v0.1.1" --generate-notes dist/*
```

Note: Manual releases won't use trusted publishing and require a PyPI API token.
