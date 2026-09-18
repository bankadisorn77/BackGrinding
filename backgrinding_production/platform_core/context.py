from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import uuid


class InspectionContext:
    """Shared data container for one inspection cycle (Python 3.6 compatible)."""

    def __init__(
        self,
        project_id: str,
        pipeline_id: str,
        device_id: str,
        cycle_id: Optional[str] = None,
        started_at: Optional[str] = None,
        camera_id: Optional[str] = None,
    ):
        self.project_id = project_id
        self.pipeline_id = pipeline_id
        self.device_id = device_id
        self.cycle_id = cycle_id or uuid.uuid4().hex
        self.started_at = started_at or datetime.utcnow().isoformat() + "Z"
        self.camera_id = camera_id
        self.frames = {}
        self.detections = {}
        self.results = {}
        self.metadata = {}

    def for_camera(self, camera_id: str) -> "InspectionContext":
        child = InspectionContext(
            project_id=self.project_id,
            pipeline_id=self.pipeline_id,
            device_id=self.device_id,
            cycle_id=self.cycle_id,
            started_at=self.started_at,
            camera_id=camera_id,
        )
        child.frames = self.frames
        child.detections = self.detections
        child.results = self.results
        child.metadata = dict(self.metadata)
        child.metadata["camera_id"] = camera_id
        return child
