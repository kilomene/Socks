"""
screenshot_capture.py
---------------------
Takes screenshots at the moment an error occurs and saves them
to the error_handler/screenshots/ folder with a timestamp.

Captures:
  1. The entire screen  (catches both the terminal and Chrome if visible)
  2. The Chrome window  (if a Chrome process handle is available)
"""

import os
import datetime

# Pillow is needed for screen capture
try:
    from PIL import ImageGrab, Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")


def _ensure_dir():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]


def capture_screen(label: str = "error") -> str | None:
    """
    Take a full-screen screenshot.
    Returns the file path saved, or None if capture failed.
    """
    _ensure_dir()

    if not PIL_AVAILABLE:
        return None

    try:
        screenshot = ImageGrab.grab()
        filename   = f"{label}_{_timestamp()}_fullscreen.png"
        filepath   = os.path.join(SCREENSHOT_DIR, filename)
        screenshot.save(filepath)
        return filepath
    except Exception:
        return None


def capture_chrome_window(chrome_proc, label: str = "error") -> str | None:
    """
    Try to capture just the Chrome window using pygetwindow (Windows)
    or fall back to a full-screen grab.
    Returns the file path saved, or None.
    """
    _ensure_dir()

    if not PIL_AVAILABLE:
        return None

    # Try to get the Chrome window specifically (Windows only)
    try:
        import pygetwindow as gw
        chrome_windows = [w for w in gw.getAllWindows()
                          if "chrome" in w.title.lower() or "google" in w.title.lower()]
        if chrome_windows:
            win = chrome_windows[0]
            left, top = win.left, win.top
            right  = left + win.width
            bottom = top  + win.height
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            filename   = f"{label}_{_timestamp()}_chrome_window.png"
            filepath   = os.path.join(SCREENSHOT_DIR, filename)
            screenshot.save(filepath)
            return filepath
    except Exception:
        pass  # pygetwindow not installed or no window found — fall back below

    # Fall back to full screen if Chrome window can't be isolated
    return capture_screen(label + "_chrome_fallback")


def capture_all(label: str = "error", chrome_proc=None) -> list[str]:
    """
    Capture everything relevant in one call.
    Returns a list of file paths that were successfully saved.
    """
    saved = []

    fullscreen_path = capture_screen(label)
    if fullscreen_path:
        saved.append(fullscreen_path)

    if chrome_proc is not None:
        chrome_path = capture_chrome_window(chrome_proc, label)
        if chrome_path and chrome_path not in saved:
            saved.append(chrome_path)

    return saved
