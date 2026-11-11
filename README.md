# Swarm Control — Protecting Agricultural Land Against Insect Pests

![Swarm UAV System](Image.jpeg)

A coordinated swarm-control system of small UAVs that autonomously surveys agricultural plantations, detects early signs of pest infestation using thermal/spectral sensing and neural networks, and reports infested coordinates to an operator web interface.

---

## 📌 Project Overview

| Item | Description |
|---|---|
| **Case** | Case 3 — Swarm Control |
| **Partner** | Agrotechnology Partner |
| **Swarm size** | 3 UAVs (minimum separation: 0.5 m) |
| **Detection method** | Thermal indicators (canopy temperature) + spectral indicators (leaf color) |
| **AI model** | Neural-network detection, mAP@0.5 ≥ 85% |
| **Max frame diagonal** | ≤ 10 inches (multirotor) |

### Key Features
- ✅ Autonomous flight along predefined routes
- ✅ Indoor autonomous control of 3 UAVs with a unified coordination algorithm
- ✅ Position synchronization and in-flight collision avoidance (≥ 0.5 m separation)
- ✅ Infestation detection via thermal / spectral indicators
- ✅ Coordinated response: leader assigns follow-up scan to follower drones
- ✅ Local coordinate determination and transmission to operator web UI
- ✅ Swarm status display (positions, zones, mission status, detections)
- ✅ Payload carrying and use by at least one drone
- ✅ Neural-network detection in thermal images (mAP@0.5 ≥ 85%)

---

## 🛠️ Dependencies

| Software / Library | Version | Purpose |
|---|---|---|
| Python | 3.9+ | Main development language |
| OpenCV | 4.x | Computer vision / image processing |
| PyTorch / YOLOv26 | latest | Neural-network detection model |
| DroneKit | latest | UAV control and telemetry |
| ROS 1 | Noetic | Middleware |
| Qss / Pyqt5| latest | Operator web interface backend |
| NumPy, Pandas | latest | Data processing |

---

## ⚙️ Installation

```bash
# 1. Clone the repository
git clone https://github.com/Mahdi-Aghaziarati/Swarm-Control-Agriculture.git
cd Swarm-Control-Agriculture

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# ===========================================
# Core / General
# ===========================================
numpy>=1.24.0,<3.0.0
opencv-python>=4.8.0
# opencv-python-headless>=4.8.0   # Use this instead on headless servers (no GUI)

# ===========================================
# YOLO / Deep Learning  (Tree & Fire.py)
# ===========================================
ultralytics>=8.0.0
torch>=2.0.0
torchvision>=0.15.0
# For GPU (CUDA 11.8 example), install from the official index:
#   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# ===========================================
# ROS 1 – Noetic  (Termal Drone object detection.py)
# ===========================================
# NOTE: The following are NOT installable via pip. Install them with apt / rosdep:
#   sudo apt install ros-noetic-ros-base
#   sudo apt install ros-noetic-cv-bridge ros-noetic-image-transport
#
# Custom packages used by the code (must exist in your catkin/colcon workspace):
#   technic
#   led_msgs
#
# Only the following Python packages are pip-installable:
rospkg>=1.5.0
catkin-pkg>=0.5.2

# ===========================================
# Networking  (client socket.py / socket server.py)
# ===========================================
# The `socket` and `threading` modules are part of the Python standard library.
# No external dependency is required.

# ===========================================
# Optional / Utilities
# ===========================================
pillow>=10.0.0          # Image saving/display helpers
tqdm>=4.66.0            # Optional progress bars
