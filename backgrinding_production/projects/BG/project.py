import logging
import time
from pathlib import Path
from typing import Dict, Any, Callable, List

from platform_core.project import ProjectAdapter
from platform_core.context import InspectionContext

from .config import BGConfig
from .pipelines import BG_PIPELINES
from .checklist import Checklist
from .communication import BGServerClient
from .detector import BGDetector
from .io import BGIO
from .logic import BGLogic

logger = logging.getLogger("BackGrindingProject")


class BackGrindingProject(ProjectAdapter):
    project_id = "backgrinding"

    def __init__(self, config=None, detector=None, logic=None):
        self.config = config or BGConfig()
        self.device_id = self.config.device_id
        checklist_path = Path(__file__).resolve().parents[2] / "config" / "datalist.csv"
        self.checklist = Checklist(csv_path=checklist_path)
        self.logic = logic or BGLogic(self.checklist)
        self.server = BGServerClient(self.config)
        self.detector = detector or BGDetector(
            model_dir=self.config.model_path,
            save_dir=self.config.save_image_path,
            conf=0.7,
            device="CPU",
            api=self.server,
        )
        self.io = None
        self._last_status = {
            "door_status": "CLOSED",
            "relay_status": "OFF",
            "alarm_status": "OFF",
        }

    def pipeline_definition(self, pipeline_id: str) -> Dict[str, Any]:
        return self.config.pipelines.get(pipeline_id, BG_PIPELINES.get(pipeline_id, {}))

    def get_step_handlers(self) -> Dict[str, Callable]:
        return {
            "capture": self.handle_capture,
            "detect": self.handle_detection,
            "validate": self.handle_validate,
            "decision": self.handle_decision,
            "stream_only": self.handle_stream_only,
        }

    def camera_definition(self) -> List[Dict[str, Any]]:
        return list(self.config.enabled_cameras)

    def io_definition(self) -> Dict[str, Any]:
        return {
            "inputs": {"door": self.config.inputChannel},
            "outputs": {
                "alarm": self.config.outputAlarm,
                "relay": self.config.outputContor,
                "state_machine": self.config.outputStateMachine,
            },
        }

    def storage_definition(self):
        return {"base_dir": self.config.save_image_path}

    def status_payload(self):
        return dict(self._last_status)

    def _inspection_camera_ids(self):
        return [c["id"] for c in self.config.inspection_cameras]

    def handle_capture(self, context: InspectionContext, step: Dict[str, Any]) -> bool:
        return bool(context.frames)

    def handle_detection(self, context: InspectionContext, step: Dict[str, Any]):
        results = {}
        for camera_id in self._inspection_camera_ids():
            frame = context.frames.get(camera_id)
            if frame is None:
                results[camera_id] = []
                continue
            camera_context = context.for_camera(camera_id)
            detections = self.detector.detect_image(frame, context=camera_context)
            context.detections[camera_id] = detections
            results[camera_id] = detections
        return results

    def handle_validate(self, context: InspectionContext, step: Dict[str, Any]):
        results = {}
        validation = context.metadata.setdefault("validation", {})
        for camera_id in self._inspection_camera_ids():
            detections = context.detections.get(camera_id, [])
            valid, data = self.logic.evaluate(detections)
            context.results[camera_id] = bool(valid)
            validation[camera_id] = data
            results[camera_id] = bool(valid)
        return results

    def handle_decision(self, context: InspectionContext, step: Dict[str, Any]) -> bool:
        inspection_ids = self._inspection_camera_ids()
        passed = bool(inspection_ids) and all(
            bool(context.results.get(camera_id, False)) for camera_id in inspection_ids
        )
        context.results["final"] = passed
        return passed

    def handle_stream_only(self, context: InspectionContext, step: Dict[str, Any]) -> bool:
        if context.camera_id:
            context.results[context.camera_id] = True
        return True

    def run(self, runtime):
        self.io = BGIO(runtime.io_manager, self.config)
        self.io.reset_outputs()
        self.server.register()

        # Legacy BG behavior: wait for door-open, then door-close before an inspection.
        last_door = self.io.read_door()
        while True:
            door = self.io.read_door()
            self._last_status["door_status"] = "CLOSED" if door else "OPEN"
            runtime.update_status(**self._last_status)

            if last_door == 0 and door == 1:
                self._run_inspection_cycle(runtime)
            last_door = door
            time.sleep(0.05)

    def _run_inspection_cycle(self, runtime):
        self._last_status["door_status"] = "CLOSED"
        runtime.update_status(**self._last_status)
        context = runtime.run_cycle(
            pipeline_id="backgrinding",
            cam_active=[c["id"] for c in self.config.enabled_cameras],
        )
        passed = bool(context.results.get("final", False))

        if passed:
            self.io.set_alarm(False)
            self.io.set_relay(True)
            self._last_status["relay_status"] = "ON"
            self._last_status["alarm_status"] = "OFF"
            runtime.update_status(**self._last_status)
            time.sleep(0.3)
            self.io.set_relay(False)
            self._last_status["relay_status"] = "OFF"
        else:
            self.io.set_relay(False)
            self.io.set_alarm(True)
            self._last_status["relay_status"] = "OFF"
            self._last_status["alarm_status"] = "ON"
            runtime.update_status(**self._last_status)
            self._wait_alarm_clear(runtime)

        runtime.update_status(**self._last_status)

    def _wait_alarm_clear(self, runtime):
        started = time.time()
        while time.time() - started < 15.0:
            if self.io.read_door() == 0:
                break
            time.sleep(0.1)
        self.io.set_alarm(False)
        self._last_status["alarm_status"] = "OFF"

    def shutdown(self, runtime):
        if self.io:
            self.io.reset_outputs()
        self._last_status.update({"relay_status": "OFF", "alarm_status": "OFF"})
