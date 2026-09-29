import asyncio
import ctypes
import datetime
import io
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageDraw, ImageTk
import psutil
import requests

from backgrinding_production.ProcessClass.pipe import resiver

# ================= Configurations & Paths =================
BASE_DIR = r"D:\BG"
PYTHON_W = os.path.join(BASE_DIR, "env", "Scripts", "pythonw.exe")
if not os.path.exists(PYTHON_W):
  PYTHON_W = sys.executable

WORKER_DIR = os.path.join(BASE_DIR, "backgrinding_production")
STOP_WORKER_FLAG = os.path.join(BASE_DIR, "stop_worker.flag")
OUTPUT_IMG_DIR = os.path.join(WORKER_DIR, "saved_images_output")
CONFIG_FILE = os.path.join(WORKER_DIR, "config", "config.json")
ICON_PATH = os.path.join(BASE_DIR, "icon", "ICON.ico")
LOG_DIR = os.path.join(BASE_DIR, "logs")
WORKER_LOG = os.path.join(LOG_DIR, "worker_stdout.log")

try:
  myappid = "app.bg.aisystem.v1"
  ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
  pass

# DETACHED_FLAGS = 0x00000008 | 0x08000000
DETACHED_FLAGS = 0x08000000

# Get Local IP
IP = "127.0.0.1"
try:
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  s.connect(("8.8.8.8", 80))
  IP = s.getsockname()[0]
  s.close()
except Exception:
  try:
    IP = socket.gethostbyname(socket.gethostname())
  except Exception:
    pass

STREAM_URL = f"http://{IP}:8095/video_feed"


# ================= Process Management =================
def get_pid_by_script(script_name: str):
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


def stop_worker_process(pid: int):
  if not pid:
    return
  try:
    with open(STOP_WORKER_FLAG, "w", encoding="utf-8") as f:
      f.write("STOP")
  except Exception:
    pass

  try:
    proc = psutil.Process(pid)
    proc.wait(timeout=1.5)
    return
  except (psutil.TimeoutExpired, psutil.NoSuchProcess):
    try:
      proc.kill()
    except Exception:
      pass
  except Exception:
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(pid)],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def safe_read_json(filepath: str, retries: int = 3, delay: float = 0.05):
  if not os.path.exists(filepath):
    return None
  for _ in range(retries):
    try:
      with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if content:
          return json.loads(content)
    except (PermissionError, json.JSONDecodeError, OSError):
      time.sleep(delay)
  return None


# ================= Components =================
class ConfigModal(tk.Toplevel):

  def __init__(self, parent, config_path, on_save_callback):
    super().__init__(parent)
    self.title("System Configuration")
    self.geometry("620x520")
    self.config_path = config_path
    self.on_save = on_save_callback
    self.config_data = {}

    if os.path.exists(ICON_PATH):
      try:
        self.iconbitmap(ICON_PATH)
      except Exception:
        pass

    self.configure(padx=20, pady=20)
    self.transient(parent)
    self.grab_set()

    self.load_config()
    self._build_ui()
    self.populate_data()

  def load_config(self):
    data = safe_read_json(self.config_path)
    if data and isinstance(data, dict):
      self.config_data = data

  def _build_ui(self):
    ttk.Label(
        self, text="System Configuration", font=("Arial", 16, "bold")
    ).pack(anchor="w", pady=(0, 10))

    frame = ttk.Frame(self)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="Device ID").grid(
        row=0, column=0, sticky="w", pady=5
    )
    self.ent_device = ttk.Entry(frame, width=22)
    self.ent_device.grid(row=0, column=1, sticky="w", padx=5)

    ttk.Label(frame, text="MQTT Broker").grid(
        row=0, column=2, sticky="w", padx=10
    )
    self.ent_mqtt = ttk.Entry(frame, width=22)
    self.ent_mqtt.grid(row=0, column=3, sticky="w")

    ttk.Label(frame, text="Web Server IP").grid(
        row=1, column=0, sticky="w", pady=5
    )
    self.ent_web = ttk.Entry(frame, width=22)
    self.ent_web.grid(row=1, column=1, sticky="w", padx=5)

    ttk.Label(frame, text="GPIO Channels", font=("Arial", 10, "bold")).grid(
        row=2, column=0, columnspan=4, sticky="w", pady=(15, 5)
    )

    ttk.Label(frame, text="Input Channel").grid(
        row=3, column=0, sticky="w", pady=3
    )
    self.sp_in = ttk.Spinbox(frame, from_=0, to=100, width=10)
    self.sp_in.grid(row=3, column=1, sticky="w", padx=5)

    ttk.Label(frame, text="Output Alarm").grid(
        row=3, column=2, sticky="w", padx=10
    )
    self.sp_out_al = ttk.Spinbox(frame, from_=0, to=100, width=10)
    self.sp_out_al.grid(row=3, column=3, sticky="w")

    ttk.Label(frame, text="Output Relay (Contor)").grid(
        row=4, column=0, sticky="w", pady=3
    )
    self.sp_out_con = ttk.Spinbox(frame, from_=0, to=100, width=10)
    self.sp_out_con.grid(row=4, column=1, sticky="w", padx=5)

    ttk.Label(frame, text="Output Light (SM)").grid(
        row=4, column=2, sticky="w", padx=10
    )
    self.sp_out_sm = ttk.Spinbox(frame, from_=0, to=100, width=10)
    self.sp_out_sm.grid(row=4, column=3, sticky="w")

    ttk.Label(frame, text="Model Configuration", font=("Arial", 10, "bold")).grid(
        row=5, column=0, columnspan=4, sticky="w", pady=(15, 5)
    )
    ttk.Label(frame, text="Model Path").grid(row=6, column=0, sticky="w")
    self.ent_model = ttk.Entry(frame, width=45)
    self.ent_model.grid(
        row=6, column=1, columnspan=3, sticky="w", padx=5, pady=2
    )

    btn_frame = ttk.Frame(self)
    btn_frame.pack(fill=tk.X, pady=20)
    ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(
        side=tk.RIGHT, padx=5
    )
    ttk.Button(btn_frame, text="Save Changes", command=self._save).pack(
        side=tk.RIGHT
    )

  def populate_data(self):
    self.ent_device.insert(
        0,
        self.config_data.get(
            "device_id", self.config_data.get("name", "BG-01")
        ),
    )
    self.ent_mqtt.insert(
        0,
        self.config_data.get(
            "MQTTServer", self.config_data.get("mqtt_broker", "")
        ),
    )
    self.ent_web.insert(0, self.config_data.get("server_url", ""))

    self.sp_in.set(
        self.config_data.get(
            "inputChannel", self.config_data.get("input_channel", 0)
        )
    )
    self.sp_out_al.set(
        self.config_data.get(
            "outputAlarm", self.config_data.get("output_alarm_channel", 0)
        )
    )
    self.sp_out_con.set(
        self.config_data.get(
            "outputContor", self.config_data.get("output_relay_channel", 1)
        )
    )
    self.sp_out_sm.set(
        self.config_data.get(
            "outputStateMachine", self.config_data.get("output_light_channel", 2)
        )
    )
    self.ent_model.insert(0, self.config_data.get("model_path", ""))

  def _save(self):
    try:
      updated = dict(self.config_data)

      dev_id = self.ent_device.get().strip()
      updated["device_id"] = dev_id
      updated["name"] = dev_id

      mqtt_srv = self.ent_mqtt.get().strip()
      updated["MQTTServer"] = mqtt_srv
      updated["mqtt_broker"] = mqtt_srv

      updated["server_url"] = self.ent_web.get().strip()

      in_ch = int(self.sp_in.get())
      updated["inputChannel"] = in_ch
      updated["input_channel"] = in_ch

      al_ch = int(self.sp_out_al.get())
      updated["outputAlarm"] = al_ch
      updated["output_alarm_channel"] = al_ch

      con_ch = int(self.sp_out_con.get())
      updated["outputContor"] = con_ch
      updated["output_relay_channel"] = con_ch

      sm_ch = int(self.sp_out_sm.get())
      updated["outputStateMachine"] = sm_ch
      updated["output_light_channel"] = sm_ch

      updated["model_path"] = self.ent_model.get().strip()

      self.on_save(updated)
      self.destroy()
    except ValueError as e:
      messagebox.showerror(
          "Validation Error", f"Channels must be integer numbers: {e}"
      )
    except Exception as e:
      messagebox.showerror("Error", f"Invalid input: {e}")


class ImageGalleryModal(tk.Toplevel):

  def __init__(self, parent, img_path):
    super().__init__(parent)
    self.title("Image Log Gallery")
    self.geometry("860x640")
    self.img_path = img_path
    self.transient(parent)

    if os.path.exists(ICON_PATH):
      try:
        self.iconbitmap(ICON_PATH)
      except Exception:
        pass

    top_frame = ttk.Frame(self)
    top_frame.pack(fill=tk.X, padx=10, pady=10)
    ttk.Label(
        top_frame, text="Saved Inspection Logs", font=("Arial", 14, "bold")
    ).pack(side=tk.LEFT)
    ttk.Button(top_frame, text="Refresh", command=self.load_images).pack(
        side=tk.RIGHT
    )

    self.canvas = tk.Canvas(self, bg="#f1f5f9", highlightthickness=0)
    scrollbar = ttk.Scrollbar(
        self, orient=tk.VERTICAL, command=self.canvas.yview
    )
    self.scrollable_frame = ttk.Frame(self.canvas)

    self.scrollable_frame.bind(
        "<Configure>",
        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
    )
    self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
    self.canvas.configure(yscrollcommand=scrollbar.set)

    self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    self.bind("<MouseWheel>", self._on_mouse_wheel)

    self.images_ref = []
    self.load_images()

  def _on_mouse_wheel(self, event):
    if self.winfo_exists():
      self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

  def load_images(self):
    for widget in self.scrollable_frame.winfo_children():
      widget.destroy()
    self.images_ref.clear()

    if not os.path.exists(self.img_path):
      return

    valid = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
    try:
      files = [
          f for f in os.listdir(self.img_path) if f.lower().endswith(valid)
      ]
      files.sort(
          key=lambda x: os.path.getmtime(os.path.join(self.img_path, x)),
          reverse=True,
      )
    except Exception:
      return

    col, row = 0, 0
    for f in files:
      path = os.path.join(self.img_path, f)
      try:
        with Image.open(path) as img:
          img.thumbnail((180, 180))
          tk_img = ImageTk.PhotoImage(img.copy())

        self.images_ref.append(tk_img)

        card = tk.Frame(
            self.scrollable_frame,
            bg="white",
            bd=1,
            relief="solid",
            padx=5,
            pady=5,
        )
        card.grid(row=row, column=col, padx=8, pady=8)

        lbl_img = tk.Label(card, image=tk_img, bg="white", cursor="hand2")
        lbl_img.pack()
        lbl_img.bind(
            "<Button-1>", lambda e, p=path, n=f: self.preview_image(p, n)
        )

        display_name = f if len(f) <= 22 else f[:10] + "..." + f[-9:]
        tk.Label(
            card, text=display_name, font=("Consolas", 8), bg="white"
        ).pack(pady=(3, 0))

        col += 1
        if col > 3:
          col = 0
          row += 1
      except Exception:
        continue

  def preview_image(self, path, name):
    prev = tk.Toplevel(self)
    prev.title(f"Preview: {name}")
    prev.geometry("800x600")
    try:
      with Image.open(path) as img:
        img.thumbnail((800, 600))
        tk_img = ImageTk.PhotoImage(img.copy())
      lbl = tk.Label(prev, image=tk_img, bg="black")
      lbl.image = tk_img
      lbl.pack(fill=tk.BOTH, expand=True)
    except Exception:
      pass


# ================= Main Application =================
class App(tk.Tk):

  def __init__(self):
    super().__init__()
    self.title("BG System - Desktop Controller (Shared Memory Monitor)")
    self.geometry("1400x850")
    self.configure(bg="#f8fafc")

    if os.path.exists(ICON_PATH):
      try:
        self.iconbitmap(ICON_PATH)
      except Exception:
        pass

    self.is_running = True
    self.last_log_size = 0
    self.show_overlay = tk.BooleanVar(value=False)
    self.stream_image = None
    self.last_result_img_path = None

    # เก็บสถานะที่อ่านสดมาจาก Shared Memory (RAM)
    self.hw_status = {
        "camera": "OFF",
        "gpio": "OFF",
        "last_update": 0,
    }

    # เชื่อมต่อ Shared Memory ผ่านคลาส resiver (เหมือน Agent)
    self.pipe = resiver(on_data_received=self.handle_incoming_pipe_data)

    self._build_ui()
    self._start_threads()

    # Main Loop Timers
    self.after(500, self.sync_dashboard)
    self.after(1000, self.poll_result_image)
    self.protocol("WM_DELETE_WINDOW", self.on_closing)

  def handle_incoming_pipe_data(self, data):
    """Callback อัปเดตสถานะทันทีเมื่อมีข้อมูลใหม่ส่งมาที่ Shared Memory"""
    if isinstance(data, dict):
      status_dict = data.get("status", data)
      if isinstance(status_dict, dict):
        self.hw_status["camera"] = status_dict.get("camera", "OFF")
        self.hw_status["gpio"] = status_dict.get("gpio", "OFF")
        self.hw_status["last_update"] = status_dict.get("last_update", time.time())

  def _build_ui(self):
    header = tk.Frame(self, bg="white", height=55)
    header.pack(fill=tk.X, side=tk.TOP)

    tk.Label(
        header,
        text="Backgrinding Inspection System",
        font=("Arial", 16, "bold"),
        bg="white",
        fg="#0f172a",
    ).pack(side=tk.LEFT, padx=20, pady=12)
    self.lbl_clock = tk.Label(
        header, text="--:--:--", font=("Consolas", 12), bg="white", fg="#64748b"
    )
    self.lbl_clock.pack(side=tk.RIGHT, padx=20)

    main_frame = tk.Frame(self, bg="#f8fafc")
    main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

    left_col = tk.Frame(main_frame, bg="#f8fafc")
    left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    vid_card = tk.Frame(left_col, bg="white", bd=1, relief="solid")
    vid_card.pack(fill=tk.BOTH, expand=True)

    vid_header = tk.Frame(vid_card, bg="white")
    vid_header.pack(fill=tk.X, padx=10, pady=6)
    tk.Label(
        vid_header,
        text="Live Camera Stream",
        font=("Arial", 12, "bold"),
        bg="white",
    ).pack(side=tk.LEFT)
    ttk.Checkbutton(
        vid_header, text="Detection Overlay", variable=self.show_overlay
    ).pack(side=tk.RIGHT, padx=10)
    tk.Label(
        vid_header,
        text="● LIVE",
        font=("Arial", 10, "bold"),
        fg="#ef4444",
        bg="white",
    ).pack(side=tk.RIGHT)

    self.canvas_video = tk.Canvas(vid_card, bg="black", highlightthickness=0)
    self.canvas_video.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    right_col = tk.Frame(main_frame, bg="#f8fafc", width=420)
    right_col.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
    right_col.pack_propagate(False)

    # 1. Status Card
    stat_card = tk.Frame(
        right_col, bg="white", bd=1, relief="solid", pady=10, padx=12
    )
    stat_card.pack(fill=tk.X, pady=(0, 15))

    stat_header = tk.Frame(stat_card, bg="white")
    stat_header.pack(fill=tk.X)
    tk.Label(
        stat_header,
        text="System State",
        font=("Arial", 12, "bold"),
        bg="white",
    ).pack(side=tk.LEFT)
    tk.Button(
        stat_header,
        text="⚙ Config",
        font=("Arial", 9, "bold"),
        bd=1,
        bg="#f1f5f9",
        command=self.open_config,
    ).pack(side=tk.RIGHT)

    stat_mid = tk.Frame(stat_card, bg="white")
    stat_mid.pack(fill=tk.X, pady=12)
    self.lbl_status = tk.Label(
        stat_mid,
        text="STOPPED",
        font=("Arial", 14, "bold"),
        fg="#64748b",
        bg="white",
    )
    self.lbl_status.pack(side=tk.LEFT)

    self.btn_toggle = tk.Button(
        stat_mid,
        text="START",
        bg="#16a34a",
        fg="white",
        font=("Arial", 10, "bold"),
        width=8,
        command=self.toggle_worker,
    )
    self.btn_toggle.pack(side=tk.RIGHT, padx=5)
    tk.Button(
        stat_mid,
        text="GALLERY",
        bg="#2563eb",
        fg="white",
        font=("Arial", 10, "bold"),
        command=self.open_gallery,
    ).pack(side=tk.RIGHT)

    stat_bot = tk.Frame(stat_card, bg="white")
    stat_bot.pack(fill=tk.X, pady=(5, 0))
    self.lbl_cam = tk.Label(
        stat_bot,
        text="CAM: OFF",
        font=("Arial", 9, "bold"),
        bg="#e2e8f0",
        fg="#475569",
        padx=6,
        pady=2,
    )
    self.lbl_cam.pack(side=tk.LEFT, padx=3)
    self.lbl_gpio = tk.Label(
        stat_bot,
        text="GPIO: OFF",
        font=("Arial", 9, "bold"),
        bg="#e2e8f0",
        fg="#475569",
        padx=6,
        pady=2,
    )
    self.lbl_gpio.pack(side=tk.LEFT, padx=3)

    # 2. Terminal Log
    term_card = tk.Frame(
        right_col, bg="white", bd=1, relief="solid", pady=8, padx=10
    )
    term_card.pack(fill=tk.X, pady=(0, 15))
    tk.Label(
        term_card, text="Worker Terminal Logs", font=("Arial", 10, "bold"), bg="white"
    ).pack(anchor="w")

    self.txt_log = tk.Text(
        term_card, height=8, bg="#0f172a", fg="#4ade80", font=("Consolas", 8)
    )
    self.txt_log.pack(fill=tk.X, pady=5)

    # 3. Result Display
    res_card = tk.Frame(
        right_col, bg="white", bd=1, relief="solid", pady=8, padx=10
    )
    res_card.pack(fill=tk.BOTH, expand=True)
    tk.Label(
        res_card, text="Latest Inspection Result", font=("Arial", 10, "bold"), bg="white"
    ).pack(anchor="w")
    self.lbl_res_time = tk.Label(
        res_card, text="--:--:--", font=("Consolas", 9), bg="white", fg="gray"
    )
    self.lbl_res_time.pack(anchor="e")
    self.lbl_res_img = tk.Label(res_card, bg="#0f172a")
    self.lbl_res_img.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

  # ================= Threads =================
  def _start_threads(self):
    threading.Thread(target=self._mjpeg_worker, daemon=True).start()
    threading.Thread(target=self._shm_listener_thread, daemon=True).start()

  def _shm_listener_thread(self):
    """รัน Event Loop ของ resiver (Shared Memory) ในเบื้องหลัง"""
    asyncio.run(self.pipe.run_pipe_resiver())

  def _update_canvas_from_thread(self, tk_img, x_offset, y_offset):
    """เรนเดอร์ภาพแบบจัดกึ่งกลาง Canvas"""
    if not self.is_running or not self.winfo_exists():
      return
    self.canvas_video.delete("stream_frame")
    self.canvas_video.create_image(
        x_offset, y_offset, anchor=tk.NW, image=tk_img, tags="stream_frame"
    )
    self.stream_image = tk_img

  def _mjpeg_worker(self):
    while self.is_running:
      try:
        res = requests.get(STREAM_URL, stream=True, timeout=4)
        if res.status_code == 200:
          byte_data = bytes()
          for chunk in res.iter_content(chunk_size=2048):
            if not self.is_running:
              break
            byte_data += chunk
            a = byte_data.find(b"\xff\xd8")
            b = byte_data.find(b"\xff\xd9")
            if a != -1 and b != -1:
              jpg = byte_data[a : b + 2]
              byte_data = byte_data[b + 2 :]

              try:
                img = Image.open(io.BytesIO(jpg))

                # วาด Overlay
                if self.show_overlay.get():
                  draw = ImageDraw.Draw(img)
                  w, h = img.size
                  sx, sy = w / 1000, h / 1000

                  draw.rectangle(
                      [
                          460 * sx,
                          56 * sy,
                          (460 + 77) * sx,
                          (56 + 90) * sy,
                      ],
                      outline="#22FF00",
                      width=2,
                  )
                  draw.polygon(
                      [
                          (459 * sx, 558 * sy),
                          (203 * sx, 352 * sy),
                          (47 * sx, 706 * sy),
                          (307 * sx, 903 * sy),
                      ],
                      outline="#22FF00",
                      width=2,
                  )
                  draw.polygon(
                      [
                          (547 * sx, 553 * sy),
                          (796 * sx, 335 * sy),
                          (959 * sx, 674 * sy),
                          (712 * sx, 890 * sy),
                      ],
                      outline="#22FF00",
                      width=2,
                  )
                  draw.polygon(
                      [
                          (184 * sx, 0),
                          (805 * sx, 0),
                          (812 * sx, 318 * sy),
                          (503 * sx, 568 * sy),
                          (185 * sx, 334 * sy),
                      ],
                      outline="#22FF00",
                      width=2,
                  )

                cw = self.canvas_video.winfo_width()
                ch = self.canvas_video.winfo_height()
                if cw > 10 and ch > 10:
                  orig_w, orig_h = img.size
                  # คำนวณ Scale Factor เพื่อรักษาอัตราส่วนภาพ (Aspect Ratio)
                  scale = min(cw / orig_w, ch / orig_h)
                  new_w = max(1, int(orig_w * scale))
                  new_h = max(1, int(orig_h * scale))

                  # หา Offset ให้อยู่กึ่งกลาง Canvas (Pillarbox/Letterbox)
                  x_offset = (cw - new_w) // 2
                  y_offset = (ch - new_h) // 2

                  img_resized = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
                  tk_img = ImageTk.PhotoImage(img_resized)
                  self.after(0, self._update_canvas_from_thread, tk_img, x_offset, y_offset)
              except Exception:
                pass
      except Exception:
        time.sleep(2)

  # ================= Polling Loop =================
  def sync_dashboard(self):
    self.lbl_clock.config(text=datetime.datetime.now().strftime("%H:%M:%S"))

    pid = get_pid_by_script("StateMachine.py")
    if pid:
      self.lbl_status.config(text="RUNNING", fg="#16a34a")
      self.btn_toggle.config(text="STOP", bg="#dc2626")

      # ตรวจสอบความสดใหม่ของข้อมูลจาก RAM (ไม่เกิน 5 วินาที)
      is_fresh = (time.time() - self.hw_status.get("last_update", 0)) < 5.0
      cam_val = self.hw_status.get("camera", "OFF")
      gpio_val = self.hw_status.get("gpio", "OFF")

      cam_ok = (cam_val in ["ONLINE", "ON"]) and is_fresh
      gpio_ok = (gpio_val in ["ONLINE", "ON"]) and is_fresh

      self.lbl_cam.config(
          text="CAM: ONLINE" if cam_ok else f"CAM: {cam_val}",
          bg="#bbf7d0" if cam_ok else "#fecaca",
          fg="#166534" if cam_ok else "#991b1b",
      )
      self.lbl_gpio.config(
          text="GPIO: ONLINE" if gpio_ok else f"GPIO: {gpio_val}",
          bg="#bbf7d0" if gpio_ok else "#fecaca",
          fg="#166534" if gpio_ok else "#991b1b",
      )
    else:
      self.lbl_status.config(text="STOPPED", fg="#64748b")
      self.btn_toggle.config(text="START", bg="#16a34a")
      self.lbl_cam.config(text="CAM: OFF", bg="#e2e8f0", fg="#475569")
      self.lbl_gpio.config(text="GPIO: OFF", bg="#e2e8f0", fg="#475569")

    # Tail Log
    if os.path.exists(WORKER_LOG):
      try:
        curr_size = os.path.getsize(WORKER_LOG)
        if curr_size > self.last_log_size:
          with open(
              WORKER_LOG, "r", encoding="utf-8", errors="ignore"
          ) as f:
            f.seek(self.last_log_size)
            new_lines = f.read()
            if new_lines:
              self.txt_log.insert(tk.END, new_lines)
              self.txt_log.see(tk.END)
          self.last_log_size = curr_size
        elif curr_size < self.last_log_size:
          self.last_log_size = 0
      except Exception:
        pass

    if self.is_running:
      self.after(500, self.sync_dashboard)

  def poll_result_image(self):
    if os.path.exists(OUTPUT_IMG_DIR):
      exts = (".jpg", ".jpeg", ".png")
      try:
        files = [
            os.path.join(OUTPUT_IMG_DIR, f)
            for f in os.listdir(OUTPUT_IMG_DIR)
            if f.lower().endswith(exts)
        ]
        if files:
          latest = max(files, key=os.path.getmtime)
          if latest != self.last_result_img_path:
            self.last_result_img_path = latest
            with Image.open(latest) as img:
              cw = self.lbl_res_img.winfo_width()
              ch = self.lbl_res_img.winfo_height()
              if cw > 10 and ch > 10:
                orig_w, orig_h = img.size
                scale = min(cw / orig_w, ch / orig_h)
                new_w = max(1, int(orig_w * scale))
                new_h = max(1, int(orig_h * scale))
                img_display = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
              else:
                img_display = img.copy()
              tk_img = ImageTk.PhotoImage(img_display)

            self.lbl_res_img.config(image=tk_img)
            self.lbl_res_img.image = tk_img

            basename = os.path.basename(latest)
            match = re.search(
                r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", basename
            )
            if match:
              y, m, d, h, mi, s = match.groups()
              self.lbl_res_time.config(text=f"{y}-{m}-{d} {h}:{mi}:{s}")
            else:
              mtime = os.path.getmtime(latest)
              self.lbl_res_time.config(
                  text=datetime.datetime.fromtimestamp(mtime).strftime(
                      "%Y-%m-%d %H:%M:%S"
                  )
              )
      except Exception:
        pass

    if self.is_running:
      self.after(1000, self.poll_result_image)

  # ================= Actions =================
  def toggle_worker(self):
    pid = get_pid_by_script("StateMachine.py")
    if pid:
      stop_worker_process(pid)
    else:
      if os.path.exists(STOP_WORKER_FLAG):
        try:
          os.remove(STOP_WORKER_FLAG)
        except OSError:
          pass
      cmd = f'"{PYTHON_W}" -u StateMachine.py >> "{WORKER_LOG}" 2>&1'
      subprocess.Popen(
          cmd, cwd=WORKER_DIR, shell=True, creationflags=DETACHED_FLAGS
      )

  def open_config(self):
    ConfigModal(self, CONFIG_FILE, self._on_config_save)

  def _on_config_save(self, new_config_data):
    try:
      with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(new_config_data, f, indent=2, ensure_ascii=False)
      messagebox.showinfo("Success", "Config saved. Restarting Worker...")
    except Exception as e:
      messagebox.showerror("Error", f"Failed to save config: {e}")
      return

    def _restart():
      pid = get_pid_by_script("StateMachine.py")
      if pid:
        stop_worker_process(pid)
        time.sleep(1.0)
      if os.path.exists(STOP_WORKER_FLAG):
        try:
          os.remove(STOP_WORKER_FLAG)
        except OSError:
          pass
      cmd = f'"{PYTHON_W}" -u StateMachine.py >> "{WORKER_LOG}" 2>&1'
      subprocess.Popen(
          cmd, cwd=WORKER_DIR, shell=True, creationflags=DETACHED_FLAGS
      )

    threading.Thread(target=_restart, daemon=True).start()

  def open_gallery(self):
    ImageGalleryModal(self, OUTPUT_IMG_DIR)

  def on_closing(self):
    self.is_running = False
    try:
      self.pipe.close()
    except Exception:
      pass
    self.destroy()


if __name__ == "__main__":
  app = App()
  app.mainloop()