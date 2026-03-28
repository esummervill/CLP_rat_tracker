#!/usr/bin/env python3
"""
CLP Rat Tracker - Conditioned Place Preference Experiment Tool

Launch this file to start the application:
    python main.py
"""

import logging
import os
import pathlib
import subprocess
import sys


REQUIRED_PACKAGES = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "numpy": "numpy",
    "matplotlib": "matplotlib",
}


def auto_install(package_name):
    """Attempt to pip-install a package into the current environment."""
    print(f"  Installing {package_name}...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def check_and_install_dependencies():
    missing = []
    for import_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append((import_name, pip_name))

    if not missing:
        return True

    print("=" * 55)
    print("  INSTALLING DEPENDENCIES")
    print("=" * 55)
    print()
    print("  The following packages are needed:")
    for _, pip_name in missing:
        print(f"    - {pip_name}")
    print()
    print("  Attempting automatic installation...")
    print()

    # Make sure pip itself is available
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        logging.getLogger(__name__).error("pip is not available")
        print("  [ERROR] pip is not available.")
        print("  Please install pip first, then re-run this script.")
        _show_error_gui(
            "pip is not available.\n\n"
            "Please reinstall Python from python.org and\n"
            "check 'Add Python to PATH' during installation."
        )
        return False

    failed = []
    for import_name, pip_name in missing:
        if auto_install(pip_name):
            print(f"  [OK] {pip_name} installed successfully")
        else:
            failed.append(pip_name)
            print(f"  [FAILED] {pip_name} could not be installed")

    print()

    if failed:
        msg = (
            "Some packages could not be installed:\n\n"
            + "\n".join(f"  - {p}" for p in failed)
            + "\n\nTry running this in a terminal:\n\n"
            + f"  {sys.executable} -m pip install " + " ".join(failed)
        )
        logging.getLogger(__name__).error("Package install failed: %s", failed)
        print("  " + msg.replace("\n", "\n  "))
        _show_error_gui(msg)
        return False

    # Verify everything actually imports now
    still_missing = []
    for import_name, pip_name in missing:
        try:
            __import__(import_name)
        except ImportError:
            still_missing.append(pip_name)

    if still_missing:
        msg = (
            "Packages were installed but still can't be loaded:\n\n"
            + "\n".join(f"  - {p}" for p in still_missing)
            + "\n\nTry restarting the application."
        )
        logging.getLogger(__name__).error("Imports still missing: %s", still_missing)
        _show_error_gui(msg)
        return False

    print("  All dependencies installed successfully!")
    print("=" * 55)
    print()
    return True


def _show_error_gui(message):
    """Show an error dialog if tkinter is available."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("CLP Rat Tracker - Setup Error", message)
        root.destroy()
    except Exception:
        pass


def main():
    from log_setup import log_banner_after_imports, setup_logging

    setup_logging()
    log = logging.getLogger(__name__)
    log.info(
        "Application folder (this copy of the code): %s",
        pathlib.Path(__file__).resolve().parent,
    )

    if not check_and_install_dependencies():
        log.error("Dependency check failed; exiting")
        sys.exit(1)

    log_banner_after_imports()

    try:
        from app import App

        app = App()
        app.mainloop()
    except Exception:
        logging.getLogger(__name__).exception("Fatal error in application")
        raise


if __name__ == "__main__":
    main()
