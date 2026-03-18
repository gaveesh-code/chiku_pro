"""
CHIKU PRO - Wake Word Engine
Always-on listener that detects "Hey Chiku" using Vosk (offline).
When the wake word is detected, it triggers command listening mode.
"""

import json
import threading
import time
import os
import sys

# ─── Audio Config ────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000
CHUNK_SIZE = 4000  # ~0.25 seconds of audio at 16kHz

# ─── Wake Word Variants ─────────────────────────────────────────────────────
WAKE_WORDS = [
    "hey chiku",
    "he chiku",
    "a chiku",
    "hey cheeku",
    "hey chicken",   # Common misrecognition
    "hey chico",
    "hey sheeku",
    "hey chiku pro",
    "ok chiku",
    "hi chiku",
    "chiku",
]

# ─── Vosk Model Path ────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATHS = [
    os.path.join(BASE_DIR, "vosk-model-small-en-in-0.4"),
    os.path.join(BASE_DIR, "vosk-model-small-en-us-0.15"),
    os.path.join(BASE_DIR, "vosk-model"),
]

# ─── Imports ─────────────────────────────────────────────────────────────────
_vosk_available = False
_pyaudio_available = False

try:
    import vosk
    vosk.SetLogLevel(-1)  # Suppress Vosk logs
    _vosk_available = True
except ImportError:
    pass

try:
    import pyaudio
    _pyaudio_available = True
except ImportError:
    pass

# Fallback: try sounddevice
_sd_available = False
if not _pyaudio_available:
    try:
        import sounddevice as sd
        _sd_available = True
    except ImportError:
        pass


class WakeWordEngine:
    """
    Continuously listens for the wake word "Hey Chiku" in the background.
    Uses Vosk for offline speech recognition — no internet needed.
    Falls back to Google Speech Recognition if Vosk unavailable.
    """

    def __init__(self):
        self.listening = False
        self.thread = None
        self.wake_callback = None  # Called when wake word detected
        self.model = None
        self.recognizer = None
        self._stop_event = threading.Event()
        self._paused = False

        # State
        self.last_wake_time = 0
        self.cooldown = 2  # Seconds between wake detections

        # Load Vosk model
        self._load_model()

    def _load_model(self):
        """Load the Vosk speech recognition model."""
        if not _vosk_available:
            print("[WakeWord] Vosk not available. Install: pip install vosk")
            return

        for model_path in MODEL_PATHS:
            if os.path.exists(model_path):
                try:
                    self.model = vosk.Model(model_path)
                    self.recognizer = vosk.KaldiRecognizer(self.model, SAMPLE_RATE)
                    self.recognizer.SetWords(True)
                    print(f"[WakeWord] ✅ Vosk model loaded from: {os.path.basename(model_path)}")
                    return
                except Exception as e:
                    print(f"[WakeWord] ⚠️ Model load error: {e}")

        print("[WakeWord] ⚠️ No Vosk model found. Wake word will use Google Speech.")

    def _check_wake_word(self, text):
        """Check if the transcribed text contains a wake word."""
        text_lower = text.lower().strip()

        for wake in WAKE_WORDS:
            if wake in text_lower:
                return True

        # Fuzzy check: if "chiku" appears anywhere
        if "chiku" in text_lower or "cheeku" in text_lower or "chico" in text_lower:
            return True

        return False

    def _vosk_listen_loop(self):
        """Main loop: listen with Vosk (offline) for wake word."""
        audio_stream = None
        pa = None

        try:
            if _pyaudio_available:
                pa = pyaudio.PyAudio()
                audio_stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=CHUNK_SIZE,
                )
                audio_stream.start_stream()
            elif _sd_available:
                pass  # Will use sounddevice below
            else:
                print("[WakeWord] ❌ No audio input available (need PyAudio or sounddevice)")
                return

            print("[WakeWord] 🎤 Listening for 'Hey Chiku'...")

            while self.listening and not self._stop_event.is_set():
                if self._paused:
                    time.sleep(0.3)
                    continue

                try:
                    # Get audio data
                    if _pyaudio_available and audio_stream:
                        data = audio_stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    elif _sd_available:
                        data = sd.rec(
                            CHUNK_SIZE,
                            samplerate=SAMPLE_RATE,
                            channels=1,
                            dtype='int16',
                            blocking=True,
                        )
                        data = data.tobytes()
                    else:
                        break

                    # Feed to Vosk recognizer
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "")

                        if text and self._check_wake_word(text):
                            self._on_wake_detected(text)

                    else:
                        # Partial results (faster detection)
                        partial = json.loads(self.recognizer.PartialResult())
                        partial_text = partial.get("partial", "")

                        if partial_text and self._check_wake_word(partial_text):
                            self._on_wake_detected(partial_text)
                            # Reset recognizer after detection
                            self.recognizer = vosk.KaldiRecognizer(self.model, SAMPLE_RATE)
                            self.recognizer.SetWords(True)

                except OSError:
                    time.sleep(0.5)
                except Exception as e:
                    if self.listening:
                        time.sleep(0.2)

        finally:
            if audio_stream:
                try:
                    audio_stream.stop_stream()
                    audio_stream.close()
                except Exception:
                    pass
            if pa:
                try:
                    pa.terminate()
                except Exception:
                    pass

            print("[WakeWord] 🛑 Wake word listener stopped.")

    def _google_listen_loop(self):
        """Fallback: listen with Google Speech Recognition for wake word."""
        try:
            import speech_recognition as sr
        except ImportError:
            print("[WakeWord] ❌ Neither Vosk nor SpeechRecognition available.")
            return

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8

        print("[WakeWord] 🎤 Listening for 'Hey Chiku' (Google mode)...")

        while self.listening and not self._stop_event.is_set():
            if self._paused:
                time.sleep(0.3)
                continue

            try:
                with sr.Microphone(sample_rate=SAMPLE_RATE) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)

                text = recognizer.recognize_google(audio, language="en-in")

                if self._check_wake_word(text):
                    self._on_wake_detected(text)

            except Exception:
                continue

        print("[WakeWord] 🛑 Wake word listener stopped.")

    def _on_wake_detected(self, text):
        """Called when the wake word is detected."""
        now = time.time()
        if now - self.last_wake_time < self.cooldown:
            return  # Cooldown — avoid double triggers

        self.last_wake_time = now
        print(f"\n🔔 Wake word detected! (heard: '{text}')")

        if self.wake_callback:
            # Pause wake word listening while processing command
            self._paused = True
            try:
                self.wake_callback()
            except Exception as e:
                print(f"❌ Callback error: {e}")
            finally:
                self._paused = False

    def start(self, on_wake=None):
        """
        Start the wake word listener in a background thread.
        
        Args:
            on_wake: Callback function called when wake word is detected.
                     This function should listen for the actual command and execute it.
        """
        if self.listening:
            print("[WakeWord] Already listening.")
            return

        self.wake_callback = on_wake
        self.listening = True
        self._stop_event.clear()

        # Choose listening method
        if self.model and self.recognizer:
            target = self._vosk_listen_loop
        else:
            target = self._google_listen_loop

        self.thread = threading.Thread(target=target, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the wake word listener."""
        self.listening = False
        self._stop_event.set()

        if self.thread:
            self.thread.join(timeout=3)
            self.thread = None

    def pause(self):
        """Temporarily pause listening (e.g., while CHIKU is speaking)."""
        self._paused = True

    def resume(self):
        """Resume listening after pause."""
        self._paused = False

    def is_active(self):
        """Check if the engine is currently listening."""
        return self.listening and not self._paused


# ─── Global instance ────────────────────────────────────────────────────────
wake_engine = WakeWordEngine()
