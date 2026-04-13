"""
╔══════════════════════════════════════════════════════════════╗
║               CHIKU PRO - AI Desktop Companion              ║
║          Voice-controlled Windows AI Assistant               ║ 
║                                                              ║
║  Features:                                                   ║
║  • 🔐 Face Lock + PIN/Password multi-factor auth             ║
║  • Voice recognition (mic) + keyboard fallback               ║
║  • LLM-powered command parsing (OpenAI/Gemini/Ollama)        ║
║  • App open/close, web search, volume control                ║
║  • Camera with face & hand detection (MediaPipe)             ║
║  • Screenshot, system info, shell commands                   ║
║  • Risk analysis & action logging                            ║
║  • Persistent memory across sessions                         ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from core.executor import execute_action, execute_action_async
from core.brain import parse_user_input
from core.voice import listen, speak, speak_done
from core.memory import memory
from core.vision import vision
from core.auth import auth_system


# ─── Banner ──────────────────────────────────────────────────────────────────
BANNER = r"""
   ██████╗██╗  ██╗██╗██╗  ██╗██╗   ██╗    ██████╗ ██████╗  ██████╗ 
  ██╔════╝██║  ██║██║██║ ██╔╝██║   ██║    ██╔══██╗██╔══██╗██╔═══██╗
  ██║     ███████║██║█████╔╝ ██║   ██║    ██████╔╝██████╔╝██║   ██║
  ██║     ██╔══██║██║██╔═██╗ ██║   ██║    ██╔═══╝ ██╔══██╗██║   ██║
  ╚██████╗██║  ██║██║██║  ██╗╚██████╔╝    ██║     ██║  ██║╚██████╔╝
   ╚═════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝
                    AI Desktop Companion v2.0          
"""

# ─── Special Commands (handled before LLM parsing) ──────────────────────────
EXIT_COMMANDS = {"exit", "quit", "stop", "bye", "shutdown chiku", "band karo"}
HELP_TEXT = """
╔══════════════════════════════════════════════════════════════╗
║                    CHIKU PRO — COMMANDS                     ║
╠══════════════════════════════════════════════════════════════╣
║  🚀 App Control:                                            ║
║     "open chrome"  "open notepad"  "open spotify"           ║
║     "close chrome"  "close notepad"                         ║
║                                                              ║
║  🌐 Web:                                                     ║
║     "open google.com"  "search for Python tutorials"        ║
║                                                              ║
║  🔊 Volume:                                                  ║
║     "volume 50"  "mute"  "full volume"  "volume up"         ║
║                                                              ║
║  📷 Camera:                                                  ║
║     "camera on"  "camera off"  "start camera"               ║
║                                                              ║
║  🖥️ System:                                                  ║
║     "screenshot"  "system info"  "type hello world"         ║
║                                                              ║
║  ⚡ Shell:                                                    ║
║     "run command dir"  "shell ipconfig"                      ║
║                                                              ║
║  🔐 Security:                                                ║
║     "security status"  "change pin"  "change password"      ║
║     "re-enroll face"  "update face"  "reset security"       ║
║                                                              ║
║  💬 Chat:                                                     ║
║     Just talk naturally — CHIKU will try to help!            ║
║                                                              ║
║  🛑 Exit:                                                     ║
║     "exit"  "quit"  "stop"  "bye"                            ║
╚══════════════════════════════════════════════════════════════╝
"""

# ─── Security Commands ──────────────────────────────────────────────────────
SECURITY_COMMANDS = {
    "security status", "security", "lock status", "auth status",
    "change pin", "change my pin", "update pin",
    "change password", "change my password", "update password",
    "re-enroll face", "reenroll face", "reset face", "enroll face again",
    "update face", "add face samples", "improve face",
    "reset security", "factory reset security", "remove all locks",
    "change lock", "change security", "change auth mode",
}


def handle_security_command(command):
    """Handle security-related commands."""
    cmd = command.strip().lower()

    # Status
    if cmd in {"security status", "security", "lock status", "auth status"}:
        print(f"\n{'='*50}")
        print("  🔐 SECURITY STATUS")
        print(f"{'='*50}")
        print(auth_system.get_status())
        print(f"{'='*50}\n")
        speak("Here is your security status.")
        return True

    # Change PIN
    if cmd in {"change pin", "change my pin", "update pin"}:
        if auth_system.pin_hash:
            auth_system.change_pin()
        else:
            print("  ⚠️ No PIN is set. Setting up a new PIN...")
            auth_system._setup_pin()
            auth_system._save_config()
        speak("PIN updated.")
        return True

    # Change Password
    if cmd in {"change password", "change my password", "update password"}:
        if auth_system.password_hash:
            auth_system.change_password()
        else:
            print("  ⚠️ No password is set. Setting up a new password...")
            auth_system._setup_password()
            auth_system._save_config()
        speak("Password updated.")
        return True

    # Re-enroll Face
    if cmd in {"re-enroll face", "reenroll face", "reset face", "enroll face again"}:
        speak("Starting face re-enrollment.")
        auth_system.re_enroll_face()
        return True

    # Update Face (add more samples)
    if cmd in {"update face", "add face samples", "improve face"}:
        speak("Adding more face samples for better recognition.")
        auth_system.update_face()
        return True

    # Reset All Security
    if cmd in {"reset security", "factory reset security", "remove all locks"}:
        confirm = input("  ⚠️ This will DELETE all security data. Type 'yes' to confirm: ").strip()
        if confirm.lower() == "yes":
            auth_system.reset_all()
            speak("All security has been reset.")
        else:
            speak("Reset cancelled.")
        return True

    # Change Auth Mode
    if cmd in {"change lock", "change security", "change auth mode"}:
        auth_system.change_auth_mode()
        return True

    return False


def greet_user():
    """Personalized greeting based on time of day and memory."""
    import datetime
    hour = datetime.datetime.now().hour

    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    elif hour < 21:
        greeting = "Good evening"
    else:
        greeting = "Hey there"

    # Use auth system owner name first, then memory
    name = auth_system.owner_name or memory.get_user_name()
    if name:
        greeting += f", {name}"

    greeting += "! CHIKU Pro is ready. How can I help you?"
    return greeting


def main():
    """Main entry point for CHIKU PRO."""
    print(BANNER)
    print("=" * 62)

    # ─── AUTHENTICATION ─────────────────────────────────────────────────
    if not auth_system.is_setup_done:
        # First time — run security setup
        print("\n  🆕 First time running CHIKU PRO!")
        print("  Let's set up your security.\n")
        auth_system.first_time_setup()

        # Sync name to memory
        if auth_system.owner_name:
            memory.set_user_name(auth_system.owner_name)
    else:
        # Returning user — authenticate
        authenticated = auth_system.authenticate()
        if not authenticated:
            print("\n  🚫 Authentication failed. CHIKU cannot start.")
            speak("Authentication failed. Access denied.")
            sys.exit(1)

    # ─── POST-AUTH: GREET & START ────────────────────────────────────────
    greeting = greet_user()
    speak(greeting)

    print("\n💡 Type 'help' to see all commands.")
    print("💡 Say 'exit' or 'quit' to stop.\n")

    # ─── Main Loop ───────────────────────────────────────────────────────
    while True:
        try:
            user_input = listen()

            if not user_input:
                time.sleep(0.5)
                continue

            # ── Special: Exit ────────────────────────────────────────────
            if user_input.strip().lower() in EXIT_COMMANDS:
                speak("Goodbye! Shutting down CHIKU Pro.")
                vision.stop()
                break

            # ── Special: Help ────────────────────────────────────────────
            if user_input.strip().lower() in {"help", "commands", "what can you do"}:
                print(HELP_TEXT)
                speak("Here are the things I can do. Check the screen.")
                continue

            # ── Special: Security Commands ───────────────────────────────
            if user_input.strip().lower() in SECURITY_COMMANDS:
                handle_security_command(user_input)
                continue

            # ── Special: History ─────────────────────────────────────────
            if user_input.strip().lower() in {"history", "recent", "what did i do"}:
                recent = memory.get_recent_actions(5)
                if recent:
                    print("\n📜 Recent Actions:")
                    for entry in recent:
                        action = entry.get("action", {})
                        ts = entry.get("timestamp", "")
                        print(f"  [{ts}] {action.get('type', '?')}: {action}")
                    speak("Here are your recent actions.")
                else:
                    speak("No recent actions found.")
                continue

            # ── Parse and Execute ────────────────────────────────────────
            actions = parse_user_input(user_input)

            if not actions:
                speak("Sorry, I didn't understand that. Try 'help' for commands.")
                continue

            for action in actions:
                def _on_done(result, act=action):
                    if result:
                        print(f"  → {result}")
                    memory.store_action(act)

                execute_action_async(action, callback=_on_done)

        except KeyboardInterrupt:
            print("\n\n⚡ Keyboard interrupt detected.")
            speak("Shutting down.")
            vision.stop()
            break

        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            time.sleep(1)

    print("\n" + "=" * 62)
    print("  CHIKU PRO shutdown complete. See you next time! 👋")
    print("=" * 62)


if __name__ == "__main__":
    main()