"""
CHIKU PRO - Voice Module
Handles speech recognition (microphone input) and text-to-speech output.
Falls back to keyboard input if microphone is unavailable.
Optimized: Vosk offline recognition, async TTS, one-time calibration.
"""

import pyttsx3
import threading
import queue
import os
import json

# ─── TTS Engine (text-to-speech) ─────────────────────────────────────────────
_engine = pyttsx3.init()
_engine_lock = threading.Lock()

# Configure voice properties
_voices = _engine.getProperty("voices")
if len(_voices) > 1:
    _engine.setProperty("voice", _voices[1].id)  # Female voice if available
_engine.setProperty("rate", 185)   # Slightly faster speaking speed
_engine.setProperty("volume", 1.0)

# ─── Async TTS Queue ─────────────────────────────────────────────────────────
_tts_queue = queue.Queue()
_tts_done_event = threading.Event()
_tts_done_event.set()  # Start as "done"


def _tts_worker():
    """Background thread that processes TTS requests from the queue."""
    while True:
        text = _tts_queue.get()
        if text is None:
            break
        _tts_done_event.clear()
        with _engine_lock:
            try:
                _engine.say(text)
                _engine.runAndWait()
            except RuntimeError:
                pass
        _tts_done_event.set()
        _tts_queue.task_done()


_tts_thread = threading.Thread(target=_tts_worker, daemon=True)
_tts_thread.start()


# ─── Try Vosk for OFFLINE recognition (fast, no internet) ───────────────────
_vosk_available = False
_vosk_model = None
_vosk_recognizer = None

try:
    import vosk
    vosk.SetLogLevel(-1)

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _VOSK_MODEL_PATHS = [
        os.path.join(BASE_DIR, "vosk-model-small-en-in-0.4"),
        os.path.join(BASE_DIR, "vosk-model-small-en-us-0.15"),
        os.path.join(BASE_DIR, "vosk-model"),
    ]

    for _mp in _VOSK_MODEL_PATHS:
        if os.path.exists(_mp):
            _vosk_model = vosk.Model(_mp)
            _vosk_available = True
            print(f"[VOICE] ✅ Vosk offline model loaded: {os.path.basename(_mp)}")
            break

    if not _vosk_available:
        print("[VOICE] Vosk model folder not found, will use Google Speech.")
except ImportError:
    print("[VOICE] Vosk not installed, will use Google Speech.")


# ─── Try importing speech recognition (fallback) ────────────────────────────
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

# ─── PyAudio for Vosk direct mic access ──────────────────────────────────────
_pyaudio_available = False
try:
    import pyaudio
    _pyaudio_available = True
except ImportError:
    pass

# ─── One-time microphone calibration (for Google fallback) ───────────────────
_mic_calibrated = False


def _calibrate_mic_once():
    """Calibrate ambient noise once, then skip on subsequent listen calls."""
    global _mic_calibrated
    if _mic_calibrated or not _sr_available:
        return
    try:
        with sr.Microphone() as source:
            _recognizer.adjust_for_ambient_noise(source, duration=0.5)
        _mic_calibrated = True
    except Exception:
        pass


# Run calibration at import time (non-blocking)
threading.Thread(target=_calibrate_mic_once, daemon=True).start()


def speak(text):
    """Speak the given text aloud (async) and print it to the console."""
    print(f"🤖 CHIKU: {text}")
    _tts_queue.put(text)


def speak_sync(text):
    """Speak and block until speech finishes (for auth/critical moments)."""
    print(f"🤖 CHIKU: {text}")
    _tts_queue.put(text)
    _tts_queue.join()  # Wait for the queue to drain


def speak_done():
    """Say a short completion message."""
    speak("Done boss.")


def wait_for_speech():
    """Block until any pending speech finishes."""
    _tts_done_event.wait()


def listen():
    """
    Listen for a voice command via microphone.
    Priority: Vosk (offline, fast) > Google (online) > Keyboard.
    Returns the recognized text in lowercase, or None on failure.
    """
    # Wait for any pending TTS to finish before listening
    _tts_done_event.wait()

    if _vosk_available and _pyaudio_available:
        return _listen_vosk()
    elif _sr_available:
        return _listen_mic()
    else:
        return _listen_keyboard()


# ─── Vosk Offline Listener (FAST — no internet needed) ──────────────────────
_VOSK_SAMPLE_RATE = 16000
_VOSK_CHUNK = 4000  # ~0.25 seconds at 16kHz


def _listen_vosk():
    """Use Vosk for offline speech recognition — instant, no network."""
    pa = None
    stream = None
    try:
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=_VOSK_SAMPLE_RATE,
            input=True,
            frames_per_buffer=_VOSK_CHUNK,
        )
        stream.start_stream()

        rec = vosk.KaldiRecognizer(_vosk_model, _VOSK_SAMPLE_RATE)
        rec.SetWords(False)  # Faster — don't need word-level timestamps

        print("🎤 Listening...")

        silence_chunks = 0
        max_silence = 12  # ~3 seconds of silence → stop
        max_chunks = 60   # ~15 seconds max recording
        heard_speech = False
        total_chunks = 0

        while total_chunks < max_chunks:
            data = stream.read(_VOSK_CHUNK, exception_on_overflow=False)
            total_chunks += 1

            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()
                if text:
                    print(f"🗣️  You said: {text}")
                    return text.lower()
                # Empty result after detecting end of speech
                if heard_speech:
                    break
            else:
                partial = json.loads(rec.PartialResult())
                partial_text = partial.get("partial", "").strip()
                if partial_text:
                    heard_speech = True
                    silence_chunks = 0
                else:
                    if heard_speech:
                        silence_chunks += 1
                        if silence_chunks >= max_silence:
                            # Finalize
                            final = json.loads(rec.FinalResult())
                            text = final.get("text", "").strip()
                            if text:
                                print(f"🗣️  You said: {text}")
                                return text.lower()
                            break

        # Get any remaining
        final = json.loads(rec.FinalResult())
        text = final.get("text", "").strip()
        if text:
            print(f"🗣️  You said: {text}")
            return text.lower()

        return None

    except OSError:
        print("❌ Microphone not available. Switching to keyboard.")
        return _listen_keyboard()
    except Exception as e:
        print(f"❌ Vosk error: {e}")
        # Fall back to Google if Vosk fails
        if _sr_available:
            return _listen_mic()
        return _listen_keyboard()
    finally:
        if stream:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
        if pa:
            try:
                pa.terminate()
            except Exception:
                pass


def _listen_mic():
    """Fallback: Use Google Speech Recognition (needs internet)."""
    global _sr_available
    try:
        with sr.Microphone() as source:
            print("🎤 Listening (Google)...")
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
        return _listen_keyboard()
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