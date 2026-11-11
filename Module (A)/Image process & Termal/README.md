# Drone Image Processing & Thermal Analysis

A structured repository dedicated to organizing, developing, and executing image processing and thermal analysis pipelines for drone-captured data. This project serves as a comprehensive workspace for testing computer vision algorithms, analyzing aerial imagery, and building modular Python-based processing scripts.

---

## 📂 Repository Structure
```text
Module (A)/
└── Image process & Termal/
└── Drone Topic main/
└── Code/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   └── main.py
├── data/
│   ├── raw/
│   └── processed/
├── outputs/
└── notebooks/
📁 Directory Guide
Module (A)/: Top-level project domain container.
Image process & Termal/: Sub-module focusing on image processing and thermal data analysis. (Note: Preserving the folder name Termal; standard technical spelling is Thermal).
Drone Topic main/: Core thematic folder dedicated to drone-related aerial applications.
Code/: Main working directory containing source code, dependencies, and execution scripts.
src/: Core source code directory for processing modules and pipeline scripts.
data/raw/: Immutable raw input imagery and sensor datasets.
data/processed/: Intermediate or preprocessed datasets resulting from transformations.
outputs/: Final results including processed images, segmentation masks, and analytical plots.
notebooks/: Exploratory data analysis, prototyping, and testing via Jupyter Notebooks.
⚙️ Requirements & Dependencies
Python: 3.10 or higher
Package Manager: pip
Dependencies are managed via requirements.txt. The core stack includes:

opencv-python (Computer vision & image filtering)
numpy (Numerical computations and array manipulation)
matplotlib (Plotting and visualization)
scikit-image (Image processing algorithms)
openpyxl (Excel report generation for numerical metrics)
🚀 Installation & Setup
Navigate to the Code directory from your terminal and set up the environment:

Clone the repository and navigate to the code folder:
bash
   cd "Module (A)/Image process & Termal/Drone Topic main/Code"
   
Create and activate a virtual environment:
Windows (PowerShell):
powershell
python -m venv .venv
.venv\Scripts\Activate.ps1

Linux / macOS:
bash
python -m venv .venv
source .venv/bin/activate

Install dependencies:
bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   
💻 Usage & Execution
Place your input images inside data/raw/ and run the main processing script from the src/ directory:

bash
python src/main.py
Python Script Example (src/main.py)
The pipeline uses Python’s pathlib to ensure cross-platform compatibility without hardcoding local absolute paths:

python
from pathlib import Path
import cv2

# Define paths relative to the project root structure
ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT_DIR / "data" / "raw"
OUTPUT_DIR = ROOT_DIR / "outputs"

def run_pipeline(filename: str = "sample.jpg"):
input_path = INPUT_DIR / filename
output_path = OUTPUT_DIR / f"processed_{filename}"

if not input_path.exists():
raise FileNotFoundError(f"Input image not found at: {input_path}")

# Read image, convert to grayscale, and apply Canny edge detection
img = cv2.imread(str(input_path))
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(gray, 100, 200)

# Save output
cv2.imwrite(str(output_path), edges)
print(f"Processing complete. Result saved to: {output_path}")

if __name__ == "__main__":
run_pipeline()
🔬 Thermal & Aerial Imagery Guidelines
Raw Data Integrity: Always keep raw imagery in data/raw/ immutable; never overwrite original captures.
Thermal Data Caution: Thermal imagery often contains radiometric temperature/intensity matrices rather than standard 8-bit RGB values. Verify file formats (such as raw TIFF or metadata-rich formats) before quantitative analysis. Pseudo-color maps (like JET or VIRIDIS) visualize data but do not preserve absolute temperature values unless calibrated.
File Naming & LFS: Use short, lowercase, and descriptive filenames (e.g., flight01_thermal_001.tif). For large aerial datasets, use Git LFS (Large File Storage) instead of committing heavy binaries directly to Git history.
🛠️ Development Conventions
Conventional Commits: Follow structured commit messages for clear version control:
feat: add thermal thresholding module
fix: handle unreadable or corrupted input frames
docs: update installation guidelines
Exclusions: Maintain a .gitignore file to exclude .venv/, __pycache__/, and local outputs.
📌 Path Naming Recommendation
The current folder structure contains spaces, parentheses, and special characters (&), which require escaping in CLI shells and URLs. For optimal long-term compatibility, consider refactoring folder names using kebab-case:

text
module-a/
└── image-processing-thermal/
└── drone-topic-main/
└── code/
📄 License & Contact
This project is currently unlicensed. For questions, suggestions, or contributions, please open an issue in the repository.
