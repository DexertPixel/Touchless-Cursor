# Hand Cursor

Control a Windows desktop pointer with a webcam and hand gestures. The app uses MediaPipe hand landmarks to track your index fingertip, recognize pinch gestures, and map your hand movement to the full screen.

> **Project type:** Python desktop accessibility/interaction prototype · **Platform:** Windows 10/11 · **Input:** webcam

## Features

- Move the pointer by pointing with your index finger.
- Click by pinching your thumb and index finger together. A pinch clicks once; release before clicking again.
- Scroll by bringing your thumb, index, and middle fingertips together and moving your hand vertically.
- Map the camera control area to the full display, with responsive smoothing to reduce small hand tremors.
- Show a mirrored live preview with hand landmarks and current gesture status.
- Process webcam frames locally; the app does not record or upload video.

## Run it on Windows

### Quick start

1. Install Python 3.10 or newer. Make sure the Python launcher command `py` works in Command Prompt or PowerShell.
2. Download this repository and extract it, or clone it with Git.
3. Double-click **Start Hand Cursor.bat**. The launcher creates a local `.venv`, installs packages from `requirements.txt`, and starts the app.
4. Allow camera access if Windows prompts you. On first run, the hand-landmarker model is downloaded into the project folder.
5. Point your index finger inside the outlined preview box. Press **Q** while the preview window is active to quit.

### Manual setup

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python hand_cursor.py
```

## Gesture controls

| Gesture | Action |
| --- | --- |
| Point with index finger | Move pointer |
| Pinch thumb and index finger | Click once; release to re-arm |
| Pinch thumb, index, and middle fingertips | Scroll up or down by moving your hand |

The preview is mirrored so left/right movement feels natural. The outlined camera region maps to the whole laptop display. Move your fingertip toward each edge of that box to reach the corresponding edge of the screen.

## Safety and troubleshooting

- **Emergency stop:** move the physical mouse to a screen corner. PyAutoGUI's fail-safe stops the app.
- **Camera not found:** close other apps using the camera. If your webcam is not device 0, change `CAMERA_INDEX` near the top of `hand_cursor.py`.
- **Gestures are unreliable:** use good front lighting, keep the full hand in view, and move the hand slightly farther from the camera.
- **Click does not trigger:** hold the pinch briefly, then open the fingers before the next click. The preview status shows the recognized gesture.
- **Slow first launch:** first-time setup installs Python packages and downloads the hand-landmarker model; later launches reuse them.

## Development and checks

Run the offline tests from this folder:

```powershell
.venv\Scripts\python.exe -m unittest -v test_hand_cursor.py
```

The tests cover gesture classification, one-click-per-pinch behavior, control-box screen mapping, and cursor smoothing. Webcam tracking and physical click feel should be checked on a computer with a camera.

## How it works

OpenCV captures and mirrors webcam frames. MediaPipe Tasks finds 21 hand landmarks in each frame. The app compares fingertip distances relative to hand size to identify click and scroll pinches, and checks index-finger extension for pointer movement. Pointer coordinates are mapped from the preview control box to the display, filtered to reduce jitter, and sent to Windows through PyAutoGUI.

## Repository contents

- `hand_cursor.py` — webcam tracking, gesture recognition, screen mapping, and Windows input.
- `Start Hand Cursor.bat` — creates the virtual environment and launches the program.
- `requirements.txt` — Python dependencies.
- `test_hand_cursor.py` — offline unit tests for gesture and cursor logic.

The MediaPipe hand-landmarker model is downloaded on first run rather than checked into this repository.

## License

No license is included yet. Add a license if you want others to reuse, modify, or redistribute this project.
