from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class ProjectAdapter(ABC):
    """Project-specific boundary.

    Platform code can load any project implementing this small contract.
    """

    project_id = "unknown"

    @abstractmethod
    def status_payload(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def pipeline_definition(self, pipeline_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def run_pipeline(self, pipeline_id: str, context):
        raise NotImplementedError

    def io_definition(self) -> Dict[str, Any]:
        return {}

    def camera_definition(self):
        return []
