"""
CHIKU PRO - System Tray Application
Runs CHIKU silently in the background with a system tray icon.
No console window needed — works like Siri/Cortana.
"""

import threading
import time
import os
import sys

# Add project root to path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.wake_word import wake_engine
from core.voice import speak, listen, _sr_available
from core.brain import parse_user_input
from core.executor import execute_action
from core.memory import memory
from core.auth import auth_system
from core.vision import vision

# ─── Try importing pystray ──────────────────────────────────────────────────
_tray_available = False
try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    _tray_available = True
except ImportError:
    print("[Tray] pystray not available. Install: pip install pystray Pillow")


# ─── Notification Sound ─────────────────────────────────────────────────────
def _play_notification():
    """Play a wake-up notification sound."""
    try:
        import winsound
        # Play the system "ding" sound
        winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
    except Exception:
        pass


def _play_success():
    """Play a success sound."""
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_OK)
    except Exception:
        pass


def _play_error():
    """Play an error sound."""
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONHAND)
    except Exception:
        pass


# ─── Create Tray Icon Image ─────────────────────────────────────────────────
def _create_icon_image(status="idle"):
    """Create a tray icon image programmatically."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    if status == "listening":
        bg_color = (0, 200, 100, 255)   # Green = actively listening
    elif status == "processing":
        bg_color = (255, 165, 0, 255)   # Orange = processing
    elif status == "error":
        bg_color = (255, 50, 50, 255)   # Red = error
    else:
        bg_color = (50, 120, 220, 255)  # Blue = idle/standby

    draw.ellipse([4, 4, size-4, size-4], fill=bg_color)

    # "C" letter for CHIKU
    try:
        font = ImageFont.truetype("arial", 32)
    except Exception:
        font = ImageFont.load_default()

    draw.text((18, 12), "C", fill=(255, 255, 255, 255), font=font)

    return img


class ChikuTrayApp:
    """
    System tray application for CHIKU PRO.
    Runs in the background, listens for "Hey Chiku", and executes commands.
    """

    def __init__(self):
        self.tray_icon = None
        self.is_running = False
        self.is_authenticated = False
        self.status = "idle"  # idle, listening, processing, error

    def _on_wake_word_detected(self):
        """Called when 'Hey Chiku' is detected."""
        self.status = "listening"
        self._update_icon()
        _play_notification()

        speak("Yes?")

        # Listen for the actual command
        command = listen()

        if not command:
            speak("I didn't catch that.")
            self.status = "idle"
            self._update_icon()
            return

        print(f"📝 Command: {command}")
        self.status = "processing"
        self._update_icon()

        # Check for exit
        if command.strip().lower() in {"exit", "quit", "stop", "bye", "shutdown chiku", "shut down"}:
            speak("Goodbye! Going to sleep.")
            self._quit(None, None)
            return

        # Parse and execute
        try:
            actions = parse_user_input(command)

            if not actions:
                speak("Sorry, I didn't understand that.")
                self.status = "idle"
                self._update_icon()
                return

            for action in actions:
                result = execute_action(action)
                memory.store_action(action)
                if result:
                    print(f"  → {result}")

            _play_success()

        except Exception as e:
            print(f"❌ Error: {e}")
            speak("Something went wrong.")
            _play_error()

        self.status = "idle"
        self._update_icon()

    def _update_icon(self):
        """Update the tray icon based on current status."""
        if self.tray_icon:
            try:
                self.tray_icon.icon = _create_icon_image(self.status)
                status_text = {
                    "idle": "CHIKU PRO — Waiting for 'Hey Chiku'",
                    "listening": "CHIKU PRO — Listening...",
                    "processing": "CHIKU PRO — Processing...",
                    "error": "CHIKU PRO — Error",
                }
                self.tray_icon.title = status_text.get(self.status, "CHIKU PRO")
            except Exception:
                pass

    def _show_status(self, icon, item):
        """Show CHIKU's current status."""
        print(f"\n{'='*50}")
        print("  🤖 CHIKU PRO STATUS")
        print(f"{'='*50}")
        print(f"  Status: {self.status}")
        print(f"  Wake Engine: {'Active' if wake_engine.is_active() else 'Inactive'}")
        print(f"  Auth: {auth_system.auth_mode}")
        print(f"  Owner: {auth_system.owner_name or 'Not set'}")
        print(f"{'='*50}\n")

    def _toggle_listening(self, icon, item):
        """Toggle wake word listening on/off."""
        if wake_engine.listening:
            wake_engine.stop()
            self.status = "idle"
            speak("CHIKU going to sleep.")
        else:
            wake_engine.start(on_wake=self._on_wake_word_detected)
            self.status = "idle"
            speak("CHIKU is listening again.")
        self._update_icon()

    def _manual_command(self, icon, item):
        """Trigger manual command input (simulate wake word)."""
        self._on_wake_word_detected()

    def _open_camera(self, icon, item):
        """Toggle camera on/off."""
        if vision.is_running():
            vision.stop()
            speak("Camera stopped.")
        else:
            vision.start()
            speak("Camera started.")

    def _security_settings(self, icon, item):
        """Open security settings."""
        auth_system.change_auth_mode()

    def _quit(self, icon, item):
        """Quit CHIKU completely."""
        self.is_running = False
        wake_engine.stop()
        vision.stop()

        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass

        print("\n👋 CHIKU PRO has shut down.")
        os._exit(0)

    def run(self):
        """Start the CHIKU tray application."""
        print(r"""
   ██████╗██╗  ██╗██╗██╗  ██╗██╗   ██╗    ██████╗ ██████╗  ██████╗ 
  ██╔════╝██║  ██║██║██║ ██╔╝██║   ██║    ██╔══██╗██╔══██╗██╔═══██╗
  ██║     ███████║██║█████╔╝ ██║   ██║    ██████╔╝██████╔╝██║   ██║
  ██║     ██╔══██║██║██╔═██╗ ██║   ██║    ██╔═══╝ ██╔══██╗██║   ██║
  ╚██████╗██║  ██║██║██║  ██╗╚██████╔╝    ██║     ██║  ██║╚██████╔╝
   ╚═════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝
                  🎙️ Always-On Background Mode
        """)

        # ── Authentication ──────────────────────────────────────────────
        if auth_system.is_setup_done and auth_system.auth_mode != "none":
            authenticated = auth_system.authenticate()
            if not authenticated:
                speak("Authentication failed. CHIKU cannot start.")
                return
        elif not auth_system.is_setup_done:
            auth_system.first_time_setup()
            if auth_system.owner_name:
                memory.set_user_name(auth_system.owner_name)

        self.is_authenticated = True
        self.is_running = True

        # ── Greeting ────────────────────────────────────────────────────
        import datetime
        hour = datetime.datetime.now().hour
        name = auth_system.owner_name or memory.get_user_name() or "Boss"

        if hour < 12:
            greet = f"Good morning, {name}!"
        elif hour < 17:
            greet = f"Good afternoon, {name}!"
        elif hour < 21:
            greet = f"Good evening, {name}!"
        else:
            greet = f"Hey, {name}!"

        speak(f"{greet} CHIKU is now running in the background. Just say 'Hey Chiku' whenever you need me.")

        # ── Start Wake Word Engine ──────────────────────────────────────
        wake_engine.start(on_wake=self._on_wake_word_detected)

        # ── Start System Tray ───────────────────────────────────────────
        if _tray_available:
            self._run_tray()
        else:
            self._run_console()

    def _run_tray(self):
        """Run with system tray icon."""
        menu = pystray.Menu(
            pystray.MenuItem("🤖 CHIKU PRO", self._show_status, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "🎤 Listening",
                self._toggle_listening,
                checked=lambda item: wake_engine.listening,
            ),
            pystray.MenuItem("💬 Say Command", self._manual_command),
            pystray.MenuItem("📷 Camera", self._open_camera),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🔐 Security", self._security_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Quit CHIKU", self._quit),
        )

        self.tray_icon = pystray.Icon(
            name="chiku_pro",
            icon=_create_icon_image("idle"),
            title="CHIKU PRO — Say 'Hey Chiku'",
            menu=menu,
        )

        print("✅ CHIKU running in system tray. Say 'Hey Chiku' to activate!")
        print("   Right-click the tray icon for options.\n")

        # This blocks until quit
        self.tray_icon.run()

    def _run_console(self):
        """Fallback: run in console mode if pystray not available."""
        print("✅ CHIKU running in background. Say 'Hey Chiku' to activate!")
        print("   Press Ctrl+C to quit.\n")

        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⚡ Shutting down...")
            self._quit(None, None)


# ─── Entry Point ─────────────────────────────────────────────────────────────
def main():
    """Start CHIKU as a background tray application."""
    app = ChikuTrayApp()
    app.run()


if __name__ == "__main__":
    main()
