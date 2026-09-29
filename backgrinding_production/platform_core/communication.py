from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseCommunicator(ABC):
    @abstractmethod
    def send_status(self, payload: Dict[str, Any]):
        pass