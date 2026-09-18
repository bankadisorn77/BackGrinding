from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import re
from socketserver import ThreadingMixIn
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class _ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  daemon_threads = True


class _MJPEGHandler(BaseHTTPRequestHandler):
  PATH_PATTERN = re.compile(r'^/video_feed_(\d+)')

  def do_GET(self):
    match = self.PATH_PATTERN.match(self.path)
    if not match:
      self.send_response(404)
      self.end_headers()
      return

    cam_index = int(match.group(1))

    controller: MultiCameraServer = self.server.controller
    if not controller.is_camera_registered(cam_index):
      self.send_response(404)
      self.end_headers()
      return

    self.send_response(200)
    self.send_header('Age', '0')
    self.send_header('Cache-Control', 'no-cache, private')
    self.send_header('Pragma', 'no-cache')
    self.send_header(
        'Content-Type', 'multipart/x-mixed-replace; boundary=frame'
    )
    self.end_headers()

    try:
      last_sent = None
      while not controller.stop_event.is_set():
        frame_bytes = controller.get_frame(cam_index)

        if frame_bytes is not None and frame_bytes is not last_sent:
          last_sent = frame_bytes
          self.wfile.write(b'--frame\r\n')
          self.send_header('Content-Type', 'image/jpeg')
          self.send_header('Content-Length', str(len(frame_bytes)))
          self.end_headers()
          self.wfile.write(frame_bytes)
          self.wfile.write(b'\r\n')

        time.sleep(0.04)  # ~25 FPS
    except (BrokenPipeError, ConnectionResetError):
      pass
    except Exception as e:
      logger.debug('Stream client disconnected (%s): %s', self.path, e)

  def log_message(self, format, *args):
    return


class MultiCameraServer:

  def __init__(self, host: str = '0.0.0.0', port: int = 8095):
    self.host = host
    self.port = port
    self._frames = {}
    self._lock = threading.Lock()
    self.stop_event = threading.Event()
    self._server: Optional[_ThreadedHTTPServer] = None
    self._server_thread: Optional[threading.Thread] = None

  def update_frame(self, cam_index: int, frame_bytes: bytes):
    if frame_bytes is None:
      return
    with self._lock:
      self._frames[cam_index] = frame_bytes

  def get_frame(self, cam_index: int) -> Optional[bytes]:
    with self._lock:
      return self._frames.get(cam_index)

  def is_camera_registered(self, cam_index: int) -> bool:
    with self._lock:
      return cam_index in self._frames

  def start(self):
    if self._server_thread and self._server_thread.is_alive():
      logger.warning('MJPEG Server is already running.')
      return

    self.stop_event.clear()
    self._server = _ThreadedHTTPServer((self.host, self.port), _MJPEGHandler)
    self._server.controller = self

    self._server_thread = threading.Thread(
        target=self._server.serve_forever, daemon=True
    )
    self._server_thread.start()
    logger.info(
        'Multi-Camera MJPEG Server started at http://%s:%s',
        self.host,
        self.port,
    )

  def stop(self):
    self.stop_event.set()
    if self._server:
      self._server.shutdown()
      self._server.server_close()
      logger.info('Multi-Camera MJPEG Server stopped.')