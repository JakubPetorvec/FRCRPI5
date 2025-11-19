from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from .base_screen import BaseScreen
from .menu_screen import MenuButton


class ConfirmScreen(BaseScreen):

    def __init__(self, app, message, on_confirm):
        super().__init__(app)
        self.message = message
        self.on_confirm = on_confirm

    def build(self):
        layout = FloatLayout()

        # TITULEK
        title = Label(
            text="[b]Confirmation[/b]",
            markup=True,
            font_size=55,
            size_hint=(1, None),
            height=120,
            pos_hint={"center_x": 0.5, "top": 0.98},
            halign="center",
            valign="middle",
            color=(1, 1, 1, 1)
        )
        title.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        layout.add_widget(title)

        # ZPRÁVA
        msg = Label(
            text=self.message,
            markup=True,
            font_size=35,
            size_hint=(0.9, None),
            height=200,
            pos_hint={"center_x": 0.5, "center_y": 0.55},
            halign="center",
            valign="middle",
            color=(1, 1, 1, 1)
        )
        msg.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        layout.add_widget(msg)

        # YES BUTTON
        yes_btn = MenuButton(
            text="Yes",
            font_size=35,
            size_hint=(0.35, 0.13),
            pos_hint={"x": 0.08, "y": 0.08}
        )
        yes_btn.bind(on_release=lambda *_: self.confirm())
        layout.add_widget(yes_btn)

        # NO BUTTON
        no_btn = MenuButton(
            text="No",
            font_size=35,
            size_hint=(0.35, 0.13),
            pos_hint={"right": 0.92, "y": 0.08}
        )
        no_btn.bind(on_release=lambda *_: self.app.open_previous())
        layout.add_widget(no_btn)

        return layout

    # uživatel potvrdil
    def confirm(self):
        try:
            self.on_confirm()
        except Exception as e:
            self.app.logger.error(f"Confirm action failed: {e}")
        self.app.open_previous()
