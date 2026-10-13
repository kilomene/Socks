# error_handler/

This folder is the error reporting system for SOCKS5-Chro5-killswitch.

## What it does

Every time something goes wrong anywhere in the program, this system will:

1. **Classify the severity** — MINOR, MAJOR, or CRITICAL
2. **Print a plain-English report** in the terminal (colour-coded)
3. **Take a screenshot** of the screen (and Chrome window if open) and save it here
4. **Write a full record** to `error_log.txt`

---

## Severity levels

| Level    | Colour        | Meaning                                                              |
|----------|---------------|----------------------------------------------------------------------|
| MINOR    | 🟡 Yellow     | Something small went wrong. The app may keep running.               |
| MAJOR    | 🔴 Light red  | A key feature failed. You likely need to take action.               |
| CRITICAL | 💀 Red        | Security or session integrity is at risk. The app will stop.        |

---

## Folder structure

```
error_handler/
  __init__.py            ← imports report_error for use anywhere
  error_reporter.py      ← main entry point: call report_error(e, source_module="...")
  error_classifier.py    ← maps exceptions to severity + plain English cause
  screenshot_capture.py  ← takes screenshots and saves them here
  screenshots/           ← created automatically; screenshots saved here
  error_log.txt          ← created automatically; full error history
  README.md              ← this file
```

---

## How to use it in any module

```python
from error_handler import report_error

try:
    some_risky_operation()
except Exception as e:
    report_error(e, source_module="local_proxy", chrome_proc=chrome_proc)
```

- `source_module` — the name of the file where the error happened (without .py)
- `chrome_proc`   — pass the Chrome Popen handle if you have it (enables Chrome-window screenshot)
- `extra_context` — optional extra plain-English note, e.g. `"Happened during proxy startup"`

---

## Requirements

Screenshots require **Pillow**:

```
pip install pillow
```

For Chrome-window-only screenshots (Windows), also install:

```
pip install pygetwindow
```

These are optional — if not installed, everything still works, just without screenshots.
