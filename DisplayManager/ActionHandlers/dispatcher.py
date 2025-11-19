from Screens.confirm_screen import ConfirmScreen
from Screens.base_log_screen import BaseLogScreen
from Screens.robot_sonic_screen import SonicScreen
from Screens.apriltag_screen import AprilTagScreen

import subprocess


def dispatch_action(app, action: str):

    # LOG/ERROR VIEW
    if action.startswith("log:"):
        path = action.split("log:", 1)[1]
        app.navigate_to(BaseLogScreen(app, path))
        return

    if action.startswith("error:"):
        path = action.split("error:", 1)[1]
        app.navigate_to(BaseLogScreen(app, path, error_mode=True))
        return

    # RESTART ACTION (with confirmation)
    if action.startswith("restart:"):
        service = action.split("restart:", 1)[1]

        def do_restart():
            subprocess.run(["sudo", "systemctl", "restart", f"{service}"])

        msg = f"Do you really want to restart\n[b]{service}.service[/b] ?"
        app.navigate_to(ConfirmScreen(app, msg, do_restart))
        return

    if action == "robot_sonic":
        app.navigate_to(SonicScreen(app))
        return

    # >>>>> APRIL TAGS – JEDNA INSTANCI OBDRZOVKY <<<<<
    if action == "april_tags":
        # vytvoříme jen jednou, pak už jen recyklujeme
        if app.april_tag_screen is None:
            app.april_tag_screen = AprilTagScreen(app)
        app.navigate_to(app.april_tag_screen)
        return

    # fallback
    app.logger.warn(f"No handler for action: {action}")
