import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
import time


@dataclass
class BurnSession:
    """Thread-safe status holder for a single CD burn session."""
    id: str
    title: str
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    # Status fields
    is_burning: bool = False
    current_status: str = "Idle"
    progress_percentage: int = 0
    last_error: Optional[str] = None
    burner_detected: bool = False
    disc_present: bool = False
    disc_blank_or_erasable: bool = False

    # Audit fields
    started_at: Optional[float] = None  # epoch seconds
    ended_at: Optional[float] = None    # epoch seconds
    events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "session_id": self.id,
                "title": self.title,
                "is_burning": self.is_burning,
                "current_status": self.current_status,
                "progress_percentage": self.progress_percentage,
                "last_error": self.last_error,
                "burner_detected": self.burner_detected,
                "disc_present": self.disc_present,
                "disc_blank_or_erasable": self.disc_blank_or_erasable,
                "started_at": self.started_at,
                "ended_at": self.ended_at,
                "events": list(self.events),
            }

    # --- Mutators ---
    def start(self, status: str = "Starting...", progress: int = 0) -> None:
        with self._lock:
            self.is_burning = True
            self.current_status = status
            self.progress_percentage = progress
            self.last_error = None
            self.started_at = time.time()
            # First audit event
            self.events.append({
                "ts": self.started_at,
                "type": "session_start",
                "status": status,
                "progress": progress,
            })

    def update_status(self, status: str, progress: Optional[int] = None) -> None:
        with self._lock:
            self.current_status = status
            if progress is not None:
                self.progress_percentage = int(max(0, min(100, progress)))

    def set_error(self, message: str) -> None:
        with self._lock:
            self.is_burning = False
            self.current_status = "Error"
            self.last_error = message
            self.ended_at = time.time()
            self.events.append({
                "ts": self.ended_at,
                "type": "session_end",
                "result": "error",
                "error_message": message,
            })

    def complete(self) -> None:
        with self._lock:
            self.is_burning = False
            self.current_status = "Completed"
            self.progress_percentage = 100
            self.last_error = None
            self.ended_at = time.time()
            self.events.append({
                "ts": self.ended_at,
                "type": "session_end",
                "result": "success",
            })

    def update_burner_state(self, *, detected: bool, present: bool, blank_or_erasable: bool) -> None:
        with self._lock:
            self.burner_detected = detected
            self.disc_present = present
            self.disc_blank_or_erasable = blank_or_erasable
            if detected and present and blank_or_erasable:
                self.current_status = "Burner Ready"
            elif detected and present and not blank_or_erasable:
                self.current_status = "Disc Not Blank/Erasable"
            elif detected and not present:
                self.current_status = "No Disc"
            else:
                self.current_status = "No Burner Detected"

    # --- Audit helpers ---
    def log_event(self, event_type: str, **details: Any) -> None:
        with self._lock:
            self.events.append({
                "ts": time.time(),
                "type": event_type,
                **details,
            })


class BurnSessionManager:
    """Manages burn sessions with simple single-concurrency policy."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: Dict[str, BurnSession] = {}
        self._last_session_id: Optional[str] = None

    def create(self, *, title: str, session_id: str) -> BurnSession:
        with self._lock:
            sess = BurnSession(id=session_id, title=title)
            self._sessions[session_id] = sess
            self._last_session_id = session_id
            return sess

    def get(self, session_id: str) -> Optional[BurnSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def last(self) -> Optional[BurnSession]:
        with self._lock:
            if self._last_session_id is None:
                return None
            return self._sessions.get(self._last_session_id)

    def is_any_burning(self) -> bool:
        with self._lock:
            for s in self._sessions.values():
                if s.is_burning:
                    return True
            return False

    def cleanup_finished(self) -> None:
        with self._lock:
            to_del = [sid for sid, s in self._sessions.items() if not s.is_burning and s.current_status in ("Completed", "Error")]
            for sid in to_del:
                self._sessions.pop(sid, None)


__all__ = ["BurnSession", "BurnSessionManager"]

