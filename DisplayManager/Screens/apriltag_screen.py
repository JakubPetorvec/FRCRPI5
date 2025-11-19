import threading
import zmq
import time
import zmq.utils.jsonapi as jsonapi

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle

from Screens.base_screen import BaseScreen
from Screens.menu_screen import MenuButton


# ============================================================
#  HEZKÝ BOX S POZADÍM A ZAOBLENÝMI ROHY
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
#  APRIL TAG SCREEN
# ============================================================
class AprilTagScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app)

        # ZMQ setup
        self.ctx = zmq.Context.instance()
        self.sock = self.ctx.socket(zmq.DEALER)
        self.sock.setsockopt(zmq.IDENTITY, b"DisplayManager")
        self.sock.connect("ipc:///tmp/messenger_data.sock")

        # send register
        self.sock.send_json({"sender": "DisplayManager", "target": None})

        self.thread = None
        self.running = False

        # dict of seen tags
        self.seen_tags = {}  # id -> timestamp

    # ============================================================
    #  BUILD UI
    # ============================================================
    def build(self):
        layout = FloatLayout()

        # ========================================================
        #  TITLE – FIXNUTO, ABY BYL VIDĚT
        # ========================================================
        self.screen_label = Label(
            text="[b]Camera – AprilTags[/b]",
            markup=True,
            font_size=38,
            size_hint=(1, 0.10),
            pos_hint={"center_x": 0.5, "top": 0.99},
            halign="center",
            valign="middle",
            color=(1, 1, 1, 1)
        )
        self.screen_label.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        layout.add_widget(self.screen_label)

        # ------- LEVÝ BOX -------
        self.current_box = PrettyBox(
            bg=(0.18, 0.18, 0.18, 1),
            radius=25,
            orientation="vertical",
            size_hint=(0.47, 0.70),
            pos_hint={"x": 0.02, "y": 0.15},
            padding=35,
            spacing=10,
        )

        self.current_label = Label(
            text="[b]Current Tag[/b]\nNo data…",
            markup=True,
            font_size=28,
            halign="left",
            valign="top",
            color=(1, 1, 1, 1)
        )
        self.current_label.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        self.current_box.add_widget(self.current_label)

        layout.add_widget(self.current_box)

        # ------- PRAVÝ BOX -------
        self.seen_box = PrettyBox(
            bg=(0.18, 0.18, 0.18, 1),
            radius=25,
            orientation="vertical",
            size_hint=(0.48, 0.70),
            pos_hint={"x": 0.50, "y": 0.15},
            padding=35,
            spacing=5,
        )

        self.seen_label = Label(
            text="[b]Seen Tags[/b]\n(none)",
            markup=True,
            font_size=30,
            halign="left",
            valign="top",
            color=(1, 1, 1, 1)
        )
        self.seen_label.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        self.seen_box.add_widget(self.seen_label)

        layout.add_widget(self.seen_box)

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
        self.app.logger.info("AprilTagScreen ZMQ listener started")

    def thread_loop(self):
        while self.running:
            try:
                msg = self.sock.recv_json(flags=zmq.NOBLOCK)
                self.process_message(msg)

            except zmq.Again:
                time.sleep(0.01)

            except Exception as e:
                self.app.logger.error(f"AprilTagScreen ZMQ error: {e}")
                time.sleep(0.05)

    # ============================================================
    #  PROCESS MESSAGE
    # ============================================================
    def process_message(self, msg):
        if msg.get("type") != "camera_event":
            return
        if msg.get("mode") != "APRILTAG":
            return

        tags = msg["payload"]["tags"]
        if not tags:
            Clock.schedule_once(lambda *_: self.update_no_tag(), 0)
            return

        Clock.schedule_once(lambda *_: self.update_tag(tags[0]), 0)

    # ============================================================
    #  UPDATE UI
    # ============================================================
    def update_tag(self, t):
        now = time.strftime("%d.%m.%Y %H:%M:%S")

        # left panel
        self.current_label.text = (
            f"[b]Current Tag[/b]\n\n"
            f"ID: {t['id']}\n"
            f"Family: {t['family']}\n"
            f"Center: {t['center'][0]:.1f}, {t['center'][1]:.1f}\n"
            f"Offset: {t['offset'][0]:.1f}, {t['offset'][1]:.1f}\n"
            f"Last seen: {now}"
        )

        # right panel
        self.seen_tags[t["id"]] = now

        lines = ["[b]Seen Tags[/b]\n"]
        for tid, ts in sorted(self.seen_tags.items()):
            lines.append(f"ID {tid} — {ts}")

        self.seen_label.text = "\n".join(lines)

    def update_no_tag(self):
        self.current_label.text = "[b]Current Tag[/b]\nNo data…"

    def on_leave(self):
        self.running = False
        self.app.logger.info("AprilTagScreen listener stopped")
