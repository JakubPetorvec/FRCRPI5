import threading
import zmq
import time
import zmq.utils.jsonapi as jsonapi

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics.texture import Texture
from kivy.graphics import Color, RoundedRectangle, Rectangle

import qrcode
import numpy as np

from Screens.base_screen import BaseScreen
from Screens.menu_screen import MenuButton


# ============================================================
#  HEZKÝ BOX (zaoblené rohy)
# ============================================================
class PrettyBox(BoxLayout):
    def __init__(self, bg=(0.17, 0.17, 0.17, 1), radius=20, **kwargs):
        super().__init__(**kwargs)
        self.radius = radius
        self.bg = bg

        with self.canvas.before:
            Color(*self.bg)
            self.rect = RoundedRectangle(radius=[self.radius])

        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *_):
        self.rect.pos = self.pos
        self.rect.size = self.size


# ============================================================
#  QR CODE SCREEN
# ============================================================
class QRCodeScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app)

        self.ctx = zmq.Context.instance()
        self.sock = self.ctx.socket(zmq.DEALER)
        self.sock.setsockopt(zmq.IDENTITY, b"DisplayManager")
        self.sock.connect("ipc:///tmp/messenger_data.sock")
        self.sock.send_json({"sender": "DisplayManager", "target": None})

        self.thread = None
        self.running = False

        self.last_data = None        # text QR kódu
        self.last_xy = ("---", "---")
        self.last_time = None

        self.qr_texture = None

    # ============================================================
    #  BUILD UI
    # ============================================================
    def build(self):
        layout = FloatLayout()

        # ------- TITLE -------
        title = Label(
            text="[b]Camera – QR Code[/b]",
            markup=True,
            font_size=38,
            size_hint=(1, 0.10),
            pos_hint={"center_x": 0.5, "top": 0.99},
            halign="center",
            valign="middle",
            color=(1, 1, 1, 1)
        )
        title.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        layout.add_widget(title)

        # ======================================================
        #  LEFT – QR CODE IMAGE
        # ======================================================
        self.preview_box = PrettyBox(
            bg=(0.18, 0.18, 0.18, 1),
            radius=25,
            orientation="vertical",
            size_hint=(0.47, 0.70),
            pos_hint={"x": 0.02, "y": 0.15},
            padding=20
        )

        with self.preview_box.canvas:
            # zobrazovaný QR obrázek
            self.qr_rect = Rectangle(size=(0, 0), pos=(0, 0))

        self.preview_box.bind(pos=self.update_qr_rect, size=self.update_qr_rect)
        layout.add_widget(self.preview_box)

        # ======================================================
        #  RIGHT – INFO PANEL
        # ======================================================
        self.info_box = PrettyBox(
            bg=(0.18, 0.18, 0.18, 1),
            radius=25,
            orientation="vertical",
            size_hint=(0.48, 0.70),
            pos_hint={"x": 0.50, "y": 0.15},
            padding=35,
            spacing=5,
        )

        self.info_label = Label(
            text="[b]Last QR Code[/b]\nNo data…",
            markup=True,
            font_size=26,
            halign="left",
            valign="top",
            color=(1, 1, 1, 1)
        )
        self.info_label.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        self.info_box.add_widget(self.info_label)

        layout.add_widget(self.info_box)

        # ------- BACK -------
        back_btn = MenuButton(
            text="Back",
            font_size=30,
            size_hint=(0.20, 0.10),
            pos_hint={"right": 0.97, "top": 0.13},
        )
        back_btn.bind(on_release=lambda *_: self.app.open_previous())
        layout.add_widget(back_btn)

        Clock.schedule_once(lambda *_: self.start_listener(), 0)
        return layout

    # ============================================================
    #  QR CODE GENERATION
    # ============================================================
    def generate_qr_texture(self, text):
        if not text:
            self.qr_texture = None
            return

        qr = qrcode.QRCode(
            version=2,
            box_size=8,
            border=2
        )
        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img = np.array(img.convert("RGB"))

        h, w, c = img.shape

        texture = Texture.create(size=(w, h), colorfmt='rgb')
        texture.blit_buffer(img.flatten(), colorfmt='rgb', bufferfmt='ubyte')
        texture.flip_vertical()

        self.qr_texture = texture

    # ============================================================
    #  CANVAS UPDATE
    # ============================================================
    def update_qr_rect(self, *_):
        bx, by = self.preview_box.pos
        bw, bh = self.preview_box.size

        size = min(bw - 40, bh - 40)

        if self.qr_texture:
            self.qr_rect.texture = self.qr_texture
            self.qr_rect.size = (size, size)
            self.qr_rect.pos = (bx + (bw - size) / 2, by + (bh - size) / 2)
        else:
            self.qr_rect.size = (0, 0)

    # ============================================================
    #  ZMQ LISTENER
    # ============================================================
    def start_listener(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self.thread_loop, daemon=True).start()

    def thread_loop(self):
        while self.running:
            try:
                msg = self.sock.recv_json(flags=zmq.NOBLOCK)
                self.process_message(msg)

            except zmq.Again:
                time.sleep(0.01)
            except Exception as e:
                self.app.logger.error(f"QRCodeScreen ZMQ error: {e}")
                time.sleep(0.05)

    # ============================================================
    #  PROCESS DATA
    # ============================================================
    def process_message(self, msg):
        if msg.get("type") != "camera_event":
            return
        if msg.get("mode") != "QRCODE":
            return

        payload = msg.get("payload", {})
        codes = payload.get("codes", [])

        if not codes:
            Clock.schedule_once(lambda *_: self.update_ui_no_detection(), 0)
            return

        first = codes[0]

        text = first.get("data", "")
        offset = first.get("offset", [None, None])

        try:
            x = float(offset[0])
            y = float(offset[1])
        except:
            x, y = "---", "---"

        Clock.schedule_once(lambda *_: self.update_ui(text, x, y), 0)

    # ============================================================
    #  UI UPDATE
    # ============================================================
    def update_ui(self, text, x, y):
        self.last_data = text
        self.last_xy = (x, y)
        self.last_time = time.strftime("%d.%m.%Y %H:%M:%S")

        self.generate_qr_texture(text)
        self.update_qr_rect()

        self.info_label.text = (
            "[b]Last QR Code[/b]\n\n"
            f"[b]Data:[/b] {text}\n"
            f"[b]X:[/b] {x}\n"
            f"[b]Y:[/b] {y}\n"
            f"[b]Time:[/b] {self.last_time}"
        )

    def update_ui_no_detection(self):
        x = y = "---"

        if self.last_data:
            self.info_label.text = (
                "[b]Last QR Code[/b]\n\n"
                f"[b]Data:[/b] {self.last_data}\n"
                f"[b]X:[/b] ---\n"
                f"[b]Y:[/b] ---\n"
                f"[b]Time:[/b] {self.last_time}"
            )
        else:
            self.info_label.text = "[b]Last QR Code[/b]\nNo data…"

        self.last_xy = ("---", "---")
        self.update_qr_rect()

    # ============================================================
    #  EXIT
    # ============================================================
    def on_leave(self):
        self.running = False
