from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR_ROOT = REPO_ROOT / "releases" / "current" / "orchestrator"


def _prepare_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure orchestrator modules are (re)loaded from the repo path."""
    monkeypatch.syspath_prepend(str(ORCHESTRATOR_ROOT))
    for name in ("orchestrator", "ui", "dependency_guard"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    for name in ("paho", "paho.mqtt", "paho.mqtt.client"):
        monkeypatch.delitem(sys.modules, name, raising=False)


def test_orchestrator_entrypoint_missing_dependency(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    _prepare_missing_dependency(monkeypatch)
    dependency_guard = importlib.import_module("dependency_guard")
    original_import = dependency_guard.importlib.import_module

    def fake_import(name, package=None):
        if name == "paho.mqtt.client":
            raise ImportError("missing module")
        return original_import(name, package)

    monkeypatch.setattr(dependency_guard.importlib, "import_module", fake_import)

    with pytest.raises(SystemExit) as excinfo:
        importlib.import_module("orchestrator")

    assert excinfo.value.code == 1
    message = caplog.text
    assert "pip install -r releases/current/orchestrator/requirements.txt" in message
    assert "paho.mqtt.client" in message
    sys.modules.pop("orchestrator", None)


def test_ui_entrypoint_missing_dependency(monkeypatch: pytest.MonkeyPatch):
    _prepare_missing_dependency(monkeypatch)
    dependency_guard = importlib.import_module("dependency_guard")
    original_import = dependency_guard.importlib.import_module

    def fake_import(name, package=None):
        if name == "paho.mqtt.client":
            raise ImportError("missing module")
        return original_import(name, package)

    monkeypatch.setattr(dependency_guard.importlib, "import_module", fake_import)

    calls: list[tuple[str, str]] = []

    def record_messagebox(title: str, message: str) -> None:
        calls.append((title, message))

    monkeypatch.setattr("tkinter.messagebox.showerror", record_messagebox)

    with pytest.raises(SystemExit) as excinfo:
        importlib.import_module("ui")

    assert excinfo.value.code == 1
    assert calls, "Expected the UI to show a dependency error dialog"
    title, message = calls[0]
    assert "Missing dependency" in title
    assert "pip install -r releases/current/orchestrator/requirements.txt" in message
    assert "paho.mqtt.client" in message
    sys.modules.pop("ui", None)
