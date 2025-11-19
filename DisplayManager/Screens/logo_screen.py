from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from .base_screen import BaseScreen

class ClickableImage(ButtonBehavior, Image):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        return False

class LogoScreen(BaseScreen):

    def build(self):
        layout = FloatLayout()

        logo = ClickableImage(
            source="chobot_logo.png",
            size_hint=(0.8,0.8),
            pos_hint={"center_x":0.5, "center_y":0.5},
            allow_stretch=True
        )
        logo.bind(on_release=lambda *_: self.app.open_menu())

        layout.add_widget(logo)
        return layout
