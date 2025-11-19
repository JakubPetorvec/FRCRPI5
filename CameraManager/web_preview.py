import socket
import threading
import cv2
import numpy as np
import http.server
import socketserver
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ProgramManager.ports import PREVIEW_PORT
from LoggerManager.logger import Logger

log = Logger("WebPreview")

latest_frame = None


def udp_receiver():
    global latest_frame

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PREVIEW_PORT))

    log.info(f"Listening for preview frames on UDP {PREVIEW_PORT}")

    while True:
        data, _ = sock.recvfrom(200000)
        frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if frame is not None:
            latest_frame = frame


class MJPEGHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global latest_frame

        if self.path != "/":
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
        self.end_headers()

        log.info("HTTP client connected")

        while True:
            if latest_frame is None:
                continue

            ret, jpg = cv2.imencode(".jpg", latest_frame)
            if not ret:
                continue

            try:
                self.wfile.write(b"--FRAME\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                self.wfile.write(jpg.tobytes())
                self.wfile.write(b"\r\n")
            except BrokenPipeError:
                log.info("HTTP client disconnected")
                break


def start_http_server():
    PORT = 8081
    log.info(f"Starting MJPEG server on {PORT}")

    with socketserver.TCPServer(("", PORT), MJPEGHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    threading.Thread(target=udp_receiver, daemon=True).start()
    start_http_server()
