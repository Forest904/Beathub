#!/usr/bin/env python
"""
Core progress primitives shared by background jobs and HTTP adapters.

Provides a simple publish/subscribe broker plus a publisher interface so
other layers can depend on abstractions instead of concrete broker types.
"""

from __future__ import annotations

import json
import threading
import time
from queue import Queue, Empty
from typing import Dict, Iterator


class ProgressBroker:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: Dict[int, Queue] = {}
        self._next_id = 1

    def publish(self, event: dict) -> None:
        with self._lock:
            for q in self._subscribers.values():
                q.put(event)

    def subscribe(self, heartbeat_seconds: int = 15) -> Iterator[str]:
        """Return an iterator yielding SSE-formatted lines."""
        with self._lock:
            sid = self._next_id
            self._next_id += 1
            q: Queue = Queue()
            self._subscribers[sid] = q

        last_beat = time.time()
        try:
            while True:
                try:
                    ev = q.get(timeout=1.0)
                    payload = json.dumps(ev, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
                except Empty:
                    now = time.time()
                    if now - last_beat >= heartbeat_seconds:
                        last_beat = now
                        yield "event: heartbeat\n" + f"data: {{\"ts\": {int(now)} }}\n\n"
        finally:
            with self._lock:
                self._subscribers.pop(sid, None)


class ProgressPublisher:
    def publish(self, event: dict) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class BrokerPublisher(ProgressPublisher):
    def __init__(self, broker: ProgressBroker) -> None:
        self._broker = broker

    def publish(self, event: dict) -> None:
        self._broker.publish(event)


__all__ = ["ProgressBroker", "ProgressPublisher", "BrokerPublisher"]
