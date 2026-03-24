"""
CHIKU PRO - Memory Module
Stores conversation history, last actions, user preferences, and context.
Persists to a JSON file for cross-session memory.
"""

import json
import os
import datetime

MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chiku_memory.json")


from core.database import db

class Memory:
    def __init__(self):
        self.last_action = None
        self.last_app = None
        self.action_history = []        # Recent action log (session only)
        self.max_history = 50           # Keep last 50 actions

    # We do not use _save and _load anymore because DB is remote
    # We map preferences and user_name directly to db.add_memory

    def store_action(self, action):
        """Store an executed action in history (Session only, not DB)."""
        self.last_action = action

        # Track last opened app
        if action.get("type") == "open_app":
            self.last_app = action.get("app")

        # Add to history with timestamp
        import datetime
        entry = {
            "action": action,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        self.action_history.append(entry)

        # Trim history
        if len(self.action_history) > self.max_history:
            self.action_history = self.action_history[-self.max_history:]

    def get_last_action(self):
        """Get the most recent action."""
        return self.last_action

    def get_last_app(self):
        """Get the most recently opened app name."""
        return self.last_app

    def set_user_name(self, name):
        """Set the user's name (Saved to Supabase)."""
        db.add_memory("user_name", name)

    def get_user_name(self):
        """Get the user's name from Supabase."""
        return db.get_latest_memory("user_name")

    def set_preference(self, key, value):
        """Set a user preference in Supabase."""
        # Convert any values to string since DB content is TEXT
        db.add_memory(f"preference_{key}", str(value))

    def get_preference(self, key, default=None):
        """Get a user preference from Supabase."""
        val = db.get_latest_memory(f"preference_{key}")
        return val if val is not None else default

    def get_recent_actions(self, count=5):
        """Get the last N actions from history (session)."""
        return self.action_history[-count:]

    def clear_history(self):
        """Clear action history."""
        self.action_history = []


# ─── Global memory instance ─────────────────────────────────────────────────
memory = Memory()