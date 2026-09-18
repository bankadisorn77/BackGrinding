import os
import cv2 as cv
import time
import json
import numpy as np
import signal
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from ProcessClass.ueyeCam import UeyeCamera
from ProcessClass.GPIO import GPIO
from ProcessClass.pathProcess import PathProcess, getdatetime, StatusLevel
from ProcessClass.BGconfig import BackgrindConfig
from ProcessClass.logicAnalysis import Analysis
from ProcessClass.detector import Detector
from ProcessClass.serverAPI import API_CALL
from ProcessClass.pipe import sender
from ProcessClass.MJPEGStreamHandler import MultiCameraServer

BASE_DIR = r"D:\BG"
STOP_FLAG_FILE = os.path.join(BASE_DIR, "stop_worker.flag")
LATEST_JPEG_BYTES = None
STREAM_LOCK = threading.Lock()

# class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
#     daemon_threads = True

# class MJPEGStreamHandler(BaseHTTPRequestHandler):
#     def do_GET(self):
#         global LATEST_JPEG_BYTES
#         if self.path.startswith('/video_feed_1'):
#             self.send_response(200)
#             self.send_header('Age', '0')
#             self.send_header('Cache-Control', 'no-cache, private')
#             self.send_header('Pragma', 'no-cache')
#             self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
#             self.end_headers()
#             try:
#                 while True:
#                     with STREAM_LOCK:
#                         frame_bytes = LATEST_JPEG_BYTES

#                     if frame_bytes is not None:
#                         self.wfile.write(b'--frame\r\n')
#                         self.send_header('Content-Type', 'image/jpeg')
#                         self.send_header('Content-Length', str(len(frame_bytes)))
#                         self.end_headers()
#                         self.wfile.write(frame_bytes)
#                         self.wfile.write(b'\r\n')
#                     time.sleep(0.06)
#             except Exception:
#                 pass
#         else:
#             self.send_response(404)
#             self.end_headers()

#     def log_message(self, format, *args):
#         return

# def start_mjpeg_server(port=8095):
#     try:
#         server = ThreadedHTTPServer(('0.0.0.0', port), MJPEGStreamHandler)
#         server.serve_forever()
#     except Exception as e:
#         print(f"[STREAM ERROR] {e}")

class StateMachine:
    def __init__(self):
        # CLASS
        self.stream_server = MultiCameraServer(port=8095)
        self.stream_server.start()
        self.path = PathProcess()
        self.pathsaveImg = self.path.savePath
        self.config = BackgrindConfig()
        self.analysis = Analysis()
        self.camera = UeyeCamera() 
        self.gpio = GPIO()
        self.api=API_CALL(config=self.config)
        self.detector = Detector(model_dir=self.config.model_path, save_dir=self.config.save_image_path, conf=0.7,api=self.api)
        self.sender = sender()
        # PROGRAM STATE
        self.state = 's1'
        self.io = 0
        self.current_io = 0
        self.count = 0  
        self.CallbackClearstate = None
        self.resultYolo = None
        self.procReboot = False
        self.is_disconnected = False 
        self.current_frame = None 
        self.frame_snapshot = None 
        # PATH 
        self.path.createdir()
        self.reloadconfig()
        # GPIO
        self.output_write(self.config.outputAlarm, on=False)
        self.output_write(self.config.outputContor, on=False)
        self.output_write(self.config.outputStateMachine, on=False)

        self.cam_status = False
        self.gpio_status = False
        self.program_status = 'OFF'
        self.door_status = 'OFF'
        self.light_status = 'OFF'
        self.relay_status = 'OFF'
        self.alarm_status = 'OFF'

        # Threading
        self.frame_lock = threading.Lock()      
        self.stop_event = threading.Event()
        self.hw_heartbeat_thread = None
        self.stream_thread = None
        self.STATUS_FILE = r"config\hw_status.json"
        if not os.path.exists(os.path.dirname(self.STATUS_FILE)):
            self.STATUS_FILE = r"config\hw_status.json"

        self.hw_monitor_active = False
        # threading.Thread(target=start_mjpeg_server, daemon=True).start()
        threading.Thread(target=self.camera_loop, args=(0, 1), daemon=True).start()  # CAM 1
        threading.Thread(target=self.camera_loop, args=(1, 2), daemon=True).start()



    def camera_loop(self,cam_id: int, stream_index: int):
        while self.hw_monitor_active:
            try:
                frame = self.camera.get_latest_frame()
                if frame is not None:
                    h, w = frame.shape[:2]
                    scale = 800 / w if w > 800 else 1.0
                    preview = cv.resize(frame, (800, int(h * scale))) if scale < 1.0 else frame
                    ret, buffer = cv.imencode('.jpg', preview, [cv.IMWRITE_JPEG_QUALITY, 75])
                    if ret:
                        self.stream_server.update_frame(stream_index, buffer.tobytes())
            except Exception:
                pass
            time.sleep(0.05)



    # def _stream_updater_worker(self):
    #     global LATEST_JPEG_BYTES
    #     while self.hw_monitor_active:
    #         try:
    #             frame = self.camera.get_latest_frame()
    #             if frame is not None:
    #                 h, w = frame.shape[:2]
    #                 scale = 800 / w if w > 800 else 1.0
    #                 preview = cv.resize(frame, (800, int(h * scale))) if scale < 1.0 else frame
    #                 ret, buffer = cv.imencode('.jpg', preview, [cv.IMWRITE_JPEG_QUALITY, 75])
    #                 if ret:
    #                     with STREAM_LOCK:
    #                         LATEST_JPEG_BYTES = buffer.tobytes()
    #         except Exception:
    #             pass
    #         time.sleep(0.05)

    def reloadconfig(self):
        try:
            self.config.loadConfig()
            self.device_id = self.config.device_id
            self.inputChannel = self.config.inputChannel
            self.outputAlarm = self.config.outputAlarm
            self.outputContor = self.config.outputContor
            self.outputStateMachine = self.config.outputStateMachine
            self.cameraAOI = self.config.cameraAOI
            self.width = self.cameraAOI['width']
            self.height = self.cameraAOI['height']
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
        self.program_status = 'RUNNING'
        self.procReboot = False
        self.is_disconnected = False
        self.count = 0
        reConnect = 0

        if os.path.exists(STOP_FLAG_FILE):
            try: os.remove(STOP_FLAG_FILE)
            except Exception: pass
            
        camconnect = self.camera.connection(self.width, self.height)
        print(f'Camera connection status: {camconnect}')
        
        while not camconnect:
            if self.check_stop_requested():
                break
            if reConnect <= 10:
                print(f'Attempting camera reconnect: {reConnect+1}...')
                time.sleep(1.5)
                camconnect = self.camera.connection(self.width, self.height)
                if camconnect:
                    reConnect = 0
                else:
                    reConnect += 1
            else:
                print("Failed to connect Camera after multiple attempts.")
                break

        if camconnect:    
            self.read_io()
            self.hw_monitor_active = True
            self.hw_heartbeat_thread = threading.Thread(target=self._hw_heartbeat_worker, daemon=True)
            self.hw_heartbeat_thread.start()

            self.stream_thread = threading.Thread(target=self._stream_updater_worker, daemon=True)
            self.stream_thread.start()
            
            while not self.check_stop_requested():
                if self.state == 's1': self.handle_state_s1()
                elif self.state == 's2': self.handle_state_s2()
                elif self.state == 's3': self.handle_state_s3()
                elif self.state == 's4': self.handle_state_s4()
                elif self.state == 's5': self.handle_state_s5()
                time.sleep(0.05)
                
        self.DisconnectAll()

    def handle_state_s1(self):
        self.read_io()
        if self.current_io == 1:
            self.door_status = 'CLOSED'
            self.update_hw_status()
            while self.current_io == 1 and not self.check_stop_requested():
                self.read_io()
                time.sleep(0.1)
        
        if not self.check_stop_requested():
            self.state = 's2'

    def handle_state_s2(self):
        self.output_write(self.config.outputContor, on=False)
        self.relay_status = 'OFF'
        self.door_status = 'OPEN'
        self.update_hw_status()
        while self.current_io == 0 and not self.check_stop_requested():
            self.read_io()
            time.sleep(0.05)
        
        if self.check_stop_requested():
            return

        new_frame = self.camera.get_latest_frame()
        self.door_status = 'CLOSED'
        self.update_hw_status()
        if new_frame is not None:
            with self.frame_lock:
                self.current_frame = new_frame
                self.frame_snapshot = new_frame.copy()

            self.SaveImg(self.frame_snapshot)
            self.state = 's3'
        else:
            self.camera.hCamConnected = False
            self.output_write(self.config.outputStateMachine, on=False)
            self.light_status ='OFF'
            self.update_hw_status()
            # self.update_hw_status(cam_ok=False)
            self.state = 's1'

    def handle_state_s3(self):
        self.resultYolo = None

        with self.frame_lock:
            frame_to_send = None if self.frame_snapshot is None else self.frame_snapshot.copy()

        if frame_to_send is None:
            self.state = 's4'
            return

        try:
            response = self.detector.detect_image(frame_to_send, json_safe=True)
            if response and "result" in response:
                self.resultYolo = response["result"]
            else:
                self.state = 's4'
                return

            res, data = self.LogicAnalysis(self.resultYolo)
            if res:
                self.output_write(self.config.outputContor, on=True)
                self.relay_status = 'ON'
                self.state = 's1'
            else:
                self.state = 's4'

        except Exception as e:
            self.state = 's4'

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
                    self.alarm_status = 'OFF'
                    self.update_hw_status()
                    self.reset_cycle_data()
                    break 

                if time.time() - start_time >= 15:
                    self.output_write(self.config.outputAlarm, on=False)
                    self.alarm_status ='OFF'
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
        self.state = 's1'
        self.current_frame = None

    def clear_state(self):
        self.output_write(self.config.outputAlarm, on=False)
        self.output_write(self.config.outputContor, on=False)
        self.alarm_status ='OFF'
        self.relay_status ='OFF'

    def checkClearState(self):
        self.state = 's5'

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
        self.alarm_status ='ON'
        self.relay_status ='OFF'

    def read_io(self):
        if hasattr(self, 'gpio') and self.gpio.is_connected:
            io = self.gpio.readInput(self.inputChannel)
            if io is not None:
                self.io = io
                self.current_io = io
                return io
        self.io = 0
        self.current_io = 0
        return 0

    def output_write(self, ch: int, on: bool = False):
        if hasattr(self, 'gpio') and self.gpio.is_connected:
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
        self.program_status = 'OFF'
        self.door_status = 'OFF'
        self.light_status = 'OFF'
        self.relay_status = 'OFF'
        self.alarm_status = 'OFF'
        self.update_hw_status(cam = 'OFF', gpio = 'OFF')

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

        try:
            self.camera.disconnect()
        except Exception as e:
            print(f"[Warning] Failed disconnecting Camera: {e}")

    def update_hw_status(self, cam=None, gpio=None, force=False):
        cam_ok = getattr(self.camera, 'hCamConnected', False)
        gpio_ok = getattr(self.gpio, 'is_connected', False)

        payload = {'status':{
                "camera": cam if cam is not None else ("ONLINE" if cam_ok else "ERROR"),
                "gpio": gpio if gpio is not None else ("ONLINE" if gpio_ok else "ERROR"),
                "program_status": self.program_status,
                "relay_status": self.relay_status,
                "light_status": self.light_status,
                "door_status": self.door_status,
                "alarm_status": self.alarm_status,
                "last_update": time.time()
            }}
        self.cam_status = cam_ok
        self.gpio_status = gpio_ok
        self.sender.send_event(payload)


    def _hw_heartbeat_worker(self):
        while not self.stop_event.is_set():
            if self.hw_monitor_active:
                try:
                    gpio_ok = self.gpio.ping() if hasattr(self, 'gpio') and self.gpio else False
                    cam_ok = self.camera.is_connected() if hasattr(self, 'camera') and self.camera else False

                    if cam_ok and gpio_ok:
                        self.output_write(self.config.outputStateMachine, on=True)
                        self.light_status = 'ON'
                    else:
                        self.output_write(self.config.outputStateMachine, on=False)
                        self.output_write(self.config.outputContor, on=False)
                        self.light_status = 'OFF'
                        self.relay_status ='OFF'
                    self.update_hw_status()

                    if self.stop_event.wait(timeout=5.0):
                        break
                except Exception as e:
                    print(f"[Worker Exception] {e}")

if __name__ == '__main__':
    sm = StateMachine()
    def shutdown(signum, frame):
        sm.procReboot = True
        sm.DisconnectAll()
        sys.exit(0)
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    try: sm.run()
    finally: sm.DisconnectAll()