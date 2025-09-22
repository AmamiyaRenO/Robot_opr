"""Simple Tkinter UI for interacting with the game orchestrator over MQTT."""
from __future__ import annotations

import json
import logging
import os
import queue
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import paho.mqtt.client as mqtt
import tkinter as tk
from tkinter import messagebox
import yaml

from manifest import GameEntry, Manifest, ManifestError

LOGGER = logging.getLogger("orchestrator.ui")


def load_yaml(path: str) -> Dict[str, Any]:
    """Load a YAML file and return the parsed dictionary."""
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


Event = Tuple[str, Any]


class OrchestratorUI:
    """Tkinter-based control surface for the orchestrator."""

    def __init__(
        self,
        root: tk.Tk,
        *,
        games: List[GameEntry],
        mqtt_host: str,
        mqtt_port: int,
        intent_topic: str,
        state_topic: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.root = root
        self.root.title("Robot Game Launcher")
        self.root.minsize(520, 420)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._games = games
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._intent_topic = intent_topic
        self._state_topic = state_topic
        self._username = username
        self._password = password

        self._events: "queue.Queue[Event]" = queue.Queue()
        self._connected = False
        self._alive = True
        self._log_limit = 100

        self.connection_var = tk.StringVar(value="Connecting…")
        self.state_var = tk.StringVar(value="Mode: unknown • Game: –")
        self.detail_var = tk.StringVar(value="")

        self._build_layout()

        # MQTT client setup
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id="orchestrator-ui"
        )
        if self._username:
            self._client.username_pw_set(self._username, self._password or None)
        self._client.enable_logger(logging.getLogger("orchestrator.ui.mqtt"))
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        self._append_log("Connecting to MQTT…")
        self._client.loop_start()
        try:
            self._client.connect_async(self._mqtt_host, self._mqtt_port, keepalive=10)
        except ValueError:
            # Fallback for older versions where connect_async may be missing.
            self._client.connect(self._mqtt_host, self._mqtt_port, keepalive=10)

        self._schedule_event_pump()

    def _build_layout(self) -> None:
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        title = tk.Label(frame, text="Robot Game Launcher", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w")

        status_frame = tk.Frame(frame)
        status_frame.pack(fill="x", pady=(10, 6))
        tk.Label(status_frame, text="Connection:", width=12, anchor="w").pack(
            side="left"
        )
        tk.Label(status_frame, textvariable=self.connection_var, anchor="w").pack(
            side="left", fill="x", expand=True
        )

        state_box = tk.LabelFrame(frame, text="Current state")
        state_box.pack(fill="x", pady=(4, 10))
        tk.Label(state_box, textvariable=self.state_var, anchor="w").pack(
            anchor="w", padx=8, pady=(6, 2)
        )
        tk.Label(state_box, textvariable=self.detail_var, anchor="w", fg="#555555").pack(
            anchor="w", padx=8, pady=(0, 6)
        )

        game_frame = tk.LabelFrame(frame, text="Available games")
        game_frame.pack(fill="both", expand=True)
        self.game_list = tk.Listbox(game_frame, height=6, exportselection=False)
        self.game_list.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)

        scrollbar = tk.Scrollbar(game_frame, orient="vertical", command=self.game_list.yview)
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)
        self.game_list.configure(yscrollcommand=scrollbar.set)

        for game in self._games:
            label = f"{game.name} ({game.id})"
            self.game_list.insert(tk.END, label)

        button_frame = tk.Frame(frame)
        button_frame.pack(fill="x", pady=(6, 0))
        launch_btn = tk.Button(button_frame, text="Launch Selected", command=self.launch_selected)
        launch_btn.pack(side="left")
        exit_btn = tk.Button(button_frame, text="Back to Hub", command=self.send_exit_intent)
        exit_btn.pack(side="left", padx=(8, 0))

        log_frame = tk.LabelFrame(frame, text="Recent events")
        log_frame.pack(fill="both", expand=True, pady=(12, 0))
        self.log_list = tk.Listbox(log_frame, height=8)
        self.log_list.pack(fill="both", expand=True, padx=8, pady=8)

    def _schedule_event_pump(self) -> None:
        if not self._alive:
            return
        self.root.after(200, self._drain_events)

    def _drain_events(self) -> None:
        if not self._alive:
            return
        while True:
            try:
                event_type, payload = self._events.get_nowait()
            except queue.Empty:
                break
            if event_type == "connection":
                self._handle_connection_event(payload)
            elif event_type == "state":
                self._handle_state_event(payload)
            elif event_type == "log":
                self._append_log(str(payload))
        self._schedule_event_pump()

    def _handle_connection_event(self, payload: Dict[str, Any]) -> None:
        status = payload.get("status")
        if status == "connected":
            self._connected = True
            reason = payload.get("reason")
            message = "Connected"
            if reason is not None:
                message = f"Connected (rc={reason})"
            self.connection_var.set(message)
            self._append_log("Connected to MQTT broker")
            # Subscribe after we know we are connected
            self._client.subscribe(self._state_topic)
        elif status == "connect_error":
            self._connected = False
            self.connection_var.set("Connection failed")
            detail = payload.get("detail", "unknown error")
            self._append_log(f"MQTT connect error: {detail}")
        elif status == "disconnected":
            self._connected = False
            rc = payload.get("reason")
            message = "Disconnected"
            if rc is not None:
                message = f"Disconnected (rc={rc})"
            self.connection_var.set(message)
            self._append_log("Disconnected from MQTT broker")

    def _handle_state_event(self, payload: Dict[str, Any]) -> None:
        mode = str(payload.get("mode", "UNKNOWN")).upper()
        game_id = payload.get("game_id") or "–"
        detail = payload.get("detail") or ""
        self.state_var.set(f"Mode: {mode} • Game: {game_id}")
        self.detail_var.set(detail)

        timestamp = payload.get("ts")
        if isinstance(timestamp, (int, float)):
            ts_text = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
        else:
            ts_text = datetime.now().strftime("%H:%M:%S")

        summary = f"{ts_text} • {mode} ({game_id})"
        if detail:
            summary = f"{summary} — {detail}"
        self._append_log(summary)

        if mode == "RUNNING":
            for idx, game in enumerate(self._games):
                if game.id == game_id:
                    self.game_list.selection_clear(0, tk.END)
                    self.game_list.selection_set(idx)
                    self.game_list.see(idx)
                    break
        elif mode in {"IDLE", "ERROR"}:
            self.game_list.selection_clear(0, tk.END)

    def _append_log(self, message: str) -> None:
        self.log_list.insert(tk.END, message)
        if self.log_list.size() > self._log_limit:
            self.log_list.delete(0)
        self.log_list.see(tk.END)

    def _publish_intent(self, payload: Dict[str, Any]) -> None:
        if not self._connected:
            messagebox.showwarning("Not connected", "MQTT broker is not connected yet.")
            return
        try:
            self._client.publish(self._intent_topic, json.dumps(payload))
            self._append_log(f"Published {payload.get('type')} intent")
        except Exception as exc:  # pragma: no cover - defensive UI reporting
            LOGGER.exception("failed to publish intent")
            messagebox.showerror("Publish failed", f"Unable to publish intent: {exc}")

    def launch_selected(self) -> None:
        selection = self.game_list.curselection()
        if not selection:
            messagebox.showinfo("Select a game", "Please choose a game to launch.")
            return
        game = self._games[selection[0]]
        self._publish_intent(
            {
                "type": "LAUNCH_GAME",
                "game_name": game.name,
                "source": "ui",
            }
        )

    def send_exit_intent(self) -> None:
        self._publish_intent({"type": "BACK_HOME", "source": "ui"})

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):  # type: ignore[override]
        if reason_code == 0:
            self._events.put(("connection", {"status": "connected", "reason": reason_code}))
        else:
            self._events.put(
                (
                    "connection",
                    {
                        "status": "connect_error",
                        "detail": f"rc={reason_code}",
                    },
                )
            )

    def _on_disconnect(self, client, userdata, reason_code, properties=None):  # type: ignore[override]
        self._events.put(("connection", {"status": "disconnected", "reason": reason_code}))

    def _on_message(self, client, userdata, msg):  # type: ignore[override]
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError as exc:
            self._events.put(("log", f"Invalid state payload: {exc}"))
            return
        if not isinstance(payload, dict):
            self._events.put(("log", "Ignored non-dict state payload"))
            return
        self._events.put(("state", payload))

    def on_close(self) -> None:
        self.shutdown()
        self.root.destroy()

    def shutdown(self) -> None:
        if not self._alive:
            return
        self._alive = False
        try:
            self._client.disconnect()
        except Exception:
            pass
        try:
            self._client.loop_stop(force=True)
        except Exception:
            pass
        self.connection_var.set("Disconnected")
        self._append_log("UI closed")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    config_path = os.path.join(repo_root, "config", "ports.yaml")
    manifest_path = os.path.join(repo_root, "config", "manifest.json")
    schema_path = os.path.join(repo_root, "config", "manifest.schema.json")

    root = tk.Tk()

    try:
        config = load_yaml(config_path)
    except OSError as exc:
        messagebox.showerror("Configuration error", f"Failed to load {config_path}: {exc}")
        root.destroy()
        return

    mqtt_cfg = config.get("mqtt", {})
    topics_cfg = config.get("topics", {})

    try:
        manifest = Manifest(manifest_path, schema_path)
    except ManifestError as exc:
        messagebox.showerror("Manifest error", str(exc))
        root.destroy()
        return

    ui = OrchestratorUI(
        root,
        games=manifest.games,
        mqtt_host=mqtt_cfg.get("host", "127.0.0.1"),
        mqtt_port=int(mqtt_cfg.get("port", 1883)),
        intent_topic=topics_cfg.get("intent", "robot/intent"),
        state_topic=topics_cfg.get("state", "robot/state"),
        username=mqtt_cfg.get("username") or None,
        password=mqtt_cfg.get("password") or None,
    )

    try:
        root.mainloop()
    finally:
        ui.shutdown()


if __name__ == "__main__":
    main()
