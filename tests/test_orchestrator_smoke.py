import json
import os
import threading
import time

import pytest

mqtt = pytest.importorskip(
    "paho.mqtt.client",
    reason="paho-mqtt is required for the orchestrator smoke test",
)


def load_ports_yaml():
    import yaml
    here = os.path.dirname(os.path.dirname(__file__))
    with open(os.path.join(here, 'config', 'ports.yaml'), 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    cfg = load_ports_yaml()
    topics = cfg['topics']
    host = cfg['mqtt']['host']
    port = int(cfg['mqtt']['port'])

    last_state = {}

    def on_connect(client, userdata, flags, reason_code, properties=None):
        client.subscribe(topics['state'])
        client.publish(topics['intent'], json.dumps({"type": "LAUNCH_GAME", "game_name": "记事本", "source": "test"}))

    def on_message(client, userdata, msg):
        nonlocal last_state
        try:
            last_state = json.loads(msg.payload.decode('utf-8'))
        except Exception:
            pass

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, keepalive=10)

    t = threading.Thread(target=client.loop_forever, daemon=True)
    t.start()

    t0 = time.time()
    while time.time() - t0 < 8:
        if last_state.get('mode') in ('STARTING', 'RUNNING', 'ERROR'):
            break
        time.sleep(0.1)

    print('state:', last_state)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

