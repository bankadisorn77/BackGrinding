import datetime
import json
import paho.mqtt.client as mqtt
from ProcessClass.getip import GetIPAddress
from ProcessClass.pathProcess import StatusLevel
from ProcessClass.repeatedTimer import RepeatedTimer


class MQTT:

  def __init__(
      self,
      broker_url="127.0.0.1",
      device_id="BG-01",
      api_key=None,
      control=None,
      agentStartup=None,
      restart=None,
      deletedevic=None,
  ):
    self.MQTTserver = broker_url
    self.machineID = device_id
    self.api_key = api_key
    self.MQTTConnected = False
    self.agentStartup = agentStartup
    self._has_started = False  

    
    try:
      self.mqtt_client = mqtt.Client(
        client_id=self.machineID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
      )
    except AttributeError:
      self.mqtt_client = mqtt.Client()

    self.mqtt_client.on_connect = self.onConnectedMqtt
    self.mqtt_client.on_disconnect = self.onDisconnectedMqtt
    self.mqtt_client.on_message = self.onMessageMqtt

    # ตั้งค่า Auto-reconnect delay
    self.mqtt_client.reconnect_delay_set(min_delay=2, max_delay=30)

    # Callbacks
    self.callbackProgramcontrol = control
    self.callbackRestart = restart
    self.callbackDeletedevice = deletedevic

    self.currentMachineIP = GetIPAddress().get_local_ip()
    self.timer = RepeatedTimer(30, self.sendHeardbeat)
    self.useRobot = False


  def topic(self):
    prefix = "BackgrindingMQTT"
    pub_status = f"{prefix}/{self.machineID}/status"
    pub_heartbeat = f"{prefix}/{self.machineID}/heartbeat"

    sub_programcontrol = f"{prefix}/{self.machineID}/program/control"
    sub_programconfig = f"{prefix}/{self.machineID}/program/config"
    sub_deletedevice = f"{prefix}/{self.machineID}/delete"

    return [pub_status, pub_heartbeat], [
        sub_programcontrol,
        sub_programconfig,
        sub_deletedevice,
    ]

  def setMQTTServer(self, machineID, MQTTserver):
    if (
        (MQTTserver != self.MQTTserver)
        or (machineID != self.machineID)
        or (not self.MQTTConnected)
    ):
      self.disconnectMQTT()
      self.MQTTserver = MQTTserver
      self.machineID = machineID
      self.currentMachineIP = GetIPAddress().get_local_ip()
      print(
          f"[MQTT] New Target Server: {self.MQTTserver} | Device ID:"
          f" {self.machineID}"
      )
      self.connectMqtt()

  def connectMqtt(self):
    try:
      lwt_topic1 = f'BackgrindingMQTT/{self.machineID}/status'
      lwt_topic2 = f'BackgrindingMQTT/{self.machineID}/heartbeat'
      lwt_dict1 = {
          'api_key': self.api_key,
          'program_status': 'OFF',
          'camera_status': 'OFF',
          'gpio_status': 'OFF',
          'relay_status': 'OFF',
          'light_status': 'OFF',
          'door_status': 'OFF',
          'alarm_status': 'OFF',
      }
      lwt_payload1 = json.dumps(lwt_dict1)
      
      lwt_dict2 =  {
            "IP": GetIPAddress().get_local_ip(),
            "name": self.machineID,
            "Running Status": 'INACTIVE',
            "last_update": datetime.datetime.now().strftime("%H:%M:%S"),
        }
      lwt_payload2 = json.dumps(lwt_dict2)

      self.mqtt_client.will_set(
          topic=lwt_topic1, payload=lwt_payload1, qos=1, retain=False
      )
      self.mqtt_client.will_set(
          topic=lwt_topic2, payload=lwt_payload2, qos=1, retain=False
      )
      port = 1883
      self.mqtt_client.connect_async(self.MQTTserver, port, keepalive=15)
      self.mqtt_client.loop_start()

      if not self.timer.is_running:
        self.timer.start()
    except Exception as e:
      print(f"[MQTT] Connection setup error: {e}")
      self.MQTTConnected = False

  def disconnectMQTT(self):
    try:
      self.MQTTConnected = False
      if self.timer.is_running:
        self.timer.stop()
      self.mqtt_client.loop_stop()
      self.mqtt_client.disconnect()
      print("[MQTT] Disconnected cleanly.")
    except Exception:
      pass

  # ==================== Logging & Callbacks ====================
  def onProgramcontrol(self, data):
    if self.callbackProgramcontrol is not None:
      self.callbackProgramcontrol(data)

  def onProgramconfig(self, data):
    if self.callbackRestart is not None:
      self.callbackRestart(data)

  def onDeletedevice(self, data):
    print("[MQTT DELETE]")
    if self.callbackDeletedevice is not None:
      self.callbackDeletedevice(data)

  # ==================== Publish Data ====================

  def statusMsg(self, msg, api_key):
    if isinstance(msg, str):
      try:
        msg = json.loads(msg)
      except Exception:
        msg = {}

    if not isinstance(msg, dict):
      return

    payload = {
        "camera": msg.get("camera", "OFF"),
        "gpio": msg.get("gpio", "OFF"),
        "program_status": msg.get("program_status", "OFF"),
        "relay_status": msg.get("relay_status", "OFF"),
        "light_status": msg.get("light_status", "OFF"),
        "door_status": msg.get("door_status", "OFF"),
        "alarm_status": msg.get("alarm_status", "OFF"),
        "api_key": api_key,
        "last_update": msg.get(
            "last_update", datetime.datetime.now().timestamp()
        ),
    }
    self.publish(json.dumps(payload), 0)

  def sendHeardbeat(self, isRunning="ACTIVE"):
    if self.MQTTConnected:
      try:
        param = {
            "IP": GetIPAddress().get_local_ip(),
            "name": self.machineID,
            "Running Status": isRunning,
            "last_update": datetime.datetime.now().strftime("%H:%M:%S"),
        }
        self.publish(json.dumps(param), 1)
      except Exception:
        pass

  def publish(self, msg, i):
    if self.MQTTConnected:
      try:
        topic, _ = self.topic()
        self.mqtt_client.publish(topic[i], msg)
      except Exception as e:
        print(f"[MQTT] Publish error: {e}")

  # ==================== MQTT Events ====================

  def onConnectedMqtt(self, client, userdata, flags, rc, properties=None):
    if rc == 0:
      self.MQTTConnected = True
      _, sub_topics = self.topic()
      for t in sub_topics:
        self.mqtt_client.subscribe(t, qos=0)

      print("[MQTT] Connected Event (rc=0)")
      if not self._has_started and callable(self.agentStartup):
        self._has_started = True
        self.agentStartup()
    else:
      self.MQTTConnected = False

  def onDisconnectedMqtt(self, client, userdata, *args):
    self.MQTTConnected = False
    print("[MQTT] Disconnected. Client will auto-reconnect in background.")

  def onMessageMqtt(self, client, userdata, msg):
    _, sub_topics = self.topic()
    try:
      payload_str = msg.payload.decode("utf-8").strip()

      try:
        data = json.loads(payload_str)
      except json.JSONDecodeError:
        data = payload_str

      if msg.topic == sub_topics[0]:
        self.onProgramcontrol(data)
      elif msg.topic == sub_topics[1]:
        if isinstance(data, str):
          try:
            data = json.loads(data)
          except Exception:
            data = {}
        self.onProgramconfig(data)
      elif msg.topic == sub_topics[2]:
        if isinstance(data, str):
          try:
            data = json.loads(data)
          except Exception:
            pass
        self.onDeletedevice(data)

    except Exception as e:
      print(f"[MQTT] Error handling message: {e}")

