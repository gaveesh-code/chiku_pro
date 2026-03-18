"""
CHIKU PRO - Memory Module
Stores conversation history, last actions, user preferences, and context.
Persists to a JSON file for cross-session memory.
"""

import json
import os
import datetime

MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chiku_memory.json")


class Memory:
    def __init__(self):
        self.last_action = None
        self.last_app = None
        self.user_name = None
        self.action_history = []        # Recent action log
        self.max_history = 50           # Keep last 50 actions
        self.preferences = {}           # User preferences
        self._load()

    def _load(self):
        """Load memory from disk."""
        try:
            if os.path.exists(MEMORY_FILE):
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.user_name = data.get("user_name")
                    self.last_app = data.get("last_app")
                    self.action_history = data.get("action_history", [])
                    self.preferences = data.get("preferences", {})
        except Exception:
            pass

    def _save(self):
        """Persist memory to disk."""
        try:
            data = {
                "user_name": self.user_name,
                "last_app": self.last_app,
                "action_history": self.action_history[-self.max_history:],
                "preferences": self.preferences,
                "last_updated": datetime.datetime.now().isoformat(),
            }
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def store_action(self, action):
        """Store an executed action in history."""
        self.last_action = action

        # Track last opened app
        if action.get("type") == "open_app":
            self.last_app = action.get("app")

        # Add to history with timestamp
        entry = {
            "action": action,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        self.action_history.append(entry)

        # Trim history
        if len(self.action_history) > self.max_history:
            self.action_history = self.action_history[-self.max_history:]

        self._save()

    def get_last_action(self):
        """Get the most recent action."""
        return self.last_action

    def get_last_app(self):
        """Get the most recently opened app name."""
        return self.last_app

    def set_user_name(self, name):
        """Set the user's name."""
        self.user_name = name
        self._save()

    def get_user_name(self):
        """Get the user's name."""
        return self.user_name

    def set_preference(self, key, value):
        """Set a user preference."""
        self.preferences[key] = value
        self._save()

    def get_preference(self, key, default=None):
        """Get a user preference."""
        return self.preferences.get(key, default)

    def get_recent_actions(self, count=5):
        """Get the last N actions from history."""
        return self.action_history[-count:]

    def clear_history(self):
        """Clear action history."""
        self.action_history = []
        self._save()


# ─── Global memory instance ─────────────────────────────────────────────────
memory = Memory()