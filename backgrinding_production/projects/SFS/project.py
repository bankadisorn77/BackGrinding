from typing import Dict, Any, Callable, List
from platform_core.project import ProjectAdapter
from platform_core.context import InspectionContext
from .detector import SfsDetector

class SfsPokaYokeProject(ProjectAdapter):
    project_id = "sfs_pokayoke"

    def __init__(self, config=None):
        # self.config = config
        self.config = {"cameras": [
                                    {
                                        "id": "cam_1",
                                        "driver": "ueye",
                                        "hardware_index": 1,
                                    },
                                    {
                                        "id": "cam_2",
                                        "driver": "ueye",
                                        "hardware_index": 2,
                                    },
                                    {
                                        "id": "cam_3",
                                        "driver": "ueye",
                                        "hardware_index": 3,
                                    },                                                                        
                                ]}
        self.device_id = getattr(config, "device_id", "sfs_station_01") if config else "sfs_station_01"
        self.detector = SfsDetector()

    def camera_definition(self) -> List[Dict[str, Any]]:
        if isinstance(self.config, dict):
            cameras = self.config.get("cameras", [])
        else:
            cameras = getattr(self.config, "cameras", [])

        return [
            c for c in cameras
            if c.get("enabled", True)
        ]

    def pipeline_definition(self, pipeline_id: str) -> Dict[str, Any]:
        return {
            "mode": "shared",
            "steps": [
                {"id": "capture", "type": "capture"},
                {"id": "measure", "type": "measure"},
                {"id": "decision", "type": "decision"}
            ]
        }

    def get_step_handlers(self) -> Dict[str, Callable]:
        return {
            "capture": self.handle_capture,
            "measure": self.handle_measure,
            "decision": self.handle_decision,
        }

    def handle_capture(self, context: InspectionContext, step: Dict[str, Any]) -> bool:
        target_camera = context.camera_id or (list(context.frames.keys())[0] if context.frames else None)
        return bool(target_camera and context.frames.get(target_camera) is not None)
    

    def handle_measure(self, context: InspectionContext, step: Dict[str, Any]):
        target_camera = context.camera_id or (list(context.frames.keys())[0] if context.frames else None)
        frame = context.frames.get(target_camera)
        _, info = self.detector.detect_frame(frame)
        context.metadata["measure_info"] = info
        return info

    def handle_decision(self, context: InspectionContext, step: Dict[str, Any]) -> bool:
        info = context.metadata.get("measure_info", {})
        is_pass, reason = self.detector.evaluate(info)

        context.results["cam_top"] = is_pass
        context.results["final"] = is_pass
        context.metadata["reason"] = reason
        return is_pass