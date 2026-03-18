"""
CHIKU PRO - App Control Module
Opens and closes desktop applications and URLs on Windows.
"""

import subprocess
import webbrowser
import shutil
import os


# ─── Known Applications Map ─────────────────────────────────────────────────
KNOWN_APPS = {
    # Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "browser": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "firefox": "firefox",

    # Dev Tools
    "code": "code",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "cmd": "cmd",
    "command prompt": "cmd",
    "terminal": "cmd",
    "powershell": "powershell",
    "git bash": "git-bash",

    # Productivity
    "notepad": "notepad",
    "note pad": "notepad",
    "wordpad": "wordpad",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "snipping tool": "SnippingTool",
    "task manager": "taskmgr",

    # Communication
    "discord": "discord",
    "telegram": "telegram",
    "whatsapp": "whatsapp",
    "teams": "teams",
    "zoom": "zoom",
    "skype": "skype",

    # Media
    "spotify": "spotify",
    "music": "spotify",
    "vlc": "vlc",

    # System
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "settings": "ms-settings:",
    "control panel": "control",
}

# ─── Process names for killing apps ─────────────────────────────────────────
PROCESS_NAMES = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "msedge": "msedge.exe",
    "firefox": "firefox.exe",
    "notepad": "notepad.exe",
    "code": "Code.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "discord": "Discord.exe",
    "telegram": "Telegram.exe",
    "spotify": "Spotify.exe",
    "vlc": "vlc.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "calc": "Calculator.exe",
    "calculator": "Calculator.exe",
    "teams": "Teams.exe",
    "zoom": "Zoom.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "taskmgr": "Taskmgr.exe",
    "task manager": "Taskmgr.exe",
}


def open_app(app_name):
    """Open a desktop application by name."""
    app_name_lower = app_name.lower().strip()

    try:
        # 1. Check known apps map
        if app_name_lower in KNOWN_APPS:
            exe = KNOWN_APPS[app_name_lower]
            subprocess.Popen(f"start {exe}", shell=True)
            return f"✅ {app_name} opened."

        # 2. Check if it's on the system PATH
        if shutil.which(app_name_lower):
            subprocess.Popen(f"start {app_name_lower}", shell=True)
            return f"✅ {app_name} opened."

        # 3. Try generic Windows start command  
        subprocess.Popen(f"start {app_name_lower}", shell=True)
        return f"⚡ Tried opening {app_name}."

    except Exception as e:
        return f"❌ Failed to open {app_name}: {e}"


def close_app(app_name):
    """Close/kill a running application by name."""
    app_name_lower = app_name.lower().strip()

    try:
        # Look up the process name
        process = PROCESS_NAMES.get(app_name_lower, f"{app_name_lower}.exe")

        result = subprocess.run(
            f"taskkill /f /im {process}",
            shell=True,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return f"✅ {app_name} closed."
        else:
            # Try by window title
            result2 = subprocess.run(
                f'taskkill /f /fi "WINDOWTITLE eq {app_name}*"',
                shell=True,
                capture_output=True,
                text=True,
            )
            if result2.returncode == 0:
                return f"✅ {app_name} closed."
            return f"⚠️ {app_name} might not be running."

    except Exception as e:
        return f"❌ Failed to close {app_name}: {e}"


def open_url(url):
    """Open a URL in the default web browser."""
    try:
        if not url.startswith("http"):
            url = "https://" + url

        webbrowser.open(url)
        return f"✅ Opened {url}"

    except Exception as e:
        return f"❌ Failed to open URL: {e}"


def search_web(query):
    """Search the web using Google."""
    try:
        import urllib.parse
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        webbrowser.open(search_url)
        return f"✅ Searching for: {query}"

    except Exception as e:
        return f"❌ Search failed: {e}"