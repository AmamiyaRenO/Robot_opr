"""Manifest loading utilities for the game orchestrator."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from jsonschema import validate


class ManifestError(Exception):
    """Raised when the manifest file cannot be parsed or validated."""


@dataclass
class GameEntry:
    """Single entry in the manifest."""

    id: str
    name: str
    exec: str
    synonyms: List[str]
    workdir: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    healthcheck: Dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalize synonyms to lowercase for lookup simplicity.
        self.synonyms = [s.lower() for s in self.synonyms]
        # Ensure optional collections are always concrete types.
        self.args = list(self.args or [])
        self.env = dict(self.env or {})
        self.healthcheck = dict(self.healthcheck or {})


class Manifest:
    """Loads and resolves entries from the manifest file."""

    def __init__(self, manifest_path: str, schema_path: str):
        self._manifest_path = manifest_path
        self._schema_path = schema_path
        self._games: Dict[str, GameEntry] = {}
        self._syn_to_id: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self._manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with open(self._schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
        except OSError as exc:
            raise ManifestError(f"failed to load manifest: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ManifestError(f"invalid manifest json: {exc}") from exc

        try:
            validate(instance=data, schema=schema)
        except Exception as exc:  # jsonschema.ValidationError and friends
            raise ManifestError(f"manifest validation failed: {exc}") from exc

        games = data.get("games", [])
        self._games.clear()
        self._syn_to_id.clear()
        for raw in games:
            entry = GameEntry(
                id=raw["id"],
                name=raw["name"],
                exec=raw["exec"],
                synonyms=raw.get("synonyms", []),
                workdir=raw.get("workdir"),
                args=raw.get("args") or [],
                env=raw.get("env") or {},
                healthcheck=raw.get("healthcheck") or {"type": "none"},
            )
            self._games[entry.id] = entry
            # Allow lookup by synonyms, name, and id (case-insensitive).
            for key in entry.synonyms + [entry.name.lower(), entry.id.lower()]:
                self._syn_to_id[key] = entry.id

    def resolve(self, spoken: str) -> Optional[GameEntry]:
        key = (spoken or "").lower().strip()
        if not key:
            return None
        game_id = self._syn_to_id.get(key)
        return self._games.get(game_id) if game_id else None

    def get(self, game_id: str) -> Optional[GameEntry]:
        return self._games.get(game_id)

    @property
    def games(self) -> List[GameEntry]:
        return list(self._games.values())


__all__ = ["Manifest", "GameEntry", "ManifestError"]
