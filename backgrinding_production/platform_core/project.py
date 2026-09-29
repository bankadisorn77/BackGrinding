from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable
from .context import InspectionContext


class ProjectAdapter(ABC):

    @property
    @abstractmethod
    def project_id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def pipeline_definition(self, pipeline_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_step_handlers(self) -> Dict[str, Callable[[InspectionContext, Dict[str, Any]], Any]]:
        raise NotImplementedError

    def camera_definition(self) -> List[Dict[str, Any]]:
        return []

    def io_definition(self) -> Dict[str, Any]:
        return {}

    def status_payload(self) -> Dict[str, Any]:
        return {}

    def run_pipeline(self, pipeline_id: str, context: InspectionContext):
        pass