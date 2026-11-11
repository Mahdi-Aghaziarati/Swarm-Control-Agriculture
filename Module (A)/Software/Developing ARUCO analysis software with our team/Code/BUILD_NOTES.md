# Build verification

## Completed

- Python syntax compilation passed for app.py, engine.py, and exports.py.
- 14 automated engine/export/language tests passed.
- The GUI smoke-test class was skipped because the build environment does not have the Tk shared libraries required by Tkinter (libtk8.6.so).
- A real CLI analysis of samples/demo.webp found 45 unique marker IDs: 100 through 144.
- The auto-selected dictionary was DICT_4X4_250, tied with DICT_4X4_1000. The English report records the ambiguity.
- Sample output files were generated under samples/result/.

## Not verified in this environment

- Opening and interacting with the desktop window on Windows.
- Camera device access and capture.
- Execution of the Windows .bat files.

The desktop application uses standard Tkinter from the official Windows Python installation. The application is provided as Python source, not as a frozen .exe. Runtime packages must be installed in the local virtual environment. No claim of a successful Windows GUI run is made.
