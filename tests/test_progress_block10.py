import json
import threading
import time
from queue import Queue

import pytest


@pytest.mark.unit
def test_publish_and_subscribe_basic():
    from src.progress import ProgressBroker

    broker = ProgressBroker()
    gen = broker.subscribe()

    # Consume in a background thread so the generator registers the subscriber
    out_q: Queue = Queue()

    def consume():
        try:
            chunk = next(gen)
            out_q.put(chunk)
        except Exception as e:
            out_q.put(e)

    t = threading.Thread(target=consume, daemon=True)
    t.start()

    # Wait until the subscriber is registered
    deadline = time.time() + 1.0
    while time.time() < deadline and not broker._subscribers:
        time.sleep(0.001)

    broker.publish({"a": 1, "b": "x"})
    chunk = out_q.get(timeout=1.0)

    assert isinstance(chunk, str)
    assert chunk.startswith("data: ")
    assert chunk.strip().endswith("}")
    payload = json.loads(chunk[len("data: ") :].strip())
    assert payload == {"a": 1, "b": "x"}


@pytest.mark.unit
def test_heartbeat_without_events(monkeypatch):
    import src.progress as prog

    broker = prog.ProgressBroker()

    # Make queue.get return immediately with Empty so we don't sleep
    def fake_get(self, timeout=1.0):
        raise prog.Empty()

    monkeypatch.setattr(prog.Queue, "get", fake_get, raising=True)

    # Control time flow so that a heartbeat is emitted immediately
    times = iter([0, 20, 40])

    def fake_time():
        try:
            return next(times)
        except StopIteration:
            return 40

    monkeypatch.setattr(prog.time, "time", staticmethod(fake_time), raising=True)

    gen = broker.subscribe(heartbeat_seconds=15)
    chunk = next(gen)
    assert "event: heartbeat" in chunk or chunk.startswith("event: heartbeat")


@pytest.mark.unit
def test_unsubscribe_on_generator_close():
    from src.progress import ProgressBroker

    broker = ProgressBroker()
    assert len(broker._subscribers) == 0
    gen = broker.subscribe()

    # Prime the generator in a background thread so that it registers
    def consume():
        try:
            next(gen)
        except Exception:
            pass

    out_q: Queue = Queue()

    def consume_once():
        try:
            chunk = next(gen)
            out_q.put(chunk)
        except Exception as e:
            out_q.put(e)

    t = threading.Thread(target=consume_once, daemon=True)
    t.start()

    deadline = time.time() + 1.0
    while time.time() < deadline and not broker._subscribers:
        time.sleep(0.001)

    assert len(broker._subscribers) == 1

    # Cause the generator to yield once so it's no longer executing,
    # then close it to trigger cleanup in finally block.
    broker.publish({"ok": 1})
    chunk = out_q.get(timeout=1.0)
    assert isinstance(chunk, str) and chunk.startswith("data: ")

    gen.close()
    assert len(broker._subscribers) == 0
