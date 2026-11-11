markdown
# Autonomous Fire Detection and Mapping Drone (ROS / Technic Platform)

This repository contains an autonomous Python script designed for the Technic / COEX drone platform running under ROS (Robot Operating System) and Gazebo simulation. The drone systematically scans an ArUco marker-defined field, detects fire targets via computer vision, marks them with bounding boxes, provides visual feedback using onboard LEDs, and logs precise spatial coordinates.

---

## Features

- **Autonomous Grid Scanning:** Executes a lawnmower (zig-zag) search pattern across the entire ArUco map area at a controlled low altitude for precision computer vision.
- **Real-Time Fire Detection:** Utilizes OpenCV with HSV color space filtering and contour analysis to detect red fire-like objects from the downward-facing camera feed (`main_camera/image_raw_throttled`).
- **Visual Bounding Box & Snapshot:** Automatically draws bounding boxes around detected fire targets, labels them, and saves snapshot evidence locally (`/home/technic/Desktop/fire_detected_bbox.png`).
- **Telemetry Logging:** Retrieves and prints exact 3D spatial coordinates (`aruco_map` frame) of the detected fire in the terminal.
- **Onboard LED Feedback:** Interacts with the `led/set_leds` ROS service to flash red upon fire detection, subsequently switching to a solid yellow state.
- **Robust Landing Mechanism:** Implements a fail-safe landing routine upon completion or service interruption.

---

## Prerequisites

- ROS (Melodic / Noetic)
- Python 3 with `rospy` and `opencv-python` (`cv_bridge`)
- Technic simulation environment and packages (`technic`, `led_msgs`)

---

## Usage

1. Clone this repository or place the script in your workspace.
2. Launch your Gazebo simulation with the ArUco map world:
```bash
   roslaunch technic_simulation simulator.launch
   
