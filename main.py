"""
main.py
-------
Guess-the-Song filter – entry point.

Controls
  SPACE  →  spin the song wheel
  Q      →  quit

Pipeline
  Webcam → MediaPipe Face Mesh → forehead anchor → SongSpinner overlay
"""

import cv2
import mediapipe as mp

from spinner import SongSpinner

# ─── MediaPipe setup ──────────────────────────────────────────────────────────
mp_face_mesh   = mp.solutions.face_mesh
mp_drawing     = mp.solutions.drawing_utils
mp_draw_styles = mp.solutions.drawing_styles

FOREHEAD_IDX = 10          # MediaPipe Face Mesh landmark for top of forehead

# ─── Camera setup ─────────────────────────────────────────────────────────────
CAM_INDEX = 0
FRAME_W   = 1280
FRAME_H   = 720

# ─── Asset paths ──────────────────────────────────────────────────────────────
CSV_PATH  = "assets/name.csv"
COVER_DIR = "assets/cover"


def run() -> None:
    spinner = SongSpinner(CSV_PATH, COVER_DIR)

    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index {CAM_INDEX}")

    with mp_face_mesh.FaceMesh(
        max_num_faces            = 4,
        refine_landmarks         = True,
        min_detection_confidence = 0.5,
        min_tracking_confidence  = 0.5,
    ) as face_mesh:

        print("Camera running  │  SPACE = spin  │  Q = quit")

        while True:
            ok, frame = cap.read()
            if not ok:
                continue

            frame = cv2.flip(frame, 1)          # mirror / selfie mode
            h, w  = frame.shape[:2]

            # ── Face detection ────────────────────────────────────────────
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results = face_mesh.process(rgb)
            rgb.flags.writeable = True

            face_found = False
            if results.multi_face_landmarks:
                for face_lms in results.multi_face_landmarks:
                    face_found = True

                    # Forehead anchor in pixel coords
                    lm = face_lms.landmark[FOREHEAD_IDX]
                    fx = int(lm.x * w)
                    fy = int(lm.y * h)

                    # Draw spinner card above the head
                    frame = spinner.render_overlay(frame, fx, fy)

                    # Small anchor dot (debug; remove when polished)
                    cv2.circle(frame, (fx, fy), 4, (0, 255, 100), -1)

            # ── No-face fallback: render card at top-centre ────────────────
            if not face_found:
                frame = spinner.render_overlay(frame, w // 2, h // 3)

            # ── HUD ───────────────────────────────────────────────────────
            hud = "SPACE = spin    Q = quit"
            cv2.putText(frame, hud, (10, h - 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (200, 200, 200), 1, cv2.LINE_AA)

            cv2.imshow("Guess the Song", frame)

            # ── Key handling ──────────────────────────────────────────────
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord(" "):
                spinner.trigger_spin()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run()
