"""A complete gate must reject inherited selectors before invoking check tools."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("selector", ["PREK_SKIP", "SKIP", "PYTEST_ADDOPTS"])
def test_inherited_selection_cannot_report_complete_validation(tmp_path, selector):
    marker = tmp_path / "tool-invoked"
    for command in ("python3", "prek"):
        tool = tmp_path / command
        tool.write_text('#!/bin/sh\ntouch "$TOOL_MARKER"\nexit 99\n')
        tool.chmod(0o755)
    environment = os.environ.copy()
    for name in ("PREK_SKIP", "SKIP", "PYTEST_ADDOPTS"):
        environment.pop(name, None)
    environment.update(
        {
            selector: "skip-sentinel",
            "PATH": str(tmp_path) + os.pathsep + environment["PATH"],
            "TOOL_MARKER": str(marker),
        }
    )
    script = Path(__file__).resolve().parents[1] / "scripts" / "check-local.sh"
    result = subprocess.run(
        ["bash", str(script)],
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 2
    assert selector in result.stderr
    assert "Local checks passed" not in result.stdout
    assert not marker.exists()
