"""
CHIKU PRO - Vision System
Real-time face and hand detection using MediaPipe + OpenCV.
Runs in a separate thread to not block the main loop.
"""

import cv2
import threading
import time


# ─── Lazy-load MediaPipe (optional dependency) ──────────────────────────────
_mp_available = False
try:
    import mediapipe as mp
    _mp_available = True
except ImportError:
    _mp_available = False
    print("[CHIKU] mediapipe not installed. Vision will be limited.")
    print("[CHIKU] Install it with: pip install mediapipe")


class VisionSystem:
    """
    Camera-based vision system with face and hand detection.
    Runs in a background thread.
    """

    def __init__(self):
        self.running = False
        self.thread = None
        self.cap = None
        self.lock = threading.Lock()

        # Detection state
        self.face_detected = False
        self.hand_detected = False
        self.face_count = 0
        self.hand_count = 0

        # Throttle prints to avoid spam
        self.last_print_time = 0
        self.print_interval = 3  # seconds

        # MediaPipe (initialized on start)
        self._face_detector = None
        self._hand_detector = None
        self._mp_draw = None
        self._mp_hands = None

    def _init_detectors(self):
        """Initialize MediaPipe detectors (lazy loading)."""
        if not _mp_available:
            return False

        try:
            mp_face = mp.solutions.face_detection
            self._mp_hands = mp.solutions.hands
            self._mp_draw = mp.solutions.drawing_utils

            self._face_detector = mp_face.FaceDetection(
                model_selection=0,
                min_detection_confidence=0.6
            )
            self._hand_detector = self._mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.5
            )
            return True

        except Exception as e:
            print(f"⚠️ MediaPipe init error: {e}")
            return False

    def _vision_loop(self):
        """Main vision processing loop (runs in background thread)."""
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            print("❌ Camera not available.")
            self.running = False
            return

        # Set camera properties for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        has_detectors = self._init_detectors()
        print("👁️ Vision system started." + (" (with AI detection)" if has_detectors else " (basic mode)"))

        while self.running:
            ret, frame = self.cap.read()

            if not ret:
                time.sleep(0.01)
                continue

            # Flip for mirror effect
            frame = cv2.flip(frame, 1)

            if has_detectors:
                frame = self._process_detections(frame)

            # Add status overlay
            self._draw_overlay(frame)

            cv2.imshow("CHIKU Vision", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:  # q or ESC
                break

        # Cleanup
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        self.running = False
        print("👁️ Vision system stopped.")

    def _process_detections(self, frame):
        """Run face and hand detection on a frame."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # ── Face Detection ──────────────────────────────────────────────
        self.face_detected = False
        self.face_count = 0

        if self._face_detector:
            face_results = self._face_detector.process(rgb)

            if face_results.detections:
                self.face_detected = True
                self.face_count = len(face_results.detections)

                for detection in face_results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    h, w, _ = frame.shape

                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    bw = int(bbox.width * w)
                    bh = int(bbox.height * h)

                    # Draw face bounding box
                    cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)

                    # Confidence label
                    conf = detection.score[0]
                    cv2.putText(frame, f"Face {conf:.0%}",
                                (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                0.6, (0, 255, 0), 2)

        # ── Hand Detection ──────────────────────────────────────────────
        self.hand_detected = False
        self.hand_count = 0

        if self._hand_detector:
            hand_results = self._hand_detector.process(rgb)

            if hand_results.multi_hand_landmarks:
                self.hand_detected = True
                self.hand_count = len(hand_results.multi_hand_landmarks)

                for hand_landmarks in hand_results.multi_hand_landmarks:
                    self._mp_draw.draw_landmarks(
                        frame,
                        hand_landmarks,
                        self._mp_hands.HAND_CONNECTIONS,
                        self._mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=3),
                        self._mp_draw.DrawingSpec(color=(0, 255, 255), thickness=2),
                    )

        # Throttled console output
        now = time.time()
        if now - self.last_print_time > self.print_interval:
            if self.face_detected:
                print(f"👤 Face detected ({self.face_count})")
            if self.hand_detected:
                print(f"✋ Hand detected ({self.hand_count})")
            if self.face_detected or self.hand_detected:
                self.last_print_time = now

        return frame

    def _draw_overlay(self, frame):
        """Draw status overlay on the frame."""
        h, w = frame.shape[:2]

        # Semi-transparent status bar at top
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 40), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        # Status text
        status = "CHIKU Vision"
        if self.face_detected:
            status += f" | 👤 Faces: {self.face_count}"
        if self.hand_detected:
            status += f" | ✋ Hands: {self.hand_count}"

        cv2.putText(frame, status, (10, 28),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # Quit hint at bottom
        cv2.putText(frame, "Press 'Q' or ESC to close",
                     (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX,
                     0.4, (150, 150, 150), 1)

    def start(self):
        """Start the vision system in a background thread."""
        with self.lock:
            if self.running:
                print("👁️ Vision is already running.")
                return

            self.running = True
            self.thread = threading.Thread(target=self._vision_loop, daemon=True)
            self.thread.start()

    def stop(self):
        """Stop the vision system."""
        with self.lock:
            if not self.running:
                return

            self.running = False

        if self.thread:
            self.thread.join(timeout=3)

        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    def is_running(self):
        """Check if the vision system is currently active."""
        return self.running


# ─── Global vision instance ─────────────────────────────────────────────────
vision = VisionSystem()