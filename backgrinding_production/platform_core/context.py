from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid


@dataclass
class InspectionContext:
    project_id: str
    pipeline_id: str
    device_id: str
    cycle_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    camera_id: Optional[str] = None
    frames: Dict[str, Any] = field(default_factory=dict)
    detections: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

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
