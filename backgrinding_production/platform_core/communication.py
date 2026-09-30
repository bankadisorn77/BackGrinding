# platform_core/communication.py
import time
import logging
from typing import Dict, Any

logger = logging.getLogger("Communication")

try:
    from ProcessClass.pipe import sender as _SharedMemorySender
except Exception:
    _SharedMemorySender = None


class PlatformStatusReporter:
    """Reports platform status without making shared-memory support mandatory."""
    def __init__(self):
        self.sender = None
        if _SharedMemorySender is not None:
            try:
                self.sender = _SharedMemorySender()
            except Exception as exc:
                logger.warning("Shared memory sender initialization failed: %s", exc)

    def report(self, payload: Dict[str, Any]):
        if self.sender:
            data = dict(payload)
            data["last_update"] = time.time()
            try:
                self.sender.send_event({"status": data})
            except Exception as exc:
                logger.warning("Status report failed: %s", exc)

    def close(self):
        if self.sender:
            try:
                self.sender.close()
            except Exception:
                pass
            self.sender = None
