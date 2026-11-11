import cv2
import numpy as np
import time

# ═══════════════════════════════════════════════════════════════
#  FLAME DETECTION SYSTEM  —  HSV-based Color Segmentation
#  Professional Dashboard Edition
# ═══════════════════════════════════════════════════════════════

def nothing(_):
    """Callback stub required by OpenCV trackbars."""
    pass


# ─── Dashboard Theme (BGR) ─────────────────────────────────────
BG_DARK      = (28, 28, 28)
PANEL_DARK   = (45, 45, 45)
ACCENT_GREEN = (80, 220, 100)
ACCENT_RED   = (60, 60, 240)
TEXT_LIGHT   = (230, 230, 230)
TEXT_DIM     = (150, 150, 150)

WINDOW_MAIN  = "Flame Detection | Live Feed"
WINDOW_CTRL  = "Flame Detection | Control Panel"
WINDOW_MASK  = "Flame Detection | Red Mask"


# ─── Control Panel Setup ───────────────────────────────────────
cv2.namedWindow(WINDOW_CTRL, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WINDOW_CTRL, 420, 420)

# Red hue wraps around 0° and 180° in HSV → two ranges required
cv2.createTrackbar("Hue Min  (Range 1)", WINDOW_CTRL,   0, 180, nothing)
cv2.createTrackbar("Hue Max  (Range 1)", WINDOW_CTRL,  10, 180, nothing)
cv2.createTrackbar("Hue Min  (Range 2)", WINDOW_CTRL, 170, 180, nothing)
cv2.createTrackbar("Hue Max  (Range 2)", WINDOW_CTRL, 180, 180, nothing)

cv2.createTrackbar("Sat Min",  WINDOW_CTRL, 120, 255, nothing)
cv2.createTrackbar("Sat Max",  WINDOW_CTRL, 255, 255, nothing)
cv2.createTrackbar("Val Min",  WINDOW_CTRL,  70, 255, nothing)
cv2.createTrackbar("Val Max",  WINDOW_CTRL, 255, 255, nothing)

# Minimum blob area (pixels²) to reject small noise
cv2.createTrackbar("Min Area", WINDOW_CTRL, 500, 50000, nothing)


# ─── Video Source ──────────────────────────────────────────────
cap = cv2.VideoCapture(0)          # Use "flame.mp4" for a video file
if not cap.isOpened():
    print("[ERROR] Could not open video source.")
    exit(1)

prev_time = time.time()

# ═══════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # ─── Preprocessing ─────────────────────────────────────────
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    hsv     = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    # ─── Read Trackbar Values ──────────────────────────────────
    h_min1 = cv2.getTrackbarPos("Hue Min  (Range 1)", WINDOW_CTRL)
    h_max1 = cv2.getTrackbarPos("Hue Max  (Range 1)", WINDOW_CTRL)
    h_min2 = cv2.getTrackbarPos("Hue Min  (Range 2)", WINDOW_CTRL)
    h_max2 = cv2.getTrackbarPos("Hue Max  (Range 2)", WINDOW_CTRL)
    s_min  = cv2.getTrackbarPos("Sat Min",  WINDOW_CTRL)
    s_max  = cv2.getTrackbarPos("Sat Max",  WINDOW_CTRL)
    v_min  = cv2.getTrackbarPos("Val Min",  WINDOW_CTRL)
    v_max  = cv2.getTrackbarPos("Val Max",  WINDOW_CTRL)
    min_area = cv2.getTrackbarPos("Min Area", WINDOW_CTRL)

    # ─── Dual-range Red Mask ───────────────────────────────────
    mask1 = cv2.inRange(hsv,
                        np.array([h_min1, s_min, v_min]),
                        np.array([h_max1, s_max, v_max]))
    mask2 = cv2.inRange(hsv,
                        np.array([h_min2, s_min, v_min]),
                        np.array([h_max2, s_max, v_max]))
    mask = cv2.bitwise_or(mask1, mask2)

    # ─── Morphological Cleanup ─────────────────────────────────
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # ─── Contour Detection ─────────────────────────────────────
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

    flame_count = 0

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue

        flame_count += 1
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = w / float(h)

        # Corner-styled bounding box (modern look)
        cv2.rectangle(frame, (x, y), (x + w, y + h), ACCENT_GREEN, 2)
        cv2.putText(frame, f"FLAME  {int(area)} px²  AR:{aspect_ratio:.2f}",
                    (x, max(y - 10, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, ACCENT_GREEN, 2)

    # ─── FPS Calculation ───────────────────────────────────────
    now = time.time()
    fps = 1.0 / max(now - prev_time, 1e-6)
    prev_time = now

    # ═══════════════════════════════════════════════════════════
    #  DASHBOARD OVERLAY
    # ═══════════════════════════════════════════════════════════
    h_img, w_img = frame.shape[:2]

    # Semi-transparent top panel
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w_img, 90), PANEL_DARK, -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # Title
    cv2.putText(frame, "FLAME DETECTION SYSTEM",
                (20, 35), cv2.FONT_HERSHEY_DUPLEX, 0.9, TEXT_LIGHT, 1)

    # Status badge
    status_text  = "● FLAME DETECTED" if flame_count > 0 else "○ NO FLAME"
    status_color = ACCENT_RED if flame_count > 0 else ACCENT_GREEN
    cv2.putText(frame, status_text, (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

    # FPS + blob count (right side)
    cv2.putText(frame, f"FPS: {fps:5.1f}", (w_img - 180, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, TEXT_LIGHT, 1)
    cv2.putText(frame, f"Blobs: {flame_count}", (w_img - 180, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, TEXT_DIM, 1)

    # Bottom threshold strip
    info = (f"H:[{h_min1}-{h_max1}]∪[{h_min2}-{h_max2}]  "
            f"S:[{s_min}-{s_max}]  V:[{v_min}-{v_max}]  MinArea:{min_area}")
    cv2.putText(frame, info, (20, h_img - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, TEXT_DIM, 1)

    # ─── Display ───────────────────────────────────────────────
    cv2.imshow(WINDOW_MAIN, frame)
    cv2.imshow(WINDOW_MASK, mask)

    key = cv2.waitKey(1) & 0xFF
    if key in (ord('q'), 27):       # Q or ESC to quit
        break

cap.release()
cv2.destroyAllWindows()