# Claude Code Session End Hook for Cost Tracking

- [Claude Code Session End Hook for Cost Tracking](#claude-code-session-end-hook-for-cost-tracking)
  - [Introduction](#introduction)
  - [Installation](#installation)
    - [Configuration](#configuration)
  - [Development](#development)
    - [Testing](#testing)
    - [Build and publish](#build-and-publish)
      - [Configure Publishing to Pypi](#configure-publishing-to-pypi)
      - [Publishing to Test Pypi](#publishing-to-test-pypi)
      - [Publishing to Pypi](#publishing-to-pypi)

## Introduction

Claude Code hook that should run at the end of sessions.  The hook will log cost
and usage in a CSV file, in `~/.claude` folder.

## Installation

```bash
pip install cc-costtrack
```

### Configuration

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cc-costtrack"
          }
        ]
      }
    ]
  }
}
```

## Development

Set up a virtual environment:

```bash
python3 -m venv .venv
```

Activate the virtual environment before running any of the steps below:

```bash
source .venv/bin/activate
```

### Testing

```bash
pip install -e ".[test]"
pytest
```

### Build and publish

Build the distribution:

```bash
pip install -e ".[package]"
python -m build
```

This creates `dist/` with `.tar.gz` and `.whl` files.

#### Configure Publishing to Pypi

Configure PyPI credentials in `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-<your-api-token>

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-<your-test-api-token>
```

API tokens can be created at:

- PyPI: https://pypi.org/manage/account/token/
- TestPyPI: https://test.pypi.org/manage/account/token/

Alternatively, set credentials via environment variables instead of `~/.pypirc`:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-<your-api-token>
```

To target TestPyPI, override the repository URL:

```bash
export TWINE_REPOSITORY_URL=https://test.pypi.org/legacy/
```

#### Publishing to Test Pypi

To publish to TestPyPI first:

```bash
pip install -e ".[package,publish]"

# Using ini file:
twine upload --repository testpypi dist/*

# Or, with environment variables:
export TWINE_REPOSITORY_URL=https://test.pypi.org/legacy/
twine upload dist/*
```

#### Publishing to Pypi

Publish to PyPI:

```bash
pip install -e ".[publish]"
twine upload dist/*
```
