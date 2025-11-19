from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from .base_screen import BaseScreen
from .menu_screen import MenuButton
import zmq
import zmq.asyncio
import threading


class SonicScreen(BaseScreen):

    def __init__(self, app):
        super().__init__(app)

        # default hodnoty
        self.sonics = ["---"] * 8
        self.labels = []

        # ZMQ
        self.ctx = zmq.asyncio.Context()
        self.sock = self.ctx.socket(zmq.DEALER)

        # MUSÍM mít identitu – jinak mě server nepozná
        self.sock.setsockopt(zmq.IDENTITY, b"DISPLAY")

        self.sock.connect("ipc:///tmp/messenger_data.sock")

        self.running = True

        # listener thread
        threading.Thread(target=self._listener_thread, daemon=True).start()

        Clock.schedule_once(lambda *_: self.subscribe(), 0.5)

    # ---------------------------------------------------------
    def build(self):
        layout = FloatLayout()

        title = Label(
            text="[b]Ultrasonic Sensors[/b]",
            markup=True,
            font_size=55,
            size_hint=(1, 0.1),
            pos_hint={"top": 0.98},
            halign="center",
            valign="middle",
            color=(1, 1, 1, 1)
        )
        title.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        layout.add_widget(title)

        # robot square
        with layout.canvas:
            Color(0.2, 0.2, 0.25, 1)
            self.robot_rect = Rectangle(size=(350, 350), pos=(215, 150))

        positions = [
            (190, 460), (265, 460),
            (500, 460), (575, 460),
            (190, 115), (265, 115),
            (500, 115), (575, 115),
        ]

        for i in range(8):
            lbl = Label(
                text=f"S{i+1}: ---",
                font_size=38,
                size_hint=(None, None),
                size=(160, 60),
                pos=positions[i],
                color=(1, 1, 1, 1)
            )
            self.labels.append(lbl)
            layout.add_widget(lbl)

        back = MenuButton(
            text="Back",
            font_size=34,
            size_hint=(0.25, 0.1),
            pos_hint={"right": 0.97, "y": 0.05}
        )
        back.bind(on_release=lambda *_: self.close())
        layout.add_widget(back)

        return layout

    # ---------------------------------------------------------
    def subscribe(self):
        self.sock.send_json({
            "sender": "DISPLAY",
            "target": "SONIC_MANAGER",
            "cmd": "SUBSCRIBE_STATE"
        })
        self.app.logger.info("Subscribed to SONIC_MANAGER")

    # ---------------------------------------------------------
    def _listener_thread(self):
        poller = zmq.Poller()
        poller.register(self.sock, zmq.POLLIN)

        while self.running:
            events = dict(poller.poll(100))
            if self.sock in events:
                try:
                    msg = self.sock.recv_json()
                except:
                    continue

                if msg.get("sender") == "SONIC_MANAGER":
                    data = msg.get("data", {}).get("sonics")
                    if data:
                        Clock.schedule_once(lambda *_: self.update_values(data))

    # ---------------------------------------------------------
    def update_values(self, data):
        for i in range(8):
            try:
                self.labels[i].text = f"S{i+1}: {data[i]:.0f}"
            except:
                self.labels[i].text = f"S{i+1}: ---"

    # ---------------------------------------------------------
    def close(self):
        self.running = False
        self.app.open_previous()
