"""
CHIKU PRO - Executor Module
Executes parsed action dicts by dispatching to the appropriate modules.
Integrates risk analysis, logging, and voice feedback.
"""

import subprocess
import os
import datetime

from core.app_control import open_app, close_app, open_url, search_web
from core.volume_control import set_volume
from core.vision import vision
from core.risk_analyzer import analyze_risk
from core.logger import log_action
from core.voice import speak


def execute_action(action):
    """
    Execute a single action dict.
    Returns a result string describing what was done.
    """
    action_type = action.get("type", "")
    result = ""

    try:
        # ── Open App ────────────────────────────────────────────────────
        if action_type == "open_app":
            app = action.get("app", "")
            risk = analyze_risk(f"open {app}")
            log_action(f"open_app: {app}", risk)

            if risk == "HIGH":
                speak(f"High risk detected for opening {app}. Skipping.")
                return f"⛔ Blocked (HIGH risk): open {app}"

            result = open_app(app)
            speak(f"{app} opened.")

        # ── Close App ───────────────────────────────────────────────────
        elif action_type == "close_app":
            app = action.get("app", "")
            risk = analyze_risk(f"taskkill {app}")
            log_action(f"close_app: {app}", risk)

            if risk == "HIGH":
                speak(f"High risk detected. Not closing {app}.")
                return f"⛔ Blocked (HIGH risk): close {app}"

            result = close_app(app)
            speak(f"{app} closed.")

        # ── Open URL ────────────────────────────────────────────────────
        elif action_type == "open_url":
            url = action.get("url", "")
            log_action(f"open_url: {url}", "LOW")
            result = open_url(url)
            speak("Website opened.")

        # ── Web Search ──────────────────────────────────────────────────
        elif action_type == "search_web":
            query = action.get("query", "")
            log_action(f"search_web: {query}", "LOW")
            result = search_web(query)
            speak(f"Searching for {query}.")

        # ── Volume Control ──────────────────────────────────────────────
        elif action_type == "volume":
            level = action.get("level", 50)
            log_action(f"volume: {level}", "LOW")
            result = set_volume(level)
            speak(f"Volume set to {level} percent.")

        # ── Camera On ───────────────────────────────────────────────────
        elif action_type == "camera_on":
            log_action("camera_on", "LOW")
            vision.start()
            result = "✅ Camera started."
            speak("Camera started.")

        # ── Camera Off ──────────────────────────────────────────────────
        elif action_type == "camera_off":
            log_action("camera_off", "LOW")
            vision.stop()
            result = "✅ Camera stopped."
            speak("Camera stopped.")

        # ── Screenshot ──────────────────────────────────────────────────
        elif action_type == "screenshot":
            log_action("screenshot", "LOW")
            result = _take_screenshot()
            speak("Screenshot taken.")

        # ── System Info ─────────────────────────────────────────────────
        elif action_type == "system_info":
            log_action("system_info", "LOW")
            result = _get_system_info()
            speak("Here is your system information.")

        # ── Type Text ───────────────────────────────────────────────────
        elif action_type == "type_text":
            text = action.get("text", "")
            log_action(f"type_text: {text[:50]}", "LOW")
            result = _type_text(text)

        # ── Shell Command ───────────────────────────────────────────────
        elif action_type == "shell_command":
            command = action.get("command", "")
            risk = analyze_risk(command)
            log_action(f"shell: {command}", risk)

            if risk == "HIGH":
                speak("Dangerous command detected! I cannot execute this.")
                return f"⛔ Blocked (HIGH risk): {command}"

            if risk == "MEDIUM":
                speak(f"Medium risk command: {command}. Proceeding with caution.")

            result = _run_shell(command)
            speak("Command executed.")

        # ── Chat / Conversation ─────────────────────────────────────────
        elif action_type == "chat":
            message = action.get("message", "I'm not sure what you mean.")
            speak(message)
            result = f"💬 {message}"

        # ── Unknown ─────────────────────────────────────────────────────
        else:
            result = f"⚠️ Unknown action type: {action_type}"

    except Exception as e:
        result = f"❌ Error executing {action_type}: {e}"

    return result


# ─── Helper Functions ────────────────────────────────────────────────────────

def _take_screenshot():
    """Take a screenshot and save to Desktop."""
    try:
        from PIL import ImageGrab
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        filepath = os.path.join(desktop, f"chiku_screenshot_{timestamp}.png")

        screenshot = ImageGrab.grab()
        screenshot.save(filepath)
        return f"✅ Screenshot saved: {filepath}"

    except ImportError:
        # Fallback: use Windows Snipping Tool
        try:
            subprocess.Popen("snippingtool /clip", shell=True)
            return "✅ Snipping Tool launched."
        except Exception:
            return "❌ Could not take screenshot. Install Pillow: pip install Pillow"
    except Exception as e:
        return f"❌ Screenshot failed: {e}"


def _get_system_info():
    """Gather system information."""
    info_lines = []

    try:
        import platform
        info_lines.append(f"💻 OS: {platform.system()} {platform.release()} ({platform.version()})")
        info_lines.append(f"🖥️  Machine: {platform.machine()}")
        info_lines.append(f"👤 User: {os.getlogin()}")
    except Exception:
        pass

    try:
        import psutil
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        info_lines.append(f"⚡ CPU Usage: {cpu_percent}%")

        # RAM
        ram = psutil.virtual_memory()
        used_gb = ram.used / (1024 ** 3)
        total_gb = ram.total / (1024 ** 3)
        info_lines.append(f"🧠 RAM: {used_gb:.1f} GB / {total_gb:.1f} GB ({ram.percent}%)")

        # Disk
        disk = psutil.disk_usage("C:\\")
        disk_used = disk.used / (1024 ** 3)
        disk_total = disk.total / (1024 ** 3)
        info_lines.append(f"💾 Disk (C:): {disk_used:.1f} GB / {disk_total:.1f} GB ({disk.percent}%)")

        # Battery
        battery = psutil.sensors_battery()
        if battery:
            plug = "🔌 Plugged In" if battery.power_plugged else "🔋 On Battery"
            info_lines.append(f"🔋 Battery: {battery.percent}% ({plug})")

    except ImportError:
        info_lines.append("ℹ️ Install psutil for detailed info: pip install psutil")
    except Exception as e:
        info_lines.append(f"⚠️ System info error: {e}")

    return "\n".join(info_lines) if info_lines else "Could not retrieve system info."


def _type_text(text):
    """Type text on screen using pyautogui."""
    try:
        import pyautogui
        import time
        time.sleep(0.5)  # Small delay to let user focus the target window
        pyautogui.typewrite(text, interval=0.03)
        return f"✅ Typed: {text}"
    except ImportError:
        return "❌ pyautogui not installed. Run: pip install pyautogui"
    except Exception as e:
        return f"❌ Type error: {e}"


def _run_shell(command):
    """Execute a shell command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout.strip()
        error = result.stderr.strip()

        if output:
            print(f"📋 Output:\n{output}")
        if error:
            print(f"⚠️ Stderr:\n{error}")

        return f"✅ Command executed. Return code: {result.returncode}"

    except subprocess.TimeoutExpired:
        return "⏰ Command timed out (30s limit)."
    except Exception as e:
        return f"❌ Shell error: {e}"