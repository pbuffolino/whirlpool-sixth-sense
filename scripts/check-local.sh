#!/usr/bin/env bash
# Run from a clean, frozen candidate; prek may apply formatting fixes.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Commit the candidate first; local validation requires a clean worktree." >&2
  exit 2
fi
PYTHON=${PYTHON:-python3}
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 14), "Python 3.14+ is required"'
HEAD_BEFORE=$(git rev-parse HEAD)
"$PYTHON" -m pytest --log-cli-level=debug
echo "Running pinned prek hooks, including Ruff, basedpyright and zizmor."
echo "Hooks can format files; any changes require review, a new commit and a rerun."
prek run --all-files
test "$(git rev-parse HEAD)" = "$HEAD_BEFORE"
test -z "$(git status --porcelain)"
echo "Local checks passed at $HEAD_BEFORE. Independent Codex review is still required."
