"""
Video-based rat position tracker for Conditioned Place Preference experiments.
Uses OpenCV background subtraction to detect the rat and determine which
side of a user-defined dividing line it occupies in each frame.
"""

import csv
import logging
import os
from dataclasses import dataclass, field

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TrackingResult:
    fps: float = 0.0
    total_frames: int = 0
    side_a_frames: int = 0
    side_b_frames: int = 0
    undetermined_frames: int = 0
    positions: list = field(default_factory=list)
    side_per_frame: list = field(default_factory=list)
    crossings: int = 0

    @property
    def duration_seconds(self) -> float:
        return self.total_frames / self.fps if self.fps > 0 else 0

    @property
    def side_a_seconds(self) -> float:
        return self.side_a_frames / self.fps if self.fps > 0 else 0

    @property
    def side_b_seconds(self) -> float:
        return self.side_b_frames / self.fps if self.fps > 0 else 0

    @property
    def preference_index(self) -> float:
        """Preference index: (B - A) / (A + B). Ranges from -1 to 1."""
        total = self.side_a_frames + self.side_b_frames
        if total == 0:
            return 0.0
        return (self.side_b_frames - self.side_a_frames) / total

    @property
    def side_a_percent(self) -> float:
        total = self.side_a_frames + self.side_b_frames
        if total == 0:
            return 0.0
        return (self.side_a_frames / total) * 100

    @property
    def side_b_percent(self) -> float:
        total = self.side_a_frames + self.side_b_frames
        if total == 0:
            return 0.0
        return (self.side_b_frames / total) * 100


def point_side_of_line(point, line_start, line_end):
    """
    Determine which side of a line a point is on.
    Returns 'A' for left/above, 'B' for right/below, None if on the line.
    Uses the cross product of the line direction and point-to-start vector.
    """
    px, py = point
    x1, y1 = line_start
    x2, y2 = line_end
    cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    if cross > 0:
        return "A"
    elif cross < 0:
        return "B"
    return None


class RatTracker:
    def __init__(self, video_path: str, line_start: tuple, line_end: tuple,
                 min_contour_area: int = 500, sensitivity: int = 50):
        self.video_path = video_path
        self.line_start = line_start
        self.line_end = line_end
        self.min_contour_area = min_contour_area
        self.sensitivity = sensitivity
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def get_first_frame(video_path: str):
        """Static helper to grab the first frame from a video file."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error("get_first_frame: VideoCapture failed to open: %s", video_path)
            return None
        ret, frame = cap.read()
        cap.release()
        if ret:
            logger.debug(
                "get_first_frame: ok shape=%s",
                getattr(frame, "shape", None),
            )
            return frame
        logger.error("get_first_frame: read() returned no frame: %s", video_path)
        return None

    def get_video_info(video_path: str):
        """Return (fps, total_frames, width, height) for a video file."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error("get_video_info: VideoCapture failed to open: %s", video_path)
            return None
        fps = cap.get(cv2.CAP_PROP_FPS)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if w <= 0 or h <= 0:
            logger.warning(
                "get_video_info: unusual dimensions w=%s h=%s for %s",
                w,
                h,
                video_path,
            )
        return fps, total, w, h

    def run(self, progress_callback=None, frame_callback=None):
        """
        Process the video and track the rat's position.

        progress_callback(fraction): called with 0.0-1.0 progress
        frame_callback(frame, position, side): called with annotated frame data
        """
        self._cancel = False
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            logger.error("run: cannot open video: %s", self.video_path)
            raise FileNotFoundError(f"Cannot open video: {self.video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            logger.warning("run: CAP_PROP_FPS was %s; using 30.0", fps)
            fps = 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        logger.info(
            "run: processing %s fps=%.3f frames=%s sensitivity=%s min_area=%s",
            self.video_path,
            fps,
            total_frames,
            self.sensitivity,
            self.min_contour_area,
        )

        bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=300,
            varThreshold=max(10, 100 - self.sensitivity),
            detectShadows=True,
        )

        result = TrackingResult(fps=fps, total_frames=total_frames)
        prev_side = None
        frame_idx = 0

        while True:
            if self._cancel:
                cap.release()
                return None

            ret, frame = cap.read()
            if not ret:
                break

            fg_mask = bg_subtractor.apply(frame)

            # Remove shadows (marked as 127 by MOG2) and apply threshold
            _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(
                fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            position = None
            side = None

            if contours:
                valid = [c for c in contours
                         if cv2.contourArea(c) >= self.min_contour_area]
                if valid:
                    largest = max(valid, key=cv2.contourArea)
                    M = cv2.moments(largest)
                    if M["m00"] > 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        position = (cx, cy)
                        side = point_side_of_line(
                            position, self.line_start, self.line_end
                        )

            result.positions.append(position)
            result.side_per_frame.append(side)

            if side == "A":
                result.side_a_frames += 1
            elif side == "B":
                result.side_b_frames += 1
            else:
                result.undetermined_frames += 1

            if prev_side is not None and side is not None and side != prev_side:
                result.crossings += 1
            if side is not None:
                prev_side = side

            frame_idx += 1

            if frame_callback and frame_idx % 3 == 0:
                frame_callback(frame, position, side, frame_idx)

            if progress_callback and frame_idx % 10 == 0:
                progress_callback(frame_idx / max(total_frames, 1))

        cap.release()
        if progress_callback:
            progress_callback(1.0)
        logger.info(
            "run: finished frames=%s side_a=%s side_b=%s undetermined=%s crossings=%s",
            len(result.positions),
            result.side_a_frames,
            result.side_b_frames,
            result.undetermined_frames,
            result.crossings,
        )
        return result


def export_results_csv(result: TrackingResult, output_path: str,
                       side_a_label="Side A", side_b_label="Side B"):
    """Export frame-by-frame tracking data to CSV."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Frame", "Time (s)", "X", "Y", "Side",
            f"{side_a_label} Cumulative (s)", f"{side_b_label} Cumulative (s)"
        ])
        a_cum = 0
        b_cum = 0
        for i, (pos, side) in enumerate(
            zip(result.positions, result.side_per_frame)
        ):
            t = i / result.fps if result.fps > 0 else 0
            x = pos[0] if pos else ""
            y = pos[1] if pos else ""
            side_label = ""
            if side == "A":
                side_label = side_a_label
                a_cum += 1
            elif side == "B":
                side_label = side_b_label
                b_cum += 1
            writer.writerow([
                i, f"{t:.3f}", x, y, side_label,
                f"{a_cum / result.fps:.3f}" if result.fps > 0 else 0,
                f"{b_cum / result.fps:.3f}" if result.fps > 0 else 0,
            ])


def export_summary_csv(result: TrackingResult, output_path: str,
                       video_name="", side_a_label="Side A",
                       side_b_label="Side B"):
    """Export a one-row summary of the tracking results."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Video", "Duration (s)", "FPS", "Total Frames",
            f"{side_a_label} Time (s)", f"{side_a_label} %",
            f"{side_b_label} Time (s)", f"{side_b_label} %",
            "Preference Index", "Crossings"
        ])
        writer.writerow([
            video_name,
            f"{result.duration_seconds:.2f}",
            f"{result.fps:.2f}",
            result.total_frames,
            f"{result.side_a_seconds:.2f}",
            f"{result.side_a_percent:.1f}",
            f"{result.side_b_seconds:.2f}",
            f"{result.side_b_percent:.1f}",
            f"{result.preference_index:.4f}",
            result.crossings,
        ])
