import cv2
import numpy as np
import os
import time
from ultralytics import YOLO

# ================== تنظیمات ==================
# اگر آدرس عکس اینجا داده شود، از عکس استفاده می‌شود.
# اگر خالی باشد (""), از استریم دوربین استفاده می‌شود.
IMAGE_PATH = r"image.JPG"   # مثلا: r"test.jpg"  یا  r"C:\images\tree.jpg"

# --- آدرس استریم دوربین (در صورت خالی بودن IMAGE_PATH) ---
STREAM_URL = (
    "http://192.168.0.186:8080/stream?topic=/main_camera/image_raw&type=mjpeg"
    "&width=640"
)

# --- مدل آموزش‌دیده ---
MODEL_PATH = r"weights.pt"
model = YOLO(MODEL_PATH)

# --- آستانه‌های confidence ---
CONF_TREE    = 0.60
CONF_DEFAULT = 0.60

# --- حداقل اندازه جسم ---
MIN_BOX_AREA_PX = 800

# --- نام‌های کلاس درخت ---
CLASS_TREE_NAMES = {"tree", "trees", "درخت"}

# --- تنظیمات تشخیص "افت" (نقاط غیرسبز داخل درخت) ---
PEST_MIN_AREA_PX   = 35     # افزایش یافت: حداقل مساحت لکه برای جلوگیری از نویزهای ریز
PEST_MIN_WIDTH_PX  = 6      # حداقل عرض کادر افت
PEST_MIN_HEIGHT_PX = 6      # حداقل ارتفاع کادر افت
PEST_MAX_ASPECT_RATIO = 3.0 # حداکثر نسبت اضلاع (برای حذف خطوط نازک)
PEST_SAT_THRESHOLD = 60     # حداقل اشباع رنگ
PEST_MIN_CONF      = 80.0   # فقط افت‌هایی با دقت ≥ 80% نمایش داده شوند
# =============================================


def get_conf_threshold(class_name: str) -> float:
    n = class_name.lower()
    if n in CLASS_TREE_NAMES:
        return CONF_TREE
    return CONF_DEFAULT


def _detect_pests_in_roi(frame_bgr, x1, y1, x2, y2):
    """
    داخل ناحیه درخت، پیکسل‌هایی که سبز نیستند را به‌عنوان «افت» تشخیص می‌دهد
    و با اعمال فیلترهای هندسی، از کشیدن کادرهای الکی جلوگیری می‌کند.
    """
    roi = frame_bgr[y1:y2, x1:x2]
    if roi.size == 0:
        return []

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # ماسک سبز (سالم)
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([95, 255, 255])
    green_mask = cv2.inRange(hsv, lower_green, upper_green)

    # ماسک غیرسبزِ اشباع‌دار (لکه‌های رنگی مثل قرمز/قهوه‌ای)
    sat_mask = cv2.inRange(hsv, np.array([0, PEST_SAT_THRESHOLD, 30]),
                                np.array([180, 255, 255]))

    # غیرسبز + اشباع‌دار = کاندید افت
    pest_mask = cv2.bitwise_and(sat_mask, cv2.bitwise_not(green_mask))

    # تمیزکاری مورفولوژیک (کرنل کمی بزرگتر برای حذف نقاط تک‌پیکسلی)
    kernel = np.ones((3, 3), np.uint8)
    pest_mask = cv2.morphologyEx(pest_mask, cv2.MORPH_OPEN, kernel)
    pest_mask = cv2.morphologyEx(pest_mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(pest_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    pests = []
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < PEST_MIN_AREA_PX:
            continue
            
        px, py, pw, ph = cv2.boundingRect(cnt)
        
        # --- فیلترهای هندسی جدید برای جلوگیری از کادرهای الکی ---
        if pw < PEST_MIN_WIDTH_PX or ph < PEST_MIN_HEIGHT_PX:
            continue  # لکه‌های خیلی نازک یا کوچک رد می‌شوند
            
        aspect_ratio = float(pw) / float(ph) if ph > 0 else 0
        if aspect_ratio > PEST_MAX_ASPECT_RATIO or aspect_ratio < (1.0 / PEST_MAX_ASPECT_RATIO):
            continue  # لکه‌های بیش از حد کشیده (مثل خط) رد می‌شوند
        # -----------------------------------------------------

        box_area = pw * ph
        if box_area == 0:
            continue
            
        cnt_mask = np.zeros((ph, pw), np.uint8)
        cnt_shifted = cnt - [px, py]
        cv2.drawContours(cnt_mask, [cnt_shifted], -1, 255, -1)
        pest_pixels = cv2.countNonZero(cnt_mask)
        
        # محاسبه دقت
        pest_conf = min(98.0, 60.0 + (pest_pixels / box_area) * 38.0)

        # فقط افت‌هایی با دقت ≥ 80%
        if pest_conf < PEST_MIN_CONF:
            continue

        pests.append((pest_conf, x1 + px, y1 + py, pw, ph))
        
    return pests


def detect_trees(frame):
    """تشخیص درخت با YOLO + تشخیص افت داخل باکس درخت."""
    annotated_frame = frame.copy()
    results = model.predict(frame, verbose=False)
    r = results[0]

    if r.boxes is not None and len(r.boxes) > 0:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            class_name = model.names[cls_id]

            # فقط کلاس درخت
            if class_name.lower() not in CLASS_TREE_NAMES:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            x1 = max(0, x1); y1 = max(0, y1)
            x2 = min(annotated_frame.shape[1], x2)
            y2 = min(annotated_frame.shape[0], y2)

            w = max(0, x2 - x1)
            h = max(0, y2 - y1)
            area = w * h

            if area < MIN_BOX_AREA_PX:
                continue

            if conf < get_conf_threshold(class_name):
                continue

            # کادر سبز درخت
            label = f"{class_name} {conf*100:.1f}%"
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(annotated_frame, label, (x1, max(15, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)

            # تشخیص افت داخل باکس درخت (فقط ≥ 80%)
            pests = _detect_pests_in_roi(annotated_frame, x1, y1, x2, y2)
            for pest_conf, px, py, pw, ph in pests:
                cv2.rectangle(annotated_frame, (px, py), (px + pw, py + ph),
                              (0, 0, 255), 2)
                cv2.putText(annotated_frame,
                            f"Pest {pest_conf:.1f}%",
                            (px, max(15, py - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                            (0, 0, 255), 1, cv2.LINE_AA)

            if pests:
                cv2.putText(annotated_frame,
                            "Pest Detected!",
                            (x1, min(annotated_frame.shape[0] - 10, y2 + 22)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                            (0, 0, 255), 2, cv2.LINE_AA)

    cv2.putText(annotated_frame, "Tree & Pest Detection", (15, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA)

    return annotated_frame


def run_on_image(path):
    if not os.path.isfile(path):
        print(f"فایل عکس پیدا نشد: {path}")
        return
    frame = cv2.imread(path)
    if frame is None:
        print("عکس قابل خواندن نیست.")
        return
    annotated = detect_trees(frame)
    cv2.imshow("Tree & Pest Detection", annotated)
    print("برای بستن پنجره هر کلیدی را بزنید...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def run_on_stream(url):
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        print("استریم باز نشد.")
        return
    print("برای خروج 'q' را بزنید.")
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue
        annotated = detect_trees(frame)
        cv2.imshow("Tree & Pest Detection", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    if IMAGE_PATH.strip():
        run_on_image(IMAGE_PATH)
    else:
        run_on_stream(STREAM_URL)