"""Intent routing utilities for MQTT payloads."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

LOGGER = logging.getLogger("orchestrator.intent_router")


@dataclass
class Intent:
    type: str
    game_name: Optional[str] = None
    source: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


class IntentRouter:
    def __init__(
        self,
        on_launch: Callable[[Intent], None],
        on_exit: Callable[[Intent], None],
    ) -> None:
        self._on_launch = on_launch
        self._on_exit = on_exit

    def dispatch(self, payload: Dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            LOGGER.error("intent payload must be a dict")
            return
        intent_type = (payload.get("type") or "").upper()
        intent = Intent(
            type=intent_type,
            game_name=payload.get("game_name") or payload.get("game"),
            source=payload.get("source"),
            raw=payload,
        )
        if intent_type == "LAUNCH_GAME":
            self._on_launch(intent)
        elif intent_type in {"BACK_HOME", "QUIT"}:
            self._on_exit(intent)
        else:
            LOGGER.info("ignoring unsupported intent", extra={"type": intent_type})


__all__ = ["Intent", "IntentRouter"]
