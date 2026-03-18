"""
CHIKU PRO - Face Lock Module
Face enrollment and recognition using OpenCV's LBPH Face Recognizer.
Stores face data locally for offline authentication.
"""

import cv2
import numpy as np
import os
import json
import time

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACE_DATA_DIR = os.path.join(BASE_DIR, "face_data")
FACE_MODEL_PATH = os.path.join(FACE_DATA_DIR, "face_model.yml")
FACE_META_PATH = os.path.join(FACE_DATA_DIR, "face_meta.json")

# ─── Haar Cascade for face detection ────────────────────────────────────────
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

# ─── Settings ────────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 70    # Lower = stricter match (LBPH distance)
NUM_ENROLLMENT_SAMPLES = 30  # Number of face images to capture during enrollment
RECOGNITION_TIMEOUT = 15     # Seconds to try recognition before failing


class FaceLock:
    """Face enrollment and recognition system."""

    def __init__(self):
        self.recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1,
            neighbors=8,
            grid_x=8,
            grid_y=8,
        )
        self.is_enrolled = False
        self.owner_name = None

        # Create face data directory
        os.makedirs(FACE_DATA_DIR, exist_ok=True)

        # Load existing model if available
        self._load_model()

    def _load_model(self):
        """Load a previously trained face model."""
        if os.path.exists(FACE_MODEL_PATH) and os.path.exists(FACE_META_PATH):
            try:
                self.recognizer.read(FACE_MODEL_PATH)
                with open(FACE_META_PATH, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                self.owner_name = meta.get("owner_name", "Owner")
                self.is_enrolled = True
                return True
            except Exception as e:
                print(f"⚠️ Could not load face model: {e}")
        return False

    def _save_model(self):
        """Save the trained face model to disk."""
        try:
            self.recognizer.save(FACE_MODEL_PATH)
            meta = {
                "owner_name": self.owner_name,
                "enrolled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "confidence_threshold": CONFIDENCE_THRESHOLD,
                "num_samples": NUM_ENROLLMENT_SAMPLES,
            }
            with open(FACE_META_PATH, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Could not save face model: {e}")
            return False

    def _detect_faces(self, gray_frame):
        """Detect faces in a grayscale frame. Returns list of (x, y, w, h)."""
        faces = face_cascade.detectMultiScale(
            gray_frame,
            scaleFactor=1.2,
            minNeighbors=6,
            minSize=(80, 80),
        )
        return faces

    def _preprocess_face(self, gray_frame, face_rect):
        """Extract and normalize a face region."""
        x, y, w, h = face_rect
        face_roi = gray_frame[y:y+h, x:x+w]
        # Resize to a standard size
        face_resized = cv2.resize(face_roi, (200, 200))
        # Histogram equalization for lighting normalization
        face_eq = cv2.equalizeHist(face_resized)
        return face_eq

    def enroll(self, owner_name=None):
        """
        Enroll a new face. Opens the camera and captures face samples.
        Returns True if enrollment was successful.
        """
        if owner_name:
            self.owner_name = owner_name

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("❌ Camera not available for face enrollment.")
            return False

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        face_samples = []
        labels = []
        sample_count = 0

        print(f"\n{'='*50}")
        print("  📸 FACE ENROLLMENT")
        print(f"{'='*50}")
        print(f"  Look at the camera. I need {NUM_ENROLLMENT_SAMPLES} samples.")
        print("  Move your head slightly for better accuracy.")
        print("  Press 'Q' to cancel.\n")

        while sample_count < NUM_ENROLLMENT_SAMPLES:
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.flip(frame, 1)  # Mirror
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = self._detect_faces(gray)

            for (x, y, w, h) in faces:
                # Draw progress rectangle
                progress = sample_count / NUM_ENROLLMENT_SAMPLES
                color = (
                    int(255 * (1 - progress)),   # R decreases
                    int(255 * progress),          # G increases
                    0
                )
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)

                # Capture face sample
                face_processed = self._preprocess_face(gray, (x, y, w, h))
                face_samples.append(face_processed)
                labels.append(0)  # Label 0 = owner
                sample_count += 1

                # Show progress
                cv2.putText(frame, f"Captured: {sample_count}/{NUM_ENROLLMENT_SAMPLES}",
                            (x, y - 15), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, color, 2)

            # Draw overlay
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (640, 50), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

            # Progress bar
            bar_width = int(580 * (sample_count / NUM_ENROLLMENT_SAMPLES))
            cv2.rectangle(frame, (30, 15), (30 + bar_width, 35), (0, 255, 100), -1)
            cv2.rectangle(frame, (30, 15), (610, 35), (255, 255, 255), 1)

            cv2.putText(frame, f"ENROLLING: {sample_count}/{NUM_ENROLLMENT_SAMPLES}",
                        (200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.imshow("CHIKU - Face Enrollment", frame)

            key = cv2.waitKey(100) & 0xFF
            if key == ord('q') or key == 27:
                print("❌ Enrollment cancelled.")
                cap.release()
                cv2.destroyAllWindows()
                return False

        cap.release()
        cv2.destroyAllWindows()

        # Train the recognizer
        if len(face_samples) > 0:
            print("⏳ Training face recognition model...")
            self.recognizer.train(face_samples, np.array(labels))
            self.is_enrolled = True

            if self._save_model():
                print(f"✅ Face enrolled successfully for '{self.owner_name}'!")
                print(f"   Saved {len(face_samples)} samples.\n")
                return True

        print("❌ Enrollment failed — not enough face samples.")
        return False

    def verify(self, timeout=None):
        """
        Verify the current user's face against the enrolled face.
        Opens camera and tries to match within the timeout period.
        
        Returns: (success: bool, confidence: float)
        """
        if not self.is_enrolled:
            print("⚠️ No face enrolled. Run enrollment first.")
            return False, 0.0

        if timeout is None:
            timeout = RECOGNITION_TIMEOUT

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("❌ Camera not available for face verification.")
            return False, 0.0

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        start_time = time.time()
        best_confidence = 999.0
        verified = False

        print(f"\n{'='*50}")
        print("  🔒 FACE VERIFICATION")
        print(f"{'='*50}")
        print(f"  Look at the camera to unlock...")
        print(f"  Timeout: {timeout} seconds | Press 'Q' to cancel\n")

        while (time.time() - start_time) < timeout:
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = self._detect_faces(gray)
            elapsed = time.time() - start_time
            remaining = max(0, timeout - elapsed)

            for (x, y, w, h) in faces:
                face_processed = self._preprocess_face(gray, (x, y, w, h))

                # Predict
                label, confidence = self.recognizer.predict(face_processed)

                # LBPH: lower confidence = better match
                if confidence < best_confidence:
                    best_confidence = confidence

                if confidence < CONFIDENCE_THRESHOLD:
                    # ✅ MATCH!
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                    cv2.putText(frame, f"UNLOCKED! ({confidence:.0f})",
                                (x, y - 15), cv2.FONT_HERSHEY_SIMPLEX,
                                0.7, (0, 255, 0), 2)
                    cv2.imshow("CHIKU - Face Lock", frame)
                    cv2.waitKey(1000)  # Show success for 1 second
                    verified = True
                    break
                else:
                    # ❌ Not a match
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 3)
                    cv2.putText(frame, f"Unknown ({confidence:.0f})",
                                (x, y - 15), cv2.FONT_HERSHEY_SIMPLEX,
                                0.7, (0, 0, 255), 2)

            if verified:
                break

            # Draw overlay
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (640, 50), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

            # Timer bar
            timer_width = int(580 * (remaining / timeout))
            timer_color = (0, 255, 100) if remaining > 5 else (0, 100, 255)
            cv2.rectangle(frame, (30, 15), (30 + timer_width, 35), timer_color, -1)
            cv2.rectangle(frame, (30, 15), (610, 35), (255, 255, 255), 1)

            cv2.putText(frame, f"SCANNING... {remaining:.0f}s",
                        (220, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.imshow("CHIKU - Face Lock", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                print("❌ Face verification cancelled.")
                break

        cap.release()
        cv2.destroyAllWindows()

        if verified:
            match_pct = max(0, 100 - best_confidence)
            print(f"✅ Face verified! Welcome back, {self.owner_name}! (Match: {match_pct:.0f}%)")
        else:
            print(f"❌ Face verification failed. Best confidence: {best_confidence:.1f}")

        return verified, best_confidence

    def reset(self):
        """Delete enrolled face data and reset the system."""
        try:
            if os.path.exists(FACE_MODEL_PATH):
                os.remove(FACE_MODEL_PATH)
            if os.path.exists(FACE_META_PATH):
                os.remove(FACE_META_PATH)

            self.is_enrolled = False
            self.owner_name = None
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            print("✅ Face data deleted. System reset.")
            return True
        except Exception as e:
            print(f"❌ Reset failed: {e}")
            return False

    def update(self, additional_samples=15):
        """
        Add more face samples to improve recognition.
        Useful for different lighting or angles.
        """
        if not self.is_enrolled:
            print("⚠️ No face enrolled. Use enroll() first.")
            return False

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("❌ Camera not available.")
            return False

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        face_samples = []
        labels = []
        sample_count = 0

        print(f"\n📸 Updating face data... Need {additional_samples} more samples.")
        print("  Move your head to different angles/positions.\n")

        while sample_count < additional_samples:
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self._detect_faces(gray)

            for (x, y, w, h) in faces:
                face_processed = self._preprocess_face(gray, (x, y, w, h))
                face_samples.append(face_processed)
                labels.append(0)
                sample_count += 1

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 200, 255), 3)
                cv2.putText(frame, f"Update: {sample_count}/{additional_samples}",
                            (x, y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)

            cv2.imshow("CHIKU - Face Update", frame)
            key = cv2.waitKey(100) & 0xFF
            if key == ord('q') or key == 27:
                break

        cap.release()
        cv2.destroyAllWindows()

        if len(face_samples) > 0:
            self.recognizer.update(face_samples, np.array(labels))
            self._save_model()
            print(f"✅ Face model updated with {len(face_samples)} new samples!")
            return True

        return False


# ─── Global face lock instance ───────────────────────────────────────────────
face_lock = FaceLock()
