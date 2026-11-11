import cv2
import numpy as np
import os

# ================== Settings ==================
# If an image path is provided, it will be used.
# If empty (""), it will fall back to the camera stream.
IMAGE_PATH = r""   # e.g., r"test.jpg" or r"C:\images\fire.jpg"

# --- Camera stream URL (used if IMAGE_PATH is empty) ---
STREAM_URL = (
    "http://192.168.0.186:8080/stream?topic=/main_camera/image_raw&type=mjpeg"
    "&width=640"
)

# --- Fire detection thresholds ---
CONF_FIRE        = 0.60   # Minimum initial confidence (0..1)
MIN_FIRE_AREA_PX = 300
MIN_BOX_AREA_PX  = 800
# =============================================


def _fire_confidence(hsv, red_mask, x, y, w, h, box_area):
    """Calculate confidence for a fire candidate."""
    roi_mask = red_mask[y:y+h, x:x+w]
    roi_hsv  = hsv[y:y+h, x:x+w]
    non_zero = cv2.countNonZero(roi_mask)
    pixel_ratio = non_zero / box_area if box_area > 0 else 0.0
    mean_val = float(np.mean(roi_hsv[:, :, 2])) / 255.0
    return min(98.0, max(60.0, pixel_ratio * 50.0 + mean_val * 50.0 + 30.0))


def _find_fire_candidates(frame, sat_min, val_min, morph_ksize, blur_ksize):
    """Find fire candidates using HSV thresholds."""
    blurred = cv2.GaussianBlur(frame, (blur_ksize, blur_ksize), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0,   sat_min, val_min]);  upper_red1 = np.array([10,  255, 255])
    lower_red2 = np.array([170, sat_min, val_min]);  upper_red2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = cv2.bitwise_or(mask1, mask2)

    kernel = np.ones((morph_ksize, morph_ksize), np.uint8)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_FIRE_AREA_PX:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        box_area = w * h
        if box_area < MIN_BOX_AREA_PX:
            continue
        conf = _fire_confidence(hsv, red_mask, x, y, w, h, box_area)
        # Keep only candidates that meet the initial confidence threshold
        if conf >= CONF_FIRE * 100.0:
            candidates.append((conf, x, y, w, h))
    return candidates


def detect_fire(frame):
    """
    Detect fire (red color only) using HSV and adaptive boosting.
    Only candidates with confidence >= CONF_FIRE*100 are drawn.
    """
    annotated_frame = frame.copy()

    sat_min      = 120
    val_min      = 70
    morph_ksize  = 5
    blur_ksize   = 5

    accepted = []

    # Try up to a few iterations with relaxed thresholds to find fire
    for it in range(20):
        cands = _find_fire_candidates(frame, sat_min, val_min, morph_ksize, blur_ksize)
        if cands:
            accepted = cands
            break
        # Relax thresholds
        sat_min     = max(40,  sat_min - 10)
        val_min     = max(30,  val_min - 5)
        morph_ksize = max(3,   morph_ksize - 1) if morph_ksize > 3 else 3
        blur_ksize  = max(3,   blur_ksize  - 2) if blur_ksize  > 3 else 3

    # Draw accepted candidates (red boxes)
    for conf, x, y, w, h in accepted:
        cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (0, 0, 255), 3)
        cv2.putText(annotated_frame, f"Fire: {conf:.1f}%",
                    (x, max(20, y - 10)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 0, 255), 2, cv2.LINE_AA)

    # Overlay title
    cv2.putText(annotated_frame, "Fire Detection", (15, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)

    return annotated_frame


def run_on_image(path):
    """Run fire detection on a single image."""
    if not os.path.isfile(path):
        print(f"Image file not found: {path}")
        return
    frame = cv2.imread(path)
    if frame is None:
        print("Could not read the image.")
        return
    annotated = detect_fire(frame)
    cv2.imshow("Fire Detection", annotated)
    print("Press any key to close the window...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def run_on_stream(url):
    """Run fire detection on a live camera stream."""
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        print("Could not open the stream.")
        return
    print("Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            continue
        annotated = detect_fire(frame)
        cv2.imshow("Fire Detection", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    if IMAGE_PATH.strip():
        run_on_image(IMAGE_PATH)
    else:
        run_on_stream(STREAM_URL)