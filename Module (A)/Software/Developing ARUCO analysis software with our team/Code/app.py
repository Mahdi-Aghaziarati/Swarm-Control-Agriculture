"""ArUco Studio Desktop - launch with python app.py (no browser required)."""
from __future__ import annotations

from exports import COLUMNS, csv_bytes
import json
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import zipfile

import cv2
from PIL import Image, ImageTk

from engine import DICTIONARIES, Settings, analyze, annotate, encode_png, load_image

BG = "#101827"
PANEL = "#172338"
TEXT = "#e6edf6"
ACCENT = "#56d9bd"


class Studio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ArUco Studio | Desktop Image Analysis")
        self.geometry("1400x900")
        self.minsize(1050, 700)
        self.configure(bg=BG)
        self.image = self.report = self.display_image = None
        self.photo = None
        self.calibration = None
        self.busy = False
        self.results = queue.Queue()
        self.zoom = None
        self.camera = None
        self.camera_window = None
        self.closed = False
        self.dictionary = tk.StringVar(value="AUTO")
        self.enhanced = tk.BooleanVar(value=True)
        self.inverted = tk.BooleanVar(value=False)
        self.labels = tk.BooleanVar(value=True)
        self.centers = tk.BooleanVar(value=True)
        self.original = tk.BooleanVar(value=False)
        self.correction = tk.StringVar(value="0.35")
        self.border = tk.StringVar(value="1")
        self.length = tk.StringVar(value="0.05")
        self.filter_ids = tk.StringVar()
        self.status = tk.StringVar(value="Open an image or load the demo to get started.")
        self.summary = tk.StringVar(value="Markers: --     Unique IDs: --     Dictionary: --")
        self.calibration_label = tk.StringVar(value="No calibration loaded (2D analysis only).")
        self._style()
        self._layout()
        self.after(100, self._poll)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Control-o>", lambda _: self.open_image())

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("TFrame", background=BG)
        style.configure("TLabelframe", background=BG, bordercolor="#34465e")
        style.configure("TLabelframe.Label", background=BG, foreground=ACCENT)
        style.configure("TLabel", background=BG)
        style.configure("TButton", padding=(10, 7))
        style.map("TButton", background=[("active", "#32516b")])
        style.configure("TCheckbutton", background=BG)
        style.configure("TEntry", fieldbackground="#24344b", foreground=TEXT)
        style.configure("TCombobox", fieldbackground="#24344b", foreground=TEXT)
        style.map("TCombobox", fieldbackground=[("readonly", "#24344b")], foreground=[("readonly", TEXT)])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=27)
        style.configure("Treeview.Heading", background="#273c56", foreground=TEXT)
        style.map("Treeview", background=[("selected", "#286477")])
        style.configure("Title.TLabel", font=("Segoe UI", 23, "bold"), foreground=ACCENT)
        style.configure("Summary.TLabel", font=("Segoe UI", 12, "bold"))

    def _layout(self):
        header = ttk.Frame(self, padding=15)
        header.pack(fill="x")
        ttk.Label(header, text="ArUco Studio", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="DESKTOP  /  LOCAL IMAGE ANALYSIS").pack(side="left", padx=24)
        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=12)
        sidebar = ttk.Frame(body, padding=10, width=265)
        body.add(sidebar, weight=0)
        main = ttk.Frame(body)
        body.add(main, weight=1)
        for text, command in [("Open Image...", self.open_image), ("Load Demo", self.demo),
                              ("Camera Snapshot...", self.open_camera)]:
            ttk.Button(sidebar, text=text, command=command).pack(fill="x", pady=4)
        detection = ttk.LabelFrame(sidebar, text="Detection", padding=10)
        detection.pack(fill="x", pady=12)
        ttk.Label(detection, text="Marker dictionary").pack(anchor="w")
        ttk.Combobox(detection, textvariable=self.dictionary, values=["AUTO"] + DICTIONARIES,
                     state="readonly", width=24).pack(fill="x", pady=5)
        ttk.Checkbutton(detection, text="Enhanced processing", variable=self.enhanced).pack(anchor="w")
        ttk.Checkbutton(detection, text="Detect inverted markers", variable=self.inverted).pack(anchor="w")
        for label, variable in [("Error correction rate (0-1)", self.correction),
                                 ("Border bits (1, 2, or 3)", self.border)]:
            ttk.Label(detection, text=label).pack(anchor="w", pady=(8, 0))
            ttk.Entry(detection, textvariable=variable).pack(fill="x")
        self.analyze_button = ttk.Button(sidebar, text="Analyze Image", command=self.run_analysis)
        self.analyze_button.pack(fill="x", pady=4)
        self.progress = ttk.Progressbar(sidebar, mode="indeterminate")
        self.progress.pack(fill="x", pady=5)
        pose = ttk.LabelFrame(sidebar, text="Optional 3D Pose", padding=10)
        pose.pack(fill="x", pady=10)
        ttk.Button(pose, text="Load Calibration JSON...", command=self.load_calibration).pack(fill="x")
        ttk.Button(pose, text="Clear Calibration", command=self.clear_calibration).pack(fill="x", pady=4)
        ttk.Label(pose, textvariable=self.calibration_label, wraplength=230).pack(anchor="w")
        ttk.Label(pose, text="Marker side length (meters)").pack(anchor="w", pady=(8, 0))
        ttk.Entry(pose, textvariable=self.length).pack(fill="x")
        ttk.Button(sidebar, text="Export Results...", command=self.export).pack(fill="x", pady=10)
        ttk.Label(sidebar, text="Local processing. No upload required.\nSettings apply on the next analysis.",
                  wraplength=240).pack(anchor="w", pady=8)
        ttk.Label(main, textvariable=self.summary, style="Summary.TLabel", wraplength=1000).pack(fill="x", pady=10)
        tabs = ttk.Notebook(main)
        tabs.pack(fill="both", expand=True)
        view = ttk.Frame(tabs)
        table = ttk.Frame(tabs)
        diagnostics = ttk.Frame(tabs)
        tabs.add(view, text="Image Viewer")
        tabs.add(table, text="Marker Data")
        tabs.add(diagnostics, text="Diagnostics & Dictionary Scan")
        tools = ttk.Frame(view, padding=5)
        tools.pack(fill="x")
        for label, variable in [("Original", self.original), ("ID labels", self.labels), ("Centers", self.centers)]:
            ttk.Checkbutton(tools, text=label, variable=variable, command=self.refresh_image).pack(side="left", padx=4)
        ttk.Button(tools, text="Fit", command=self.fit).pack(side="left", padx=4)
        ttk.Button(tools, text="+", command=lambda: self.change_zoom(1.25)).pack(side="left")
        ttk.Button(tools, text="-", command=lambda: self.change_zoom(0.8)).pack(side="left")
        ttk.Label(tools, text="IDs:").pack(side="left", padx=(12, 3))
        ttk.Entry(tools, textvariable=self.filter_ids, width=16).pack(side="left")
        ttk.Button(tools, text="Apply", command=self.refresh_image).pack(side="left", padx=4)
        self.canvas = tk.Canvas(view, bg="#080e19", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self.draw())
        self.canvas.bind("<ButtonPress-1>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B1-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        ttk.Label(view, text="Drag to pan. Use + / - to zoom. ID filter: comma-separated integers; blank shows all.").pack(pady=5)
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(table, columns=COLUMNS, show="headings", selectmode="browse")
        headings = ["Instance", "ID", "Center X (px)", "Center Y (px)", "Side (px)",
                    "Area (px²)", "Angle (deg)", "Bit errors", "Border errors", "Source"]
        for key, heading in zip(COLUMNS, headings):
            self.tree.heading(key, text=heading, command=lambda k=key: self.sort_table(k))
            self.tree.column(key, width=110, minwidth=75)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sy = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        sy.grid(row=0, column=1, sticky="ns")
        sx = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        sx.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.bind("<<TreeviewSelect>>", self.marker_details)
        self.detail = tk.Text(table, height=9, bg=PANEL, fg=TEXT, wrap="word", font=("Consolas", 10))
        self.detail.grid(row=2, column=0, columnspan=2, sticky="ew")
        self._text(self.detail, "Select a marker to inspect corners, geometry, and optional pose.")
        self.diagnostics = tk.Text(diagnostics, bg=PANEL, fg=TEXT, wrap="word", font=("Consolas", 11))
        self.diagnostics.pack(fill="both", expand=True)
        self._text(self.diagnostics, "Run an analysis to see warnings and dictionary scores.")
        ttk.Label(self, textvariable=self.status, padding=10, wraplength=1350).pack(fill="x")

    @staticmethod
    def _text(widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def set_image(self, image, name):
        if self.busy:
            messagebox.showinfo("Analysis running", "Please wait for the current analysis to finish.")
            return
        self.image, self.report = image, None
        self.tree.delete(*self.tree.get_children())
        self._text(self.detail, "Select a marker after analysis to inspect its data.")
        self._text(self.diagnostics, "Run an analysis to see warnings and dictionary scores.")
        self.summary.set("Markers: --     Unique IDs: --     Dictionary: --")
        self.status.set(f"Loaded {name} | {image.shape[1]} x {image.shape[0]} pixels")
        self.zoom = None
        self.refresh_image()

    def open_image(self):
        if self.busy:
            return
        name = filedialog.askopenfilename(title="Open Image", filetypes=[
            ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"), ("All files", "*.*")])
        if name:
            self.read_path(Path(name))

    def read_path(self, path):
        try:
            self.set_image(load_image(path.read_bytes()), path.name)
        except Exception as exc:
            messagebox.showerror("Cannot open image", str(exc))

    def demo(self):
        if not self.busy:
            self.read_path(Path(__file__).parent / "samples" / "demo.webp")

    def load_calibration(self):
        if self.busy:
            return
        name = filedialog.askopenfilename(title="Load Calibration", filetypes=[("JSON", "*.json")])
        if name:
            try:
                data = json.loads(Path(name).read_text(encoding="utf-8-sig"))
                if not isinstance(data, dict):
                    raise ValueError("Calibration must be a JSON object.")
                for key in ("camera_matrix", "dist_coeffs", "image_width", "image_height"):
                    if key not in data:
                        raise ValueError(f"Missing calibration field: {key}")
                self.calibration = data
                self.calibration_label.set(f"Loaded: {Path(name).name}\nValidated when analysis starts.")
            except Exception as exc:
                messagebox.showerror("Invalid calibration", str(exc))

    def clear_calibration(self):
        if not self.busy:
            self.calibration = None
            self.calibration_label.set("No calibration loaded (2D analysis only).")

    def run_analysis(self):
        if self.busy:
            return
        if self.image is None:
            messagebox.showinfo("No image", "Open an image first.")
            return
        try:
            settings = Settings(self.dictionary.get(), self.enhanced.get(), self.inverted.get(),
                                float(self.correction.get()), int(self.border.get()))
            if not 0 <= settings.correction_rate <= 1 or settings.border_bits not in (1, 2, 3):
                raise ValueError("Correction rate must be 0-1; border bits must be 1, 2, or 3.")
            length = float(self.length.get()) if self.calibration is not None else None
        except ValueError as exc:
            messagebox.showerror("Invalid settings", str(exc))
            return
        self.busy = True
        self.analyze_button.configure(state="disabled")
        self.progress.start(12)
        self.status.set("Analyzing image... Auto dictionary scanning may take a moment.")
        image, calibration = self.image.copy(), self.calibration

        def worker():
            try:
                self.results.put((True, analyze(image, settings, calibration, length)))
            except Exception as exc:
                self.results.put((False, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _poll(self):
        try:
            ok, result = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.progress.stop()
            self.analyze_button.configure(state="normal")
            if ok:
                self.report = result
                self.show_report()
            else:
                self.status.set("Analysis failed. Any previous result remains unchanged.")
                messagebox.showerror("Analysis failed", result)
        if not self.closed:
            self.after(100, self._poll)

    def show_report(self):
        r = self.report
        self.summary.set(f"Markers: {r['count']}     Unique IDs: {len(r['unique_ids'])}     "
                         f"Dictionary: {r['dictionary']}     Time: {r['elapsed_ms']:.0f} ms")
        self.tree.delete(*self.tree.get_children())
        for m in r["markers"]:
            values = [f"{m[k]:.2f}" if isinstance(m[k], float) else m[k] for k in COLUMNS]
            self.tree.insert("", "end", iid=str(m["instance"]), values=values)
        self._text(self.detail, "Select a marker to inspect all values.")
        lines = ["ANALYSIS NOTES", "=" * 65, *r["warnings"], "", f"Image: {r['image']}",
                 f"OpenCV: {r['opencv_version']}", f"Settings: {r['settings']}",
                 f"Unique IDs: {r['unique_ids']}", f"Duplicate IDs: {r['duplicate_ids']}",
                 f"Tied dictionaries: {r['tied_dictionaries']}",
                 f"Rejected candidates (original pass): {r['rejected_candidates_original']}",
                 f"Conflicts: {json.dumps(r['conflicts'])}", "", "DICTIONARY SCAN (original image)",
                 "Dictionary                    Count   Zero-bit matches   Bit errors"]
        for item in r["dictionary_scan"]:
            lines.append(f"{item['dictionary']:<30}{item['count']:>5}{item['zero_bit_matches']:>19}{item['total_bit_errors']:>13}")
        lines += ["", "Bit errors are diagnostic Hamming distances, not confidence probabilities.",
                  "Pixel angles and geometry are image-plane measurements, not physical pose.",
                  "Exports always contain ALL detected markers, regardless of display filters."]
        self._text(self.diagnostics, "\n\n".join(lines[:2]) + "\n" + "\n".join(lines[2:]))
        self.status.set(f"Analysis complete: {r['count']} markers. Review the Diagnostics tab for limitations.")
        self.refresh_image()

    def selected_ids(self):
        text = self.filter_ids.get().strip()
        return {int(x.strip()) for x in text.split(",")} if text else None

    def refresh_image(self):
        if self.image is None:
            return
        try:
            selected = self.selected_ids()
        except ValueError:
            messagebox.showerror("Invalid ID filter", "Enter comma-separated integer IDs, such as 100,101,105.")
            return
        bgr = self.image
        if self.report and not self.original.get():
            bgr = annotate(bgr, self.report, self.labels.get(), self.centers.get(), selected)
        self.display_image = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        self.draw()

    def draw(self):
        if self.display_image is None:
            return
        w, h = self.display_image.size
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        scale = self.zoom if self.zoom is not None else min(cw / w, ch / h)
        # Bound rendered image memory while still allowing useful zoom.
        scale = max(0.02, min(scale, 5.0, 6000 / max(w, h)))
        size = (max(1, round(w * scale)), max(1, round(h * scale)))
        resized = self.display_image.resize(size, Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.create_image(max(cw, size[0]) / 2, max(ch, size[1]) / 2, image=self.photo)
        self.canvas.configure(scrollregion=(0, 0, max(cw, size[0]), max(ch, size[1])))

    def fit(self):
        self.zoom = None
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self.draw()

    def change_zoom(self, factor):
        if self.display_image is None:
            return
        if self.zoom is None:
            w, h = self.display_image.size
            self.zoom = min(self.canvas.winfo_width() / w, self.canvas.winfo_height() / h)
        self.zoom = max(0.02, min(self.zoom * factor, 5.0, 6000 / max(self.display_image.size)))
        self.draw()

    def sort_table(self, column):
        rows = [(self.tree.set(i, column), i) for i in self.tree.get_children()]
        def key(item):
            try:
                return float(item[0])
            except ValueError:
                return item[0]
        reverse = getattr(self, "last_sort", None) == (column, False)
        self.last_sort = (column, reverse)
        for index, (_, iid) in enumerate(sorted(rows, key=key, reverse=reverse)):
            self.tree.move(iid, "", index)

    def marker_details(self, _event=None):
        selected = self.tree.selection()
        if selected and self.report:
            marker = next(m for m in self.report["markers"] if str(m["instance"]) == selected[0])
            self._text(self.detail, json.dumps(marker, indent=2))

    def export(self):
        if self.report is None:
            messagebox.showinfo("No results", "Analyze an image before exporting.")
            return
        path = filedialog.asksaveasfilename(title="Export All Detected Markers", defaultextension=".zip",
            initialfile="aruco_results.zip", filetypes=[("Complete ZIP bundle", "*.zip"),
            ("JSON report", "*.json"), ("CSV marker table", "*.csv"), ("Annotated PNG", "*.png")])
        if not path:
            return
        try:
            destination = Path(path)
            report = json.dumps(self.report, indent=2).encode("utf-8")
            extension = destination.suffix.lower()
            if extension == ".json":
                destination.write_bytes(report)
            elif extension == ".csv":
                destination.write_bytes(csv_bytes(self.report))
            elif extension == ".png":
                destination.write_bytes(encode_png(annotate(self.image, self.report)))
            elif extension == ".zip":
                with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr("report.json", report)
                    archive.writestr("markers.csv", csv_bytes(self.report))
                    archive.writestr("annotated.png", encode_png(annotate(self.image, self.report)))
                    archive.writestr("original.png", encode_png(self.image))
                    archive.writestr("README.txt", "Exports contain all detections. Display filters are not applied.\n"
                        "Review report warnings, dictionary ambiguity, and calibration limitations.\n")
            else:
                raise ValueError("Choose a .zip, .json, .csv, or .png extension.")
            self.status.set(f"Saved: {destination}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def open_camera(self):
        if self.busy:
            return
        if self.camera_window is not None:
            self.camera_window.lift()
            return
        from tkinter.simpledialog import askinteger
        index = askinteger("Camera", "Camera device index (usually 0):", initialvalue=0, minvalue=0, maxvalue=20)
        if index is None:
            return
        capture = cv2.VideoCapture(index)
        if not capture.isOpened():
            capture.release()
            messagebox.showerror("Camera unavailable", "Cannot open camera. Check device index, permissions, and other apps.")
            return
        self.camera = capture
        self.camera_frame = None
        win = self.camera_window = tk.Toplevel(self)
        win.title("Camera Snapshot")
        win.transient(self)
        win.grab_set()
        self.camera_preview = ttk.Label(win)
        self.camera_preview.pack(padx=10, pady=10)
        ttk.Label(win, text="Capture a still image, then click Analyze Image in the main window.").pack(padx=10)
        ttk.Button(win, text="Capture Snapshot", command=self.capture_snapshot).pack(pady=10)
        win.protocol("WM_DELETE_WINDOW", self.close_camera)
        self.camera_tick()

    def camera_tick(self):
        if self.camera is None:
            return
        ok, frame = self.camera.read()
        if not ok:
            self.close_camera()
            messagebox.showerror("Camera error", "Unable to read a frame from the camera.")
            return
        self.camera_frame = frame
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        image.thumbnail((800, 550))
        self.camera_photo = ImageTk.PhotoImage(image)
        self.camera_preview.configure(image=self.camera_photo)
        self.camera_window.after(40, self.camera_tick)

    def capture_snapshot(self):
        if self.camera_frame is not None:
            frame = self.camera_frame.copy()
            self.close_camera()
            self.set_image(frame, "Camera snapshot")

    def close_camera(self):
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        if self.camera_window is not None:
            self.camera_window.destroy()
            self.camera_window = None

    def _close(self):
        self.closed = True
        self.close_camera()
        self.destroy()


if __name__ == "__main__":
    Studio().mainloop()
