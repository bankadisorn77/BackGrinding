# platform_core/communication.py
import time
import logging
from typing import Dict, Any
from ProcessClass.pipe import sender

logger = logging.getLogger("Communication")

class PlatformStatusReporter:
    def __init__(self):
        try:
            self.sender = sender()
        except Exception as e:
            logger.warning(f"Shared memory sender initialization failed: {e}")
            self.sender = None

    def report(self, payload: Dict[str, Any]):
        if self.sender:
            payload["last_update"] = time.time()
            self.sender.send_event({"status": payload})

    def close(self):
        if self.sender:
            try:
                self.sender.close()
            except Exception as e:
                logger.warning(f"Error closing sender: {e}")