#!/usr/bin/env python
"""
In-memory progress broker for streaming SpotDL download updates to clients.

Provides a simple publish/subscribe model used by the SSE endpoint.
"""

from __future__ import annotations

import json
import threading
import time
from queue import Queue, Empty
from typing import Dict, Iterator, Optional


class ProgressBroker:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: Dict[int, Queue] = {}
        self._next_id = 1

    def publish(self, event: dict) -> None:
        with self._lock:
            for q in self._subscribers.values():
                # Non-blocking put: queue default is unbounded; keep it simple
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
                    # heartbeat to keep connections alive
                    now = time.time()
                    if now - last_beat >= heartbeat_seconds:
                        last_beat = now
                        yield "event: heartbeat\n" + f"data: {{\"ts\": {int(now)} }}\n\n"
        finally:
            with self._lock:
                self._subscribers.pop(sid, None)


__all__ = ["ProgressBroker"]

