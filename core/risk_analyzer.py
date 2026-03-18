"""
CHIKU PRO - Risk Analyzer
Analyzes commands for potential danger levels before execution.
"""

# ─── Dangerous Keywords ──────────────────────────────────────────────────────

HIGH_RISK_KEYWORDS = [
    "format",
    "del /",
    "del \\",
    "rmdir",
    "rd /s",
    "diskpart",
    "shutdown",
    "restart",
    "reg delete",
    "reg add",
    "powershell -encodedcommand",
    "net user",
    "net localgroup",
    "cipher /w",
    "bcdedit",
    "sfc /scannow",
    "bootrec",
    "wmic os",
    "format c:",
    "rm -rf",
    ":(){",            # Fork bomb pattern
    ":(){ :|:& };:",   # Fork bomb
]

MEDIUM_RISK_KEYWORDS = [
    "taskkill",
    "netsh",
    "sc stop",
    "sc delete",
    "sc config",
    "wmic",
    "icacls",
    "takeown",
    "attrib",
    "netstat",
    "ipconfig /release",
    "net stop",
    "net start",
    "reg query",
]

LOW_RISK_KEYWORDS = [
    "dir",
    "echo",
    "type",
    "cls",
    "ping",
    "ipconfig",
    "systeminfo",
    "hostname",
    "whoami",
    "set",
    "ver",
    "time",
    "date",
]


def analyze_risk(command):
    """
    Analyze a command string and return its risk level.
    Returns: 'HIGH', 'MEDIUM', or 'LOW'
    """
    if not command:
        return "LOW"

    cmd_lower = command.lower().strip()

    # Check HIGH risk first
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in cmd_lower:
            return "HIGH"

    # Check MEDIUM risk
    for keyword in MEDIUM_RISK_KEYWORDS:
        if keyword in cmd_lower:
            return "MEDIUM"

    return "LOW"


def is_safe(command):
    """Quick check if a command is safe to execute."""
    return analyze_risk(command) != "HIGH"


def get_risk_description(risk_level):
    """Get a human-readable description of the risk level."""
    descriptions = {
        "HIGH": "⛔ DANGEROUS — This command could damage your system or delete important data.",
        "MEDIUM": "⚠️ CAUTION — This command modifies system settings. Proceed carefully.",
        "LOW": "✅ SAFE — This command is safe to execute.",
    }
    return descriptions.get(risk_level, "Unknown risk level.")