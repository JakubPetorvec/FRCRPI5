import os
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

from .base_screen import BaseScreen
from .menu_screen import MenuButton


class BaseLogScreen(BaseScreen):

    def __init__(self, app, log_path, error_mode=False):
        super().__init__(app)
        self.log_path = log_path
        self.error_mode = error_mode

    def build(self):
        layout = FloatLayout()

        # ============================
        # TITULEK
        # ============================
        filename = os.path.basename(self.log_path)

        title = Label(
            text=f"[b]{filename}[/b]",
            markup=True,
            font_size=48,
            size_hint=(1, 0.12),
            pos_hint={"top": 0.97},
            halign="center",
            valign="middle",
            color=(1, 1, 1, 1),
        )
        title.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        layout.add_widget(title)

        # ============================
        # SCROLL VIEW
        # ============================
        self.scroll = ScrollView(
            size_hint=(1, 0.74),
            pos_hint={"x": 0, "y": 0.15},
            do_scroll_x=False
        )
        layout.add_widget(self.scroll)

        # ============================
        # TEXT LABEL
        # ============================
        self.text = Label(
            text=self.load_text(),
            markup=True,
            font_size=22,
            size_hint=(1, None),     # nutné pro scroll
            halign="left",
            valign="top",
            color=(1, 1, 1, 1),
        )

        # zalamování textu
        self.text.bind(
            texture_size=lambda inst, val: setattr(inst, "height", val[1]),
            size=lambda inst, val: setattr(inst, "text_size", (inst.width, None))
        )

        self.scroll.add_widget(self.text)

        # Auto scroll dolů po otevření
        Clock.schedule_once(lambda *_: self.scroll.scroll_to(self.text), 0)

        # ============================
        # REFRESH
        # ============================
        refresh_btn = MenuButton(
            text="Refresh",
            font_size=28,
            size_hint=(0.25, 0.08),
            pos_hint={"x": 0.03, "y": 0.02},
        )
        refresh_btn.bind(on_release=lambda *_: self.refresh())
        layout.add_widget(refresh_btn)

        # ============================
        # BACK
        # ============================
        back_btn = MenuButton(
            text="Back",
            font_size=28,
            size_hint=(0.25, 0.08),
            pos_hint={"right": 0.97, "y": 0.02},
        )
        back_btn.bind(on_release=lambda *_: self.app.open_previous())
        layout.add_widget(back_btn)

        return layout

    # ============================
    # načti maximálně 500 řádků
    # ============================
    def load_text(self):
        try:
            with open(self.log_path, "r") as f:
                raw = f.read()

            lines = raw.split("\n")

            # vezmi posledních 500
            lines = lines[-500:]

            colored = []
            for line in lines:
                low = line.lower()

                if "[error]" in low:
                    line = line.replace("[ERROR]", "[color=#ff5555][ERROR][/color]")
                if "[warn]" in low:
                    line = line.replace("[WARN]", "[color=#ffaa00][WARN][/color]")
                if "[debug]" in low:
                    line = line.replace("[DEBUG]", "[color=#55aaff][DEBUG][/color]")
                if "[info]" in low:
                    line = line.replace("[INFO]", "[color=#55ff55][INFO][/color]")

                colored.append(line)

            return "\n".join(colored)

        except Exception as e:
            return f"[color=#ff0000]Failed to read log file: {e}[/color]"

    # ============================
    # refresh
    # ============================
    def refresh(self):
        self.text.text = self.load_text()

        Clock.schedule_once(
            lambda *_: self.scroll.scroll_to(self.text), 0
        )

        self.app.logger.debug("Log refreshed")
