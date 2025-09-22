"""MQTT-driven orchestrator responsible for launching games."""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
import yaml

from healthcheck import HealthCheckDefaults, HealthCheckError, HealthChecker
from intent_router import Intent, IntentRouter
from manifest import Manifest, ManifestError
from process_manager import ProcessExit, ProcessManager

LOGGER = logging.getLogger("orchestrator")


def setup_logging() -> None:
    """Configure a JSON-style logger with UTC timestamps."""
    logging.basicConfig(
        level=logging.INFO,
        format='{"ts": "%(asctime)sZ", "level": "%(levelname)s", "service": "%(name)s", "msg": "%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    logging.Formatter.converter = time.gmtime


def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class Orchestrator:
    def __init__(self, repo_root: str):
        cfg = load_yaml(os.path.join(repo_root, "config", "ports.yaml"))
        mqtt_cfg = cfg.get("mqtt", {})
        topics_cfg = cfg.get("topics", {})
        health_cfg = cfg.get("healthcheck", {})

        self._topics = topics_cfg
        self._mqtt_host = mqtt_cfg.get("host", "127.0.0.1")
        self._mqtt_port = int(mqtt_cfg.get("port", 1883))
        self._manifest = Manifest(
            os.path.join(repo_root, "config", "manifest.json"),
            os.path.join(repo_root, "config", "manifest.schema.json"),
        )
        defaults = HealthCheckDefaults(
            timeout_sec=float(health_cfg.get("default_timeout_sec", 5.0)),
            interval_sec=float(health_cfg.get("default_interval_sec", 0.2)),
        )
        self._health = HealthChecker(defaults)
        self._pm = ProcessManager()
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="orchestrator")
        if mqtt_cfg.get("username"):
            self._client.username_pw_set(mqtt_cfg.get("username"), mqtt_cfg.get("password") or None)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._router = IntentRouter(self._handle_launch_intent, self._handle_exit_intent)

    def _publish_state(self, mode: str, detail: str = "", game_id: Optional[str] = None) -> None:
        payload = {
            "mode": mode,
            "game_id": game_id or self._pm.current_game_id,
            "detail": detail,
            "ts": time.time(),
        }
        LOGGER.debug("publishing state", extra={"payload": payload})
        self._client.publish(self._topics.get("state", "robot/state"), json.dumps(payload))

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        LOGGER.info("connected to mqtt", extra={"reason_code": reason_code})
        client.subscribe(self._topics.get("intent", "robot/intent"))
        self._publish_state("IDLE" if not self._pm.is_running() else "RUNNING")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError as exc:
            LOGGER.error("invalid payload", extra={"error": str(exc)})
            return
        self._router.dispatch(payload)

    def _handle_launch_intent(self, intent: Intent) -> None:
        spoken = intent.game_name or ""
        game = self._manifest.resolve(spoken)
        if not game:
            detail = f"unknown game: {spoken}"
            LOGGER.warning(detail)
            self._publish_state("ERROR", detail)
            return

        if self._pm.is_running():
            self._publish_state("STOPPING")
            exit_info = self._pm.stop()
            self._handle_process_exit(exit_info)

        LOGGER.info("launching game", extra={"game_id": game.id, "source": intent.source})
        try:
            self._publish_state("STARTING", game_id=game.id)
            self._pm.start(game)
            self._health.wait_until_healthy(game)
        except HealthCheckError as exc:
            LOGGER.error("healthcheck failed", extra={"game_id": game.id, "detail": str(exc)})
            self._publish_state("ERROR", str(exc), game_id=game.id)
            exit_info = self._pm.stop()
            if exit_info:
                self._handle_process_exit(exit_info)
            return
        except Exception as exc:
            LOGGER.exception("launch failed", extra={"game_id": game.id})
            self._publish_state("ERROR", str(exc), game_id=game.id)
            exit_info = self._pm.stop()
            if exit_info:
                self._handle_process_exit(exit_info)
            return

        self._publish_state("RUNNING", game_id=game.id)

    def _handle_exit_intent(self, intent: Intent) -> None:
        if not self._pm.is_running():
            LOGGER.info("received exit intent while idle")
            self._publish_state("IDLE")
            return

        LOGGER.info("stopping game due to exit intent", extra={"source": intent.source})
        self._publish_state("STOPPING")
        exit_info = self._pm.stop()
        self._handle_process_exit(exit_info)

    def _handle_process_exit(self, exit_info: Optional[ProcessExit]) -> None:
        if not exit_info:
            return
        if exit_info.expected:
            LOGGER.info(
                "game exited",
                extra={"game_id": exit_info.game_id, "returncode": exit_info.returncode},
            )
            self._publish_state("IDLE")
        else:
            detail = (
                f"game {exit_info.game_id or 'unknown'} crashed"
                f" (code={exit_info.returncode})"
            )
            LOGGER.error(detail)
            self._publish_state("IDLE", detail)

    def _poll_for_exit(self) -> None:
        exit_info = self._pm.poll_exit()
        if exit_info and not exit_info.expected:
            self._handle_process_exit(exit_info)

    def run(self) -> None:
        LOGGER.info("starting orchestrator loop")
        self._client.connect(self._mqtt_host, self._mqtt_port, keepalive=10)
        self._client.loop_start()
        try:
            while True:
                self._poll_for_exit()
                time.sleep(0.5)
        except KeyboardInterrupt:
            LOGGER.info("keyboard interrupt received, shutting down")
        finally:
            self._client.loop_stop()
            self._client.disconnect()
            exit_info = self._pm.stop()
            self._handle_process_exit(exit_info)


def main() -> None:
    setup_logging()
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    try:
        orchestrator = Orchestrator(repo_root)
    except ManifestError as exc:
        LOGGER.error("failed to initialise orchestrator", extra={"error": str(exc)})
        raise SystemExit(1) from exc
    orchestrator.run()


if __name__ == "__main__":
    main()
