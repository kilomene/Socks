"""
error_reporter.py
-----------------
The main entry point for the error handler system.

Usage anywhere in the project:
    from error_handler import report_error
    
    try:
        risky_operation()
    except Exception as e:
        report_error(e, source_module="local_proxy", chrome_proc=chrome_proc)

What it does when called:
  1. Classifies the error (MINOR / MAJOR / CRITICAL) and builds a
     plain-English description of where and why it happened.
  2. Prints a colour-coded report to the terminal.
  3. Takes a screenshot of the screen (and Chrome window if provided)
     and saves it to error_handler/screenshots/.
  4. Appends a full record to error_handler/error_log.txt.
"""

import os
import traceback
import datetime
import colorama
from colorama import Fore, Style

from .error_classifier import classify, ErrorSeverity
from .screenshot_capture import capture_all

colorama.init(autoreset=True)

# Where error logs are written
ERROR_LOG_PATH = os.path.join(os.path.dirname(__file__), "error_log.txt")

# Re-export so callers can do: from error_handler import report_error, ErrorSeverity
__all__ = ["report_error", "ErrorSeverity"]


# ── Colour map ────────────────────────────────────────────────────────────────

_COLOURS = {
    ErrorSeverity.MINOR:    Fore.YELLOW,
    ErrorSeverity.MAJOR:    Fore.LIGHTRED_EX,
    ErrorSeverity.CRITICAL: Fore.RED,
}

_ICONS = {
    ErrorSeverity.MINOR:    "⚠️  MINOR",
    ErrorSeverity.MAJOR:    "🔴 MAJOR",
    ErrorSeverity.CRITICAL: "💀 CRITICAL",
}


# ── Public API ────────────────────────────────────────────────────────────────

def report_error(
    exception:     Exception,
    source_module: str  = "unknown",
    chrome_proc           = None,
    extra_context: str  = "",
) -> None:
    """
    Classify, display, screenshot, and log an error.

    Parameters
    ----------
    exception     : The caught exception object.
    source_module : The name of the Python file where the error occurred
                    (without .py), e.g. "local_proxy", "kill_switch".
    chrome_proc   : (optional) The Chrome subprocess.Popen handle so a
                    Chrome-window screenshot can be attempted.
    extra_context : (optional) Any extra plain-English note to add to the report.
    """
    info       = classify(exception, source_module)
    severity   = info["severity"]
    colour     = _COLOURS[severity]
    icon       = _ICONS[severity]
    timestamp  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── 1. Terminal output ────────────────────────────────────────────────────
    divider = colour + "─" * 60 + Style.RESET_ALL
    print()
    print(divider)
    print(colour + f"  {icon}  ERROR REPORT" + Style.RESET_ALL)
    print(divider)
    print(Fore.WHITE  + f"  Time      : {timestamp}")
    print(Fore.WHITE  + f"  Where     : {info['location']}")
    print(Fore.WHITE  + f"  What      : {info['cause']}")
    if extra_context:
        print(Fore.CYAN + f"  Note      : {extra_context}")
    print(Fore.LIGHTBLACK_EX + f"  Raw error : {info['raw_error']}")

    # ── 2. Screenshot ─────────────────────────────────────────────────────────
    label          = f"{severity.value}_{source_module}"
    screenshot_paths = capture_all(label=label, chrome_proc=chrome_proc)

    if screenshot_paths:
        print(Fore.GREEN + f"  Screenshot: saved {len(screenshot_paths)} file(s):")
        for p in screenshot_paths:
            print(Fore.GREEN + f"    → {p}")
    else:
        print(Fore.LIGHTBLACK_EX +
              "  Screenshot: not available "
              "(install 'pillow' and optionally 'pygetwindow' to enable)")

    print(divider)
    print()

    # ── 3. Write to error_log.txt ─────────────────────────────────────────────
    _write_log(
        timestamp        = timestamp,
        severity         = severity,
        location         = info["location"],
        cause            = info["cause"],
        raw_error        = info["raw_error"],
        extra_context    = extra_context,
        screenshot_paths = screenshot_paths,
        tb               = traceback.format_exc(),
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _write_log(
    timestamp, severity, location, cause,
    raw_error, extra_context, screenshot_paths, tb,
):
    os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)

    screenshots_line = (
        "\n".join(f"    {p}" for p in screenshot_paths)
        if screenshot_paths else "    (none)"
    )

    entry = (
        f"\n{'='*60}\n"
        f"TIMESTAMP  : {timestamp}\n"
        f"SEVERITY   : {severity.value}\n"
        f"WHERE      : {location}\n"
        f"WHAT       : {cause}\n"
        + (f"NOTE       : {extra_context}\n" if extra_context else "")
        + f"RAW ERROR  : {raw_error}\n"
        f"SCREENSHOTS:\n{screenshots_line}\n"
        f"TRACEBACK  :\n{tb.strip()}\n"
    )

    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass  # Never let the error reporter crash the app
