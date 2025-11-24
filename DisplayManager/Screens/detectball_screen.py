import threading
import zmq
import time
import zmq.utils.jsonapi as jsonapi

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle, Ellipse, Rectangle

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
#  DETECT BALL SCREEN
# ============================================================
class DetectBallScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app)

        self.ctx = zmq.Context.instance()
        self.sock = self.ctx.socket(zmq.DEALER)
        self.sock.setsockopt(zmq.IDENTITY, b"DisplayManager")
        self.sock.connect("ipc:///tmp/messenger_data.sock")

        self.sock.send_json({"sender": "DisplayManager", "target": None})

        self.thread = None
        self.running = False

        self.last_xy = (-1, -1)
        self.last_time = None

    # ============================================================
    #  BUILD UI
    # ============================================================
    def build(self):
        layout = FloatLayout()

        # ------- TITLE -------
        title = Label(
            text="[b]Camera – Detect Ball[/b]",
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
        #  LEFT BOX – SIMULACE POLOHY MÍČE
        # ======================================================
        self.preview_box = PrettyBox(
            bg=(0.18, 0.18, 0.18, 1),
            radius=25,
            orientation="vertical",
            size_hint=(0.47, 0.70),
            pos_hint={"x": 0.02, "y": 0.15},
            padding=20
        )

        # --- kreslící plátno ---
        with self.preview_box.canvas:
            Color(0.3, 0.3, 0.3, 1)
            self.box_rect = Rectangle()

            Color(1, 0.2, 0.2, 1)
            self.ball_dot = Ellipse(size=(30, 30), pos=(-100, -100))  # mimo obraz

        self.preview_box.bind(pos=self.update_canvas, size=self.update_canvas)
        layout.add_widget(self.preview_box)

        # ======================================================
        #  RIGHT BOX – POSLEDNÍ DATA
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
            text="[b]Last Detection[/b]\nNo data…",
            markup=True,
            font_size=28,
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
    #  ZMQ THREAD
    # ============================================================
    def start_listener(self):
        if self.running:
            return

        self.running = True
        threading.Thread(target=self.thread_loop, daemon=True).start()
        self.app.logger.info("DetectBallScreen ZMQ listener started")

    def thread_loop(self):
        while self.running:
            try:
                msg = self.sock.recv_json(flags=zmq.NOBLOCK)
                self.process_message(msg)

            except zmq.Again:
                time.sleep(0.01)

            except Exception as e:
                self.app.logger.error(f"DetectBallScreen ZMQ error: {e}")
                time.sleep(0.05)

    # ============================================================
    #  PROCESS MESSAGE
    # ============================================================
    def process_message(self, msg):
        if msg.get("type") != "camera_event":
            return
        if msg.get("mode") != "DETECTBALL":
            return

        payload = msg.get("payload", {})
        ball = payload.get("ball", {})

        x = ball.get("x", -1)
        y = ball.get("y", -1)
        detected = ball.get("detected", False)

        Clock.schedule_once(lambda *_: self.update_ui(x, y), 0)

    # ============================================================
    #  UPDATE UI
    # ============================================================
    def update_canvas(self, *_):
        self.box_rect.pos = self.preview_box.pos
        self.box_rect.size = self.preview_box.size

        self.update_ball_position()

    def update_ball_position(self):
        x, y = self.last_xy

        if x == -1 and y == -1:
            self.ball_dot.pos = (-100, -100)
            return

        bx, by = self.preview_box.pos
        bw, bh = self.preview_box.size

        px = bx + (bw / 2) + x - 15
        py = by + (bh / 2) - y - 15

        self.ball_dot.pos = (px, py)

    def update_ui(self, x, y):
        self.last_xy = (x, y)
        now = time.strftime("%d.%m.%Y %H:%M:%S")
        self.last_time = now

        # pravý panel
        self.info_label.text = (
            f"[b]Last Detection[/b]\n\n"
            f"X: {x}\n"
            f"Y: {y}\n"
            f"Time: {now}"
        )

        # levý panel – vykresli míč
        self.update_ball_position()

    def on_leave(self):
        self.running = False
        self.app.logger.info("DetectBallScreen listener stopped")
