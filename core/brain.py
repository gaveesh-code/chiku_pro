"""
CHIKU PRO - Brain Module
Intelligent command parser using LLM (with offline fallback).
Converts natural language into structured action dicts.
"""

import json
import re
from core.llm_router import get_llm_response


# ─── LLM System Prompt ──────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are CHIKU's brain — an AI command parser for a Windows desktop assistant.

Your job: Convert the user's natural language command into a JSON array of action objects.

Available action types and their parameters:

1. {"type": "open_app", "app": "<app_name>"}
   - Open desktop applications (chrome, notepad, vscode, spotify, discord, calculator, paint, edge, cmd, powershell, telegram, etc.)

2. {"type": "open_url", "url": "<full_url>"}
   - Open a website URL in the browser

3. {"type": "search_web", "query": "<search_query>"}
   - Search the web for something

4. {"type": "volume", "level": <0-100>}
   - Set system volume to a percentage

5. {"type": "camera_on"}
   - Start/enable the camera/vision system

6. {"type": "camera_off"}
   - Stop/disable the camera/vision system

7. {"type": "shell_command", "command": "<windows_command>"}
   - Execute a Windows shell command (cmd/powershell)

8. {"type": "type_text", "text": "<text_to_type>"}
   - Type text on screen using keyboard automation

9. {"type": "screenshot"}
   - Take a screenshot

10. {"type": "system_info"}
    - Show system information (RAM, CPU, disk, etc.)

11. {"type": "close_app", "app": "<app_name>"}
    - Close/kill a running application

12. {"type": "chat", "message": "<response_text>"}
    - For general conversation or questions — respond naturally

Rules:
- ALWAYS return a valid JSON array, even for single actions: [{"type": "..."}]
- For compound commands (e.g., "open chrome and notepad"), return multiple actions in the array.
- If the user is just chatting or asking a question, use the "chat" type with a natural response.
- For "mute", set volume to 0. For "full volume" or "max volume", set to 100.
- "volume up" means +10 from current (use 60 as default). "volume down" means -10 (use 40).
- Do NOT add any explanation, just the JSON array.
"""


# ─── Offline Keyword Fallback Parser ─────────────────────────────────────────
def _offline_parse(text):
    """Keyword-based parser when LLM is unavailable."""
    text = text.lower().strip()
    actions = []

    # ── App Opening ──────────────────────────────────────────────────────
    app_keywords = {
        "chrome": "chrome", "google chrome": "chrome", "browser": "chrome",
        "notepad": "notepad", "note pad": "notepad",
        "vs code": "code", "vscode": "code", "visual studio code": "code",
        "spotify": "spotify", "music": "spotify",
        "discord": "discord",
        "telegram": "telegram",
        "calculator": "calc", "calc": "calc",
        "paint": "mspaint",
        "edge": "msedge", "microsoft edge": "msedge",
        "cmd": "cmd", "command prompt": "cmd", "terminal": "cmd",
        "powershell": "powershell",
        "file explorer": "explorer", "explorer": "explorer", "files": "explorer",
        "task manager": "taskmgr",
        "settings": "ms-settings:",
        "control panel": "control",
    }

    # Check for "close" / "kill" / "stop" commands
    close_match = re.search(r"(?:close|kill|stop|exit|quit)\s+(.+)", text)
    if close_match:
        target = close_match.group(1).strip()
        for keyword, app in app_keywords.items():
            if keyword in target:
                actions.append({"type": "close_app", "app": app})
                return actions
        actions.append({"type": "close_app", "app": target})
        return actions

    # Check for "open" commands
    open_match = re.search(r"(?:open|launch|start|run)\s+(.+)", text)
    if open_match:
        target = open_match.group(1).strip()

        # Is it a URL?
        if "." in target and " " not in target:
            url = target if target.startswith("http") else f"https://{target}"
            actions.append({"type": "open_url", "url": url})
            return actions

        for keyword, app in app_keywords.items():
            if keyword in target:
                actions.append({"type": "open_app", "app": app})
                return actions

        # Unknown app — try anyway
        actions.append({"type": "open_app", "app": target})
        return actions

    # ── Web Search ───────────────────────────────────────────────────────
    search_match = re.search(r"(?:search|google|look up|find)\s+(?:for\s+)?(.+)", text)
    if search_match:
        query = search_match.group(1).strip()
        actions.append({"type": "search_web", "query": query})
        return actions

    # ── Volume ───────────────────────────────────────────────────────────
    if "mute" in text:
        actions.append({"type": "volume", "level": 0})
        return actions

    if "full volume" in text or "max volume" in text:
        actions.append({"type": "volume", "level": 100})
        return actions

    if "volume up" in text:
        actions.append({"type": "volume", "level": 60})
        return actions

    if "volume down" in text:
        actions.append({"type": "volume", "level": 40})
        return actions

    vol_match = re.search(r"(?:volume|vol)\s*(?:to|at|set)?\s*(\d+)", text)
    if vol_match:
        actions.append({"type": "volume", "level": int(vol_match.group(1))})
        return actions

    # Also match: "set volume to 50" / "50 percent volume"
    vol_match2 = re.search(r"(\d+)\s*(?:percent|%)?\s*volume", text)
    if vol_match2:
        actions.append({"type": "volume", "level": int(vol_match2.group(1))})
        return actions

    # ── Camera ───────────────────────────────────────────────────────────
    if any(kw in text for kw in ["camera on", "start camera", "enable camera", "vision on"]):
        actions.append({"type": "camera_on"})
        return actions

    if any(kw in text for kw in ["camera off", "stop camera", "disable camera", "vision off"]):
        actions.append({"type": "camera_off"})
        return actions

    # ── Screenshot ───────────────────────────────────────────────────────
    if "screenshot" in text or "screen shot" in text or "capture screen" in text:
        actions.append({"type": "screenshot"})
        return actions

    # ── System Info ──────────────────────────────────────────────────────
    if any(kw in text for kw in ["system info", "system status", "how much ram",
                                   "cpu usage", "battery", "disk space"]):
        actions.append({"type": "system_info"})
        return actions

    # ── Type Text ────────────────────────────────────────────────────────
    type_match = re.search(r"(?:type|write|enter)\s+['\"]?(.+?)['\"]?\s*$", text)
    if type_match and not any(kw in text for kw in ["open", "search", "volume"]):
        actions.append({"type": "type_text", "text": type_match.group(1)})
        return actions

    # ── Shell Command ────────────────────────────────────────────────────
    shell_match = re.search(r"(?:execute|run command|shell)\s+(.+)", text)
    if shell_match:
        actions.append({"type": "shell_command", "command": shell_match.group(1)})
        return actions

    # ── Fallback: treat as chat ──────────────────────────────────────────
    if text:
        actions.append({"type": "chat", "message": f"I heard: '{text}'. I'm not sure what to do with that yet."})

    return actions


# ─── Main Parser ─────────────────────────────────────────────────────────────
def parse_user_input(user_input):
    """
    Parse user's natural language input into a list of action dicts.
    Uses LLM if available, falls back to keyword matching.
    """
    if not user_input or not user_input.strip():
        return []

    user_input = user_input.strip()

    # Try LLM first
    try:
        prompt = f"User command: {user_input}"
        llm_response = get_llm_response(prompt, system_prompt=SYSTEM_PROMPT)

        if llm_response:
            # Extract JSON from the response (handle markdown code blocks)
            json_str = llm_response.strip()

            # Remove markdown code fences if present
            if "```" in json_str:
                match = re.search(r"```(?:json)?\s*(.*?)```", json_str, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()

            actions = json.loads(json_str)

            if isinstance(actions, list) and len(actions) > 0:
                # Validate each action has a 'type' key
                valid = all(isinstance(a, dict) and "type" in a for a in actions)
                if valid:
                    return actions

    except (json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"⚠️  LLM response parse error: {e}")
    except Exception as e:
        print(f"⚠️  LLM error: {e}")

    # Fallback to offline keyword parser
    return _offline_parse(user_input)