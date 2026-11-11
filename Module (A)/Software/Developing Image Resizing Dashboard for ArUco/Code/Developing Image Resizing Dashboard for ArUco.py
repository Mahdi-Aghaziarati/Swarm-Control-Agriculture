"""
Image Resizer Dashboard
=======================
A modern GUI application that resizes images to a fixed physical size
(250 mm × 250 mm @ 144 DPI) and exports them as JPEG files.

Features:
    • Modern dark-themed dashboard layout
    • Drag-and-drop file selection
    • Live preview of the first selected image
    • Real-time conversion log
    • Progress bar with status counter
    • Configurable output size and DPI
"""

import os
import threading
import tkinter as tk
from dataclasses import dataclass, field
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


# ---------- Theme ----------
@dataclass(frozen=True)
class Theme:
    bg: str = "#0f172a"          # slate-900
    surface: str = "#1e293b"     # slate-800
    surface_alt: str = "#334155" # slate-700
    border: str = "#475569"      # slate-600
    text: str = "#f1f5f9"        # slate-100
    text_muted: str = "#94a3b8"  # slate-400
    accent: str = "#38bdf8"      # sky-400
    accent_hover: str = "#0ea5e9"# sky-500
    success: str = "#22c55e"     # green-500
    warning: str = "#f59e0b"     # amber-500
    danger: str = "#ef4444"      # red-500


THEME = Theme()


# ---------- Configuration ----------
@dataclass
class Config:
    mm_per_inch: float = 25.4
    target_size_mm: int = 250
    target_dpi: int = 144
    jpeg_quality: int = 95
    supported_extensions: tuple = (
        ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp",
    )

    @property
    def pixel_size(self) -> int:
        return int(round((self.target_size_mm / self.mm_per_inch) * self.target_dpi))


CONFIG = Config()


# ---------- Core logic ----------
def resize_image(input_path: str, output_path: str) -> int:
    """Resize an image to the configured physical size and save as JPEG."""
    size = CONFIG.pixel_size
    with Image.open(input_path) as img:
        if img.mode != "RGB":
            img = img.convert("RGB")
        resized = img.resize((size, size), Image.LANCZOS)
        resized.save(
            output_path, "JPEG",
            quality=CONFIG.jpeg_quality,
            dpi=(CONFIG.target_dpi, CONFIG.target_dpi),
        )
    return size


# ---------- Reusable widgets ----------
class Card(tk.Frame):
    """A rounded-looking surface card used to group content."""

    def __init__(self, master, title: str = "", **kwargs):
        super().__init__(
            master,
            bg=THEME.surface,
            highlightbackground=THEME.border,
            highlightthickness=1,
            bd=0,
            **kwargs,
        )
        if title:
            tk.Label(
                self, text=title, bg=THEME.surface, fg=THEME.text_muted,
                font=("Segoe UI", 9, "bold"), anchor="w",
            ).pack(fill="x", padx=16, pady=(12, 0))


class ActionButton(tk.Button):
    """A flat, modern button with hover feedback."""

    def __init__(self, master, text: str, command=None,
                 bg: str = THEME.accent, fg: str = "#0b1220",
                 hover: str = THEME.accent_hover, **kwargs):
        super().__init__(
            master, text=text, command=command,
            bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
            relief="flat", bd=0, cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=18, pady=10,
            **kwargs,
        )
        self._bg, self._hover = bg, hover
        self.bind("<Enter>", lambda _: self.config(bg=self._hover))
        self.bind("<Leave>", lambda _: self.config(bg=self._bg))


# ---------- Main dashboard ----------
class Dashboard:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.selected_files: list[str] = []
        self.output_dir: str = ""
        self.is_running = False
        self._preview_image = None  # keep a reference to avoid GC

        self._setup_window()
        self._build_layout()
        self._bind_drag_and_drop()

    # ----- window & helpers -----
    def _setup_window(self):
        self.root.title("Image Resizer — Professional Dashboard")
        self.root.geometry("1040x700")
        self.root.minsize(900, 620)
        self.root.configure(bg=THEME.bg)

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Modern.Horizontal.TProgressbar",
            troughcolor=THEME.surface_alt,
            background=THEME.accent,
            bordercolor=THEME.surface_alt,
            lightcolor=THEME.accent,
            darkcolor=THEME.accent,
            thickness=10,
        )

    def _build_layout(self):
        # Header
        header = tk.Frame(self.root, bg=THEME.bg)
        header.pack(fill="x", padx=28, pady=(24, 8))

        tk.Label(
            header, text="Image Resizer",
            bg=THEME.bg, fg=THEME.text,
            font=("Segoe UI", 22, "bold"),
        ).pack(side="left")

        tk.Label(
            header,
            text=f"Target: {CONFIG.target_size_mm} mm × {CONFIG.target_size_mm} mm  "
                 f"@ {CONFIG.target_dpi} DPI  •  {CONFIG.pixel_size} × {CONFIG.pixel_size} px",
            bg=THEME.bg, fg=THEME.text_muted,
            font=("Segoe UI", 10),
        ).pack(side="left", padx=16, pady=(8, 0))

        # Main content: left (input) + right (preview/log)
        content = tk.Frame(self.root, bg=THEME.bg)
        content.pack(fill="both", expand=True, padx=28, pady=12)

        left = tk.Frame(content, bg=THEME.bg)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        right = tk.Frame(content, bg=THEME.bg)
        right.pack(side="right", fill="both", expand=True, padx=(12, 0))

        self._build_input_card(left)
        self._build_preview_card(right)
        self._build_log_card(right)
        self._build_footer()

    # ----- left column: input & controls -----
    def _build_input_card(self, parent):
        card = Card(parent, title="1. INPUT")
        card.pack(fill="both", expand=True)

        # Drop zone / selection area
        self.drop_zone = tk.Frame(
            card, bg=THEME.surface_alt,
            highlightbackground=THEME.border, highlightthickness=1,
        )
        self.drop_zone.pack(fill="both", expand=True, padx=16, pady=12)

        self.drop_label = tk.Label(
            self.drop_zone,
            text="Drag & drop images here\nor click 'Add Files' below",
            bg=THEME.surface_alt, fg=THEME.text_muted,
            font=("Segoe UI", 11), justify="center",
        )
        self.drop_label.pack(expand=True, pady=32)

        # Buttons row
        btn_row = tk.Frame(card, bg=THEME.surface)
        btn_row.pack(fill="x", padx=16, pady=(0, 16))

        ActionButton(btn_row, "Add Files", self.add_files).pack(side="left")
        ActionButton(
            btn_row, "Clear", self.clear_files,
            bg=THEME.surface_alt, fg=THEME.text, hover=THEME.border,
        ).pack(side="left", padx=8)

        # Counter
        self.count_label = tk.Label(
            btn_row, text="0 file(s) selected",
            bg=THEME.surface, fg=THEME.text_muted,
            font=("Segoe UI", 9),
        )
        self.count_label.pack(side="right")

        # Output folder
        out_card = Card(parent, title="2. OUTPUT FOLDER")
        out_card.pack(fill="x", pady=(12, 0))

        row = tk.Frame(out_card, bg=THEME.surface)
        row.pack(fill="x", padx=16, pady=12)

        self.out_label = tk.Label(
            row, text="No folder selected",
            bg=THEME.surface, fg=THEME.text_muted,
            font=("Segoe UI", 9), anchor="w",
        )
        self.out_label.pack(side="left", fill="x", expand=True)

        ActionButton(
            row, "Browse", self.choose_output,
            bg=THEME.surface_alt, fg=THEME.text, hover=THEME.border,
        ).pack(side="right")

    # ----- right column: preview -----
    def _build_preview_card(self, parent):
        card = Card(parent, title="PREVIEW")
        card.pack(fill="both", expand=True)

        self.preview = tk.Label(
            card, text="No image selected",
            bg=THEME.surface_alt, fg=THEME.text_muted,
            font=("Segoe UI", 10),
        )
        self.preview.pack(fill="both", expand=True, padx=16, pady=12)

    # ----- right column: log -----
    def _build_log_card(self, parent):
        card = Card(parent, title="ACTIVITY LOG")
        card.pack(fill="both", expand=True, pady=(12, 0))

        self.log = tk.Text(
            card, bg=THEME.surface_alt, fg=THEME.text,
            font=("Consolas", 9), bd=0, relief="flat",
            wrap="word", height=8, insertbackground=THEME.text,
        )
        self.log.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        self.log.tag_config("ok", foreground=THEME.success)
        self.log.tag_config("warn", foreground=THEME.warning)
        self.log.tag_config("err", foreground=THEME.danger)
        self.log.tag_config("info", foreground=THEME.accent)
        self.log.config(state="disabled")

    # ----- footer: progress & convert -----
    def _build_footer(self):
        footer = tk.Frame(self.root, bg=THEME.bg)
        footer.pack(fill="x", padx=28, pady=(0, 24))

        self.progress = ttk.Progressbar(
            footer, style="Modern.Horizontal.TProgressbar",
            mode="determinate", length=600,
        )
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 16))

        self.status = tk.Label(
            footer, text="Ready",
            bg=THEME.bg, fg=THEME.text_muted,
            font=("Segoe UI", 9),
        )
        self.status.pack(side="left", padx=(0, 16))

        self.convert_btn = ActionButton(
            footer, "Convert All  →", self.start_conversion,
            bg=THEME.success, fg="white", hover="#16a34a",
        )
        self.convert_btn.pack(side="right")

    # ----- drag & drop -----
    def _bind_drag_and_drop(self):
        if not DND_AVAILABLE:
            self._log("Drag & drop unavailable (pip install tkinterdnd2)", "warn")
            return
        for widget in (self.drop_zone, self.drop_label):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        paths = self.root.tk.splitlist(event.data)
        self._extend_files(paths)

    # ----- file handling -----
    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Select image files",
            filetypes=[(
                "Image files",
                " ".join(f"*{ext}" for ext in CONFIG.supported_extensions),
            )],
        )
        self._extend_files(files)

    def _extend_files(self, paths):
        added = 0
        for path in paths:
            if not os.path.isfile(path):
                continue
            if path in self.selected_files:
                continue
            if os.path.splitext(path)[1].lower() not in CONFIG.supported_extensions:
                self._log(f"Skipped unsupported: {os.path.basename(path)}", "warn")
                continue
            self.selected_files.append(path)
            added += 1

        if added:
            self._log(f"Added {added} file(s). Total: {len(self.selected_files)}", "info")
            self._update_count()
            self._update_preview(self.selected_files[-1])

    def clear_files(self):
        self.selected_files.clear()
        self._update_count()
        self.preview.config(image="", text="No image selected")
        self._preview_image = None
        self._log("Selection cleared.", "info")

    def choose_output(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_dir = folder
            self.out_label.config(text=folder, fg=THEME.text)
            self._log(f"Output folder: {folder}", "info")

    def _update_count(self):
        self.count_label.config(text=f"{len(self.selected_files)} file(s) selected")

    def _update_preview(self, path):
        try:
            with Image.open(path) as img:
                img.thumbnail((360, 260), Image.LANCZOS)
                self._preview_image = ImageTk.PhotoImage(img)
                self.preview.config(image=self._preview_image, text="")
        except Exception as exc:
            self._log(f"Preview failed: {exc}", "err")

    # ----- conversion -----
    def start_conversion(self):
        if self.is_running:
            return
        if not self.selected_files:
            messagebox.showwarning("No files", "Please add at least one image.")
            return
        if not self.output_dir:
            messagebox.showwarning("No output folder", "Please select an output folder.")
            return

        self.is_running = True
        self.convert_btn.config(state="disabled", text="Converting…")
        self.progress["maximum"] = len(self.selected_files)
        self.progress["value"] = 0
        self.status.config(text="Converting…")

        threading.Thread(target=self._run_conversion, daemon=True).start()

    def _run_conversion(self):
        success, failures = 0, []
        for i, path in enumerate(self.selected_files, start=1):
            base = os.path.splitext(os.path.basename(path))[0]
            out_path = os.path.join(self.output_dir, f"{base}.jpg")
            try:
                resize_image(path, out_path)
                success += 1
                self._log(f"✓ {os.path.basename(path)} → {base}.jpg", "ok")
            except Exception as exc:
                failures.append(f"{os.path.basename(path)}: {exc}")
                self._log(f"✗ {os.path.basename(path)}: {exc}", "err")

            self.root.after(0, self._update_progress, i)

        self.root.after(0, self._finish_conversion, success, failures)

    def _update_progress(self, value):
        self.progress["value"] = value

    def _finish_conversion(self, success, failures):
        self.is_running = False
        self.convert_btn.config(state="normal", text="Convert All  →")
        self.status.config(text=f"Done — {success} succeeded, {len(failures)} failed")
        self._log(
            f"Conversion finished. Success: {success}, Failed: {len(failures)}",
            "info" if not failures else "warn",
        )
        if failures:
            messagebox.showwarning(
                "Completed with errors",
                f"{success} file(s) converted.\n{len(failures)} failed:\n\n"
                + "\n".join(failures[:10]),
            )
        else:
            messagebox.showinfo(
                "Completed",
                f"✅ All {success} file(s) converted successfully.\n\n"
                f"Output: {self.output_dir}",
            )

    # ----- logging -----
    def _log(self, message: str, level: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.config(state="normal")
        self.log.insert("end", f"[{timestamp}] {message}\n", level)
        self.log.see("end")
        self.log.config(state="disabled")


# ---------- Entry point ----------
def main():
    root = TkinterDnD.Tk() if DND_AVAILABLE else tk.Tk()
    Dashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()