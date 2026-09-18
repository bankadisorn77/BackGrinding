from __future__ import annotations

import time
from typing import Any, Dict


class CameraManager:
    """Generic camera lifecycle/health manager.

    Concrete camera drivers live outside the platform core. The manager only
    knows the small interface needed by the runtime: connection, latest frame,
    status and disconnect.
    """

    def __init__(self, cameras: Dict[str, Any]):
        self.cameras = cameras

    def get(self, camera_id: str) -> Any:
        return self.cameras.get(camera_id)

    def ids(self):
        return list(self.cameras.keys())

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

    def disconnect_all(self):
        for camera_id, camera in self.cameras.items():
            try:
                camera.disconnect()
            except Exception as exc:
                print(f"[CameraManager] {camera_id} disconnect error: {exc}")
