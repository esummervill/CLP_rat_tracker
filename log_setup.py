"""
Application logging: rotating file, per-session file, console, and stderr capture.

Logs live under ./logs/ next to the package (same folder as this file).
"""

from __future__ import annotations

import atexit
import logging
import os
import sys
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Tuple

LOG_DIR_NAME = "logs"
MAIN_LOG = "clp_rat_tracker.log"


class _StreamToLogger:
    """Send writes to a logger (captures OpenCV/Tk stderr spam)."""

    def __init__(self, logger: logging.Logger, level: int):
        self._logger = logger
        self._level = level
        self._buffer = ""

    def write(self, buf: str) -> int:
        self._buffer += buf
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.rstrip()
            if line:
                self._logger.log(self._level, line)
        return len(buf)

    def flush(self) -> None:
        if self._buffer.strip():
            self._logger.log(self._level, self._buffer.rstrip())
            self._buffer = ""


def get_log_dir() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base, LOG_DIR_NAME)
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def setup_logging(
    *,
    capture_stderr: bool = True,
    console_level: int = logging.WARNING,
) -> Tuple[str, str]:
    """
    Configure root logging. Returns (main_log_path, session_log_path).
    """
    log_dir = get_log_dir()
    main_path = os.path.join(log_dir, MAIN_LOG)
    session_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    session_path = os.path.join(log_dir, session_name)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    main_handler = RotatingFileHandler(
        main_path,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    main_handler.setLevel(logging.DEBUG)
    main_handler.setFormatter(fmt)

    session_handler = logging.FileHandler(session_path, encoding="utf-8")
    session_handler.setLevel(logging.DEBUG)
    session_handler.setFormatter(fmt)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console.setFormatter(fmt)

    root.addHandler(main_handler)
    root.addHandler(session_handler)
    root.addHandler(console)

    atexit.register(logging.shutdown)

    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    log = logging.getLogger("log_setup")

    def _excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical(
            "Uncaught exception in main thread",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = _excepthook

    if hasattr(threading, "excepthook"):

        def _thread_excepthook(args: threading.ExceptHookArgs) -> None:
            logging.error(
                "Uncaught exception in thread %r",
                args.thread.name,
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )

        threading.excepthook = _thread_excepthook  # type: ignore[attr-defined]

    if capture_stderr:
        sys.stderr = _StreamToLogger(  # type: ignore[assignment]
            logging.getLogger("stderr"),
            logging.WARNING,
        )

    log.info("=" * 60)
    log.info("CLP Rat Tracker session start")
    log.info("Main log: %s", main_path)
    log.info("Session log: %s", session_path)
    log.info("Python: %s", sys.version.replace("\n", " "))
    log.info("Executable: %s", sys.executable)
    log.info("CWD: %s", os.getcwd())
    log.info("Platform: %s", sys.platform)

    return main_path, session_path


def log_banner_after_imports() -> None:
    """Call after cv2/numpy are available."""
    try:
        import cv2
        import numpy as np

        logging.getLogger("log_setup").info(
            "OpenCV %s | NumPy %s", cv2.__version__, np.__version__
        )
    except Exception as e:
        logging.getLogger("log_setup").warning("Could not log library versions: %s", e)
