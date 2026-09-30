# platform_core/runtime.py
from __future__ import annotations
import uuid
import time
import logging
from typing import List, Optional, Dict, Any

from .context import InspectionContext
from .camera_manager import CameraManager
from .pipeline import PipelineEngine
from .project import ProjectAdapter
from .health import HealthMonitor
from .io_manager import BaseIOManager, AdvantechIOManager, DummyIOManager
from .communication import PlatformStatusReporter

logger = logging.getLogger("PlatformRuntime")


class PlatformRuntime:
    def __init__(
        self,
        project: ProjectAdapter,
        camera_manager: Optional[CameraManager] = None,
        health_monitor: Optional[HealthMonitor] = None,
        io_manager: Optional[BaseIOManager] = None,
        io_device: str = "USB-4761,BID#0",
    ):
        self.project = project
        self.pipeline_engine = PipelineEngine()
        self.health_monitor = health_monitor
        self.reporter = PlatformStatusReporter()

        # camera
        if camera_manager is not None:
            self.camera_manager = camera_manager
        else:
            cam_defs = self.project.camera_definition()
            self.camera_manager = CameraManager.from_definitions(cam_defs)

        # IO Advantech
        if io_manager is not None:
            self.io_manager = io_manager
        else:
            try:
                self.io_manager = AdvantechIOManager(device=io_device)
            except Exception:
                self.io_manager = DummyIOManager()

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
            time.sleep(0.5)

        if hasattr(self.io_manager, "connect"):
            self.io_manager.connect()

        if self.health_monitor:
            self.health_monitor.start()

        self.update_status(program_status="RUNNING")
        return cam_ok

    def stop(self):
        self.update_status(program_status="OFF")
        if self.health_monitor:
            self.health_monitor.stop()
        if self.camera_manager:
            self.camera_manager.disconnect_all()
        if self.io_manager:
            self.io_manager.close()
        if hasattr(self, "reporter") and self.reporter:
            self.reporter.close()

    def update_status(self, **kwargs):
        status = {
            "camera": "ONLINE" if (self.camera_manager and self.camera_manager.all_connected()) else "OFF",
            "gpio": "ONLINE" if (self.io_manager and self.io_manager.is_connected()) else "OFF",
            "program_status": "RUNNING",
            "relay_status": "OFF",
            "light_status": "OFF",
            "door_status": "CLOSED",
            "alarm_status": "OFF",
        }
        status.update(kwargs)
        self.reporter.report(status)

    def run_cycle(
        self, 
        pipeline_id: str, 
        cycle_id: Optional[str] = None, 
        cam_active: Optional[List[str]] = None
    ) -> InspectionContext:
        current_cycle_id = cycle_id or uuid.uuid4().hex
        context = InspectionContext(
            project_id=self.project.project_id,
            pipeline_id=pipeline_id,
            device_id=getattr(self.project, "device_id", "edge_device"),
            cycle_id=current_cycle_id,
        )

        definition = self.project.pipeline_definition(pipeline_id)
        if not definition:
            return context

        if self.camera_manager:
            if cam_active is not None:
                target_cams = [cid for cid in cam_active if cid in self.camera_manager.ids()]
            else:
                target_cams = self.camera_manager.ids()

            for cam_id in target_cams:
                frame = self.camera_manager.snap(cam_id)
                if frame is not None:
                    context.frames[cam_id] = frame
                else:
                    logger.warning(f"[Runtime] Failed to snap frame from {cam_id}")

        context = self.pipeline_engine.run(definition, context)
        return context