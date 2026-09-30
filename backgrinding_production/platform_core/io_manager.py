# platform_core/io_manager.py
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger("IOManager")


class BaseIOManager(ABC):
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def read_input(self, channel: int) -> int:
        pass

    @abstractmethod
    def write_output(self, channel: int, value: bool) -> bool:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def close(self):
        pass


class AdvantechIOManager(BaseIOManager):

    def __init__(self, device: str = "USB-4761,BID#0", auto_connect: bool = False):
        self.device = device
        self.gpio = None
        self._is_connected = False
        
        if auto_connect:
            self.connect()

    def connect(self) -> bool:
        try:
            from .module.gpio.advantech import GPIO
            if self.gpio:
                self.close()

            self.gpio = GPIO(device=self.device)
            self._is_connected = getattr(self.gpio, "is_connected", False)
            logger.info(f"[IOManager] Connected: {self._is_connected}")
            return self._is_connected
        except Exception as e:
            logger.error(f"[IOManager] Connect failed: {e}")
            self._is_connected = False
            return False

    def read_input(self, channel: int) -> int:
        if not self._is_connected or not self.gpio:
            return 0
        try:
            val = self.gpio.readInput(channel)
            return val if val is not None else 0
        except Exception as e:
            logger.error(f"[IOManager] read_input error: {e}")
            return 0

    def write_output(self, channel: int, value: bool) -> bool:
        if not self._is_connected or not self.gpio:
            return False
        try:
            return bool(self.gpio.outputWrite(channel, on=value))
        except Exception as e:
            logger.error(f"[IOManager] write_output error: {e}")
            return False

    def is_connected(self) -> bool:
        return bool(self._is_connected and self.gpio and getattr(self.gpio, "is_connected", False))

    def close(self):
        if self.gpio:
            try:
                self.gpio.closeIO()
            except Exception:
                pass
        self._is_connected = False
        self.gpio = None


class DummyIOManager(BaseIOManager):
    def connect(self) -> bool:
        return True

    def read_input(self, channel: int) -> int:
        return 0

    def write_output(self, channel: int, value: bool) -> bool:
        return True

    def is_connected(self) -> bool:
        return True

    def close(self):
        pass