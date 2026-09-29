import cv2 as cv
import numpy as np
from pyueye import ueye
import sys
import threading
import time
import ctypes

class UeyeCamera:

  def __init__(self, camera_id: int = 0):
    self.camera_id = camera_id
    self.camera_index = camera_id
    self.hCam = ueye.HIDS(0)
    self.sInfo = ueye.SENSORINFO()
    self.cInfo = ueye.CAMINFO()
    self.pcImageMemory = ueye.c_mem_p()
    self.MemID = ueye.int(0)
    self.rectAOI = ueye.IS_RECT()

    self.pitch = ueye.INT(0)
    self.nBitsPerPixel_ctypes = ueye.INT(0)

    self.width = 0
    self.height = 0
    self.target_fps = 15
    self.nBitsPerPixel_py = 0
    self.bytes_per_pixel = 0

    self.m_nColorMode = ueye.INT(0)
    self.hCamConnected = False
    self.x = 0
    self.y = 0

    self.latest_frame = None
    self.frame_lock = threading.Lock()
    self.is_streaming = False
    self.stream_thread = None
    self.is_reconnecting = False

  def is_connected(self) -> bool:
    """Check this camera handle, not merely whether any uEye camera exists."""
    if not self.hCamConnected or self.hCam.value == 0:
      return False
    try:
      ret = ueye.is_GetCameraInfo(self.hCam, self.cInfo)
      if ret != ueye.IS_SUCCESS:
        self.hCamConnected = False
        return False
      return True
    except Exception:
      self.hCamConnected = False
      return False

  def ping(self) -> bool:
    return self.is_connected()

  def _get_target_camera_hids(self):
    try:
      num_cams = ueye.INT(0)
      ret = ueye.is_GetNumberOfCameras(num_cams)
      if ret != ueye.IS_SUCCESS or num_cams.value == 0:
        print(f"[CAM {self.camera_id}] No cameras detected in system.")
        return None

      count = num_cams.value
      buf_size = ctypes.sizeof(ctypes.c_ulong) + count * ctypes.sizeof(ueye.UEYE_CAMERA_INFO)
      buffer = ctypes.create_string_buffer(buf_size)
      ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ulong))[0] = count

      p_list = ctypes.cast(buffer, ctypes.POINTER(ueye.UEYE_CAMERA_LIST))
      ret = ueye.is_GetCameraList(p_list)

      if ret == ueye.IS_SUCCESS:
        cam_list = p_list.contents
        if self.camera_id < cam_list.dwCount:
          actual_id = cam_list.uci[self.camera_id].dwCameraID
          print(f"[CAM {self.camera_id}] Found hardware DevID/CamID: {actual_id}")
          return ueye.HIDS(actual_id)
        else:
          print(f"[CAM {self.camera_id}] Index exceeds available cameras count ({cam_list.dwCount}).")
      else:
        print(f"[CAM {self.camera_id}] is_GetCameraList returned error: {ret}")

    except Exception as e:
      print(f"[CAM {self.camera_id}] Read Camera List error: {e}")
    return ueye.HIDS(self.camera_id)

  def connection(self, target_width, target_height, target_fps=15):
    try:
      self.target_fps = target_fps
      self.disconnect()

      hids = self._get_target_camera_hids()
      if hids is None:
        self.hCamConnected = False
        return False

      self.hCam = hids
      print(f"[CAM {self.camera_id}] Initializing camera ID {self.hCam.value}...")

      nRet = ueye.is_InitCamera(self.hCam, None)
      if nRet != ueye.IS_SUCCESS:
        print(f"[CAM {self.camera_id}] ERROR: is_InitCamera failed with code {nRet}")
        self.hCamConnected = False
        return False

      self.hCamConnected = True
      print(f"[CAM {self.camera_id}] Camera initialized successfully.")

      if ueye.is_GetCameraInfo(self.hCam, self.cInfo) != ueye.IS_SUCCESS:
        self.disconnect()
        return False

      if ueye.is_GetSensorInfo(self.hCam, self.sInfo) != ueye.IS_SUCCESS:
        self.disconnect()
        return False

      ueye.is_ResetToDefault(self.hCam)
      ueye.is_SetDisplayMode(self.hCam, ueye.IS_SET_DM_DIB)

      self._determine_color_mode()
      if ueye.is_SetColorMode(self.hCam, self.m_nColorMode) != ueye.IS_SUCCESS:
        self.disconnect()
        return False

      actual_width, actual_height = self._set_aoi(self.x, self.y, target_width, target_height)
      if actual_width is None or actual_height is None:
        self.disconnect()
        return False
      self.width = actual_width
      self.height = actual_height

      if ueye.is_AllocImageMem(
          self.hCam, self.width, self.height, self.nBitsPerPixel_ctypes, self.pcImageMemory, self.MemID
      ) != ueye.IS_SUCCESS:
        self.disconnect()
        return False

      if ueye.is_SetImageMem(self.hCam, self.pcImageMemory, self.MemID) != ueye.IS_SUCCESS:
        self.disconnect()
        return False

      inquired_w = ueye.INT(0)
      inquired_h = ueye.INT(0)
      inquired_bits = ueye.INT(0)

      if ueye.is_InquireImageMem(
          self.hCam, self.pcImageMemory, self.MemID, inquired_w, inquired_h, inquired_bits, self.pitch
      ) != ueye.IS_SUCCESS:
        self.pitch.value = self.width * self.bytes_per_pixel
        self.nBitsPerPixel_py = self.nBitsPerPixel_ctypes.value
      else:
        self.width = inquired_w.value
        self.height = inquired_h.value
        self.nBitsPerPixel_py = inquired_bits.value
        self.bytes_per_pixel = int(self.nBitsPerPixel_py / 8)

      actual_framerate = ueye.double(0.0)
      ueye.is_SetFrameRate(self.hCam, ueye.double(target_fps), actual_framerate)

      ueye.is_SetExternalTrigger(self.hCam, ueye.IS_SET_TRIGGER_OFF)
      if ueye.is_CaptureVideo(self.hCam, ueye.IS_DONT_WAIT) != ueye.IS_SUCCESS:
        self.disconnect()
        return False

      self.is_streaming = True
      self.stream_thread = threading.Thread(target=self._capture_worker, daemon=True)
      self.stream_thread.start()
      print(f"[CAM {self.camera_id}] Camera started in Continuous Video Mode.")
      return True

    except Exception as ex:
      print(f"[CAM {self.camera_id}] Exception during connection: {ex}")
      self.disconnect()
      return False

  def _capture_worker(self):
    delay = 1.0 / max(1, self.target_fps)

    while self.is_streaming:
      if self.hCamConnected:
        if not self.is_connected():
          self.hCamConnected = False
          with self.frame_lock:
            self.latest_frame = None
        else:
          try:
            array = ueye.get_data(
                self.pcImageMemory, self.width, self.height,
                self.nBitsPerPixel_py, self.pitch.value, copy=False
            )
            if array is not None and array.size > 0:
              if self.bytes_per_pixel == 3:
                frame = np.reshape(array, (self.height, self.width, self.bytes_per_pixel))
              elif self.bytes_per_pixel == 1:
                frame = np.reshape(array, (self.height, self.width))
                frame = cv.cvtColor(frame, cv.COLOR_GRAY2BGR)
              else:
                time.sleep(delay)
                continue

              with self.frame_lock:
                self.latest_frame = frame.copy()
            else:
              self.hCamConnected = False
          except Exception:
            self.hCamConnected = False
      time.sleep(delay)

  def get_latest_frame(self):
    if not self.is_connected():
      return None
    with self.frame_lock:
      return self.latest_frame.copy() if self.latest_frame is not None else None

  def _determine_color_mode(self):
    if int.from_bytes(self.sInfo.nColorMode.value, byteorder=sys.byteorder) == ueye.IS_COLORMODE_CBYCRY:
      self.m_nColorMode.value = ueye.IS_CM_BGR8_PACKED
      self.nBitsPerPixel_ctypes.value = 24
      self.bytes_per_pixel = 3
    else:
      self.m_nColorMode.value = ueye.IS_CM_MONO8
      self.nBitsPerPixel_ctypes.value = 8
      self.bytes_per_pixel = 1

  def _set_aoi(self, x, y, w, h):
    self.rectAOI.s32X = ueye.int(x)
    self.rectAOI.s32Y = ueye.int(y)
    self.rectAOI.s32Width = ueye.int(w)
    self.rectAOI.s32Height = ueye.int(h)

    if ueye.is_AOI(self.hCam, ueye.IS_AOI_IMAGE_SET_AOI, self.rectAOI, ueye.sizeof(self.rectAOI)) != ueye.IS_SUCCESS:
      return None, None
    if ueye.is_AOI(self.hCam, ueye.IS_AOI_IMAGE_GET_AOI, self.rectAOI, ueye.sizeof(self.rectAOI)) != ueye.IS_SUCCESS:
      return None, None
    return self.rectAOI.s32Width.value, self.rectAOI.s32Height.value

  def disconnect(self):
    self.is_streaming = False
    if self.hCamConnected or (hasattr(self, "hCam") and self.hCam.value != 0):
      try:
        ueye.is_StopLiveVideo(self.hCam, ueye.IS_WAIT)
      except Exception:
        pass
      try:
        if self.pcImageMemory and self.MemID.value != 0:
          ueye.is_FreeImageMem(self.hCam, self.pcImageMemory, self.MemID)
      except Exception:
        pass
      self.pcImageMemory = ueye.c_mem_p()
      self.MemID = ueye.int(0)
      try:
        ueye.is_ExitCamera(self.hCam)
      except Exception:
        pass
      self.hCamConnected = False
      self.hCam = ueye.HIDS(0)