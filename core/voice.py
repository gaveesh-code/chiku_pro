"""
CHIKU PRO - Voice Module
Handles speech recognition (microphone input) and text-to-speech output.
Falls back to keyboard input if microphone is unavailable.
"""

import pyttsx3
import threading

# ─── TTS Engine (text-to-speech) ─────────────────────────────────────────────
_engine = pyttsx3.init()
_engine_lock = threading.Lock()

# Configure voice properties
_voices = _engine.getProperty("voices")
if len(_voices) > 1:
    _engine.setProperty("voice", _voices[1].id)  # Female voice if available
_engine.setProperty("rate", 175)   # Speaking speed
_engine.setProperty("volume", 1.0)

# ─── Try importing speech recognition ────────────────────────────────────────
_sr_available = False
try:
    import speech_recognition as sr
    _recognizer = sr.Recognizer()
    _recognizer.energy_threshold = 300
    _recognizer.dynamic_energy_threshold = True
    _recognizer.pause_threshold = 1.0
    _sr_available = True
except ImportError:
    _sr_available = False
    print("[CHIKU] speech_recognition not installed. Using keyboard input.")
    print("[CHIKU] Install it with: pip install SpeechRecognition pyaudio")


def speak(text):
    """Speak the given text aloud and print it to the console."""
    print(f"🤖 CHIKU: {text}")
    with _engine_lock:
        try:
            _engine.say(text)
            _engine.runAndWait()
        except RuntimeError:
            # Engine busy — reinitialize
            pass


def speak_done():
    """Say a short completion message."""
    speak("Done boss.")


def listen():
    """
    Listen for a voice command via microphone.
    Falls back to keyboard input if speech recognition is unavailable.
    Returns the recognized text in lowercase, or None on failure.
    """
    if _sr_available:
        return _listen_mic()
    else:
        return _listen_keyboard()


def _listen_mic():
    """Use the microphone + Google Speech Recognition."""
    global _sr_available
    try:
        with sr.Microphone() as source:
            print("🎤 Listening...")
            _recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = _recognizer.listen(source, timeout=8, phrase_time_limit=10)

        print("⏳ Recognizing...")
        text = _recognizer.recognize_google(audio, language="en-in")
        print(f"🗣️  You said: {text}")
        return text.lower().strip()

    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        print("❌ Could not understand audio.")
        return None
    except sr.RequestError as e:
        print(f"❌ Speech service error: {e}")
        return _listen_keyboard()  # Fallback
    except AttributeError as e:
        if "PyAudio" in str(e):
            print("❌ PyAudio not installed. Switching to keyboard.")
            _sr_available = False
            return _listen_keyboard()
        print(f"❌ Voice error: {e}")
        return None
    except OSError:
        print("❌ Microphone not available. Switching to keyboard.")
        _sr_available = False
        return _listen_keyboard()
    except Exception as e:
        print(f"❌ Voice error: {e}")
        return None


def _listen_keyboard():
    """Fallback: read from keyboard input."""
    try:
        command = input("⌨️  Command: ").strip()
        if command:
            return command.lower()
        return None
    except EOFError:
        return None
    except KeyboardInterrupt:
        raise