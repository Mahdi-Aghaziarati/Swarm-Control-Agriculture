
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np
import rospy
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger
from technic import srv
from led_msgs.srv import SetLEDs
from led_msgs.msg import LEDState



state_lock = threading.Lock()
latest_jpeg = None
target_state = {
    "detected": False,
    "error_x": 0.0,
    "error_y": 0.0,
    "last_seen": 0.0,
}


led_detection_event = threading.Event()

get_telemetry = None
navigate = None
land = None


class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/video"):
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header(
            "Content-Type",
            "multipart/x-mixed-replace; boundary=FRAME"
        )
        self.end_headers()

        try:
            while not rospy.is_shutdown():
                with state_lock:
                    frame = latest_jpeg

                if frame is not None:
                    self.wfile.write(b"--FRAME\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(
                        ("Content-Length: %d\r\n\r\n" % len(frame)).encode()
                    )
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")

                time.sleep(0.04)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format_string, *args):
        rospy.loginfo("Web stream: " + format_string % args)


def led_worker():
    """
    منتظر اولین تشخیص هدف می‌ماند و سپس LED فیزیکی ایندکس ۰
    را از طریق سرویس خود کوادکوپتر قرمز می‌کند.
    """
    while not rospy.is_shutdown():
        if led_detection_event.wait(timeout=0.2):
            break

    if rospy.is_shutdown():
        return

    rospy.loginfo("Hot target detected; requesting RED physical LED.")

    while not rospy.is_shutdown():
        try:
            rospy.wait_for_service("led/set_leds", timeout=5.0)
            set_leds = rospy.ServiceProxy("led/set_leds", SetLEDs)

            # دقیقاً مطابق نمونه ارسالی شما از داکیومنت کوادکوپتر:
            response = set_leds([
                LEDState(index=int(0), r=255, g=0, b=0)
            ])

            if hasattr(response, "success") and not response.success:
                raise RuntimeError(
                    getattr(response, "message", "LED service rejected request")
                )

            rospy.loginfo("RED command sent to the quadcopter LED, index 0.")
            return

        except (rospy.ROSException, rospy.ServiceException, RuntimeError) as exc:
            rospy.logwarn("Could not set physical LED to red: %s", exc)
            time.sleep(1.0)


def init_flight_services():
    global get_telemetry, navigate, land

    rospy.loginfo("Waiting for technic flight services...")
    rospy.wait_for_service("get_telemetry", timeout=10)
    rospy.wait_for_service("navigate", timeout=10)
    rospy.wait_for_service("land", timeout=10)

    get_telemetry = rospy.ServiceProxy(
        "get_telemetry", srv.GetTelemetry
    )
    navigate = rospy.ServiceProxy(
        "navigate", srv.Navigate
    )
    land = rospy.ServiceProxy(
        "land", Trigger
    )

    rospy.loginfo("Technic flight services connected.")


def navigate_wait(
    x=0.0, y=0.0, z=0.0, speed=0.4,
    frame_id="body", auto_arm=False, tolerance=0.2
):
    response = navigate(
        x=x,
        y=y,
        z=z,
        yaw=float("nan"),
        speed=speed,
        frame_id=frame_id,
        auto_arm=auto_arm,
    )

    if not response.success:
        raise RuntimeError("Navigate failed: " + response.message)

    while not rospy.is_shutdown():
        telemetry = get_telemetry(frame_id="navigate_target")
        distance = math.sqrt(
            telemetry.x ** 2
            + telemetry.y ** 2
            + telemetry.z ** 2
        )

        if distance < tolerance:
            return

        rospy.sleep(0.1)


def land_wait():
    rospy.loginfo("Executing landing...")
    response = land()

    if hasattr(response, "success") and not response.success:
        raise RuntimeError(
            "Land failed: "
            + getattr(response, "message", "unknown error")
        )

    while not rospy.is_shutdown():
        if not get_telemetry().armed:
            rospy.loginfo("Landing complete; vehicle disarmed.")
            return

        rospy.sleep(0.2)


def flight_mission_loop():
    """
    منطق پرواز نسخه قبلی حفظ شده است.
    کنترل LED مستقل از این تابع انجام می‌شود.
    """
    try:
        init_flight_services()

        rospy.loginfo("Starting mission: takeoff to 1.5 m...")
        navigate_wait(
            z=1.5,
            speed=0.5,
            frame_id="body",
            auto_arm=True,
        )
        rospy.loginfo("Takeoff target reached; searching for hot target.")

        search_deadline = time.monotonic() + 35.0
        target_locked = False

        while (
            not rospy.is_shutdown()
            and time.monotonic() < search_deadline
        ):
            with state_lock:
                detected = target_state["detected"]
                err_x = target_state["error_x"]
                err_y = target_state["error_y"]
                last_seen = target_state["last_seen"]

            if detected and time.monotonic() - last_seen < 0.5:
                if abs(err_x) < 0.12 and abs(err_y) < 0.12:
                    rospy.loginfo("Hot target centered in image.")
                    target_locked = True
                    break

                # نگاشت جهت‌ها از نسخه قبلی است؛ پیش از پرواز
                # باید با جهت نصب واقعی دوربین تطبیق داده شود.
                corr_y = -err_x * 0.35
                corr_x = -err_y * 0.35

                response = navigate(
                    x=corr_x,
                    y=corr_y,
                    z=0.0,
                    yaw=float("nan"),
                    speed=0.3,
                    frame_id="body",
                    auto_arm=False,
                )
                if not response.success:
                    raise RuntimeError(
                        "Tracking navigate failed: " + response.message
                    )

                rospy.sleep(0.35)
            else:
                rospy.sleep(0.2)

        if rospy.is_shutdown():
            return

        if target_locked:
            navigate_wait(
                z=-0.8,
                speed=0.3,
                frame_id="body",
                tolerance=0.15,
            )
            rospy.sleep(2.0)
        else:
            rospy.logwarn(
                "Search timed out; landing at current position."
            )

        land_wait()

    except (rospy.ROSException, rospy.ServiceException, RuntimeError) as exc:
        rospy.logerr("Flight mission error: %s", exc)


def main():
    global latest_jpeg

    rospy.init_node("thermal_integrated_flight_node", anonymous=True)

    pub = rospy.Publisher(
        "/thermal/image_raw", Image, queue_size=1
    )
    rate = rospy.Rate(25)

    cap = cv2.VideoCapture(2, cv2.CAP_V4L2)
    cap.set(
        cv2.CAP_PROP_FOURCC,
        cv2.VideoWriter_fourcc("Y", "U", "Y", "V"),
    )
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 256)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 384)
    cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)

    if not cap.isOpened():
        rospy.logerr("Cannot open thermal camera /dev/video2")
        cap.release()
        return

    # اگر پورت وب اشغال باشد، قبل از شروع مأموریت خطا مشخص می‌شود.
    try:
        web_server = ThreadingHTTPServer(
            ("0.0.0.0", 8088), StreamHandler
        )
    except OSError as exc:
        rospy.logerr("Cannot start web stream on port 8088: %s", exc)
        cap.release()
        return

    threading.Thread(
        target=web_server.serve_forever,
        daemon=True,
    ).start()

    rospy.loginfo(
        "Web stream active: http://10.42.0.1:8088/video"
    )

    # کنترل LED مستقل از ترد پرواز است؛ پس لازم نیست منتظر
    # پایان takeoff یا navigate_wait بماند.
    threading.Thread(target=led_worker, daemon=True).start()

    msg = Image()
    msg.encoding = "bgr8"
    msg.is_bigendian = 0
    msg.width = 512
    msg.height = 384
    msg.step = 512 * 3
    msg.header.frame_id = "thermal_optical_frame"

    flight_thread_started = False

    try:
        while not rospy.is_shutdown():
            ret, frame = cap.read()

            if not ret or frame is None:
                rospy.logwarn_throttle(
                    5, "Cannot read a frame from /dev/video2"
                )
                rate.sleep()
                continue

            if frame.shape[0] < 192 or frame.shape[1] < 256:
                rospy.logwarn_throttle(
                    5, "Unexpected thermal frame shape: %s"
                    % (frame.shape,)
                )
                rate.sleep()
                continue

            # پرواز پس از دریافت نخستین فریم معتبر شروع می‌شود.
            if not flight_thread_started:
                threading.Thread(
                    target=flight_mission_loop,
                    daemon=True,
                ).start()
                flight_thread_started = True

            # نیمه بالایی فریم 256x384، تصویر حرارتی است.
            thermal = frame[:192, :256]
            gray = (
                thermal[:, :, 0]
                if thermal.ndim == 3
                else thermal
            )

            norm = cv2.normalize(
                gray, None, 0, 255,
                cv2.NORM_MINMAX,
                dtype=cv2.CV_8U,
            )
            bgr = cv2.applyColorMap(
                norm, cv2.COLORMAP_INFERNO
            )
            resized = cv2.resize(
                bgr, (512, 384),
                interpolation=cv2.INTER_LINEAR,
            )

            height, width = resized.shape[:2]

            # معیار تشخیص هدف داغ مطابق منطق نسخه قبلی.
            resized_gray = cv2.cvtColor(
                resized, cv2.COLOR_BGR2GRAY
            )
            _, thresholded = cv2.threshold(
                resized_gray, 205, 255,
                cv2.THRESH_BINARY,
            )

            contours, _ = cv2.findContours(
                thresholded,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE,
            )

            found_target = False

            if contours:
                largest = max(
                    contours, key=cv2.contourArea
                )
                area = cv2.contourArea(largest)

                if area > 45:
                    rx, ry, rw, rh = cv2.boundingRect(
                        largest
                    )
                    cx = rx + rw // 2
                    cy = ry + rh // 2

                    error_x = (
                        cx - width / 2.0
                    ) / (width / 2.0)
                    error_y = (
                        cy - height / 2.0
                    ) / (height / 2.0)

                    with state_lock:
                        target_state["detected"] = True
                        target_state["error_x"] = error_x
                        target_state["error_y"] = error_y
                        target_state["last_seen"] = (
                            time.monotonic()
                        )

                    found_target = True

                    # فرمان تغییر رنگ LED فیزیکی، فقط در اولین
                    # تشخیص فعال می‌شود و در ترد جدا اجرا می‌شود.
                    led_detection_event.set()

                    # کادر تصویری همچنان سبز است.
                    cv2.rectangle(
                        resized,
                        (rx, ry),
                        (rx + rw, ry + rh),
                        (0, 255, 0),
                        2,
                    )
                    cv2.circle(
                        resized,
                        (cx, cy),
                        4,
                        (0, 0, 255),
                        -1,
                    )

                    label = "Hot Target"
                    text_y = max(18, ry - 7)
                    cv2.putText(
                        resized,
                        label,
                        (rx, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1,
                        cv2.LINE_AA,
                    )

            if not found_target:
                with state_lock:
                    target_state["detected"] = False

            cv2.drawMarker(
                resized,
                (width // 2, height // 2),
                (255, 255, 255),
                cv2.MARKER_CROSS,
                20,
                1,
            )

            encoded_ok, jpeg = cv2.imencode(
                ".jpg",
                resized,
                [int(cv2.IMWRITE_JPEG_QUALITY), 80],
            )
            if encoded_ok:
                with state_lock:
                    latest_jpeg = jpeg.tobytes()

            msg.header.stamp = rospy.Time.now()
            msg.data = resized.tobytes()
            pub.publish(msg)

            rate.sleep()

    finally:
        cap.release()
        web_server.shutdown()
        web_server.server_close()


if __name__ == "__main__":
    try:
        main()
    except rospy.ROSInterruptException:
        pass
