from __future__ import annotations

import base64
import json
import logging

logger = logging.getLogger("BGCommunication")


class BGServerClient:
    def __init__(self, config):
        self.config = config
        self.base_url = "http://{}:{}".format(config.server_url, config.api_port)

    def register(self):
        try:
            import httpx
            payload = {
                "name": self.config.device_id,
                "ip_address": self.config.ip,
                "mac_address": self.config.mac,
                "io_channel": {
                    "input_channel": self.config.inputChannel,
                    "output_alarm_channel": self.config.outputAlarm,
                    "output_relay_channel": self.config.outputContor,
                    "output_light_channel": self.config.outputStateMachine,
                },
                "model_path": self.config.model_path,
                "save_image_path": self.config.save_image_path,
                "mqtt_broker": self.config.MQTTServer,
                "project_id": self.config.project_id,
                "camera_config": self.config.cameras,
                "project_config": {"project_id": self.config.project_id, "pipelines": self.config.pipelines},
                "io_config": {
                    "input": {"trigger": self.config.inputChannel},
                    "output": {"alarm": self.config.outputAlarm, "relay": self.config.outputContor, "state_machine": self.config.outputStateMachine},
                },
            }
            response = httpx.post(self.base_url + "/register_device", json=payload, timeout=10.0)
            if response.status_code == 200:
                return True
        except Exception as exc:
            logger.warning("BG server registration failed: %s", exc)
        return False

    def log_detection(self, image, detections, context):
        try:
            import cv2
            import httpx
            ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                return False
            payload = {
                "image": base64.b64encode(encoded).decode("utf-8"),
                "detected_objects": json.dumps(detections),
                "cycle_id": context.cycle_id,
                "camera_id": context.camera_id,
                "pipeline_id": context.pipeline_id,
            }
            response = httpx.post(
                self.base_url + "/image_log",
                headers={"X-API-Key": self.config.api_key},
                json=payload,
                timeout=10.0,
            )
            return response.status_code == 200
        except Exception as exc:
            logger.warning("BG detection log failed: %s", exc)
            return False
