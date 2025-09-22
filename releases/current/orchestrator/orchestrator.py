import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import paho.mqtt.client as mqtt
import psutil
import yaml
from jsonschema import validate


LOGGER = logging.getLogger("orchestrator")


def setup_logging():
    # Simple JSON logger to stdout (UTC)
    logging.basicConfig(
        level=logging.INFO,
        format='{"ts": "%(asctime)sZ", "level": "%(levelname)s", "service": "%(name)s", "msg": "%(message)s"}',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )


def load_yaml(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_json(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


@dataclass
class GameEntry:
    id: str
    name: str
    exec: str
    synonyms: List[str]
    workdir: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    healthcheck: Optional[Dict] = None


class Manifest:
    def __init__(self, manifest_path: str, schema_path: str):
        data = load_json(manifest_path)
        schema = load_json(schema_path)
        validate(instance=data, schema=schema)
        self._games: Dict[str, GameEntry] = {}
        self._syn_to_id: Dict[str, str] = {}
        for g in data['games']:
            entry = GameEntry(
                id=g['id'], name=g['name'], exec=g['exec'], synonyms=[s.lower() for s in g['synonyms']],
                workdir=g.get('workdir'), args=g.get('args') or [], env=g.get('env') or {}, healthcheck=g.get('healthcheck') or {}
            )
            self._games[entry.id] = entry
            for s in entry.synonyms + [entry.name.lower(), entry.id.lower()]:
                self._syn_to_id[s] = entry.id

    def resolve(self, spoken: str) -> Optional[GameEntry]:
        key = (spoken or '').lower().strip()
        gid = self._syn_to_id.get(key)
        return self._games.get(gid) if gid else None


class ProcessManager:
    def __init__(self):
        self._proc: Optional[psutil.Process] = None
        self._game: Optional[GameEntry] = None

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.is_running()

    def start(self, game: GameEntry):
        if self.is_running():
            raise RuntimeError("A game is already running")
        env = os.environ.copy()
        env.update(game.env or {})
        cmd = [game.exec] + (game.args or [])
        LOGGER.info(f"launching: {cmd}")
        p = subprocess.Popen(cmd, cwd=game.workdir or None, env=env)
        self._proc = psutil.Process(p.pid)
        self._game = game

    def stop(self, timeout_sec: float = 3.0):
        if not self.is_running():
            return
        proc = self._proc
        assert proc is not None
        LOGGER.info("stopping current game")
        try:
            for child in proc.children(recursive=True):
                child.terminate()
            proc.terminate()
            gone, alive = psutil.wait_procs([proc], timeout=timeout_sec)
            if alive:
                LOGGER.warning("force killing remaining process")
                for p in alive:
                    p.kill()
        finally:
            self._proc = None
            self._game = None

    @property
    def current_game_id(self) -> Optional[str]:
        return self._game.id if self._game else None


class Orchestrator:
    def __init__(self, repo_root: str):
        cfg = load_yaml(os.path.join(repo_root, 'config', 'ports.yaml'))
        self._topics = cfg['topics']
        self._mqtt_host = cfg['mqtt']['host']
        self._mqtt_port = int(cfg['mqtt']['port'])
        self._manifest = Manifest(
            os.path.join(repo_root, 'config', 'manifest.json'),
            os.path.join(repo_root, 'config', 'manifest.schema.json'),
        )
        self._pm = ProcessManager()
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="orchestrator")
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def _publish_state(self, mode: str, detail: str = ""):
        payload = {
            "mode": mode,
            "game_id": self._pm.current_game_id,
            "detail": detail,
            "ts": time.time()
        }
        self._client.publish(self._topics['state'], json.dumps(payload))

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        LOGGER.info("connected to mqtt")
        client.subscribe(self._topics['intent'])
        self._publish_state("IDLE" if not self._pm.is_running() else "RUNNING")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except Exception as e:
            LOGGER.error(f"invalid payload: {e}")
            return
        intent_type = (payload.get('type') or '').upper()
        if intent_type == 'LAUNCH_GAME':
            spoken = payload.get('game_name') or payload.get('game') or ''
            game = self._manifest.resolve(spoken)
            if not game:
                self._publish_state("ERROR", f"unknown game: {spoken}")
                return
            try:
                self._publish_state("STOPPING")
                self._pm.stop()
                self._publish_state("STARTING", game.id)
                self._pm.start(game)
                self._publish_state("RUNNING")
            except Exception as e:
                LOGGER.exception("launch failed")
                self._publish_state("ERROR", str(e))
        elif intent_type in ('BACK_HOME', 'QUIT'):
            try:
                self._publish_state("STOPPING")
                self._pm.stop()
                self._publish_state("IDLE")
            except Exception as e:
                LOGGER.exception("stop failed")
                self._publish_state("ERROR", str(e))
        else:
            LOGGER.info(f"ignore intent: {intent_type}")

    def run(self):
        LOGGER.info("starting orchestrator loop")
        self._client.connect(self._mqtt_host, self._mqtt_port, keepalive=10)
        self._client.loop_forever()


def main():
    setup_logging()
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    orch = Orchestrator(repo_root)
    orch.run()


if __name__ == '__main__':
    main()

