import logging
import time
import uuid
from typing import List, Optional

from .camera_manager import CameraManager
from .communication import PlatformStatusReporter
from .context import InspectionContext
from .health import HealthMonitor
from .io_manager import AdvantechIOManager, BaseIOManager
from .pipeline import PipelineEngine
from .project import ProjectAdapter
from .storage import ImageStorage

logger = logging.getLogger("PlatformRuntime")


class PlatformRuntime:
    """Shared lifecycle and hardware runtime for all projects."""

    def __init__(self, project: ProjectAdapter, camera_manager: Optional[CameraManager] = None,
                 io_manager: Optional[BaseIOManager] = None, health_monitor: Optional[HealthMonitor] = None,
                 io_device: str = "USB-4761,BID#0"):
        self.project = project
        self.pipeline_engine = PipelineEngine()
        self.reporter = PlatformStatusReporter()
        self.health_monitor = health_monitor or HealthMonitor(on_status_change=self._on_health_change)
        self.camera_manager = camera_manager or CameraManager.from_definitions(project.camera_definition())
        self.io_manager = io_manager or AdvantechIOManager(device=io_device)
        storage = project.storage_definition().get("base_dir") if hasattr(project, "storage_definition") else None
        self.storage = ImageStorage(storage) if storage else None
        self._running = False
        self._register_handlers()
        self._register_health_checks()

    def _register_handlers(self):
        for step_type, handler in self.project.get_step_handlers().items():
            self.pipeline_engine.register(step_type, handler)

    def _register_health_checks(self):
        self.health_monitor.register_check("camera", self.camera_manager.all_connected)
        self.health_monitor.register_check("gpio", self.io_manager.is_connected)

    def _on_health_change(self, status):
        self.update_status(health=status)

    def start(self, width=1920, height=1080):
        camera_ok = self.camera_manager.connect_all(width, height)
        io_ok = self.io_manager.connect()
        self.health_monitor.start()
        self._running = True
        self.update_status(program_status="RUNNING")
        return bool(camera_ok and io_ok)

    def run(self):
        if not self._running:
            raise RuntimeError("PlatformRuntime.start() must be called before run().")
        return self.project.run(self)

    def stop(self):
        if not self._running:
            return
        self._running = False
        try:
            self.project.shutdown(self)
        except AttributeError:
            pass
        self.update_status(program_status="OFF", relay_status="OFF", alarm_status="OFF")
        self.health_monitor.stop()
        self.camera_manager.disconnect_all()
        self.io_manager.close()
        self.reporter.close()

    def update_status(self, **kwargs):
        status = {
            "project_id": self.project.project_id,
            "camera": "ONLINE" if self.camera_manager.all_connected() else "OFF",
            "gpio": "ONLINE" if self.io_manager.is_connected() else "OFF",
            "program_status": "RUNNING" if self._running else "OFF",
            "relay_status": "OFF",
            "light_status": "OFF",
            "door_status": "CLOSED",
            "alarm_status": "OFF",
        }
        status.update(self.project.status_payload())
        status.update(kwargs)
        self.reporter.report(status)

    def run_cycle(self, pipeline_id: str, cycle_id: Optional[str] = None,
                  cam_active: Optional[List[str]] = None) -> InspectionContext:
        context = InspectionContext(
            project_id=self.project.project_id,
            pipeline_id=pipeline_id,
            device_id=getattr(self.project, "device_id", "edge_device"),
            cycle_id=cycle_id or uuid.uuid4().hex,
        )
        definition = self.project.pipeline_definition(pipeline_id)
        if not definition:
            return context

        target_cameras = cam_active if cam_active is not None else self.camera_manager.ids()
        for camera_id in target_cameras:
            if camera_id not in self.camera_manager.ids():
                continue
            frame = self.camera_manager.snap(camera_id)
            if frame is not None:
                context.frames[camera_id] = frame
                if self.storage:
                    try:
                        self.storage.save_cycle_image(frame, context.cycle_id, camera_id)
                    except Exception as exc:
                        logger.warning("Failed to save cycle image: %s", exc)
            else:
                logger.warning("Failed to snap frame from %s", camera_id)

        return self.pipeline_engine.run(definition, context)
