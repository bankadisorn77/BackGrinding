import json
import os
import signal
import sys
import threading
import time
import cv2 as cv
import numpy as np

from ProcessClass.BGconfig import BackgrindConfig
from ProcessClass.GPIO import GPIO
from ProcessClass.MJPEGStreamHandler import MultiCameraServer
from ProcessClass.detector import Detector
from ProcessClass.logicAnalysis import Analysis
from ProcessClass.pathProcess import PathProcess, StatusLevel, getdatetime
from ProcessClass.pipe import sender
from ProcessClass.serverAPI import API_CALL
from ProcessClass.ueyeCam import UeyeCamera

BASE_DIR = r"D:\BG"
STOP_FLAG_FILE = os.path.join(BASE_DIR, "stop_worker.flag")


class StateMachine:

  def __init__(self):
    # 1. MJPEG STREAM SERVER
    self.stream_server = MultiCameraServer(port=8095)
    self.stream_server.start()

    # 2. PATH & CONFIG SETUP
    self.path = PathProcess()
    self.pathsaveImg = self.path.savePath
    self.path.createdir()
    self.config = BackgrindConfig()
    self.reloadconfig()

    self.analysis = Analysis()
    self.gpio = GPIO()
    self.api = API_CALL(config=self.config)
    self.detector = Detector(
        model_dir=self.config.model_path,
        save_dir=self.config.save_image_path,
        conf=0.7,
        api=self.api,
    )
    self.sender = sender()


    self.camera = UeyeCamera(camera_id=0)
    self.cameras = {
        1: self.camera,
        2: UeyeCamera(camera_id=1),  
    }

    all_cam_ok = True    
    for cam_idx, cam_obj in self.cameras.items():
      connected = cam_obj.connection(self.width, self.height)
      print(f"[INIT] Camera {cam_idx} (HIDS {cam_obj.hCam.value}) connection status: {connected}")
      if not connected:
        all_cam_ok = False

    # 4. PROGRAM STATE
    self.state = "s1"
    self.io = 0
    self.current_io = 0
    self.count = 0
    self.CallbackClearstate = None
    self.resultYolo = None
    self.procReboot = False
    self.is_disconnected = False
    self.current_frame = None
    self.frame_snapshot = None

    # 5. GPIO OUTPUT SETUP
    self.output_write(self.config.outputAlarm, on=False)
    self.output_write(self.config.outputContor, on=False)
    self.output_write(self.config.outputStateMachine, on=False)

    self.cam_status = all_cam_ok
    self.gpio_status = False
    self.program_status = "OFF"
    self.door_status = "OFF"
    self.light_status = "OFF"
    self.relay_status = "OFF"
    self.alarm_status = "OFF"

    # 6. THREADING
    self.frame_lock = threading.Lock()
    self.stop_event = threading.Event()
    self.hw_heartbeat_thread = None

    self.hw_monitor_active = True

    for stream_idx, cam_obj in self.cameras.items():
      threading.Thread(
          target=self.camera_loop, args=(cam_obj, stream_idx), daemon=True
      ).start()

  def camera_loop(self, camera_obj, stream_index: int):
    encode_params = [cv.IMWRITE_JPEG_QUALITY, 75]
    while self.hw_monitor_active:
      try:
        frame = camera_obj.get_latest_frame()
        if frame is not None:
          h, w = frame.shape[:2]
          scale = 800 / w if w > 800 else 1.0
          preview = cv.resize(frame, (800, int(h * scale))) if scale < 1.0 else frame
          ret, buffer = cv.imencode(".jpg", preview, encode_params)
          if ret:
            self.stream_server.update_frame(stream_index, buffer.tobytes())
      except Exception:
        pass
      time.sleep(0.04)

  def reloadconfig(self):
    try:
      self.config.loadConfig()
      self.device_id = self.config.device_id
      self.inputChannel = self.config.inputChannel
      self.outputAlarm = self.config.outputAlarm
      self.outputContor = self.config.outputContor
      self.outputStateMachine = self.config.outputStateMachine
      self.cameraAOI = self.config.cameraAOI
      self.width = self.cameraAOI["width"]
      self.height = self.cameraAOI["height"]
      self.MQTTServer = self.config.MQTTServer
      self.api_key = self.config.api_key
      return True
    except Exception as e:
      print(f"[ERROR] in reloadconfig: {e}")
      return False

  def check_stop_requested(self):
    if self.procReboot:
      return True
    if os.path.exists(STOP_FLAG_FILE):
      try:
        os.remove(STOP_FLAG_FILE)
      except Exception:
        pass
      self.procReboot = True
      return True
    return False

  def run(self):
    self.program_status = "RUNNING"
    self.procReboot = False
    self.is_disconnected = False
    self.count = 0
    reConnect = 0

    if os.path.exists(STOP_FLAG_FILE):
      try:
        os.remove(STOP_FLAG_FILE)
      except Exception:
        pass

    def check_all_cams():
      for cam in self.cameras.values():
        if not cam.is_connected():
          if not cam.connection(self.width, self.height):
            return False
      return True

    all_connected = check_all_cams()

    while not all_connected:
      if self.check_stop_requested():
        break
      if reConnect <= 10:
        print(f"Attempting cameras reconnect: {reConnect+1}...")
        time.sleep(1.5)
        all_connected = check_all_cams()
        if all_connected:
          reConnect = 0
        else:
          reConnect += 1
      else:
        print("Failed to connect all cameras after multiple attempts.")
        break

    if all_connected:
      self.read_io()
      self.hw_monitor_active = True
      self.hw_heartbeat_thread = threading.Thread(
          target=self._hw_heartbeat_worker, daemon=True
      )
      self.hw_heartbeat_thread.start()

      while not self.check_stop_requested():
        if self.state == "s1":
          self.handle_state_s1()
        elif self.state == "s2":
          self.handle_state_s2()
        elif self.state == "s3":
          self.handle_state_s3()
        elif self.state == "s4":
          self.handle_state_s4()
        elif self.state == "s5":
          self.handle_state_s5()
        time.sleep(0.05)

    self.DisconnectAll()

  def handle_state_s1(self):
    self.read_io()
    if self.current_io == 1:
      self.door_status = "CLOSED"
      self.update_hw_status()
      while self.current_io == 1 and not self.check_stop_requested():
        self.read_io()
        time.sleep(0.1)

    if not self.check_stop_requested():
      self.state = "s2"

  def handle_state_s2(self):
    self.output_write(self.config.outputContor, on=False)
    self.relay_status = "OFF"
    self.door_status = "OPEN"
    self.update_hw_status()
    while self.current_io == 0 and not self.check_stop_requested():
      self.read_io()
      time.sleep(0.05)

    if self.check_stop_requested():
      return

    new_frame = self.camera.get_latest_frame()
    self.door_status = "CLOSED"
    self.update_hw_status()
    if new_frame is not None:
      with self.frame_lock:
        self.current_frame = new_frame
        self.frame_snapshot = new_frame.copy()

      self.SaveImg(self.frame_snapshot)
      self.state = "s3"
    else:
      self.camera.hCamConnected = False
      self.output_write(self.config.outputStateMachine, on=False)
      self.light_status = "OFF"
      self.update_hw_status()
      self.state = "s1"

  def handle_state_s3(self):
    self.resultYolo = None

    with self.frame_lock:
      frame_to_send = None if self.frame_snapshot is None else self.frame_snapshot.copy()

    if frame_to_send is None:
      self.state = "s4"
      return

    try:
      response = self.detector.detect_image(frame_to_send, json_safe=True)
      if response and "result" in response:
        self.resultYolo = response["result"]
      else:
        self.state = "s4"
        return

      res, data = self.LogicAnalysis(self.resultYolo)
      if res:
        self.output_write(self.config.outputContor, on=True)
        self.relay_status = "ON"
        self.state = "s1"
      else:
        self.state = "s4"

    except Exception:
      self.state = "s4"

  def handle_state_s4(self):
    try:
      start_time = time.time()
      while self.count == 0 and not self.check_stop_requested():
        self.warning_alarm()
        self.count += 1

      while not self.check_stop_requested():
        self.read_io()
        if self.current_io == 0:
          self.output_write(self.config.outputAlarm, on=False)
          self.alarm_status = "OFF"
          self.update_hw_status()
          self.reset_cycle_data()
          break

        if time.time() - start_time >= 15:
          self.output_write(self.config.outputAlarm, on=False)
          self.alarm_status = "OFF"
          self.update_hw_status()
          self.reset_cycle_data()
          break

        self.checkClearState()
        time.sleep(0.1)
    except Exception:
      self.reset_cycle_data()

  def handle_state_s5(self):
    self.clear_state()
    self.CallbackClearstate = None
    self.reset_cycle_data()

  def reset_cycle_data(self):
    self.count = 0
    self.state = "s1"
    self.current_frame = None

  def clear_state(self):
    self.output_write(self.config.outputAlarm, on=False)
    self.output_write(self.config.outputContor, on=False)
    self.alarm_status = "OFF"
    self.relay_status = "OFF"

  def checkClearState(self):
    self.state = "s5"

  def SaveImg(self, frame):
    filename = os.path.join(self.pathsaveImg, f"{getdatetime()}.jpg")
    cv.imwrite(filename, frame)

  def LogicAnalysis(self, res):
    try:
      if not isinstance(res, (list, tuple)) or len(res) != 3:
        return False, []
      return self.analysis.logicAnalysis(res)
    except Exception:
      return False, []

  def warning_alarm(self):
    self.output_write(self.config.outputAlarm, on=True)
    self.output_write(self.config.outputContor, on=False)
    self.alarm_status = "ON"
    self.relay_status = "OFF"

  def read_io(self):
    if hasattr(self, "gpio") and self.gpio.is_connected:
      io = self.gpio.readInput(self.inputChannel)
      if io is not None:
        self.io = io
        self.current_io = io
        return io
    self.io = 0
    self.current_io = 0
    return 0

  def output_write(self, ch: int, on: bool = False):
    if hasattr(self, "gpio") and self.gpio.is_connected:
      return self.gpio.outputWrite(ch, on=on)
    return False

  def DisconnectAll(self):
    if self.is_disconnected:
      return
    self.is_disconnected = True
    self.hw_monitor_active = False

    self.stop_event.set()
    if self.hw_heartbeat_thread and self.hw_heartbeat_thread.is_alive():
      self.hw_heartbeat_thread.join(timeout=2.0)

    self.program_status = "OFF"
    self.door_status = "OFF"
    self.light_status = "OFF"
    self.relay_status = "OFF"
    self.alarm_status = "OFF"
    self.update_hw_status(cam="OFF", gpio="OFF")

    try:
      self.output_write(self.config.outputAlarm, on=False)
      self.output_write(self.config.outputContor, on=False)
      self.output_write(self.config.outputStateMachine, on=False)
    except Exception as e:
      print(f"[Warning] Failed resetting GPIO outputs: {e}")

    try:
      self.gpio.closeIO()
    except Exception as e:
      print(f"[Warning] Failed closing GPIO: {e}")

    # ปิดการเชื่อมต่อของกล้องทุกตัว
    for cam in self.cameras.values():
      try:
        cam.disconnect()
      except Exception as e:
        print(f"[Warning] Failed disconnecting Camera: {e}")

  def update_hw_status(self, cam=None, gpio=None, force=False):
    cam_details = {}
    for idx, c in self.cameras.items():
      cam_key = f"camera_{idx}"
      if cam is not None:
        cam_details[cam_key] = cam
      else:
        cam_details[cam_key] = "ONLINE" if c.is_connected() else "ERROR"

    all_cam_ok = all(status == "ONLINE" for status in cam_details.values()) if cam is None else (cam == "ONLINE")
    gpio_ok = getattr(self.gpio, "is_connected", False)

    status_dict = {
        "camera": cam if cam is not None else ("ONLINE" if all_cam_ok else "ERROR"),
        "gpio": gpio if gpio is not None else ("ONLINE" if gpio_ok else "ERROR"),
        "program_status": self.program_status,
        "relay_status": self.relay_status,
        "light_status": self.light_status,
        "door_status": self.door_status,
        "alarm_status": self.alarm_status,
        "last_update": time.time(),
    }

    status_dict.update(cam_details)

    payload = {"status": status_dict}
    self.cam_status = all_cam_ok
    self.gpio_status = gpio_ok
    self.sender.send_event(payload)

  def _hw_heartbeat_worker(self):
    while not self.stop_event.is_set():
      if self.hw_monitor_active:
        try:
          gpio_ok = self.gpio.ping() if hasattr(self, "gpio") and self.gpio else False
          all_cam_ok = all(c.is_connected() for c in self.cameras.values())

          if all_cam_ok and gpio_ok:
            self.output_write(self.config.outputStateMachine, on=True)
            self.light_status = "ON"
          else:
            self.output_write(self.config.outputStateMachine, on=False)
            self.output_write(self.config.outputContor, on=False)
            self.light_status = "OFF"
            self.relay_status = "OFF"
          self.update_hw_status()

          if self.stop_event.wait(timeout=5.0):
            break
        except Exception as e:
          print(f"[Worker Exception] {e}")

if __name__ == "__main__":
  sm = StateMachine()

  def shutdown(signum, frame):
    sm.procReboot = True
    sm.DisconnectAll()
    sys.exit(0)

  signal.signal(signal.SIGINT, shutdown)
  signal.signal(signal.SIGTERM, shutdown)
  try:
    sm.run()
  finally:
    sm.DisconnectAll()