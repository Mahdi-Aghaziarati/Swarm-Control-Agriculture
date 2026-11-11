# ArUco Studio Desktop

A standalone Python desktop application with an English interface. No Streamlit, browser, web server, or cloud service is required. Images are processed locally.

## Quick start on Windows (Python 3.12)

Open PowerShell in the extracted project folder (the folder containing `app.py`). Alternatively, double-click `Setup_Windows.bat` once to create a local Python 3.12 environment and install dependencies from PyPI. Then double-click `Run_Desktop.bat` to launch. Setup requires internet access and stops if installation fails.

Manual setup:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip --index-url https://pypi.org/simple
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --index-url https://pypi.org/simple
.\.venv\Scripts\python.exe app.py
```

If `.venv` already exists and uses another Python version, rename it before creating the new environment. This does not change the system Python or any other project. Internet access is required for dependency installation, not for normal image analysis.

After the first successful installation, launch with:

```powershell
.\.venv\Scripts\python.exe app.py
```

You can also double-click `Run_Desktop.bat`. It uses this folder's `.venv` explicitly and does not install packages or change system settings.

Do not use `streamlit run`. This is a native Tkinter application and can be launched directly as a Python script. In VS Code select `.venv\Scripts\python.exe` as the interpreter before using Run Python File.

### Dependencies

- Python 3.12 is recommended for this package.
- Tkinter is included with the standard Windows Python installer (enable Tcl/Tk support).
- `opencv-contrib-python-headless` provides `cv2` and ArUco. The headless build is intentional: Tkinter handles windows and OpenCV handles image processing and camera capture.
- NumPy and Pillow are the other dependencies. Streamlit, Plotly, pandas, and a browser are not needed.
- Use a fresh environment. Do not mix `opencv-python`, `opencv-contrib-python`, and their headless variants in the same environment; they all install into `cv2`.

## Workflow

1. Open an image, load the included demo, or take a camera snapshot.
2. Select a known dictionary, or use AUTO to compare supported dictionaries.
3. Click **Analyze Image**. Analysis runs on a background thread to keep the UI usable.
4. Inspect the annotated image, marker table, and diagnostics tab.
5. Export all results as ZIP, JSON, CSV, or annotated PNG.

The demo contains 45 unique IDs, 100 through 144. `DICT_4X4_250` and `DICT_4X4_1000` tie on the demo. The selected dictionary is therefore a suggestion, not proof of the dictionary used to print the markers.

### Viewer and marker data

- Fit-to-window, zoom, and drag-to-pan.
- Toggle original image, ID labels, and centers.
- Filter image overlays by comma-separated IDs. Leave blank to show all markers.
- Sort table columns by clicking their headings.
- Select a row to inspect corners, perimeter, side ratio, bit audit, and optional 3D pose.
- All pixel coordinates refer to the EXIF-oriented input, with origin at the top-left; X increases rightward and Y downward.
- Corners follow OpenCV's decoded marker ordering. Orientation is the angle of the first edge in image coordinates, not a calibrated world orientation.
- Export files always contain all detected markers. The display filter does not remove data from exports.

### Detection settings

- **Enhanced processing:** applies CLAHE and, for images up to 6 MP, a 2x detection pass. Spatial duplicates are merged; repeated physical markers sharing an ID remain separate instances.
- **Detect inverted markers:** enables inverted-polarity detection.
- **Error correction rate:** multiplier of the dictionary's supported correction capacity, not an accuracy or confidence score. Default: 0.35.
- **Border bits:** must match the printed border width in marker cells. Default: 1.
- **AUTO:** ranks dictionaries on original-image detections using count and bit-match diagnostics. Enhancement is then run for the selected dictionary only. Families are not merged. AUTO can miss a better dictionary on a heavily degraded image; use the known print dictionary when possible.
- ID conflicts across processing passes are retained in the report for manual review. Earlier detections are kept rather than silently overwritten.
- Images larger than 24 MP are rejected to limit resource use.

## Optional calibrated 3D pose

Without calibration, analysis is in pixels only. Distances in meters cannot be inferred reliably from an arbitrary image alone.

Load a JSON file containing **real calibration values for the camera and image dimensions in use**:

```json
{
  "camera_matrix": [[800, 0, 320], [0, 800, 240], [0, 0, 1]],
  "dist_coeffs": [0, 0, 0, 0, 0],
  "image_width": 640,
  "image_height": 480
}
```

These numbers are illustrative, not a calibration for your camera. Dimensions must match the EXIF-oriented image exactly. Cropping, resizing, lens changes, and image rotation can invalidate calibration.

Enter the physical outer black-square side length in meters. With calibration loaded, analysis adds rotation vectors, translation vectors in meters, Euclidean camera-to-marker distance, and reprojection RMSE. The coordinate convention is OpenCV camera coordinates (+X right, +Y down, +Z forward). The marker origin is its center. Planar pose ambiguity can remain; low reprojection error does not guarantee physical accuracy. Clear calibration to return to 2D-only analysis.

## Camera

Camera Snapshot opens a local camera by index (usually 0). Capture a still frame and then run analysis in the main window. This is still-image analysis, not continuous real-time tracking. Device access depends on OS permissions and camera availability; close other apps using the camera if necessary.

## Exports

The ZIP bundle contains:

- `report.json`: complete analysis, settings, warnings, dictionary ranking, geometry, and optional pose.
- `markers.csv`: one row per marker instance, including JSON-encoded corners and optional pose.
- `annotated.png`: all detected markers with ID overlays.
- `original.png`: the EXIF-oriented image used for analysis.
- `README.txt`: export notes.

## Command-line analysis

The engine also works without the GUI:

```powershell
.\.venv\Scripts\python.exe engine.py samples\demo.webp --output output
.\.venv\Scripts\python.exe engine.py image.png --dictionary DICT_4X4_250 --output output
```

The CLI saves JSON and annotated PNG. Use the desktop app for CSV and ZIP exports.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Engine tests cover the supplied demo, duplicate IDs, rotation, blur/perspective, blank images, wrong dictionaries, loading, calibration, and synthetic calibrated pose. Desktop helper tests cover CSV output. GUI smoke tests run when a graphical display is available and are skipped otherwise. Test results obtained in the build environment are recorded in `BUILD_NOTES.md`.

## Troubleshooting

### No module named cv2 / PIL

Dependencies are not installed in the interpreter running the app. Use the explicit `.venv` commands above. The OpenCV package name is not `cv2`.

### No module named tkinter

Repair the official Windows Python installation and enable Tcl/Tk support. Tkinter is not installed using `pip install tkinter`. On Linux, a system Tk package and graphical display may be needed.

### Cannot find a matching package version

Check `.venv\Scripts\python.exe --version` and use Python 3.12. Upgrade pip in that environment. A stale private package index can hide package versions; the installation commands above explicitly select PyPI. If installation still fails, examine the first error in the installation log before trying to run the app.

### No markers detected

Check the print dictionary, border setting, focus, contrast, image resolution, and the presence of sufficient white margin around each black marker. Try enhanced processing and inverted-marker detection when appropriate. No software can guarantee perfect decoding of arbitrary blurred or occluded images.

## Project files

```text
app.py                 Native Tkinter desktop UI (all English)
engine.py              Detection, image loading, bit audit, geometry, pose, CLI
exports.py             CSV serialization helpers
requirements.txt       Three external dependencies
Setup_Windows.bat      One-time local Python 3.12 setup
Run_Desktop.bat        Windows launcher using local .venv
README.md              Setup and usage
BUILD_NOTES.md         Build verification and limitations
samples/demo.webp      Included test image
tests/                 Engine, export, and desktop smoke tests
```
