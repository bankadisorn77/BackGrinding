import json
import os
from pathlib import Path


class BGConfig:
    project_id = "backgrinding"

    def __init__(self, path=None):
        root = Path(__file__).resolve().parents[2]
        self.path = Path(path or os.environ.get(
            "BG_CONFIG_PATH", str(root / "config" / "config.json")
        ))
        self.device_id = "BG-Dev-01"
        self.ip = "127.0.0.1"
        self.mac = "XX:XX:XX:XX:XX:XX"
        self.inputChannel = 0
        self.outputAlarm = 0
        self.outputContor = 1
        self.outputStateMachine = 0
        self.cameraAOI = {"width": 1920, "height": 1080}
        self.MQTTServer = "localhost"
        self.server_url = "localhost"
        self.api_port = 8080
        self.model_path = str(root / "Yolov12best_bg_v2_openvino_model")
        self.save_image_path = str(root / "saved_images_output")
        self.api_key = "api_key"
        self.stop_flag_path = str(root.parent / "stop_worker.flag")
        self.cameras = [
            {"id": "cam_1", "driver": "ueye", "hardware_index": 0, "enabled": True, "pipeline": "backgrinding"},
            {"id": "cam_2", "driver": "ueye", "hardware_index": 1, "enabled": True, "pipeline": "stream_only"},
        ]
        self.pipelines = {
            "backgrinding": {
                "mode": "shared",
                "steps": [
                    {"id": "capture", "type": "capture"},
                    {"id": "detect", "type": "detect"},
                    {"id": "validate", "type": "validate"},
                    {"id": "decision", "type": "decision"},
                ],
            },
            "stream_only": {
                "mode": "shared",
                "steps": [{"id": "stream", "type": "stream_only"}],
            },
        }
        self.load()

    @property
    def width(self):
        return int(self.cameraAOI.get("width", 1920))

    @property
    def height(self):
        return int(self.cameraAOI.get("height", 1080))

    @property
    def enabled_cameras(self):
        return [c for c in self.cameras if c.get("enabled", True)]

    @property
    def inspection_cameras(self):
        return [c for c in self.enabled_cameras if c.get("pipeline") == "backgrinding"]

    def load(self):
        if not self.path.exists():
            self.save()
            return
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            for name in (
                "device_id", "ip", "mac", "MQTTServer", "server_url",
                "model_path", "save_image_path", "api_key", "project_id", "stop_flag_path",
            ):
                if name in data:
                    setattr(self, name, data[name])
            for name in (
                "inputChannel", "outputAlarm", "outputContor",
                "outputStateMachine", "api_port",
            ):
                if name in data:
                    setattr(self, name, int(data[name]))
            if not os.path.isabs(self.stop_flag_path):
                self.stop_flag_path = str(root.parent / self.stop_flag_path)
            self.cameraAOI = data.get("cameraAOI", self.cameraAOI)
            self.cameras = data.get("cameras", self.cameras)
            self.pipelines = data.get("pipelines", self.pipelines)
        except (OSError, ValueError, TypeError, KeyError):
            self.save()

    def as_dict(self):
        return {
            "device_id": self.device_id,
            "ip": self.ip,
            "mac": self.mac,
            "inputChannel": self.inputChannel,
            "outputAlarm": self.outputAlarm,
            "outputContor": self.outputContor,
            "outputStateMachine": self.outputStateMachine,
            "cameraAOI": self.cameraAOI,
            "MQTTServer": self.MQTTServer,
            "server_url": self.server_url,
            "api_port": self.api_port,
            "model_path": self.model_path,
            "save_image_path": self.save_image_path,
            "api_key": self.api_key,
            "stop_flag_path": self.stop_flag_path,
            "project_id": self.project_id,
            "cameras": self.cameras,
            "pipelines": self.pipelines,
        }

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self.as_dict(), f, indent=2)
