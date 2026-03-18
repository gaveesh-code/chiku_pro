"""
CHIKU PRO - Volume Control Module
Sets the Windows system volume using nircmd.exe or pycaw fallback.
"""

import subprocess
import os


def set_volume(level):
    """
    Set the system volume to a percentage (0-100).
    Uses nircmd.exe (bundled) or pycaw as fallback.
    """
    # Validate input
    try:
        level = int(level)
    except (ValueError, TypeError):
        return "❌ Invalid volume value. Must be a number."

    level = max(0, min(100, level))

    # Method 1: Try nircmd.exe (bundled in tools/)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    nircmd_path = os.path.join(current_dir, "tools", "nircmd.exe")

    if os.path.isfile(nircmd_path):
        try:
            volume_value = int((level / 100) * 65535)
            subprocess.run(
                [nircmd_path, "setsysvolume", str(volume_value)],
                check=True,
                capture_output=True,
            )
            return f"🔊 Volume set to {level}%"
        except subprocess.CalledProcessError as e:
            print(f"⚠️ nircmd failed: {e}")

    # Method 2: Try pycaw (Python audio control)
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        # pycaw uses scalar 0.0 to 1.0
        scalar = level / 100.0
        volume.SetMasterVolumeLevelScalar(scalar, None)

        return f"🔊 Volume set to {level}%"

    except ImportError:
        pass
    except Exception as e:
        print(f"⚠️ pycaw error: {e}")

    # Method 3: PowerShell fallback
    try:
        ps_command = (
            f'$vol = [Audio.Volume]::New(); '
            f'(New-Object -ComObject WScript.Shell).SendKeys([char]173); '
            f'Start-Sleep -Milliseconds 100'
        )
        # Simple PowerShell volume set via nircmd download or key simulation
        # This is a last resort
        subprocess.run(
            ["powershell", "-Command",
             f"$wshell = New-Object -ComObject wscript.shell; "
             f"1..50 | ForEach-Object {{ $wshell.SendKeys([char]174) }}; "  # Vol down 50 times
             f"1..{level // 2} | ForEach-Object {{ $wshell.SendKeys([char]175) }}"],  # Vol up to target
            capture_output=True,
            timeout=15,
        )
        return f"🔊 Volume approximately set to {level}%"

    except Exception as e:
        return f"❌ Could not set volume: {e}"