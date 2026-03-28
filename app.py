"""
CLP Rat Tracker - Conditioned Place Preference GUI Application

A user-friendly tool for tracking which side of a bin a rat prefers,
designed for Conditioned Place Preference (CPP) experiments.
"""

import logging
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageTk

from tracker import (
    RatTracker,
    TrackingResult,
    export_results_csv,
    export_summary_csv,
)

logger = logging.getLogger(__name__)

WINDOW_TITLE = "CLP Rat Tracker - Conditioned Place Preference"
CANVAS_MAX_W = 800
CANVAS_MAX_H = 500
SIDE_A_COLOR = "#3b82f6"
SIDE_B_COLOR = "#ef4444"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.configure(bg="#1e1e2e")
        self.minsize(960, 700)
        logger.info("Main window created (tkinter)")

        self.video_path = None
        self.first_frame = None
        self.display_frame = None
        self.scale_factor = 1.0
        self.original_size = (0, 0)

        self.line_points = []
        self.line_start = None
        self.line_end = None
        self.side_a_label_var = tk.StringVar(value="Side A")
        self.side_b_label_var = tk.StringVar(value="Side B")

        self.tracker = None
        self.result: Optional[TrackingResult] = None
        self.is_tracking = False

        self._build_ui()
        self._set_state("no_video")
        self.bind("<Map>", self._on_window_mapped)
        self.after(400, self._log_ui_ready)

    def _log_ui_ready(self) -> None:
        logger.info(
            "UI ready — click 'Open Video File' to load a recording. "
            "Preview uses the label+PhotoImage path (macOS-friendly)."
        )

    def _on_window_mapped(self, _event=None):
        """Redraw video after the window is visible."""
        if getattr(self, "_did_map_refresh", False):
            return
        self._did_map_refresh = True
        logger.debug("Window mapped; scheduling preview refresh if video loaded")
        self.after_idle(self._refresh_preview)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#1e1e2e")
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4",
                         font=("Segoe UI", 11))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"),
                         foreground="#cdd6f4", background="#1e1e2e")
        style.configure("TButton", font=("Segoe UI", 11), padding=8)
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"),
                         padding=10)
        style.configure("TLabelframe", background="#1e1e2e",
                         foreground="#cdd6f4")
        style.configure("TLabelframe.Label", background="#1e1e2e",
                         foreground="#cdd6f4", font=("Segoe UI", 11, "bold"))

        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", padx=16, pady=(12, 4))
        ttk.Label(header, text="CLP Rat Tracker",
                  style="Header.TLabel").pack(side="left")
        self.status_label = ttk.Label(header, text="No video loaded")
        self.status_label.pack(side="right")

        # Main area
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=16, pady=8)

        # Left: video preview — tk.Label + PhotoImage is reliable on macOS; Canvas+image often blanks.
        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)

        self._video_holder = tk.Frame(left, bg="#313244")
        self._video_holder.pack(expand=True, fill="both")

        self.preview = tk.Label(
            self._video_holder,
            bg="#313244",
            cursor="crosshair",
            borderwidth=0,
            highlightthickness=0,
        )
        self.preview.pack(expand=True)
        self.preview.bind("<Button-1>", self._on_preview_click)

        # Right: controls
        right = ttk.Frame(main, width=260)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)

        # -- Load section
        load_frame = ttk.LabelFrame(right, text="1. Load Video", padding=10)
        load_frame.pack(fill="x", pady=(0, 8))

        self.btn_load = ttk.Button(load_frame, text="Open Video File",
                                   command=self._load_video)
        self.btn_load.pack(fill="x")

        self.video_info_label = ttk.Label(load_frame, text="",
                                          wraplength=220)
        self.video_info_label.pack(fill="x", pady=(6, 0))

        # -- Line section
        line_frame = ttk.LabelFrame(right, text="2. Draw Dividing Line",
                                    padding=10)
        line_frame.pack(fill="x", pady=(0, 8))

        self.line_instruction = ttk.Label(
            line_frame,
            text="Click two points on the video\nto draw the line separating\nthe two sides of the bin.",
            wraplength=220,
        )
        self.line_instruction.pack(fill="x")

        self.btn_reset_line = ttk.Button(line_frame, text="Reset Line",
                                         command=self._reset_line)
        self.btn_reset_line.pack(fill="x", pady=(6, 0))

        # Side labels
        labels_frame = ttk.Frame(line_frame)
        labels_frame.pack(fill="x", pady=(8, 0))

        a_frame = ttk.Frame(labels_frame)
        a_frame.pack(fill="x", pady=2)
        a_color = tk.Label(a_frame, bg=SIDE_A_COLOR, width=3)
        a_color.pack(side="left", padx=(0, 6))
        ttk.Label(a_frame, text="Label:").pack(side="left")
        self.entry_a = ttk.Entry(a_frame, textvariable=self.side_a_label_var,
                                 width=12)
        self.entry_a.pack(side="left", padx=(4, 0))

        b_frame = ttk.Frame(labels_frame)
        b_frame.pack(fill="x", pady=2)
        b_color = tk.Label(b_frame, bg=SIDE_B_COLOR, width=3)
        b_color.pack(side="left", padx=(0, 6))
        ttk.Label(b_frame, text="Label:").pack(side="left")
        self.entry_b = ttk.Entry(b_frame, textvariable=self.side_b_label_var,
                                 width=12)
        self.entry_b.pack(side="left", padx=(4, 0))

        # -- Tracking section
        track_frame = ttk.LabelFrame(right, text="3. Run Tracking",
                                     padding=10)
        track_frame.pack(fill="x", pady=(0, 8))

        sens_frame = ttk.Frame(track_frame)
        sens_frame.pack(fill="x")
        ttk.Label(sens_frame, text="Sensitivity:").pack(side="left")
        self.sensitivity_var = tk.IntVar(value=50)
        self.sensitivity_scale = ttk.Scale(
            sens_frame, from_=10, to=90, variable=self.sensitivity_var,
            orient="horizontal"
        )
        self.sensitivity_scale.pack(side="left", fill="x", expand=True,
                                    padx=(6, 0))

        min_frame = ttk.Frame(track_frame)
        min_frame.pack(fill="x", pady=(6, 0))
        ttk.Label(min_frame, text="Min size:").pack(side="left")
        self.min_area_var = tk.IntVar(value=500)
        self.min_area_entry = ttk.Entry(min_frame,
                                        textvariable=self.min_area_var,
                                        width=8)
        self.min_area_entry.pack(side="left", padx=(6, 0))
        ttk.Label(min_frame, text="px").pack(side="left", padx=(2, 0))

        self.btn_track = ttk.Button(track_frame, text="Start Tracking",
                                    style="Accent.TButton",
                                    command=self._start_tracking)
        self.btn_track.pack(fill="x", pady=(10, 0))

        self.btn_cancel = ttk.Button(track_frame, text="Cancel",
                                     command=self._cancel_tracking)
        self.btn_cancel.pack(fill="x", pady=(4, 0))
        self.btn_cancel.pack_forget()

        self.progress = ttk.Progressbar(track_frame, mode="determinate")
        self.progress.pack(fill="x", pady=(6, 0))

        # -- Results section
        res_frame = ttk.LabelFrame(right, text="4. Results", padding=10)
        res_frame.pack(fill="x", pady=(0, 8))

        self.result_text = tk.Text(
            res_frame, height=8, bg="#313244", fg="#cdd6f4",
            font=("Consolas", 10), relief="flat", state="disabled",
            wrap="word"
        )
        self.result_text.pack(fill="x")

        btn_row = ttk.Frame(res_frame)
        btn_row.pack(fill="x", pady=(6, 0))
        self.btn_export_detail = ttk.Button(
            btn_row, text="Export CSV", command=self._export_detail
        )
        self.btn_export_detail.pack(side="left", fill="x", expand=True,
                                    padx=(0, 3))
        self.btn_export_summary = ttk.Button(
            btn_row, text="Export Summary", command=self._export_summary
        )
        self.btn_export_summary.pack(side="left", fill="x", expand=True,
                                     padx=(3, 0))

    def _set_state(self, state):
        """Enable/disable buttons based on current workflow step."""
        if state == "no_video":
            self.btn_reset_line.configure(state="disabled")
            self.btn_track.configure(state="disabled")
            self.btn_export_detail.configure(state="disabled")
            self.btn_export_summary.configure(state="disabled")
        elif state == "video_loaded":
            self.btn_reset_line.configure(state="normal")
            self.btn_track.configure(state="disabled")
            self.btn_export_detail.configure(state="disabled")
            self.btn_export_summary.configure(state="disabled")
            self.status_label.configure(
                text="Click two points to draw the dividing line"
            )
        elif state == "line_drawn":
            self.btn_reset_line.configure(state="normal")
            self.btn_track.configure(state="normal")
            self.btn_export_detail.configure(state="disabled")
            self.btn_export_summary.configure(state="disabled")
            self.status_label.configure(text="Ready to track")
        elif state == "tracking":
            self.btn_load.configure(state="disabled")
            self.btn_reset_line.configure(state="disabled")
            self.btn_track.configure(state="disabled")
            self.btn_cancel.pack(fill="x", pady=(4, 0))
            self.btn_export_detail.configure(state="disabled")
            self.btn_export_summary.configure(state="disabled")
            self.status_label.configure(text="Tracking in progress...")
        elif state == "done":
            self.btn_load.configure(state="normal")
            self.btn_reset_line.configure(state="normal")
            self.btn_track.configure(state="normal")
            self.btn_cancel.pack_forget()
            self.btn_export_detail.configure(state="normal")
            self.btn_export_summary.configure(state="normal")
            self.status_label.configure(text="Tracking complete")

    # -------------------------------------------------------- Video loading
    def _load_video(self):
        path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.mts *.MTS *.avi *.mov *.mkv *.wmv"),
                ("MP4 files", "*.mp4"),
                ("MTS files", "*.mts *.MTS"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        logger.info("Open video requested: %s", path)
        info = RatTracker.get_video_info(path)
        if info is None:
            logger.error("get_video_info failed for: %s", path)
            messagebox.showerror("Error",
                                 "Cannot open this video file.\n\n"
                                 "Make sure the file is a valid video.")
            return

        fps, total, w, h = info
        logger.info(
            "Video metadata: %sx%s fps=%s frames=%s",
            w, h, fps, total,
        )
        self.video_path = path
        self.original_size = (w, h)

        frame = RatTracker.get_first_frame(path)
        if frame is None:
            logger.error("get_first_frame returned None for: %s", path)
            messagebox.showerror("Error", "Cannot read frames from video.")
            return

        self.first_frame = frame
        self.line_points = []
        self.line_start = None
        self.line_end = None
        self.result = None
        self._clear_results()

        name = os.path.basename(path)
        dur = total / fps if fps > 0 else 0
        self.video_info_label.configure(
            text=f"{name}\n{w}x{h} | {fps:.1f} fps | {dur:.1f}s"
        )

        self._display_frame(frame)
        self.after_idle(self._refresh_preview)
        self._set_state("video_loaded")

    def _refresh_preview(self):
        """Redraw after layout (e.g. first window map)."""
        if self.first_frame is None:
            return
        self.update_idletasks()
        self._display_frame(self.first_frame)

    @staticmethod
    def _to_bgr_uint8(frame: np.ndarray) -> np.ndarray:
        """Normalize OpenCV frames to 3-channel uint8 BGR for resize/display."""
        if frame.ndim == 2:
            bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.shape[2] == 4:
            bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        elif frame.shape[2] == 3:
            bgr = frame
        else:
            raise ValueError(f"Unsupported frame shape {frame.shape}")
        if bgr.dtype != np.uint8:
            bgr = np.clip(bgr, 0, 255).astype(np.uint8)
        return bgr

    def _paint_preview_annotations(self, bgr: np.ndarray, scale: float) -> None:
        """Line, first-click marker, and side labels drawn in BGR on the resized preview."""
        if self.line_start and self.line_end:
            p1 = (
                int(round(self.line_start[0] * scale)),
                int(round(self.line_start[1] * scale)),
            )
            p2 = (
                int(round(self.line_end[0] * scale)),
                int(round(self.line_end[1] * scale)),
            )
            cv2.line(bgr, p1, p2, (34, 197, 94), 2, cv2.LINE_AA)
            mid_x = (p1[0] + p2[0]) // 2
            mid_y = (p1[1] + p2[1]) // 2
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = max((dx * dx + dy * dy) ** 0.5, 1.0)
            nx = -dy / length * 36
            ny = dx / length * 36
            font = cv2.FONT_HERSHEY_SIMPLEX
            fs = 0.55
            t = self.side_a_label_var.get()
            (tw, th), _ = cv2.getTextSize(t, font, fs, 1)
            cv2.putText(
                bgr,
                t,
                (int(mid_x + nx - tw // 2), int(mid_y + ny + th // 2)),
                font,
                fs,
                (246, 130, 59),
                1,
                cv2.LINE_AA,
            )
            t = self.side_b_label_var.get()
            (tw, th), _ = cv2.getTextSize(t, font, fs, 1)
            cv2.putText(
                bgr,
                t,
                (int(mid_x - nx - tw // 2), int(mid_y - ny + th // 2)),
                font,
                fs,
                (68, 68, 239),
                1,
                cv2.LINE_AA,
            )
        elif len(self.line_points) == 1:
            p = self.line_points[0]
            cx = int(round(p[0] * scale))
            cy = int(round(p[1] * scale))
            cv2.circle(bgr, (cx, cy), 6, (34, 197, 94), -1, cv2.LINE_AA)
            cv2.circle(bgr, (cx, cy), 8, (255, 255, 255), 1, cv2.LINE_AA)

    def _display_frame(self, frame):
        """Resize preview and show via tk.Label + PhotoImage (reliable on macOS)."""
        self.update_idletasks()

        try:
            bgr = self._to_bgr_uint8(frame)
        except Exception:
            logger.exception("Bad video frame shape %s", getattr(frame, "shape", None))
            raise

        h, w = bgr.shape[:2]
        if w <= 0 or h <= 0:
            logger.error("Invalid frame dimensions: %s", bgr.shape)
            return

        scale = min(CANVAS_MAX_W / w, CANVAS_MAX_H / h, 1.0)
        self.scale_factor = scale
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))

        resized = cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        if not self.is_tracking:
            self._paint_preview_annotations(resized, scale)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        try:
            pil = Image.fromarray(rgb, mode="RGB")
            self.display_frame = ImageTk.PhotoImage(pil, master=self)
            self.preview.configure(image=self.display_frame)
            self.preview.image = self.display_frame
        except tk.TclError:
            logger.exception("Tk Label/PhotoImage error (display frame)")
            raise
        except Exception:
            logger.exception("Failed to show frame on preview label")
            raise

        pw = int(self.preview.winfo_width())
        ph = int(self.preview.winfo_height())
        logger.info(
            "Frame displayed: video=%sx%s scaled=%sx%s label_winfo=%sx%s scale=%.4f",
            w,
            h,
            new_w,
            new_h,
            pw,
            ph,
            scale,
        )

    # --------------------------------------------------- Line drawing
    def _on_preview_click(self, event):
        if self.first_frame is None or self.is_tracking:
            return
        if len(self.line_points) >= 2:
            return

        h, w = self.first_frame.shape[:2]
        scale = self.scale_factor
        orig_x = int(round(event.x / scale))
        orig_y = int(round(event.y / scale))

        if orig_x < 0 or orig_y < 0 or orig_x >= w or orig_y >= h:
            return

        self.line_points.append((orig_x, orig_y))

        if len(self.line_points) == 1:
            self.status_label.configure(
                text="Click second point to complete the line"
            )
            self._display_frame(self.first_frame)

        elif len(self.line_points) == 2:
            self.line_start = self.line_points[0]
            self.line_end = self.line_points[1]
            self._display_frame(self.first_frame)
            self._set_state("line_drawn")

    def _reset_line(self):
        self.line_points = []
        self.line_start = None
        self.line_end = None
        if self.first_frame is not None:
            self._display_frame(self.first_frame)
        self._set_state("video_loaded")

    # ----------------------------------------------------------- Tracking
    def _start_tracking(self):
        if not self.video_path or not self.line_start:
            return

        logger.info(
            "Start tracking: video=%s line=%s->%s sensitivity=%s min_area=%s",
            self.video_path,
            self.line_start,
            self.line_end,
            self.sensitivity_var.get(),
            self.min_area_var.get(),
        )
        self.is_tracking = True
        self._set_state("tracking")
        self.progress["value"] = 0
        self._clear_results()

        sensitivity = self.sensitivity_var.get()
        min_area = self.min_area_var.get()

        self.tracker = RatTracker(
            self.video_path, self.line_start, self.line_end,
            min_contour_area=min_area, sensitivity=sensitivity
        )

        thread = threading.Thread(target=self._tracking_worker, daemon=True)
        thread.start()

    def _tracking_worker(self):
        try:
            result = self.tracker.run(
                progress_callback=self._on_progress,
                frame_callback=self._on_frame,
            )
            self.after(0, self._on_tracking_done, result)
        except Exception as e:
            logger.exception("Tracking worker failed")
            self.after(0, self._on_tracking_error, str(e))

    def _on_progress(self, fraction):
        self.after(0, lambda: self.progress.configure(
            value=int(fraction * 100)))

    def _on_frame(self, frame, position, side, frame_idx):
        def update():
            annotated = frame.copy()
            if self.line_start and self.line_end:
                cv2.line(annotated,
                         self.line_start, self.line_end,
                         (34, 197, 94), 2, cv2.LINE_AA)
            if position:
                color = ((59, 130, 246) if side == "A"
                         else (239, 68, 68) if side == "B"
                         else (200, 200, 200))
                cv2.circle(annotated, position, 8, color, -1)
                cv2.circle(annotated, position, 10, (255, 255, 255), 2)
            self._display_frame(annotated)
        self.after(0, update)

    def _on_tracking_done(self, result):
        self.is_tracking = False
        if result is None:
            self._set_state("line_drawn")
            self.status_label.configure(text="Tracking cancelled")
            return

        self.result = result
        self._set_state("done")
        self._show_results(result)

        if self.first_frame is not None:
            self._display_frame(self.first_frame)

    def _on_tracking_error(self, error_msg):
        self.is_tracking = False
        self._set_state("line_drawn")
        logger.error("Tracking error (UI): %s", error_msg)
        messagebox.showerror("Tracking Error", f"An error occurred:\n{error_msg}")

    def _cancel_tracking(self):
        if self.tracker:
            self.tracker.cancel()

    # ------------------------------------------------------------- Results
    def _clear_results(self):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.configure(state="disabled")

    def _show_results(self, r: TrackingResult):
        a_name = self.side_a_label_var.get()
        b_name = self.side_b_label_var.get()
        text = (
            f"Duration: {r.duration_seconds:.1f} s\n"
            f"\n"
            f"{a_name}: {r.side_a_seconds:.1f}s ({r.side_a_percent:.1f}%)\n"
            f"{b_name}: {r.side_b_seconds:.1f}s ({r.side_b_percent:.1f}%)\n"
            f"\n"
            f"Preference Index: {r.preference_index:+.3f}\n"
            f"  (-1 = full {a_name}, +1 = full {b_name})\n"
            f"\n"
            f"Crossings: {r.crossings}\n"
        )
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.configure(state="disabled")

    def _export_detail(self):
        if not self.result:
            return
        path = filedialog.asksaveasfilename(
            title="Save Detailed Results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="tracking_detail.csv",
        )
        if not path:
            return
        export_results_csv(
            self.result, path,
            side_a_label=self.side_a_label_var.get(),
            side_b_label=self.side_b_label_var.get(),
        )
        messagebox.showinfo("Exported", f"Detailed results saved to:\n{path}")

    def _export_summary(self):
        if not self.result:
            return
        path = filedialog.asksaveasfilename(
            title="Save Summary",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="tracking_summary.csv",
        )
        if not path:
            return
        video_name = os.path.basename(self.video_path) if self.video_path else ""
        export_summary_csv(
            self.result, path,
            video_name=video_name,
            side_a_label=self.side_a_label_var.get(),
            side_b_label=self.side_b_label_var.get(),
        )
        messagebox.showinfo("Exported", f"Summary saved to:\n{path}")
