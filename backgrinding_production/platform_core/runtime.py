from __future__ import annotations
import uuid
import logging
from typing import Optional, Dict, Any, List

from .context import InspectionContext
from .camera_manager import CameraManager
from .pipeline import PipelineEngine
from .project import ProjectAdapter
from .health import HealthMonitor
from .camera_manager import CameraManager

logger = logging.getLogger("PlatformRuntime")


class PlatformRuntime:
    def __init__(
        self,
        project: ProjectAdapter,
        camera_manager: Optional[CameraManager] = None,
        health_monitor: Optional[HealthMonitor] = None,
    ):
        self.project = project
        self.pipeline_engine = PipelineEngine()
        self.health_monitor = health_monitor
        if camera_manager is not None:
            self.camera_manager = camera_manager
        else:
            cam_defs = self.project.camera_definition()
            self.camera_manager = CameraManager.from_definitions(cam_defs)


        self._register_handlers()

    def _register_handlers(self):
        if hasattr(self.project, "get_step_handlers"):
            handlers = self.project.get_step_handlers()
            for step_type, handler_func in handlers.items():
                self.pipeline_engine.register(step_type, handler_func)

    def start(self, width: int = 1920, height: int = 1080) -> bool:
        cam_ok = True
        if self.camera_manager:
            cam_ok = self.camera_manager.connect_all(width, height)

        if self.health_monitor:
            self.health_monitor.start()

        return cam_ok

    def stop(self):
        if self.health_monitor:
            self.health_monitor.stop()

        if self.camera_manager:
            self.camera_manager.disconnect_all()

    def run_cycle(self, pipeline_id: str, cycle_id: Optional[str] = None) -> InspectionContext:
        current_cycle_id = cycle_id or uuid.uuid4().hex
        context = InspectionContext(
            project_id=self.project.project_id,
            pipeline_id=pipeline_id,
            device_id=getattr(self.project, "device_id", "edge_device"),
            cycle_id=current_cycle_id,
        )

        definition = self.project.pipeline_definition(pipeline_id)
        if not definition:
            logger.warning(f"Pipeline definition '{pipeline_id}' not found in project")
            return context

        if self.camera_manager:
            for cam_id in self.camera_manager.ids():
                frame = self.camera_manager.get_frame(cam_id, copy=True)
                if frame is not None:
                    context.frames[cam_id] = frame

        context = self.pipeline_engine.run(definition, context)
        return context