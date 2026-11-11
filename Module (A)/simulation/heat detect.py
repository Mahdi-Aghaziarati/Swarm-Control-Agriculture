import rospy
import cv2
from cv_bridge import CvBridge
from sensor_msgs.msg import Image

from technic import srv
from std_srvs.srv import Trigger
from led_msgs.msg import LEDStateArray, LEDRGB


rospy.init_node('fire_scan_node')

bridge = CvBridge()
latest_image = None

get_telemetry = rospy.ServiceProxy('get_telemetry', srv.GetTelemetry)
navigate = rospy.ServiceProxy('navigate', srv.Navigate)
land = rospy.ServiceProxy('land', Trigger)

# LED service proxy based on verified sim_leds_controller.cpp
try:
    set_leds_proxy = rospy.ServiceProxy('led/set_leds', led_msgs.srv.SetLEDs)
except Exception:
    set_leds_proxy = None


def set_led_color(r, g, b):
    if set_leds_proxy is not None:
        try:
            req = led_msgs.srv.SetLEDsRequest()
            # Assuming standard Technic LED strip length (e.g., 32 LEDs)
            for i in range(32):
                led = LEDRGB()
                led.index = i
                led.r = r
                led.g = g
                led.b = b
                req.leds.append(led)
            set_leds_proxy(req)
        except Exception:
            pass


def image_callback(msg):
    global latest_image
    try:
        latest_image = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
    except Exception:
        pass


def check_fire():
    global latest_image
    if latest_image is None:
        return False

    img = latest_image.copy()
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    mask1 = cv2.inRange(hsv, (0, 70, 70), (15, 255, 255))
    mask2 = cv2.inRange(hsv, (165, 70, 70), (180, 255, 255))
    mask = cv2.bitwise_or(mask1, mask2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for c in contours:
        if cv2.contourArea(c) > 30:
            x, y, w, h = cv2.boundingRect(c)
            # Draw bounding box around fire
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 3)
            cv2.putText(img, 'FIRE', (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # Save debug image with bounding box
            cv2.imwrite('/home/technic/Desktop/fire_detected_bbox.png', img)

            telem = get_telemetry(frame_id='aruco_map')
            print('-----------------------------------------')
            print('>>> FIRE DETECTED WITH BOUNDING BOX! <<<')
            print('Coordinates: X={:.2f}, Y={:.2f}, Z={:.2f}'.format(telem.x, telem.y, telem.z))
            print('-----------------------------------------')

            # LED Flash Red
            print('LED: Blinking Red...')
            for _ in range(3):
                set_led_color(255, 0, 0)
                rospy.sleep(0.5)
                set_led_color(0, 0, 0)
                rospy.sleep(0.5)

            # LED Solid Yellow
            print('LED: Solid Yellow')
            set_led_color(255, 255, 0)

            return True

    print('No fire in view')
    return False


rospy.Subscriber('main_camera/image_raw_throttled', Image, image_callback, queue_size=1)

print('Takeoff to lower altitude...')
# Lower altitude (z = 1.1m) for tighter camera field of view
navigate(z=1.1, frame_id='body', auto_arm=True)
rospy.sleep(5)

# Dense grid scan path with closer points for restricted FOV
scan_waypoints = [
    (-2.5, -1.2),
    (-1.2, -1.2),
    (0.0, -1.2),
    (1.2, -1.2),
    (2.5, -1.2),

    (2.5, 0.0),
    (1.2, 0.0),
    (0.0, 0.0),
    (-1.2, 0.0),
    (-2.5, 0.0),

    (-2.5, 1.2),
    (-1.2, 1.2),
    (0.0, 1.2),
    (1.2, 1.2),
    (2.5, 1.2)
]

for idx, (target_x, target_y) in enumerate(scan_waypoints, start=1):
    if rospy.is_shutdown():
        break

    print('Point {}/15 -> Moving to: x={}, y={}'.format(idx, target_x, target_y))
    navigate(frame_id='aruco_map', x=target_x, y=target_y, z=1.1, speed=0.4, auto_arm=True)
    rospy.sleep(5)

    check_fire()

print('Scan completed. Landing...')
try:
    land()
except Exception:
    navigate(frame_id='aruco_map', z=0.1, auto_arm=True)

rospy.sleep(5)
print('Finished')
