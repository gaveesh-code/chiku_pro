"""
CHIKU PRO - Logger Module
Logs all executed actions with timestamps and risk levels.
"""

import datetime
import os

LOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(LOG_DIR, "chiku_log.txt")


def log_action(command, risk_level):
    """Log an action with timestamp and risk level."""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] | RISK: {risk_level} | COMMAND: {command}\n"

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)

    except Exception as e:
        print(f"⚠️ Logging error: {e}")


def get_recent_logs(count=10):
    """Read the last N log entries."""
    try:
        if not os.path.exists(LOG_FILE):
            return []

        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        return [line.strip() for line in lines[-count:] if line.strip()]

    except Exception:
        return []


def clear_logs():
    """Clear all log entries."""
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")
        return True
    except Exception:
        return False