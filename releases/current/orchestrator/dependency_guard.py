"""Utility helpers for checking orchestrator optional dependencies."""
from __future__ import annotations

import importlib
from typing import Callable, Iterable

_REQUIREMENTS_PATH = "releases/current/orchestrator/requirements.txt"


def dependency_message(module_name: str) -> str:
    """Return the user-facing message for a missing dependency."""
    return (
        f"Missing dependency '{module_name}'. Please run "
        f"'pip install -r {_REQUIREMENTS_PATH}' before re-running."
    )


def ensure_dependencies(
    modules: Iterable[str],
    on_error: Callable[[str, str], None],
) -> None:
    """Import each module name, calling *on_error* if an ImportError occurs.

    Parameters
    ----------
    modules:
        An iterable of dotted module names to import.
    on_error:
        Callback receiving ``(module_name, friendly_message)`` when an import
        fails. The helper will exit the process with ``SystemExit(1)`` after the
        callback returns.
    """

    for module_name in modules:
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            message = dependency_message(module_name)
            on_error(module_name, message)
            raise SystemExit(1) from exc


__all__ = ["dependency_message", "ensure_dependencies"]
