# Drone Image Processing & Thermal Analysis

A structured repository dedicated to organizing, developing, and executing image processing and thermal analysis pipelines for drone-captured data. This repository serves as a workspace for testing computer vision algorithms, analyzing aerial imagery, and building modular Python-based processing scripts.

> Status: Under Active Development  
> Primary Language: Python

## Repository Structure
Module (A)/
└── Image process & Termal/
└── Drone Topic main/
└── Code/
├── README.md
├── requirements.txt
├── src/
├── data/
│   ├── raw/
│   └── processed/
├── outputs/
└── notebooks/
Directory Guide
Module (A)/: Top-level project module or domain container.
Image process & Termal/: Specific sub-module focusing on image processing and thermal data analysis. (Note: The current path preserves the folder name Termal; standard technical spelling is Thermal).
Drone Topic main/: Core thematic folder dedicated to drone-related applications.
Code/: Working directory containing source code, configurations, data partitions, and documentation.
src/: Core source code directory for processing modules and pipeline scripts.
data/raw/: Immutable raw input imagery and datasets.
data/processed/: Intermediate or preprocessed datasets resulting from initial transformations.
outputs/: Final results including processed images, segmentation masks, and analytical plots.
notebooks/: Exploratory data analysis, prototyping, and testing via Jupyter Notebooks.
Requirements
Python 3.10 or higher
pip package manager
Dependencies are managed via requirements.txt. Example stack:

text
opencv-python
numpy
matplotlib
scikit-image
openpyxl
Installation
Navigate to the Code directory from your terminal and install the required dependencies:

bash
cd "Module (A)/Image process & Termal/Drone Topic main/Code"
python -m venv .venv
Activate the virtual environment on Windows (PowerShell):

powershell
.venv\Scripts\Activate.ps1
Activate on Linux or macOS:

bash
source .venv/bin/activate
Install the dependencies:

bash
python -m pip install -r requirements.txt
Usage
Place executable processing scripts inside the src/ directory. For instance, to run the main pipeline script:

bash
python src/main.py
Note: Always construct paths dynamically using Python’s pathlib relative to the repository root. Avoid hardcoding local absolute paths (e.g., C:\Users\...).

Processing Pipeline
Typical workflow for handling drone and thermal imagery:

Read RGB aerial imagery and thermal radiometric data.
Verify image dimensions, color spaces, and data types.
Perform geometric and radiometric alignment (registration) between RGB and thermal channels if applicable.
Extract features or apply domain-specific image filters.
Apply thresholding techniques and analyze thermal zones/anomalies.
Export processed visualizations, masks, or numerical metrics to the outputs/ directory.
Simple snippet to load an image using OpenCV:

python
from pathlib import Path
import cv2

# Define path relative to the code/src structure
project_dir = Path(__file__).resolve().parents[1]
image_path = project_dir / "data" / "raw" / "sample.jpg"

image = cv2.imread(str(image_path))

if image is None:
raise FileNotFoundError(f"Failed to load image at: {image_path}")

print(f"Image shape: {image.shape}")
Caution: Thermal images often store raw temperature/intensity arrays rather than standard 8-bit RGB values. Verify file formats and metadata (e.g., TIFF metadata) before quantitative analysis; pseudo-color mapping alone does not preserve absolute temperature data.

Data Guidelines
Use short, descriptive, and lowercase filenames (e.g., flight01_thermal_001.tif).
Keep raw data strictly immutable inside data/raw/.
Choose appropriate formats depending on the sensor (e.g., standard jpg/png for visual checks, tif or raw sensor formats for quantitative thermal data).
Avoid committing large datasets directly to Git history. Utilize Git LFS (Large File Storage) or external storage solutions for heavy files.
Ensure no sensitive operational data, flight logs with coordinates, or API keys are committed to public repositories.
Development Conventions
Write clean, modular code with descriptive variable and function names.
Use pathlib for robust cross-platform path management.
Maintain a proper .gitignore file to exclude virtual environments, cache folders (__pycache__), and temporary outputs.
Follow Conventional Commits for clear version history:
feat: add thermal thresholding module
fix: handle unreadable or corrupted input frames
docs: update setup and execution guidelines
Limitations & Roadmap
Items slated for future development and refinement:

Define camera specifications (RGB & thermal sensor models) and native file formats.
Implement robust image registration and homography estimation between visual and thermal spectra.
Integrate temperature calibration models for quantitative thermal analysis (if calibration targets are available).
Add unit tests for core processing functions.
Provide a lightweight sample dataset for end-to-end pipeline testing.
License & Contact
This project currently lacks a specified license. Please add a LICENSE file before public distribution.

For issues, bug reports, or feature requests, please use the repository’s Issues tracker.

Path Naming Recommendation
The current path contains spaces, parentheses, and special characters (&), which require escaping or quoting in CLI shells and URLs. For optimal compatibility, consider refactoring folder names using kebab-case:

text
module-a/
└── image-processing-thermal/
└── drone-topic-main/
└── code/
