from kivy.uix.floatlayout import FloatLayout

class BaseScreen:
    def __init__(self, app):
        self.app = app

    def build(self):
        return FloatLayout()
