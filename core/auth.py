"""
CHIKU PRO - Authentication Module
Multi-factor authentication combining face lock with PIN/password.
Handles first-time setup, login, and security preferences.
"""

import os
import json
import hashlib
import getpass
import time

from core.face_lock import face_lock

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_CONFIG_PATH = os.path.join(BASE_DIR, "face_data", "auth_config.json")


class AuthSystem:
    """
    Multi-factor authentication for CHIKU PRO.
    
    Supported auth methods:
    - face_only:      Face recognition only
    - pin_only:       PIN code only
    - password_only:  Password only
    - face_and_pin:   Face + PIN (both required)
    - face_and_password: Face + Password (both required)
    - face_or_pin:    Face OR PIN (either works)
    - none:           No authentication
    """

    VALID_MODES = [
        "face_only",
        "pin_only",
        "password_only",
        "face_and_pin",
        "face_and_password",
        "face_or_pin",
        "none",
    ]

    def __init__(self):
        self.auth_mode = "none"
        self.pin_hash = None
        self.password_hash = None
        self.owner_name = None
        self.max_attempts = 3
        self.lockout_seconds = 30
        self.is_setup_done = False
        self._load_config()

    def _hash(self, text):
        """Create a SHA-256 hash of the given text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _load_config(self):
        """Load auth configuration from disk."""
        try:
            if os.path.exists(AUTH_CONFIG_PATH):
                with open(AUTH_CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
                self.auth_mode = config.get("auth_mode", "none")
                self.pin_hash = config.get("pin_hash")
                self.password_hash = config.get("password_hash")
                self.owner_name = config.get("owner_name")
                self.max_attempts = config.get("max_attempts", 3)
                self.lockout_seconds = config.get("lockout_seconds", 30)
                self.is_setup_done = config.get("is_setup_done", False)
        except Exception as e:
            print(f"⚠️ Could not load auth config: {e}")

    def _save_config(self):
        """Save auth configuration to disk."""
        try:
            os.makedirs(os.path.dirname(AUTH_CONFIG_PATH), exist_ok=True)
            config = {
                "auth_mode": self.auth_mode,
                "pin_hash": self.pin_hash,
                "password_hash": self.password_hash,
                "owner_name": self.owner_name,
                "max_attempts": self.max_attempts,
                "lockout_seconds": self.lockout_seconds,
                "is_setup_done": self.is_setup_done,
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open(AUTH_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Could not save auth config: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────────
    # FIRST-TIME SETUP
    # ─────────────────────────────────────────────────────────────────────

    def first_time_setup(self):
        """
        Interactive first-time security setup.
        Walks the user through choosing auth mode, enrolling face, setting PIN, etc.
        """
        print(f"\n{'='*58}")
        print("  🔐 CHIKU PRO — SECURITY SETUP")
        print(f"{'='*58}")

        # Get owner name
        name = input("\n  👤 What's your name? ").strip()
        if not name:
            name = "Boss"
        self.owner_name = name

        print(f"\n  Hey {name}! Let's set up your security.\n")
        print("  Choose your lock mode:\n")
        print("  [1] 🔒 Face Lock Only")
        print("  [2] 🔢 PIN Only")
        print("  [3] 🔑 Password Only")
        print("  [4] 🔒+🔢 Face + PIN (Most Secure)")
        print("  [5] 🔒+🔑 Face + Password")
        print("  [6] 🔒|🔢 Face OR PIN (Convenient)")
        print("  [7] 🚫 No Lock (Skip)")

        mode_map = {
            "1": "face_only",
            "2": "pin_only",
            "3": "password_only",
            "4": "face_and_pin",
            "5": "face_and_password",
            "6": "face_or_pin",
            "7": "none",
        }

        while True:
            choice = input("\n  Enter choice (1-7): ").strip()
            if choice in mode_map:
                self.auth_mode = mode_map[choice]
                break
            print("  ❌ Invalid choice. Enter 1-7.")

        # ── Set up face if needed ────────────────────────────────────────
        needs_face = self.auth_mode in ["face_only", "face_and_pin", "face_and_password", "face_or_pin"]
        if needs_face:
            print("\n  📸 Setting up Face Lock...\n")
            success = face_lock.enroll(owner_name=self.owner_name)
            if not success:
                print("  ⚠️ Face enrollment failed.")
                if self.auth_mode == "face_only":
                    print("  Falling back to PIN mode.")
                    self.auth_mode = "pin_only"
                elif self.auth_mode in ["face_and_pin", "face_or_pin"]:
                    print("  Will use PIN only.")
                    self.auth_mode = "pin_only"
                elif self.auth_mode == "face_and_password":
                    print("  Will use Password only.")
                    self.auth_mode = "password_only"

        # ── Set up PIN if needed ─────────────────────────────────────────
        needs_pin = self.auth_mode in ["pin_only", "face_and_pin", "face_or_pin"]
        if needs_pin:
            print("\n  🔢 Setting up PIN...")
            self._setup_pin()

        # ── Set up Password if needed ────────────────────────────────────
        needs_password = self.auth_mode in ["password_only", "face_and_password"]
        if needs_password:
            print("\n  🔑 Setting up Password...")
            self._setup_password()

        # ── Done ─────────────────────────────────────────────────────────
        self.is_setup_done = True
        self._save_config()

        mode_names = {
            "face_only": "🔒 Face Lock",
            "pin_only": "🔢 PIN Lock",
            "password_only": "🔑 Password Lock",
            "face_and_pin": "🔒+🔢 Face + PIN",
            "face_and_password": "🔒+🔑 Face + Password",
            "face_or_pin": "🔒|🔢 Face or PIN",
            "none": "🚫 No Lock",
        }

        print(f"\n  ✅ Security configured: {mode_names.get(self.auth_mode, self.auth_mode)}")
        print(f"{'='*58}\n")
        return True

    def _setup_pin(self):
        """Set up a PIN code."""
        while True:
            pin = input("  Enter a 4-6 digit PIN: ").strip()
            if pin.isdigit() and 4 <= len(pin) <= 6:
                confirm = input("  Confirm PIN: ").strip()
                if pin == confirm:
                    self.pin_hash = self._hash(pin)
                    print("  ✅ PIN set successfully!")
                    return
                else:
                    print("  ❌ PINs don't match. Try again.")
            else:
                print("  ❌ PIN must be 4-6 digits.")

    def _setup_password(self):
        """Set up a password."""
        while True:
            password = input("  Enter a password (min 6 chars): ").strip()
            if len(password) >= 6:
                confirm = input("  Confirm password: ").strip()
                if password == confirm:
                    self.password_hash = self._hash(password)
                    print("  ✅ Password set successfully!")
                    return
                else:
                    print("  ❌ Passwords don't match. Try again.")
            else:
                print("  ❌ Password must be at least 6 characters.")

    # ─────────────────────────────────────────────────────────────────────
    # AUTHENTICATION (LOGIN)
    # ─────────────────────────────────────────────────────────────────────

    def authenticate(self):
        """
        Run the full authentication flow based on configured mode.
        Returns True if authentication is successful, False otherwise.
        """
        if self.auth_mode == "none":
            return True

        if not self.is_setup_done:
            return self.first_time_setup()

        print(f"\n{'='*58}")
        print("  🔐 CHIKU PRO — AUTHENTICATION")
        print(f"{'='*58}")

        attempts = 0

        while attempts < self.max_attempts:
            attempts += 1
            remaining = self.max_attempts - attempts

            print(f"\n  Attempt {attempts}/{self.max_attempts}")

            success = False

            if self.auth_mode == "face_only":
                success = self._verify_face()

            elif self.auth_mode == "pin_only":
                success = self._verify_pin()

            elif self.auth_mode == "password_only":
                success = self._verify_password()

            elif self.auth_mode == "face_and_pin":
                # Both required
                face_ok = self._verify_face()
                if face_ok:
                    pin_ok = self._verify_pin()
                    success = pin_ok
                else:
                    print("  ❌ Face verification failed. PIN not prompted.")

            elif self.auth_mode == "face_and_password":
                # Both required
                face_ok = self._verify_face()
                if face_ok:
                    pw_ok = self._verify_password()
                    success = pw_ok
                else:
                    print("  ❌ Face verification failed. Password not prompted.")

            elif self.auth_mode == "face_or_pin":
                # Either works
                print("  Choose method:")
                print("  [1] 🔒 Face")
                print("  [2] 🔢 PIN")
                method = input("  Enter 1 or 2: ").strip()

                if method == "1":
                    success = self._verify_face()
                    if not success:
                        print("  💡 Try PIN instead?")
                        retry = input("  Use PIN? (y/n): ").strip().lower()
                        if retry == "y":
                            success = self._verify_pin()
                elif method == "2":
                    success = self._verify_pin()
                else:
                    print("  ❌ Invalid choice.")

            if success:
                print(f"\n  ✅ Welcome back, {self.owner_name}! 🎉")
                print(f"{'='*58}\n")
                return True
            else:
                if remaining > 0:
                    print(f"  ❌ Authentication failed. {remaining} attempt(s) remaining.")
                else:
                    print(f"\n  🚫 Max attempts reached!")

        # Lockout
        print(f"  ⏳ Locked out for {self.lockout_seconds} seconds...")
        time.sleep(self.lockout_seconds)
        print("  🔓 Lockout expired. Try again later.")
        return False

    def _verify_face(self):
        """Verify face recognition."""
        print("  📸 Starting face verification...")
        success, confidence = face_lock.verify(timeout=RECOGNITION_TIMEOUT_AUTH)
        return success

    def _verify_pin(self):
        """Verify PIN code."""
        pin = input("  🔢 Enter PIN: ").strip()
        if self.pin_hash and self._hash(pin) == self.pin_hash:
            return True
        print("  ❌ Wrong PIN.")
        return False

    def _verify_password(self):
        """Verify password."""
        password = input("  🔑 Enter password: ").strip()
        if self.password_hash and self._hash(password) == self.password_hash:
            return True
        print("  ❌ Wrong password.")
        return False

    # ─────────────────────────────────────────────────────────────────────
    # MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────

    def change_pin(self):
        """Change the PIN code (requires current PIN first)."""
        if not self._verify_pin():
            print("  ❌ Cannot change PIN — current PIN incorrect.")
            return False
        self._setup_pin()
        self._save_config()
        return True

    def change_password(self):
        """Change the password (requires current password first)."""
        if not self._verify_password():
            print("  ❌ Cannot change password — current password incorrect.")
            return False
        self._setup_password()
        self._save_config()
        return True

    def re_enroll_face(self):
        """Re-enroll face (deletes old data and starts fresh)."""
        face_lock.reset()
        success = face_lock.enroll(owner_name=self.owner_name)
        if success:
            self._save_config()
        return success

    def update_face(self):
        """Add more face samples to improve recognition."""
        return face_lock.update()

    def change_auth_mode(self):
        """Run setup again to change auth mode."""
        return self.first_time_setup()

    def reset_all(self):
        """Factory reset — delete all auth data."""
        try:
            face_lock.reset()
            if os.path.exists(AUTH_CONFIG_PATH):
                os.remove(AUTH_CONFIG_PATH)
            self.auth_mode = "none"
            self.pin_hash = None
            self.password_hash = None
            self.is_setup_done = False
            print("  ✅ All security data has been reset.")
            return True
        except Exception as e:
            print(f"  ❌ Reset failed: {e}")
            return False

    def get_status(self):
        """Get current auth status as a string."""
        mode_names = {
            "face_only": "🔒 Face Lock",
            "pin_only": "🔢 PIN Lock",
            "password_only": "🔑 Password Lock",
            "face_and_pin": "🔒+🔢 Face + PIN",
            "face_and_password": "🔒+🔑 Face + Password",
            "face_or_pin": "🔒|🔢 Face or PIN",
            "none": "🚫 No Lock",
        }
        mode_str = mode_names.get(self.auth_mode, self.auth_mode)
        face_status = "Enrolled ✅" if face_lock.is_enrolled else "Not enrolled ❌"
        pin_status = "Set ✅" if self.pin_hash else "Not set ❌"
        pw_status = "Set ✅" if self.password_hash else "Not set ❌"

        return (
            f"  Mode: {mode_str}\n"
            f"  Face: {face_status}\n"
            f"  PIN:  {pin_status}\n"
            f"  Password: {pw_status}\n"
            f"  Owner: {self.owner_name or 'Not set'}"
        )


# ─── Constants ───────────────────────────────────────────────────────────────
RECOGNITION_TIMEOUT_AUTH = 12  # Seconds for face verification during login

# ─── Global auth instance ───────────────────────────────────────────────────
auth_system = AuthSystem()
