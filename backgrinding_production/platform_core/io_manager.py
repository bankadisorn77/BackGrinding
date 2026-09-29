from abc import ABC, abstractmethod
from typing import Any

class BaseIOManager(ABC):
    @abstractmethod
    def read_input(self, channel: int) -> int:
        pass

    @abstractmethod
    def write_output(self, channel: int, value: bool) -> bool:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass