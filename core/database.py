"""
CHIKU PRO - Supabase Database Manager
Handles connections and CRUD operations for cloud memory.
"""

import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class DatabaseManager:
    def __init__(self):
        self.supabase: Client | None = None
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                print("  [DATABASE] Connected to Supabase successfully!")
            except Exception as e:
                print(f"  [DATABASE] Error connecting to Supabase: {e}")
        else:
            print("  [DATABASE] Warning: Supabase credentials not found in .env")

    # ─── Memories ────────────────────────────────────────────────────────

    def add_memory(self, category: str, content: str):
        if not self.supabase: return False
        try:
            self.supabase.table("memories").insert({"category": category, "content": content}).execute()
            return True
        except Exception as e:
            print(f"  [DB_ERROR] Failed to save memory: {e}")
            return False

    def get_memories(self, category=None):
        if not self.supabase: return []
        try:
            query = self.supabase.table("memories").select("*")
            if category:
                query = query.eq("category", category)
            response = query.order("created_at", desc=True).limit(50).execute()
            return response.data
        except Exception:
            return []

    def get_latest_memory(self, category: str):
        """Helper to get a single latest value for things like preferences/name."""
        mems = self.get_memories(category)
        return mems[0]['content'] if mems else None

    # ─── Chat History ────────────────────────────────────────────────────

    def add_chat_msg(self, role: str, content: str):
        if not self.supabase: return False
        try:
            self.supabase.table("chat_history").insert({"role": role, "content": content}).execute()
            return True
        except Exception:
            return False

    def get_chat_history(self, limit=10):
        if not self.supabase: return []
        try:
            response = self.supabase.table("chat_history").select("*").order("created_at", desc=True).limit(limit).execute()
            return list(reversed(response.data)) # chronological order
        except Exception:
            return []

    # ─── Tasks / Reminders ───────────────────────────────────────────────

    def get_tasks(self, status="pending"):
        if not self.supabase: return []
        try:
            response = self.supabase.table("tasks").select("*").eq("status", status).order("created_at", desc=False).execute()
            return response.data
        except Exception:
            return []

    def add_task(self, title: str, description: str = ""):
        if not self.supabase: return False
        try:
            self.supabase.table("tasks").insert({"title": title, "description": description}).execute()
            return True
        except Exception:
            return False

# Global database instance
db = DatabaseManager()
