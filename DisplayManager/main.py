from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.clock import Clock

import json
import os
import sys
import asyncio
import threading

from ActionHandlers.dispatcher import dispatch_action
from Screens.logo_screen import LogoScreen
from Screens.menu_screen import MenuScreen

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from LoggerManager.logger import Logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class DisplayManager(App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = Logger("DisplayManager")
        self.screen_history = []
        self.current_screen = None
        self.menu_config = None
        self.root_layout = None

        self.april_tag_screen = None 
        self.detect_ball_screen = None
        self.detect_qrcode_screen = None

        self.async_loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(
            target=self.start_async_loop,
            daemon=True
        )
        self.async_thread.start()

    def start_async_loop(self):
        asyncio.set_event_loop(self.async_loop)
        self.async_loop.run_forever()

    def build(self):
        Window.fullscreen = True

        self.logger.info("DisplayManager starting…")

        self.root_layout = FloatLayout()
        self.menu_config = self.load_config()

        self._show_screen(LogoScreen(self))

        self.logger.info("UI ready.")

        Clock.schedule_once(lambda *_: self.register_with_messenger(), 0)
        return self.root_layout

    def load_config(self):
        #self.logger.debug("Loading menu.json")
        menu_path = os.path.join(BASE_DIR, "menu.json")
        with open(menu_path) as f:
            return json.load(f)

    def register_with_messenger(self):
        import zmq
        import zmq.utils.jsonapi as jsonapi

        ctx = zmq.Context.instance()
        sock = ctx.socket(zmq.DEALER)
        sock.connect("ipc:///tmp/messenger_data.sock")

        msg = {
            "sender": "DisplayManager",
            "target": None   # jen registrace
        }
        sock.send(jsonapi.dumps(msg))
        sock.close()

        self.logger.info("DisplayManager registered to MessengerServer")

    # umožní spustit async task z obrazovky (kdybys chtěl)
    def create_async_task(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.async_loop)

    def execute_action(self, action):
        self.logger.info(f"Executing action: {action}")
        dispatch_action(self, action)

    def _show_screen(self, screen):
        #self.logger.debug(f"Switching to {screen.__class__.__name__}")
        self.root_layout.clear_widgets()
        self.current_screen = screen
        self.root_layout.add_widget(screen.build())

    def navigate_to(self, screen):
        if self.current_screen:
            self.screen_history.append(self.current_screen)
        self._show_screen(screen)

    def open_previous(self):
        self.logger.debug("Back pressed")
        if self.screen_history:
            self._show_screen(self.screen_history.pop())
        else:
            self.open_logo()

    def open_logo(self):
        #self.logger.debug("Returning to LogoScreen")
        self.screen_history.clear()
        self._show_screen(LogoScreen(self))

    def open_menu(self, items=None, title="Menu"):
        if items is None:
            items = self.menu_config["menu"]
        self.logger.info(f"Opening menu: {title}")
        self.navigate_to(MenuScreen(self, items, title))


if __name__ == "__main__":
    DisplayManager().run()
