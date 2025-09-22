import json
import os
import queue
import threading
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover - exercised in environments without paho
    mqtt = None


def load_ports_yaml():
    import yaml
    here = os.path.dirname(os.path.dirname(__file__))
    with open(os.path.join(here, 'config', 'ports.yaml'), 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    if mqtt is None:
        print(
            "Missing dependency 'paho.mqtt.client'. Please run "
            "'pip install -r releases/current/orchestrator/requirements.txt' first.",
        )
        return 1

    cfg = load_ports_yaml()
    host = cfg['mqtt']['host']
    port = int(cfg['mqtt']['port'])
    topic = cfg['topics']['telemetry_prefix'] + 'smoke'

    q = queue.Queue()

    def on_connect(client, userdata, flags, reason_code, properties=None):
        client.subscribe(topic)
        client.publish(topic, json.dumps({
            'ts': time.time(),
            'msg': 'hello from smoke test'
        }))

    def on_message(client, userdata, msg):
        q.put((msg.topic, msg.payload.decode('utf-8')))

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(host, port, keepalive=10)

    t = threading.Thread(target=client.loop_forever, daemon=True)
    t.start()

    try:
        topic_rx, payload = q.get(timeout=5)
        print('OK', topic_rx, payload)
        client.disconnect()
        return 0
    except queue.Empty:
        print('FAIL: no message echoed within 5s')
        client.disconnect()
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

