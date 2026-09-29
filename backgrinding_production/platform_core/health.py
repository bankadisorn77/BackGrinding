from __future__ import annotations
import threading
import time
import logging
from typing import Dict, Any, Callable, Optional

logger = logging.getLogger("HealthMonitor")


class HealthMonitor:
    def __init__(
        self,
        check_interval: float = 3.0,
        on_status_change: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.check_interval = check_interval
        self.on_status_change = on_status_change
        
        self._monitors: Dict[str, Callable[[], bool]] = {}
        
        self._current_status: Dict[str, bool] = {}
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def register_check(self, name: str, check_func: Callable[[], bool]):
        self._monitors[name] = check_func
        self._current_status[name] = True

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="HealthMonitorThread")
        self._thread.start()
        logger.info("HealthMonitor background service started.")

    def stop(self, timeout: float = 2.0):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        logger.info("HealthMonitor background service stopped.")

    def check_now(self) -> Dict[str, bool]:
        results = {}
        for name, func in self._monitors.items():
            try:
                results[name] = bool(func())
            except Exception as exc:
                logger.error(f"Error checking health for '{name}': {exc}")
                results[name] = False
        return results

    def is_healthy(self) -> bool:
        return all(self._current_status.values()) if self._current_status else True

    @property
    def status(self) -> Dict[str, Any]:
        return {
            "healthy": self.is_healthy(),
            "details": dict(self._current_status),
            "timestamp": time.time(),
        }

    def _run_loop(self):
        while not self._stop_event.is_set():
            new_status = self.check_now()
            if new_status != self._current_status:
                self._current_status = new_status
                logger.warning(f"System health state changed: {self._current_status}")
                if self.on_status_change:
                    try:
                        self.on_status_change(self.status)
                    except Exception as e:
                        logger.error(f"Error executing on_status_change callback: {e}")
            if self._stop_event.wait(self.check_interval):
                break