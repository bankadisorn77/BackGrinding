from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from .module.camera.ueyeCam import UeyeCamera

logger = logging.getLogger("CameraManager")


class CameraManager:
    def __init__(self, cameras: Dict[str, Any]):
        self.cameras = cameras
        self._active_alignment_cam: Optional[str] = None

    def get(self, camera_id: str) -> Optional[Any]:
        return self.cameras.get(camera_id)

    def ids(self) -> List[str]:
        return list(self.cameras.keys())

    @classmethod
    def from_definitions(cls, camera_definitions: list) -> "CameraManager":
        print("Create new camera list :", camera_definitions)
        cameras = {}
        for cam_info in camera_definitions:
            cam_id = str(cam_info.get("id", "cam_1"))
            hw_index = int(cam_info.get("hardware_index", 0))
            cameras[cam_id] = UeyeCamera(camera_id=hw_index)
        return cls(cameras)

    def connect_all(self, width: int, height: int, fps: int = 15) -> bool:
        ok = True
        for camera_id, camera in self.cameras.items():
            try:
                connected = camera.connection(width, height, fps)
            except TypeError:
                connected = camera.connection(width, height)
            except Exception as exc:
                print(f"[CameraManager] {camera_id} connect error: {exc}")
                connected = False

            if not connected:
                ok = False
        return ok

    def snap(self, camera_id: str, timeout_ms: int = 1000):
        camera = self.cameras.get(camera_id)
        if camera is None:
            return None
        if hasattr(camera, "snap_frame"):
            return camera.snap_frame(timeout_ms=timeout_ms)
        return self.get_frame(camera_id, copy=True)

    def start_alignment_live(self, camera_id: str) -> bool:
        target_camera = self.cameras.get(camera_id)
        if target_camera is None:
            logger.warning(f"[CameraManager] Camera {camera_id} not found for alignment.")
            return False

        for cid, cam in self.cameras.items():
            if cid != camera_id and getattr(cam, "is_streaming", False):
                if hasattr(cam, "stop_live"):
                    cam.stop_live()

        if hasattr(target_camera, "start_live"):
            success = target_camera.start_live()
            if success:
                self._active_alignment_cam = camera_id
            return success
        return False

    def stop_alignment_live(self, camera_id: Optional[str] = None):
        if camera_id:
            cam = self.cameras.get(camera_id)
            if cam and hasattr(cam, "stop_live"):
                cam.stop_live()
            if self._active_alignment_cam == camera_id:
                self._active_alignment_cam = None
        else:
            for cam in self.cameras.values():
                if hasattr(cam, "stop_live"):
                    cam.stop_live()
            self._active_alignment_cam = None

    def get_frame(self, camera_id: str, copy: bool = True):
        camera = self.cameras.get(camera_id)
        if camera is None:
            return None
        try:
            frame = camera.get_latest_frame()
            if frame is None:
                return None
            return frame.copy() if copy and hasattr(frame, "copy") else frame
        except Exception as exc:
            print(f"[CameraManager] {camera_id} frame error: {exc}")
            return None

    def status(self) -> Dict[str, str]:
        result = {}
        for camera_id, camera in self.cameras.items():
            try:
                result[camera_id] = "ONLINE" if camera.is_connected() else "ERROR"
            except Exception:
                result[camera_id] = "ERROR"
        return result

    def all_connected(self) -> bool:
        return all(value == "ONLINE" for value in self.status().values())

    def reconnect_disconnected(self, width: int, height: int, fps: int = 15) -> bool:
        all_ok = True
        for camera_id, camera in self.cameras.items():
            try:
                if not camera.is_connected():
                    print(f"[CameraManager] reconnecting {camera_id}")
                    if not camera.connection(width, height, fps):
                        all_ok = False
            except TypeError:
                try:
                    if not camera.is_connected():
                        if not camera.connection(width, height):
                            all_ok = False
                except Exception:
                    all_ok = False
            except Exception as exc:
                print(f"[CameraManager] {camera_id} reconnect error: {exc}")
                all_ok = False
        return all_ok

    def disconnect_all(self):
        self.stop_alignment_live()
        for camera_id, camera in self.cameras.items():
            try:
                camera.disconnect()
            except Exception as exc:
                print(f"[CameraManager] {camera_id} disconnect error: {exc}")