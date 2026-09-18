import asyncio
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import psutil

from ProcessClass.BGconfig import BackgrindConfig
from ProcessClass.MQTTControl import MQTT
from ProcessClass.pipe import resiver
from ProcessClass.serverAPI import API_CALL


class Agent:

  def __init__(self):
    self.BASE_DIR = r"D:\BG"
    self.PYTHON_W = os.path.join(self.BASE_DIR, "env", "Scripts", "pythonw.exe")
    if not os.path.exists(self.PYTHON_W):
      self.PYTHON_W = sys.executable

    self.WORKER_DIR = os.path.join(self.BASE_DIR, "backgrinding_production")
    self.CONFIG_FILE = os.path.join(self.WORKER_DIR, "config", "config.json")
    self.HW_STATUS_FILE = os.path.join(
        self.WORKER_DIR, "config", "hw_status.json"
    )
    self.STOP_WORKER_FLAG = os.path.join(self.BASE_DIR, "stop_worker.flag")
    self.LOG_DIR = os.path.join(self.BASE_DIR, "logs")
    self.WORKER_LOG = os.path.join(self.LOG_DIR, "worker_stdout.log")

    try:
      myappid = "app.bg.aisystem.v1"
      ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
      pass

    # self.DETACHED_FLAGS = 0x00000008 | 0x08000000
    self.DETACHED_FLAGS = 0x08000000

    self.config = BackgrindConfig()
    self.api = API_CALL(config=self.config)

    self.pipe = resiver(on_data_received=self.handle_incoming_pipe_data)

    self.payload = None
    self.device_id = None
    self.MQTTServer = None
    self.api_key = None
    self.MQ = None

    self.last_log_pos = 0

    self.reloadconfig(MQ=True)
    if self.MQ:
      self.MQ.sendHeardbeat(isRunning="ACTIVE")

    self.startup(register=True)

    threading.Thread(target=self._tail_log_worker, daemon=True).start()

  def startup(self, register=False):
    reload_needed = False
    while register:
      try:
        res = asyncio.run(self.api.register())
        if res:
          reload_needed = True
        print("[API Server Connected]")
        break
      except Exception:
        print("Server Connection Error. Retrying in 10s...")
        time.sleep(10)

    if reload_needed:
      self.reloadconfig()

    is_running = self.get_pid_by_script("StateMachine.py") is not None
    self.payload = {
        "camera": "OFF",
        "gpio": "OFF",
        "program_status": "RUNNING" if is_running else "OFF",
        "relay_status": "OFF",
        "light_status": "OFF",
        "door_status": "OFF",
        "alarm_status": "OFF",
        "last_update": time.time(),
    }
    if self.MQ:
      self.MQ.statusMsg(msg=self.payload, api_key=self.api_key)
    print("[AGENT] START UP COMPLETE")

  def handle_incoming_pipe_data(self, data):
    self.payload = data
    if isinstance(data, dict):
      status_data = data.get("status", data)
      if isinstance(status_data, dict) and self.MQ:
        self.MQ.statusMsg(msg=status_data, api_key=self.api_key)
    print(f"[MAIN CALLBACK] Got real-time event from RAM: {data}")

  def _tail_log_worker(self):
    while True:
      try:
        if self.MQ and self.device_id:
          log_topic = f"BackgrindingMQTT/{self.device_id}/logs"

          if os.path.exists(self.WORKER_LOG):
            curr_size = os.path.getsize(self.WORKER_LOG)

            if curr_size > self.last_log_pos:
              with open(
                  self.WORKER_LOG, "r", encoding="utf-8", errors="ignore"
              ) as f:
                f.seek(self.last_log_pos)
                lines = f.readlines()
                self.last_log_pos = f.tell()

                for line in lines:
                  clean_line = line.strip()
                  if clean_line:
                    mqtt_client = getattr(
                        self.MQ, "client", getattr(self.MQ, "mqtt_client", None)
                    )
                    if mqtt_client:
                      mqtt_client.publish(log_topic, clean_line)

            elif curr_size < self.last_log_pos:
              self.last_log_pos = 0

      except Exception as e:
        pass

      time.sleep(1.0)  

  def reloadconfig(self, MQ=False):
    try:
      self.config.loadConfig()
      self.device_id = self.config.device_id
      self.MQTTServer = self.config.MQTTServer
      self.api_key = self.config.api_key

      if MQ:
        self.MQ = MQTT(
            broker_url=self.MQTTServer,
            device_id=self.device_id,
            control=self.toggle_worker,
            agentStartup=self.startup,
            restart=self.restart_worker,
            deletedevic=self.delete_device,
            api_key=self.api_key
        )
        self._setup_mqtt()
        self.MQ.setMQTTServer(self.device_id, self.MQTTServer)

      print("[AGENT] Reload config successfully")
      return True
    except Exception as e:
      print(f"[ERROR] in reloadconfig: {e}")
      return False

  def _setup_mqtt(self):
    self.MQ.callbackProgramcontrol = self.toggle_worker
    self.MQ.callbackRestart = self.restart_worker
    self.MQ.callbackDeletedevice = self.delete_device
    self.MQ.connectMqtt()

  def get_pid_by_script(self, script_name: str):
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
      try:
        cmdline = proc.info.get("cmdline")
        if cmdline:
          cmd_str = " ".join(cmdline).lower()
          if script_name.lower() in cmd_str:
            return proc.info["pid"]
      except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass
    return None

  def stop_worker_process(self, pid: int):
    if not pid:
      return
    try:
      with open(self.STOP_WORKER_FLAG, "w", encoding="utf-8") as f:
        f.write("STOP")
    except Exception:
      pass

    try:
      proc = psutil.Process(pid)
      proc.wait(timeout=2)
      return
    except psutil.TimeoutExpired:
      try:
        proc.kill()
      except Exception:
        pass
    except Exception:
      subprocess.run(
          ["taskkill", "/F", "/T", "/PID", str(pid)],
          creationflags=subprocess.CREATE_NO_WINDOW,
      )

  def toggle_worker(self, data):
    print("[AGENT] toggle_worker")
    pid = self.get_pid_by_script("StateMachine.py")
    if pid:
      self.stop_worker_process(pid)
    else:
      if os.path.exists(self.STOP_WORKER_FLAG):
        try:
          os.remove(self.STOP_WORKER_FLAG)
        except OSError:
          pass
      cmd = (
          f'"{self.PYTHON_W}" -u StateMachine.py >> "{self.WORKER_LOG}" 2>&1'
      )
      subprocess.Popen(
          cmd,
          cwd=self.WORKER_DIR,
          shell=True,
          creationflags=self.DETACHED_FLAGS,
      )

  def restart_worker(self, data):
    if isinstance(data, str):
      try:
        data = json.loads(data)
      except Exception:
        data = {}

    mapping = {
        "name": "device_id",
        "input_channel": "inputChannel",
        "output_alarm_channel": "outputAlarm",
        "output_relay_channel": "outputContor",
        "output_light_channel": "outputStateMachine",
        "model_path": "model_path",
        "mqtt_broker": "MQTTServer",
    }
    config_to_update = {}
    for server_k, edge_k in mapping.items():
      if server_k in data and data[server_k] is not None:
        config_to_update[edge_k] = data[server_k]

    if "mqtt_broker" in data and data["mqtt_broker"] is not None:
      config_to_update["server_url"] = data["mqtt_broker"]

    self.config.setnewConfig(config_to_update)
    print(f"[AGENT] New Config Updated: {config_to_update}")

    pid = self.get_pid_by_script("StateMachine.py")
    if pid:
      self.stop_worker_process(pid)

    if os.path.exists(self.STOP_WORKER_FLAG):
      try:
        os.remove(self.STOP_WORKER_FLAG)
      except OSError:
        pass

    cmd = f'"{self.PYTHON_W}" -u StateMachine.py >> "{self.WORKER_LOG}" 2>&1'
    subprocess.Popen(
        cmd, cwd=self.WORKER_DIR, shell=True, creationflags=self.DETACHED_FLAGS
    )
    print("[AGENT] Worker process restarted.")

  def delete_device(self, data):
    print("[AGENT] Received delete command")
    pid = self.get_pid_by_script("StateMachine.py")
    if pid:
      self.stop_worker_process(pid)
    config = {
        "device_id": "",
        "ip": "",
        "mac": "",
        "model_path": "",
        "MQTTServer": "",
        "api_key": "",
        "server_url": "",
    }
    self.config.setnewConfig(config)
    self.cleanup()

  def cleanup(self):
    print("[AGENT] Cleaning up resources...")
    try:
      self.pipe.close()  
    except Exception:
      pass

    payload = {
        "camera": "OFF",
        "gpio": "OFF",
        "program_status": "OFF",
        "relay_status": "OFF",
        "light_status": "OFF",
        "door_status": "OFF",
        "alarm_status": "OFF",
        "last_update": time.time(),
    }
    if self.MQ:
      self.MQ.statusMsg(payload, self.api_key)
      self.MQ.sendHeardbeat(isRunning="INACTIVE")
      time.sleep(0.5)
      self.MQ.disconnectMQTT()

    print("[AGENT] Process terminating...")
    os._exit(0)


if __name__ == "__main__":
  a = Agent()
  try:
    asyncio.run(a.pipe.run_pipe_resiver())
  except KeyboardInterrupt:
    a.cleanup()
  except Exception as e:
    print(f"[AGENT FATAL ERROR]: {e}")
    a.cleanup()

    # [MAIN CALLBACK] Got real-time event from RAM: {'status': {'camera': 'ONLINE', 'gpio': 'ONLINE', 'program_status': 'RUNNING', 'relay_status': 'OFF', 'light_status': 'ON', 'door_status': 'CLOSED', 'alarm_status': 'OFF', 'last_update': 1789718230.305998, 'camera_1': 'ONLINE', 'camera_2': 'ONLINE'}}