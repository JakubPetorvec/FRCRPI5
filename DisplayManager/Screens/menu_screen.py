from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout

from Screens.base_screen import BaseScreen


class MenuButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.color = (1, 1, 1, 1)
        self.background_color = (0, 0, 0, 0)

        with self.canvas.before:
            Color(0.15, 0.15, 0.18, 1)
            self.rect = RoundedRectangle(radius=[20])

        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class MenuScreen(BaseScreen):

    def __init__(self, app, items, title):
        super().__init__(app)
        self.items = items
        self.title = title

    def build(self):
        layout = FloatLayout()

        # -----------------------------------
        # TITLE
        # -----------------------------------
        title_label = Label(
            text=self.title,
            font_size=60,
            size_hint=(1, None),
            height=100,
            pos_hint={"center_x": 0.5, "top": 0.97},
            color=(1, 1, 1, 1),
            valign="top",
            halign="center"
        )
        title_label.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        layout.add_widget(title_label)

        # -----------------------------------
        # SCROLLVIEW S TLAČÍTKY
        # -----------------------------------
        scroll = ScrollView(
            size_hint=(1,0.8),
            pos_hint={"center_x": 0.5, "top": 0.86},
            bar_width=20,
        )

        container = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=20,
            spacing=20
        )
        container.bind(minimum_height=container.setter("height"))

        # Naplnění tlačítky
        for item in self.items:
            btn = MenuButton(
                text=item["title"],
                font_size=34,
                size_hint=(0.65, None),
                pos_hint={"center_x": 0.5},
                height=100
            )
            btn.bind(on_release=lambda inst, i=item: self.handle(i))
            container.add_widget(btn)

        scroll.add_widget(container)
        layout.add_widget(scroll)

        # -----------------------------------
        # BACK BUTTON - FIXNÍ POZICE
        # -----------------------------------
        back_btn = MenuButton(
            text="Back",
            font_size=30,
            size_hint=(0.25, 0.09),
            pos_hint={"right": 0.99, "y": 0.89}
        )
        back_btn.bind(on_release=lambda *_: self.app.open_previous())
        layout.add_widget(back_btn)

        return layout

    def handle(self, item):
        txt = item.get("title", "Unknown")
        self.app.logger.info(f"Menu item clicked: {txt}")

        if "submenu" in item:
            self.app.open_menu(item["submenu"], item["title"])
        elif "action" in item:
            self.app.execute_action(item["action"])
        else:
            self.app.logger.warn(f"Menu item has no action: {item}")
