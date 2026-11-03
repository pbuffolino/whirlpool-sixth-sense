# AGENTS.md - Guidelines for AI Coding Agents

This document provides essential information for AI coding agents working in this repository.

## Project Overview

- **Language**: Python 3.14+
- **Type**: Asyncio-based API library for Whirlpool 6th Sense smart appliances
- **Package**: `whirlpool_sixth_sense`

## Build & Development Commands

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest --log-cli-level=debug

# Run a single test file
pytest tests/test_auth.py

# Run a single test function
pytest tests/test_auth.py::test_auth_success

# Run tests matching a pattern
pytest -k "test_attributes"

# Linting and formatting
ruff check .              # Check for lint errors
ruff check . --fix        # Auto-fix lint errors
ruff format .             # Format code

# Type checking
basedpyright

# Run all lint, format, type-check and workflow-audit hooks
prek --all-files
```

## Code Style Guidelines

### Imports
- Order: standard library, third-party, local
- Use relative imports within `whirlpool` package: `from .appliance import Appliance`
- Use absolute imports for external packages: `import aiohttp`

### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `Appliance`, `AppliancesManager` |
| Functions/Methods | snake_case | `get_machine_state`, `send_attributes` |
| Constants | UPPER_SNAKE_CASE | `ATTR_MODE`, `REQUEST_RETRY_COUNT` |
| Private members | Leading underscore | `_get_attribute`, `_data_dict` |
| Enums | PascalCase class & members | `Mode.Cool`, `FanSpeed.Auto` |

### Type Annotations
- Use full type annotations throughout
- Use Python 3.11+ union syntax: `str | None` (not `Optional[str]`)
- Use `collections.abc` for generic types: `Callable`, `Generator`, `AsyncGenerator`
- Examples:
  ```python
  def get_value(self) -> int | None:
  async def fetch_data(self, timeout: float = 30.0) -> dict[str, str]:
  ```

### Async Patterns
- Use `async`/`await` for all I/O operations
- Use `aiohttp.ClientSession` for HTTP requests
- Use `asyncio.timeout` for request timeouts
- Pass session objects rather than creating new ones

### Error Handling
- Use custom exceptions for specific error cases (e.g., `AccountLockedError`)
- Log errors using the module logger
- Return `False` or `None` for recoverable failures rather than raising exceptions
- Implement retry logic for network requests (`REQUEST_RETRY_COUNT = 3`)

### Logging
- Define module-level logger: `LOGGER = logging.getLogger(__name__)`
- Use appropriate log levels: `debug` for verbose, `error` for failures
- Use f-strings in log messages

### Class Design
- Base `Appliance` class with common functionality in `appliance.py`
- Appliance-specific classes inherit and extend with device-specific methods
- Use `@property` for computed values, `@dataclass` for data containers, `Enum` for constants

## Testing Guidelines

### Framework
- pytest with pytest-asyncio (async tests auto-detected via `asyncio_mode = auto`)
- Use `aioresponses` for mocking HTTP requests

### Test Structure
```python
async def test_feature_success(
    auth: Auth, backend_selector: BackendSelector, aioresponses_mock: aioresponses
):
    # Arrange
    aioresponses_mock.post(url, payload=mock_data)
    # Act
    result = await auth.do_auth(store=False)
    # Assert
    assert result is True
    assert auth.is_access_token_valid()
```

### Available Fixtures (from `tests/conftest.py`)
- `aioresponses_mock` - Mock HTTP responses
- `client_session_fixture` - Shared aiohttp session
- `backend_selector` - BackendSelector instance
- `auth` - Auth instance with mock credentials
- `appliances_manager` - Fully configured manager

### Mock Data
- Store mock JSON responses in `tests/data/`
- Load with: `DATA_DIR / "filename.json"`

## Linting Configuration (ruff)

Enabled rules: `E` (pycodestyle), `F` (Pyflakes), `UP` (pyupgrade), `B` (flake8-bugbear), `I` (isort)

Max complexity: 25

## Shipping the personal fork

For `pbuffolino/whirlpool-sixth-sense`, ordinary checks run locally and independent
native Codex reviewers review the exact candidate. Hosted CI and automatic PR
label checks are retired. Do not interpret missing Actions checks as a pass.

Create an isolated Python 3.14+ environment and install `requirements-dev.txt`.
Activate it, commit the candidate, then run `bash scripts/check-local.sh` from a
clean worktree. The command preserves pytest and all pinned prek hooks, including
Ruff, basedpyright, whitespace checks and zizmor. Hooks may format files. Any
changed source requires review, a new candidate commit and a rerun. Use only the
synthetic HTTP fixtures, never appliance credentials or live appliance calls.

Record the candidate SHA, Python/tool versions, actual command result and separate
Codex review findings in the PR. Use a proper PR and recheck its head before
merging. Release/security changes require separate code and security reviewers.
Reviewers must be independent of the implementer. Skips, missing tools and failed
checks remain limitations. Never forge a status or bypass a required check.

The local checkout may have `origin` pointing at the upstream `abmantis` project.
Verify owner and repository before every push or GitHub write. This personal-fork
policy authorizes no upstream write or upstream package publication.

The inherited release-drafter and PyPI definitions remain pending the owner's
decision about this fork's release purpose. Their presence does not prove an
operational or authorized publisher. Do not publish a release, register a trusted
publisher or contact PyPI to validate these definitions.

### Releasing

The upstream release process uses a release tag to replace the `0.0.0` package
version placeholder. It is not an approved release target for this personal
fork. Establish the intended package identity and owner-approved target before
any publication. Source merge, package build, installation and live appliance
acceptance are separate states; only perform the latter operations when scoped
authorization exists. Preserve the applicable upstream contribution procedure
when preparing a separately authorized upstream contribution.

Dependency and action updates are handled by Renovate (`.github/renovate.json`);
GitHub Actions are pinned to commit digests.
