"""Health check helpers for launched games."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests

from manifest import GameEntry

LOGGER = logging.getLogger("orchestrator.healthcheck")


class HealthCheckError(Exception):
    """Raised when the game fails to become healthy in time."""


@dataclass
class HealthCheckDefaults:
    timeout_sec: float
    interval_sec: float


class HealthChecker:
    def __init__(self, defaults: HealthCheckDefaults):
        self._defaults = defaults
        self._session = requests.Session()

    def wait_until_healthy(self, game: GameEntry) -> None:
        cfg = dict(game.healthcheck or {"type": "none"})
        check_type = (cfg.get("type") or "none").lower()
        if check_type == "none":
            LOGGER.info("skipping healthcheck", extra={"game_id": game.id})
            time.sleep(min(0.2, self._defaults.interval_sec))
            return
        if check_type == "http":
            self._wait_http(game, cfg)
            return
        raise HealthCheckError(f"unknown healthcheck type: {check_type}")

    def _wait_http(self, game: GameEntry, cfg: dict) -> None:
        port = cfg.get("port")
        if port is None:
            raise HealthCheckError("http healthcheck requires 'port'")
        path = cfg.get("path", "/health")
        timeout = float(cfg.get("timeout_sec", self._defaults.timeout_sec))
        interval = float(cfg.get("interval_sec", self._defaults.interval_sec))
        url = f"http://127.0.0.1:{port}{path}"
        deadline = time.time() + timeout
        last_error: Optional[str] = None

        LOGGER.info("waiting for http healthcheck", extra={"game_id": game.id, "url": url})
        while time.time() < deadline:
            try:
                resp = self._session.get(url, timeout=interval)
                if 200 <= resp.status_code < 300:
                    LOGGER.info("healthcheck ok", extra={"game_id": game.id})
                    return
                last_error = f"status={resp.status_code}"
            except requests.RequestException as exc:
                last_error = str(exc)
            time.sleep(interval)

        raise HealthCheckError(
            f"healthcheck timeout for {game.id}: {last_error or 'no successful response'}"
        )


__all__ = ["HealthChecker", "HealthCheckDefaults", "HealthCheckError"]
