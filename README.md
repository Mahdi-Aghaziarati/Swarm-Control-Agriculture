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
| Python | 3.10+ | Main development language |
| OpenCV | 4.x | Computer vision / image processing |
| PyTorch / YOLOv8 | latest | Neural-network detection model |
| MAVSDK / DroneKit | latest | UAV control and telemetry |
| ROS 2 (optional) | Humble+ | Swarm coordination middleware |
| Flask / FastAPI | latest | Operator web interface backend |
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
