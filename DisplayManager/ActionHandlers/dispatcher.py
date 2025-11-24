from Screens.confirm_screen import ConfirmScreen
from Screens.base_log_screen import BaseLogScreen
from Screens.robot_sonic_screen import SonicScreen
from Screens.apriltag_screen import AprilTagScreen
from Screens.detectball_screen import DetectBallScreen
from Screens.qrcodo_screen import QRCodeScreen

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

    if action == "april_tags":
        if app.april_tag_screen is None:
            app.april_tag_screen = AprilTagScreen(app)
        app.navigate_to(app.april_tag_screen)
        return
     
    if action == "detect_ball":
        if app.detect_ball_screen is None:
            app.detect_ball_screen = DetectBallScreen(app)
        app.navigate_to(app.detect_ball_screen)
        return

    if action == "detect_qrcode":
        if app.detect_qrcode_screen is None:
            app.detect_qrcode_screen = QRCodeScreen(app)
        app.navigate_to(app.detect_qrcode_screen)
        return

    app.logger.warn(f"No handler for action: {action}")
