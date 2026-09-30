from __future__ import annotations
from typing import Dict, Any, Callable, List
from platform_core.project import ProjectAdapter
from platform_core.context import InspectionContext

class BackGrindingProject(ProjectAdapter):
    project_id = "backgrinding"

    def __init__(self, detector=None, analysis=None, config=None):
        self.detector = detector
        self.analysis = analysis
        self.config = config
        self.device_id = getattr(config, "device_id", "edge_01") if config else "edge_01"

    def pipeline_definition(self, pipeline_id: str) -> Dict[str, Any]:
        pipelines = getattr(self.config, "pipelines", {}) if self.config else {}
        if pipeline_id in pipelines:
            return pipelines[pipeline_id]
        
        return {
            "mode": "shared",
            "steps": [
                {"id": "capture", "type": "capture"},
                {"id": "detect", "type": "detect"},
                {"id": "validate", "type": "validate"},
                {"id": "decision", "type": "decision"}
            ]
        }

    def get_step_handlers(self) -> Dict[str, Callable]:
        return {
            "capture": self.handle_capture,
            "detect": self.handle_detection,
            "validate": self.handle_validate,
            "decision": self.handle_decision,
            "stream_only": self.handle_stream_only,
        }

    def handle_capture(self, context: InspectionContext, step: Dict[str, Any]) -> bool:
        target_camera = context.camera_id or (list(context.frames.keys())[0] if context.frames else None)
        return bool(target_camera and context.frames.get(target_camera) is not None)

    def handle_detection(self, context: InspectionContext, step: Dict[str, Any]):
        target_camera = context.camera_id or (list(context.frames.keys())[0] if context.frames else None)
        frame = context.frames.get(target_camera)
        
        if frame is None:
            return False
            
        res = self.detector.detect_image(
            frame,
            json_safe=True,
            cycle_id=context.cycle_id,
            camera_id=target_camera,
            pipeline_id=context.pipeline_id
        )
        detection = res.get("result", []) if res else []
        if target_camera:
            context.detections[target_camera] = detection
        return detection

    def handle_validate(self, context: InspectionContext, step: Dict[str, Any]) -> bool:
        target_camera = context.camera_id or (list(context.detections.keys())[0] if context.detections else None)
        detection = context.detections.get(target_camera, [])
        
        try:
            valid, data = self.analysis.logicAnalysis(detection)
        except Exception:
            valid, data = False, []

        if target_camera:
            context.results[target_camera] = bool(valid)
            context.metadata.setdefault("validation", {})[target_camera] = data
        return bool(valid)

    def handle_decision(self, context: InspectionContext, step: Dict[str, Any]) -> bool:
        target_camera = context.camera_id or (list(context.results.keys())[0] if context.results else None)
        val = bool(context.results.get(target_camera, False))
        context.results["final"] = val
        return val

    def handle_stream_only(self, context: InspectionContext, step: Dict[str, Any]) -> bool:
        if context.camera_id:
            context.results[context.camera_id] = True
        return True

    def io_definition(self) -> Dict[str, Any]:
        if not self.config:
            return {}
        
        return {
            "inputs": {
                "door": getattr(self.config, "inputChannel", 0)
            },
            "outputs": {
                "alarm": getattr(self.config, "outputAlarm", 0),
                "contor": getattr(self.config, "outputContor", 0),
                "state_machine": getattr(self.config, "outputStateMachine", 0)
            }
        }

    def camera_definition(self) -> List[Dict[str, Any]]:
        if not self.config:
            return []
        return [
            c for c in getattr(self.config, "cameras", [])
            if c.get("enabled", True)
        ]