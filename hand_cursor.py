"""Control the Windows cursor with a webcam and simple hand gestures."""

from __future__ import annotations

import urllib.request
from pathlib import Path
import time

try:
    import cv2
    import mediapipe as mp
    import pyautogui
except ImportError as exc:
    print(f"Missing dependency: {exc.name}. Install dependencies with: python -m pip install -r requirements.txt")
    raise SystemExit(1)


WINDOW = "Hand Cursor"
CAMERA_INDEX = 0
SCROLL_GAIN = 8.0
# This inner camera area maps to the whole laptop screen for easier edge-to-edge movement.
CONTROL_LEFT, CONTROL_RIGHT = 0.14, 0.86
CONTROL_TOP, CONTROL_BOTTOM = 0.10, 0.90
MODEL_PATH = Path(__file__).with_name("hand_landmarker.task")
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)

# Landmark connections used to draw the hand skeleton in the preview.
HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
    (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),
)


def distance(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def distance_3d(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2) ** 0.5


def finger_is_up(hand, tip, pip):
    # Compare fingertip reach to the finger's own middle joint, independent of palm size.
    mcp = {8: 5, 12: 9, 16: 13, 20: 17}[tip]
    return distance_3d(hand[mcp], hand[tip]) > distance_3d(hand[mcp], hand[pip]) * 1.12


def classify_gesture(hand, active_gesture=None):
    """Return move/click/scroll/idle from fingertip distances relative to palm width."""
    scale = max(distance_3d(hand[5], hand[17]), distance_3d(hand[0], hand[9]), 0.001)
    ti = distance_3d(hand[4], hand[8]) / scale
    tm = distance_3d(hand[4], hand[12]) / scale
    im = distance_3d(hand[8], hand[12]) / scale

    # Hysteresis keeps a held gesture active despite a little landmark jitter.
    if active_gesture == "scroll" and max(ti, tm, im) < 0.56:
        return "scroll"

    # Require all three fingertips to meet before scrolling, so an index/thumb
    # click remains a click even when the middle finger happens to be nearby.
    if max(ti, tm, im) < 0.36:
        return "scroll"
    if active_gesture == "click" and ti < 0.62:
        return "click"
    if ti < 0.44:
        return "click"
    if finger_is_up(hand, 8, 6):
        return "move"
    return "idle"


def map_to_screen(x, y, screen_w, screen_h):
    """Map mirrored preview coordinates to the complete display, clamped to its edges."""
    target_x = ((x - CONTROL_LEFT) / (CONTROL_RIGHT - CONTROL_LEFT)) * (screen_w - 3) + 1
    target_y = ((y - CONTROL_TOP) / (CONTROL_BOTTOM - CONTROL_TOP)) * (screen_h - 3) + 1
    return (
        max(1, min(screen_w - 2, target_x)),
        max(1, min(screen_h - 2, target_y)),
    )


def smoothing_alpha(distance_px):
    """Filter tiny tremor while keeping long cursor movements responsive."""
    if distance_px < 2.5:
        return 0.0
    return min(0.88, 0.34 + distance_px / 850.0)


class ClickGate:
    """Debounce a pinch and allow exactly one click until the fingers release."""

    def __init__(self):
        self.frames = 0
        self.armed = True

    def update(self, gesture):
        if gesture != "click":
            self.frames = 0
            self.armed = True
            return False
        if not self.armed:
            return False
        self.frames += 1
        if self.frames >= 2:
            self.armed = False
            return True
        return False


def ensure_model() -> None:
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 1_000_000:
        return
    print("Downloading the hand landmark model (one-time download)...")
    partial = MODEL_PATH.with_suffix(".task.download")
    try:
        with urllib.request.urlopen(MODEL_URL, timeout=30) as response, partial.open("wb") as target:
            while block := response.read(1024 * 1024):
                target.write(block)
        if partial.stat().st_size < 1_000_000:
            raise RuntimeError("Downloaded model file is unexpectedly small.")
        partial.replace(MODEL_PATH)
    except Exception as exc:
        partial.unlink(missing_ok=True)
        raise RuntimeError(
            f"Could not download the hand model. Check your internet connection and retry. ({exc})"
        ) from exc


def draw_hand(frame, hand) -> None:
    h, w = frame.shape[:2]
    points = [(int(point.x * w), int(point.y * h)) for point in hand]
    for start, end in HAND_CONNECTIONS:
        cv2.line(frame, points[start], points[end], (80, 210, 130), 2)
    for point in points:
        cv2.circle(frame, point, 4, (40, 90, 255), -1)


def main() -> None:
    try:
        ensure_model()
    except RuntimeError as exc:
        print(exc)
        return

    pyautogui.FAILSAFE = True  # Move mouse to the top-left corner for an emergency stop.
    pyautogui.PAUSE = 0  # PyAutoGUI otherwise pauses briefly after every mouse action.
    screen_w, screen_h = pyautogui.size()
    # DirectShow usually keeps webcam latency low on Windows; fall back to OpenCV's default backend.
    camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not camera.isOpened():
        camera.release()
        camera = cv2.VideoCapture(CAMERA_INDEX)
    if not camera.isOpened():
        print("Could not open camera 0. Check that a webcam is connected and available.")
        return
    # Smaller frames reduce hand-tracking time; a one-frame buffer avoids acting on stale video.
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    vision = mp.tasks.vision
    options = vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.55,
        min_hand_presence_confidence=0.55,
        min_tracking_confidence=0.55,
    )
    cursor_x, cursor_y = screen_w / 2, screen_h / 2
    cursor_initialized = False
    active_gesture = None
    click_gate = ClickGate()
    prior_scroll_y = None
    last_timestamp_ms = 0
    scroll_remainder = 0.0
    status = "Show one hand to the camera"
    print("Hand Cursor is running. Press Q in the camera window to quit.")
    print("Emergency stop: move mouse to the top-left corner (PyAutoGUI failsafe).")

    try:
        with vision.HandLandmarker.create_from_options(options) as hand_tracker:
            while True:
                ok, frame = camera.read()
                if not ok:
                    print("Lost the camera feed.")
                    break
                frame = cv2.flip(frame, 1)
                if frame.shape[1] > 640:
                    scale = 640 / frame.shape[1]
                    frame = cv2.resize(frame, (640, int(frame.shape[0] * scale)), interpolation=cv2.INTER_AREA)
                h, w = frame.shape[:2]
                zone_left = int(CONTROL_LEFT * w)
                zone_right = int(CONTROL_RIGHT * w)
                zone_top = int(CONTROL_TOP * h)
                zone_bottom = int(CONTROL_BOTTOM * h)
                cv2.rectangle(frame, (zone_left, zone_top), (zone_right, zone_bottom), (255, 170, 50), 2)
                cv2.putText(frame, "Move fingertip inside box to reach screen edges", (zone_left, zone_top - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 210, 120), 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp_ms = max(time.monotonic_ns() // 1_000_000, last_timestamp_ms + 1)
                last_timestamp_ms = timestamp_ms
                result = hand_tracker.detect_for_video(mp_image, timestamp_ms)
                status = "Show one hand to the camera"

                if result.hand_landmarks:
                    hand = result.hand_landmarks[0]
                    draw_hand(frame, hand)
                    gesture = classify_gesture(hand, active_gesture)
                    if gesture == "scroll":
                        status = "SCROLL — move hand up/down"
                        active_gesture = "scroll"
                        click_gate.update(gesture)
                        center_y = (hand[4].y + hand[8].y + hand[12].y) / 3
                        if prior_scroll_y is not None:
                            delta = prior_scroll_y - center_y
                            scroll_remainder += delta * h * SCROLL_GAIN
                            steps = int(scroll_remainder)
                            if steps:
                                steps = max(-12, min(12, steps))
                                pyautogui.scroll(steps)
                                scroll_remainder -= steps
                        prior_scroll_y = center_y
                    elif gesture == "click":
                        prior_scroll_y = None
                        scroll_remainder = 0.0
                        active_gesture = "click"
                        if click_gate.update(gesture):
                            pyautogui.click()
                            status = "CLICK"
                        else:
                            status = "Pinch detected — release to click again" if not click_gate.armed else "Hold pinch to click"
                    elif gesture == "move":
                        status = "MOVE — point with index finger"
                        active_gesture = None
                        click_gate.update(gesture)
                        prior_scroll_y = None
                        scroll_remainder = 0.0
                        target_x, target_y = map_to_screen(hand[8].x, hand[8].y, screen_w, screen_h)
                        if not cursor_initialized:
                            cursor_x, cursor_y = target_x, target_y
                            cursor_initialized = True
                        else:
                            delta_x, delta_y = target_x - cursor_x, target_y - cursor_y
                            alpha = smoothing_alpha((delta_x * delta_x + delta_y * delta_y) ** 0.5)
                            cursor_x += delta_x * alpha
                            cursor_y += delta_y * alpha
                        pyautogui.moveTo(int(cursor_x), int(cursor_y), _pause=False)
                    else:
                        status = "Ready — point, pinch to click, or three-finger pinch to scroll"
                        active_gesture = None
                        click_gate.update(gesture)
                        prior_scroll_y = None
                        scroll_remainder = 0.0

                cv2.rectangle(frame, (0, 0), (w, 76), (24, 28, 36), -1)
                cv2.putText(frame, status, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (80, 230, 150), 2)
                cv2.putText(frame, "Q: quit   |   Mouse to top-left: emergency stop", (16, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, (225, 225, 225), 1)
                cv2.imshow(WINDOW, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                if not result.hand_landmarks:
                    # Re-arm clicks and reset scroll when the hand leaves the camera.
                    active_gesture = None
                    click_gate.update(None)
                    prior_scroll_y = None
                    scroll_remainder = 0.0
    except pyautogui.FailSafeException:
        print("Emergency stop triggered. The app has been stopped.")
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
