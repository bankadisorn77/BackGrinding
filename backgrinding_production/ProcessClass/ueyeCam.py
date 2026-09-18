import cv2 as cv
import numpy as np
from pyueye import ueye
import sys
import threading
import time

class UeyeCamera:
    def __init__(self):
        self.hCam = ueye.HIDS(0)
        self.sInfo = ueye.SENSORINFO()
        self.cInfo = ueye.CAMINFO()
        self.pcImageMemory = ueye.c_mem_p()
        self.MemID = ueye.int()
        self.rectAOI = ueye.IS_RECT()
        
        self.pitch = ueye.INT() 
        self.nBitsPerPixel_ctypes = ueye.INT(0) 

        self.width = 0
        self.height = 0
        self.target_fps = 15
        self.nBitsPerPixel_py = 0 
        self.bytes_per_pixel = 0 

        self.m_nColorMode = ueye.INT() 
        self.hCamConnected = False
        self.x = 0 
        self.y = 0 
        self.nRet = ueye.IS_SUCCESS 

        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.is_streaming = False
        self.stream_thread = None
        self.is_reconnecting = False

    def _log_error(self, message, return_code):
        print(f"ERROR: {message} failed with code {return_code}")

    def _log_warning(self, message, return_code):
        print(f"WARNING: {message} failed with code {return_code}")

    def is_connected(self) -> bool:
        """ตรวจสอบว่ากล้องยังเชื่อมต่อและมีอยู่ในระบบ Windows หรือไม่"""
        if not self.hCamConnected or self.hCam.value == 0:
            return False
        
        try:
            num_cam = ueye.INT(0)
            ret = ueye.is_GetNumberOfCameras(num_cam)
            if ret == ueye.IS_SUCCESS and num_cam.value > 0:
                return True
            else:
                self.hCamConnected = False
                return False
        except Exception:
            self.hCamConnected = False
            return False

    def ping(self) -> bool:
        return self.is_connected()

    def reconnect(self) -> bool:
        """สั่ง Reconnect กล้อง พร้อมจัดการ Handle เดิมให้สะอาด"""
        if self.is_reconnecting:
            return False

        self.is_reconnecting = True
        print("\n[CAM] Running internal auto-reconnect...")
        try:
            self.disconnect()
            time.sleep(0.5)

            target_w = self.width if self.width > 0 else 2592
            target_h = self.height if self.height > 0 else 1944
            
            success = self.connection(target_w, target_h, self.target_fps)
            if success:
                print("[CAM] Reconnected and Stream recovered successfully!")
                self.is_reconnecting = False
                return True
        except Exception as e:
            print(f"[CAM] Reconnect error: {e}")

        self.is_reconnecting = False
        return False

    def connection(self, target_width, target_height, target_fps=15):
        try:
            self.target_fps = target_fps
            self.disconnect()
            self.hCam = ueye.HIDS(0)
            
            print(f"Initializing camera ID {self.hCam.value}...")
            self.nRet = ueye.is_InitCamera(self.hCam, None)
            if self.nRet != ueye.IS_SUCCESS:
                self._log_error("is_InitCamera", self.nRet)
                self.hCamConnected = False
                return False
                
            self.hCamConnected = True
            print("Camera initialized successfully.")

            self.nRet = ueye.is_GetCameraInfo(self.hCam, self.cInfo)
            if self.nRet != ueye.IS_SUCCESS:
                self._log_error("is_GetCameraInfo", self.nRet)
                self.disconnect()
                return False
            
            self.nRet = ueye.is_GetSensorInfo(self.hCam, self.sInfo)
            if self.nRet != ueye.IS_SUCCESS:
                self._log_error("is_GetSensorInfo", self.nRet)
                self.disconnect()
                return False

            self.nRet = ueye.is_ResetToDefault(self.hCam)
            self.nRet = ueye.is_SetDisplayMode(self.hCam, ueye.IS_SET_DM_DIB)

            self._determine_color_mode() 
            self.nRet = ueye.is_SetColorMode(self.hCam, self.m_nColorMode)
            if self.nRet != ueye.IS_SUCCESS:
                self._log_error("is_SetColorMode", self.nRet)
                self.disconnect()
                return False

            actual_width, actual_height = self._set_aoi(self.x, self.y, target_width, target_height)
            if actual_width is None or actual_height is None:
                self.disconnect()
                return False
            self.width = actual_width
            self.height = actual_height

            self.nRet = ueye.is_AllocImageMem(self.hCam, self.width, self.height, self.nBitsPerPixel_ctypes, self.pcImageMemory, self.MemID)
            if self.nRet != ueye.IS_SUCCESS:
                self._log_error("is_AllocImageMem", self.nRet)
                self.disconnect()
                return False

            self.nRet = ueye.is_SetImageMem(self.hCam, self.pcImageMemory, self.MemID)
            if self.nRet != ueye.IS_SUCCESS:
                self._log_error("is_SetImageMem", self.nRet)
                self.disconnect()
                return False

            inquired_width_ctypes = ueye.INT(0)
            inquired_height_ctypes = ueye.INT(0)
            inquired_nBitsPerPixel_ctypes = ueye.INT(0) 

            self.nRet = ueye.is_InquireImageMem(self.hCam, self.pcImageMemory, self.MemID, 
                                                inquired_width_ctypes, 
                                                inquired_height_ctypes, 
                                                inquired_nBitsPerPixel_ctypes, 
                                                self.pitch)
            
            if self.nRet != ueye.IS_SUCCESS:
                self.pitch.value = self.width * self.bytes_per_pixel 
                self.nBitsPerPixel_py = self.nBitsPerPixel_ctypes.value 
            else:
                self.width = inquired_width_ctypes.value
                self.height = inquired_height_ctypes.value
                self.nBitsPerPixel_py = inquired_nBitsPerPixel_ctypes.value
                self.bytes_per_pixel = int(self.nBitsPerPixel_py / 8)

            actual_framerate = ueye.double(0.0)
            ueye.is_SetFrameRate(self.hCam, ueye.double(target_fps), actual_framerate)

            # Continuous Video Free Run
            self.nRet = ueye.is_SetExternalTrigger(self.hCam, ueye.IS_SET_TRIGGER_OFF)
            self.nRet = ueye.is_CaptureVideo(self.hCam, ueye.IS_DONT_WAIT)
            if self.nRet != ueye.IS_SUCCESS:
                self._log_error("is_CaptureVideo", self.nRet)
                self.disconnect()
                return False

            self.is_streaming = True
            self.stream_thread = threading.Thread(target=self._capture_worker, daemon=True)
            self.stream_thread.start()
            print("Camera started in Continuous Video Mode.")
            return True

        except Exception as ex:
            print(f"Error during camera connection: {ex}")
            self.disconnect()
            return False

    def _capture_worker(self):
        delay = 1.0 / max(1, self.target_fps)

        while self.is_streaming:
            if self.hCamConnected:
                if not self.is_connected():
                    print("[CAM] Camera disconnected! Entering recovery state...")
                    self.hCamConnected = False
                    with self.frame_lock:
                        self.latest_frame = None
                else:
                    try:
                        array = ueye.get_data(self.pcImageMemory, self.width, self.height, self.nBitsPerPixel_py, self.pitch.value, copy=False)
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

            else:
                try:
                    num_cams = ueye.INT(0)
                    ret = ueye.is_GetNumberOfCameras(num_cams)
                    if ret == ueye.IS_SUCCESS and num_cams.value > 0:
                        if self.reconnect():
                            break
                except Exception:
                    pass

                time.sleep(1.0)
                continue

            time.sleep(delay)

    def get_latest_frame(self):
        if not self.is_connected():
            return None
        with self.frame_lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
        return None

    def capture_one_frame(self):
        return self.get_latest_frame()

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

        self.nRet = ueye.is_AOI(self.hCam, ueye.IS_AOI_IMAGE_SET_AOI, self.rectAOI, ueye.sizeof(self.rectAOI))
        if self.nRet != ueye.IS_SUCCESS:
            return None, None
        
        self.nRet = ueye.is_AOI(self.hCam, ueye.IS_AOI_IMAGE_GET_AOI, self.rectAOI, ueye.sizeof(self.rectAOI))
        if self.nRet != ueye.IS_SUCCESS:
            return None, None
        return self.rectAOI.s32Width.value, self.rectAOI.s32Height.value

    def disconnect(self):
        self.is_streaming = False
        if self.hCamConnected or (hasattr(self, 'hCam') and self.hCam.value != 0):
            try: ueye.is_StopLiveVideo(self.hCam, ueye.IS_WAIT)
            except Exception: pass
            try:
                if self.pcImageMemory and self.MemID.value != 0:
                    ueye.is_FreeImageMem(self.hCam, self.pcImageMemory, self.MemID)
            except Exception: pass
            self.pcImageMemory = ueye.c_mem_p() 
            self.MemID = ueye.int(0) 
            try: ueye.is_ExitCamera(self.hCam)
            except Exception: pass
            self.hCamConnected = False
            self.hCam = ueye.HIDS(0)